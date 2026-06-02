"""T130: SC-003 발언자 식별 정확도 비교 로직 단위 테스트.

비교 알고리즘만 검증 — 실제 라벨 데이터셋은 운영자 측정 시 별도 준비.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.dem_shorts.db import get_connection, init_db
from src.dem_shorts.sc003_comparator import (
    compare_turn,
    compute_accuracy,
)


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "sc003.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def _add_source_video(conn, vid):
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO source_videos (video_id, title, published_at, duration_sec, "
        "session_type, status, created_at, updated_at) "
        "VALUES (?, 't', ?, 600, 'plenary', 'ready', ?, ?)",
        (vid, now, now, now),
    )
    conn.commit()


def _add_segment(conn, vid, start, end, *, name=None, confidence=0.0):
    pid = None
    if name:
        row = conn.execute("SELECT id FROM politicians WHERE name=?", (name,)).fetchone()
        if row:
            pid = row[0]
    conn.execute(
        "INSERT INTO speech_segments (source_video_id, start_sec, end_sec, "
        "politician_id, confidence, stt_text, recommendation_score) "
        "VALUES (?, ?, ?, ?, ?, '', 0)",
        (vid, start, end, pid, confidence),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# compare_turn (in-memory unit tests, no DB)
# ---------------------------------------------------------------------------


def test_compare_turn_correct():
    segs = [{"start_sec": 10, "end_sec": 50, "confidence": 0.9, "name": "이재명"}]
    res = compare_turn(
        video_id="v1", gt_start=12, gt_end=48,
        expected="이재명", segments=segs,
    )
    assert res.verdict == "correct"
    assert res.matched_politician == "이재명"


def test_compare_turn_mismatched():
    segs = [{"start_sec": 0, "end_sec": 60, "confidence": 0.9, "name": "조국"}]
    res = compare_turn(
        video_id="v1", gt_start=10, gt_end=40,
        expected="이재명", segments=segs,
    )
    assert res.verdict == "mismatched"


def test_compare_turn_missed_when_no_overlap():
    segs = [{"start_sec": 100, "end_sec": 200, "confidence": 0.9, "name": "이재명"}]
    res = compare_turn(
        video_id="v1", gt_start=10, gt_end=40,
        expected="이재명", segments=segs,
    )
    assert res.verdict == "missed"


def test_compare_turn_missed_when_low_confidence():
    """confidence < 0.7 면 미식별 처리 → expected 가 인물이면 missed."""
    segs = [{"start_sec": 0, "end_sec": 60, "confidence": 0.5, "name": "이재명"}]
    res = compare_turn(
        video_id="v1", gt_start=10, gt_end=40,
        expected="이재명", segments=segs,
    )
    assert res.verdict == "missed"


def test_compare_turn_correct_unidentified_when_expected_null():
    """expected=None 이고 자동도 식별 못하면 correct_unidentified."""
    segs = [{"start_sec": 0, "end_sec": 60, "confidence": 0.5, "name": None}]
    res = compare_turn(
        video_id="v1", gt_start=10, gt_end=40,
        expected=None, segments=segs,
    )
    assert res.verdict == "correct_unidentified"


def test_compare_turn_mismatched_when_unexpected_id():
    """expected=None 인데 자동이 식별하면 오탐 → mismatched."""
    segs = [{"start_sec": 0, "end_sec": 60, "confidence": 0.9, "name": "이재명"}]
    res = compare_turn(
        video_id="v1", gt_start=10, gt_end=40,
        expected=None, segments=segs,
    )
    assert res.verdict == "mismatched"


def test_compare_turn_picks_max_overlap_candidate():
    """겹침이 가장 긴 후보를 선택."""
    segs = [
        {"start_sec": 0, "end_sec": 20, "confidence": 0.9, "name": "조국"},     # 5초 겹침
        {"start_sec": 15, "end_sec": 60, "confidence": 0.9, "name": "이재명"},  # 25초 겹침
    ]
    res = compare_turn(
        video_id="v1", gt_start=15, gt_end=40,
        expected="이재명", segments=segs,
    )
    assert res.verdict == "correct"
    assert res.matched_politician == "이재명"


# ---------------------------------------------------------------------------
# compute_accuracy (DB 통합)
# ---------------------------------------------------------------------------


def test_compute_accuracy_skips_example_video_ids(db):
    """video_id 가 EXAMPLE_ 로 시작하면 (템플릿) 측정에서 제외."""
    gt = {
        "videos": [
            {
                "video_id": "EXAMPLE_VIDEO_ID_1",
                "turns": [{"start_sec": 0, "end_sec": 60, "expected_politician_name": "이재명"}],
            },
        ],
    }
    result = compute_accuracy(db, gt)
    assert result["total_turns"] == 0
    assert result["sc_003_pass"] is False  # total=0 도 fail


def test_compute_accuracy_full_pass(db):
    _add_source_video(db, "v1")
    _add_segment(db, "v1", 12, 48, name="이재명", confidence=0.95)

    gt = {
        "videos": [
            {
                "video_id": "v1",
                "turns": [
                    {"start_sec": 12, "end_sec": 48, "expected_politician_name": "이재명"},
                ],
            },
        ],
    }
    result = compute_accuracy(db, gt)
    assert result["total_turns"] == 1
    assert result["correct"] == 1
    assert result["accuracy"] == pytest.approx(1.0)
    assert result["sc_003_pass"] is True


def test_compute_accuracy_meets_80_percent_threshold(db):
    """8/10 정확 → 0.80 이상 → SC-003 통과."""
    _add_source_video(db, "v1")
    # 8 정확 + 2 missed
    for i in range(8):
        _add_segment(db, "v1", i * 10, i * 10 + 9, name="이재명", confidence=0.9)
    # nothing for the last 2 turns

    turns = [{"start_sec": i * 10, "end_sec": i * 10 + 9, "expected_politician_name": "이재명"} for i in range(8)]
    turns += [
        {"start_sec": 200, "end_sec": 210, "expected_politician_name": "이재명"},
        {"start_sec": 220, "end_sec": 230, "expected_politician_name": "이재명"},
    ]
    gt = {"videos": [{"video_id": "v1", "turns": turns}]}
    result = compute_accuracy(db, gt)
    assert result["total_turns"] == 10
    assert result["correct"] == 8
    assert result["missed"] == 2
    assert result["accuracy"] == pytest.approx(0.80)
    assert result["sc_003_pass"] is True


def test_compute_accuracy_below_80_percent_fails(db):
    """7/10 정확 → 0.70 → SC-003 미통과."""
    _add_source_video(db, "v1")
    for i in range(7):
        _add_segment(db, "v1", i * 10, i * 10 + 9, name="이재명", confidence=0.9)

    turns = [{"start_sec": i * 10, "end_sec": i * 10 + 9, "expected_politician_name": "이재명"} for i in range(7)]
    turns += [{"start_sec": 200 + i, "end_sec": 210 + i, "expected_politician_name": "이재명"} for i in range(3)]
    gt = {"videos": [{"video_id": "v1", "turns": turns}]}
    result = compute_accuracy(db, gt)
    assert result["accuracy"] == pytest.approx(0.70)
    assert result["sc_003_pass"] is False
