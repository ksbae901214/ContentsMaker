"""SC-003 발언자 식별 정확도 계산 (T130).

운영자가 라벨한 ground-truth(`sc003_ground_truth.json`) 를 읽어 SQLite
`speech_segments` 의 자동 식별 결과와 비교한다.

매칭 규칙:
- ground-truth turn (gt_start, gt_end) 와 시간이 겹치는 모든 speech_segments
  중 가장 오래 겹치는 1개를 매칭 후보로 선택한다.
- 매칭 후보의 confidence ≥ SPEAKER_CONFIDENCE_MIN(0.7) 이고 politician_id
  가 expected 와 일치하면 `correct`.
- 후보 없음 / confidence 미달 → expected가 null 이면 `correct_unidentified`,
  아니면 `missed`.
- 후보의 politician 이 expected 와 다르면 `mismatched`.

정확도 = (correct + correct_unidentified) / 전체 turn 수.
SC-003 통과 기준: ≥ 0.80.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.dem_shorts.config import SPEAKER_CONFIDENCE_MIN


@dataclass(frozen=True)
class TurnComparison:
    video_id: str
    gt_start: float
    gt_end: float
    expected: str | None
    matched_politician: str | None
    matched_confidence: float | None
    verdict: str  # "correct" | "correct_unidentified" | "missed" | "mismatched"


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _fetch_segments(conn: sqlite3.Connection, video_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT ss.start_sec, ss.end_sec, ss.confidence, ss.politician_id, p.name
          FROM speech_segments ss
          LEFT JOIN politicians p ON p.id = ss.politician_id
         WHERE ss.source_video_id = ?
        """,
        (video_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def compare_turn(
    *,
    video_id: str,
    gt_start: float,
    gt_end: float,
    expected: str | None,
    segments: list[dict],
    confidence_min: float = SPEAKER_CONFIDENCE_MIN,
) -> TurnComparison:
    """단일 ground-truth turn 을 자동 식별 결과와 비교."""
    candidates = [
        (s, _overlap(gt_start, gt_end, s["start_sec"], s["end_sec"]))
        for s in segments
    ]
    candidates = [(s, ov) for s, ov in candidates if ov > 0.0]

    if not candidates:
        verdict = "correct_unidentified" if expected is None else "missed"
        return TurnComparison(
            video_id=video_id,
            gt_start=gt_start,
            gt_end=gt_end,
            expected=expected,
            matched_politician=None,
            matched_confidence=None,
            verdict=verdict,
        )

    best_seg, _ = max(candidates, key=lambda t: t[1])
    confidence = float(best_seg.get("confidence") or 0.0)
    matched = best_seg.get("name")

    if confidence < confidence_min:
        # 신뢰도 미달 — 식별 안된 것으로 간주
        verdict = "correct_unidentified" if expected is None else "missed"
        return TurnComparison(
            video_id=video_id,
            gt_start=gt_start,
            gt_end=gt_end,
            expected=expected,
            matched_politician=matched,
            matched_confidence=confidence,
            verdict=verdict,
        )

    if expected is None:
        # 라벨은 미식별인데 자동이 식별함 → 오탐
        verdict = "mismatched"
    elif matched == expected:
        verdict = "correct"
    else:
        verdict = "mismatched"

    return TurnComparison(
        video_id=video_id,
        gt_start=gt_start,
        gt_end=gt_end,
        expected=expected,
        matched_politician=matched,
        matched_confidence=confidence,
        verdict=verdict,
    )


def compute_accuracy(
    conn: sqlite3.Connection,
    ground_truth: dict,
    *,
    confidence_min: float = SPEAKER_CONFIDENCE_MIN,
) -> dict:
    """ground_truth 전체에 대해 정확도 산출.

    Returns:
        {
            "total_turns": int,
            "correct": int,
            "correct_unidentified": int,
            "missed": int,
            "mismatched": int,
            "accuracy": float,            # (correct + correct_unidentified) / total
            "sc_003_pass": bool,          # accuracy ≥ 0.80
            "comparisons": list[dict],
        }
    """
    comparisons: list[TurnComparison] = []
    for video in ground_truth.get("videos", []):
        vid = video.get("video_id")
        if not vid or vid.startswith("EXAMPLE_"):
            continue
        segs = _fetch_segments(conn, vid)
        for turn in video.get("turns", []):
            comp = compare_turn(
                video_id=vid,
                gt_start=float(turn["start_sec"]),
                gt_end=float(turn["end_sec"]),
                expected=turn.get("expected_politician_name"),
                segments=segs,
                confidence_min=confidence_min,
            )
            comparisons.append(comp)

    total = len(comparisons)
    counts = {"correct": 0, "correct_unidentified": 0, "missed": 0, "mismatched": 0}
    for c in comparisons:
        counts[c.verdict] = counts.get(c.verdict, 0) + 1

    accurate = counts["correct"] + counts["correct_unidentified"]
    acc = (accurate / total) if total else 0.0

    return {
        "total_turns": total,
        **counts,
        "accuracy": round(acc, 4),
        "sc_003_pass": acc >= 0.80 and total > 0,
        "comparisons": [
            {
                "video_id": c.video_id,
                "gt_start": c.gt_start,
                "gt_end": c.gt_end,
                "expected": c.expected,
                "matched_politician": c.matched_politician,
                "matched_confidence": c.matched_confidence,
                "verdict": c.verdict,
            }
            for c in comparisons
        ],
    }


def load_ground_truth(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
