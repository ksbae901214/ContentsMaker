"""Transcript-aligned scene cutter (content-aware).

natv_clip 모드에서 기존 코드는 TTS 길이에 **비례**해 원본 영상을 잘랐음.
결과적으로 씬에서 자막(voice_text)이 말하는 내용과 화면에 보이는 원본
발화 구간이 어긋나는 문제 ("자막과 영상내용 이질감") 가 발생.

이 모듈은 각 씬의 voice_text 를 원본 transcript(자막+timestamp) 와
퍼지 매칭해 실제 말하고 있는 구간의 timestamp 를 반환한다.
매칭이 임계값 미만이면 비례 cut 으로 폴백한다.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# 매칭 점수 최소 임계값. 0.4 미만이면 "내용이 많이 다르다" 로 판단하고
# 비례 cut 폴백을 사용한다.
_MIN_SIMILARITY = 0.4

# 여러 연속 segment 를 합쳐서 매칭할 때 최대 몇 개까지 합칠지.
_DEFAULT_MAX_MERGE = 4


def _normalize(text: str) -> str:
    """매칭용 정규화 — 한글/영숫자만 남기고 공백 정리."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w가-힣]+", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def _similarity(a: str, b: str) -> float:
    """difflib.SequenceMatcher 기반 유사도 (0~1)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def align_scene_to_transcript(
    voice_text: str,
    transcript: list[dict],
    clip_start: float,
    clip_end: float,
    *,
    max_merge: int = _DEFAULT_MAX_MERGE,
    min_similarity: float = _MIN_SIMILARITY,
) -> tuple[float, float] | None:
    """voice_text 와 가장 잘 맞는 transcript 구간의 (start, end) 반환.

    clip_start ~ clip_end 범위 안 segment 만 후보로 사용.
    연속된 최대 ``max_merge`` 개 segment 를 합쳐 비교하며, 유사도가
    ``min_similarity`` 이상일 때만 반환. 아니면 None.
    """
    voice_norm = _normalize(voice_text)
    if not voice_norm or len(voice_norm) < 2:
        return None
    if not transcript:
        return None

    # Clip window 안에 포함되는 segment 만 필터 (경계 ±1s 여유)
    window = [
        s for s in transcript
        if s.get("end", 0.0) >= clip_start - 1.0
        and s.get("start", 0.0) <= clip_end + 1.0
    ]
    if not window:
        return None

    best: tuple[float, float] | None = None
    best_score = 0.0

    for i in range(len(window)):
        combined = ""
        for j in range(i, min(i + max_merge, len(window))):
            combined = (combined + " " + window[j].get("text", "")).strip()
            combined_norm = _normalize(combined)
            if not combined_norm:
                continue
            score = _similarity(voice_norm, combined_norm)
            if score > best_score:
                best_score = score
                start = max(window[i].get("start", clip_start), clip_start)
                end = min(window[j].get("end", clip_end), clip_end)
                best = (start, end)

    if best is None or best_score < min_similarity:
        return None
    return best


def align_scenes_to_transcript(
    scenes: list[dict],
    transcript: list[dict],
    clip_start: float,
    clip_end: float,
    *,
    min_similarity: float = _MIN_SIMILARITY,
) -> list[dict]:
    """전체 씬 목록을 transcript 기준으로 정렬.

    각 scene dict 는 최소한 ``scene_id``, ``voice_text``, ``start_ms``,
    ``end_ms`` 키를 가져야 한다. 반환 리스트 순서는 입력 순서 유지.
    각 원소: ``{"scene_id", "start_sec", "end_sec", "source"}``.
    source 는 ``"transcript"`` (매칭 성공) 또는 ``"proportional"`` (폴백).

    결과는 monotonic — 뒤 씬의 start 가 앞 씬의 start 보다 작아지지
    않도록 보정한다 (매칭 중 순서가 섞인 경우 다음 씬은 이전 씬
    end 이후로 clamp).
    """
    clip_duration = max(clip_end - clip_start, 0.0)
    total_ms = max((s.get("end_ms", 0) for s in scenes), default=0) or 1

    result: list[dict] = []
    cursor = clip_start  # 단조 증가 보장용

    for s in scenes:
        voice = s.get("voice_text") or ""
        sid = s.get("scene_id")

        aligned = align_scene_to_transcript(
            voice_text=voice,
            transcript=transcript,
            clip_start=clip_start,
            clip_end=clip_end,
            min_similarity=min_similarity,
        )

        if aligned is not None:
            start_sec, end_sec = aligned
            source = "transcript"
        else:
            # 비례 폴백
            start_ms = s.get("start_ms", 0)
            end_ms = s.get("end_ms", start_ms)
            start_sec = clip_start + (start_ms / total_ms) * clip_duration
            end_sec = clip_start + (end_ms / total_ms) * clip_duration
            source = "proportional"

        # 단조 증가 보장 — 뒤 씬이 앞 씬보다 앞서지 않도록
        if start_sec < cursor:
            shift = cursor - start_sec
            start_sec += shift
            end_sec += shift
        # 범위 clamp
        start_sec = max(clip_start, min(start_sec, clip_end))
        end_sec = max(start_sec + 0.1, min(end_sec, clip_end))
        cursor = start_sec

        result.append({
            "scene_id": sid,
            "start_sec": round(start_sec, 3),
            "end_sec": round(end_sec, 3),
            "source": source,
        })

    return result
