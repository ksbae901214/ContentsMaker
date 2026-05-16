"""T048: 발언자 식별 — diarization 클러스터 × 호명 패턴 결합.

Pipeline:
  1. transcript 세그먼트와 diarization 클러스터를 시간축으로 결합
  2. 각 발언 구간에서 호명 패턴 추출
  3. Whitelist 매칭
  4. confidence = 호명 빈도 / 클러스터 길이
  5. speech_segments 테이블 upsert

Research: research.md R-04 하이브리드 전략. MVP는 호명 패턴만 사용.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Iterable

from src.dem_shorts.config import SPEAKER_CONFIDENCE_MIN
from src.dem_shorts.diarization import DiarizationTurn, load_diarization
from src.dem_shorts.scoring import (
    RecommendationInputs,
    calculate_recommendation_score,
    detect_issue_keywords,
    detect_profanity,
)
from src.dem_shorts.speaker_id.name_patterns import (
    extract_named_speakers,
    match_whitelist,
)
from src.dem_shorts.stt import TranscriptSegment, load_transcript

logger = logging.getLogger(__name__)

# 상위 Whitelist 등급 (추천 점수 계산용)
_TOP_TIERS = {"pinned", "auto"}


def _fetch_whitelist(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, tier, category, is_active FROM politicians"
    ).fetchall()
    return [dict(r) for r in rows]


def _merge_turns_with_transcript(
    turns: list[DiarizationTurn],
    transcript: list[TranscriptSegment],
) -> list[dict]:
    """각 diarization 턴에 해당 시간 범위의 transcript 텍스트를 병합."""
    merged = []
    for turn in turns:
        texts = [
            s.text
            for s in transcript
            if s.start_sec < turn.end_sec and s.end_sec > turn.start_sec
        ]
        merged.append(
            {
                "start_sec": turn.start_sec,
                "end_sec": turn.end_sec,
                "cluster": turn.speaker_cluster,
                "text": " ".join(texts).strip(),
            }
        )
    return merged


def _estimate_solo(turn_index: int, turns: list[dict]) -> bool:
    """단독 발언 여부: 직전·직후 15초 내 다른 클러스터가 없으면 solo."""
    me = turns[turn_index]
    start = me["start_sec"]
    end = me["end_sec"]
    buffer = 15.0

    for i, t in enumerate(turns):
        if i == turn_index:
            continue
        if t["cluster"] == me["cluster"]:
            continue
        # Overlaps or near-adjacent in different cluster
        if t["end_sec"] >= start - buffer and t["start_sec"] <= end + buffer:
            return False
    return True


def identify_speakers(
    conn,
    video_id: str,
    *,
    whitelist: Iterable[dict] | None = None,
    top_whitelist_ids: set[int] | None = None,
) -> int:
    """video_id의 발언자를 식별하여 speech_segments upsert.

    Returns: 저장된 segment 수.
    """
    transcript = load_transcript(video_id)
    turns = load_diarization(video_id)
    merged = _merge_turns_with_transcript(turns, transcript)

    wl = list(whitelist) if whitelist is not None else _fetch_whitelist(conn)
    if top_whitelist_ids is None:
        top_whitelist_ids = {p["id"] for p in wl if p.get("tier") in _TOP_TIERS}

    # 클러스터별 이름 빈도 집계
    cluster_name_counts: dict[str, dict[str, int]] = {}
    for m in merged:
        names = extract_named_speakers(m["text"])
        matched = match_whitelist(names, wl)
        counts = cluster_name_counts.setdefault(m["cluster"], {})
        for name in matched:
            counts[name] = counts.get(name, 0) + 1

    # 클러스터별 가장 자주 호명된 이름을 대표로
    cluster_primary: dict[str, tuple[str, int]] = {}
    for cluster, counts in cluster_name_counts.items():
        if not counts:
            continue
        name, cnt = max(counts.items(), key=lambda x: x[1])
        cluster_primary[cluster] = (name, cnt)

    name_to_id: dict[str, int] = {p["name"]: p["id"] for p in wl}

    # 기존 이 영상의 segment 삭제 (idempotent upsert)
    conn.execute("DELETE FROM speech_segments WHERE source_video_id = ?", (video_id,))

    saved = 0
    for idx, m in enumerate(merged):
        cluster = m["cluster"]
        text = m["text"]
        primary = cluster_primary.get(cluster)

        if primary:
            name, cnt = primary
            # confidence = 해당 이름 호명 빈도 / (전체 호명 + 1)
            total_mentions = sum(cluster_name_counts[cluster].values())
            confidence = min(1.0, cnt / (total_mentions + 1))
            politician_id = name_to_id.get(name) if confidence >= SPEAKER_CONFIDENCE_MIN else None
        else:
            confidence = 0.0
            politician_id = None

        issue_kws = detect_issue_keywords(text)
        has_prof = detect_profanity(text)
        emotion = _estimate_emotion_strength(text)
        is_solo = _estimate_solo(idx, merged)

        rec_score = calculate_recommendation_score(
            RecommendationInputs(
                is_top_whitelist=politician_id in top_whitelist_ids if politician_id else False,
                duration_sec=m["end_sec"] - m["start_sec"],
                emotion_strength=emotion,
                issue_keyword_count=len(issue_kws),
                is_solo=is_solo,
                has_profanity=has_prof,
            )
        )

        conn.execute(
            """
            INSERT INTO speech_segments
              (source_video_id, start_sec, end_sec, politician_id, confidence,
               stt_text, recommendation_score, emotion_strength,
               issue_keywords, is_solo, has_profanity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                m["start_sec"],
                m["end_sec"],
                politician_id,
                confidence,
                text,
                rec_score,
                emotion,
                json.dumps(issue_kws, ensure_ascii=False),
                1 if is_solo else 0,
                1 if has_prof else 0,
            ),
        )
        saved += 1

    # Update SourceVideo diarization_status
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE source_videos
        SET diarization_status = 'done', status = 'ready', updated_at = ?
        WHERE video_id = ?
        """,
        (now_iso, video_id),
    )
    conn.commit()
    return saved


def _estimate_emotion_strength(text: str) -> float:
    """문장 단위 !·? 밀도 + 강조 표현으로 0~1 추정.

    실제 볼륨 분석(R-04)은 Sprint 2+. MVP는 텍스트 기반 근사.
    """
    if not text:
        return 0.0
    punct = text.count("!") + text.count("?")
    emph_markers = sum(text.count(w) for w in ("절대", "반드시", "분명히", "어떻게"))
    length = max(len(text), 1)
    raw = (punct * 5 + emph_markers * 3) / length
    return min(1.0, raw)
