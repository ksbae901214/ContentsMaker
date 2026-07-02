"""감정 모먼트 검출기 (Feature 027).

1순위: Gemini 멀티모달 — Files API로 영상을 업로드해 표정·웃음소리·정적까지
       반영한 검출 (gemini_youtube_transcriber.py와 동일한 업로드 패턴).
2순위(폴백): transcript 텍스트 기반 검출 — 멀티모달 실패/비활성 시.

격리 boundary: src.analyzer.gemini_backend.call_gemini는 read-only import.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from src.analyzer.gemini_backend import call_gemini  # read-only import (격리 boundary)

from src.jpolitics.analyzer.prompts import (
    MOMENT_DETECT_VIDEO_PROMPT,
    build_transcript_prompt,
)
from src.jpolitics.constants import (
    MAX_MOMENT_SECONDS,
    MIN_MOMENT_SECONDS,
)
from src.jpolitics.logger import logger
from src.jpolitics.models.moment import Moment

# Files API 상수 — gemini_youtube_transcriber와 동일 정책
_MODEL = "gemini-2.5-flash"
_MAX_VIDEO_BYTES = 100 * 1024 * 1024
_UPLOAD_POLL_INTERVAL_SEC = 2.0
_UPLOAD_TIMEOUT_SEC = 120.0


class MomentDetectError(Exception):
    """모먼트 검출 실패."""


# 테스트에서 monkeypatch하는 LLM 호출 지점 (transcript 폴백용)
def _call_llm(prompt: str, **kwargs) -> str:
    return call_gemini(prompt, **kwargs)


def _parse_moments_json(text: str) -> list[Moment]:
    """LLM 응답 → Moment 리스트. 코드펜스/잡음 제거 + 항목 단위 관용 파싱.

    유효하지 않은 항목(스키마 위반, 길이 제약 위반)은 버리고 진행한다 —
    한 항목의 오류가 전체 검출을 무효화하지 않도록.
    """
    candidate = text
    m = re.search(r"```(?:json)?\s*(\[.+?\])\s*```", text, re.DOTALL)
    if m:
        candidate = m.group(1)
    else:
        m = re.search(r"\[\s*\{.+\}\s*\]", text, re.DOTALL)
        if m:
            candidate = m.group(0)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise MomentDetectError(f"JSON 파싱 실패: {e} (raw 200자: {text[:200]!r})") from e

    if not isinstance(data, list):
        raise MomentDetectError(f"배열 아님: {type(data).__name__}")

    moments: list[Moment] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.debug("모먼트 %d: dict 아님 — 스킵", i)
            continue
        try:
            moment = Moment.from_dict(item)
        except (ValueError, TypeError) as e:
            logger.warning("모먼트 %d 스키마 위반 — 스킵: %s", i, e)
            continue
        if not (MIN_MOMENT_SECONDS <= moment.duration_sec <= MAX_MOMENT_SECONDS):
            logger.info(
                "모먼트 %d 길이 %.1fs 제약(%.0f~%.0fs) 위반 — 스킵",
                i, moment.duration_sec, MIN_MOMENT_SECONDS, MAX_MOMENT_SECONDS,
            )
            continue
        moments.append(moment)
    return moments


def detect_moments_from_video(video_path: Path, *, max_attempts: int = 2) -> list[Moment]:
    """Gemini 멀티모달로 영상에서 직접 모먼트 검출 (1순위).

    표정·웃음소리·좌중 반응·정적 같은 비언어 신호를 반영할 수 있어
    transcript 폴백보다 laughter/silence 검출 품질이 높다.

    Files API 처리는 간헐적으로 FAILED를 반환하므로(2026-06-11 실측,
    동일 파일 재시도로 성공) 기본 2회 시도한다.

    Raises:
        MomentDetectError: 키 미설정, 파일 초과, 업로드/분석/파싱 실패.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise MomentDetectError("GEMINI_API_KEY 미설정 — 멀티모달 검출 비활성화")
    if not video_path.exists():
        raise MomentDetectError(f"영상 파일 없음: {video_path}")

    size = video_path.stat().st_size
    if size > _MAX_VIDEO_BYTES:
        raise MomentDetectError(
            f"영상이 너무 큽니다 ({size / 1024 / 1024:.1f}MB > 100MB) — transcript 폴백 권장"
        )

    try:
        from google import genai
    except ImportError as e:
        raise MomentDetectError(f"google-genai 미설치: {e}") from e

    client = genai.Client(api_key=api_key)
    last_error: MomentDetectError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _detect_video_once(client, video_path)
        except MomentDetectError as e:
            last_error = e
            if attempt < max_attempts:
                logger.warning(
                    "멀티모달 시도 %d/%d 실패 — 재시도: %s", attempt, max_attempts, e
                )
    raise last_error  # type: ignore[misc]


def _detect_video_once(client, video_path: Path) -> list[Moment]:
    """Files API 업로드 → 분석 → 파싱 1회 시도."""
    try:
        uploaded = client.files.upload(file=str(video_path))
    except Exception as e:
        raise MomentDetectError(f"Files API 업로드 실패: {e}") from e

    started = time.time()
    while getattr(uploaded.state, "name", "") == "PROCESSING":
        if time.time() - started > _UPLOAD_TIMEOUT_SEC:
            raise MomentDetectError("Files API 처리 타임아웃 (120초)")
        time.sleep(_UPLOAD_POLL_INTERVAL_SEC)
        uploaded = client.files.get(name=uploaded.name)

    if getattr(uploaded.state, "name", "") == "FAILED":
        raise MomentDetectError(f"Files API 처리 실패: {uploaded.name}")

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=[uploaded, MOMENT_DETECT_VIDEO_PROMPT],
        )
    except Exception as e:
        raise MomentDetectError(f"Gemini 멀티모달 분석 실패: {e}") from e
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception as e:
            logger.warning("Files API 삭제 실패(무시): %s", e)

    text = (response.text or "").strip()
    if not text:
        raise MomentDetectError("Gemini 빈 응답")

    moments = _parse_moments_json(text)
    if not moments:
        raise MomentDetectError("검출된 모먼트 0개 (멀티모달)")
    logger.info("멀티모달 모먼트 %d개 검출 (%.1fs)", len(moments), time.time() - started)
    return moments


def detect_moments_from_transcript(segments: list[dict]) -> list[Moment]:
    """transcript 텍스트 기반 모먼트 검출 (폴백).

    Args:
        segments: ``[{"start": float, "end": float, "text": str}, ...]``
                  (youtube_downloader.transcribe_video_or_fallback 스키마)
    """
    if not segments:
        raise MomentDetectError("transcript가 비어 있음")

    lines = [
        f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text']}"
        for seg in segments
        if str(seg.get("text", "")).strip()
    ]
    prompt = build_transcript_prompt("\n".join(lines))

    try:
        text = _call_llm(prompt, temperature=0.3)
    except Exception as e:
        raise MomentDetectError(f"transcript 검출 LLM 호출 실패: {e}") from e

    moments = _parse_moments_json(text)
    if not moments:
        raise MomentDetectError("검출된 모먼트 0개 (transcript)")
    logger.info("transcript 모먼트 %d개 검출", len(moments))
    return moments
