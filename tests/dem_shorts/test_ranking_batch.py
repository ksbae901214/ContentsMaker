"""T103: 주간 랭킹 배치 테스트 (FR-008, FR-009).

검증 시나리오:
1. 5개 소스 점수를 mock → ranking_batch가 가중합 계산
2. z-score → sigmoid 정규화 결과 0~100 범위
3. 상위 N(=20) 명 Politician.tier='auto' 자동 등록
4. 기존 auto 등급이 2주 연속 상위 20에서 빠지면 pending → 삭제
5. WeeklyRanking upsert (같은 week_start + politician_id는 중복 삽입 안 됨)
6. 전주 대비 +15 이상 상승 시 tag='rising'
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

import pytest

from src.dem_shorts.db import get_connection, init_db


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "state.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def _add_candidate(conn, name, tier="pending", category="female"):
    from datetime import datetime

    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO politicians
          (name, party, role, bio, tone_guide, tier, category, is_active,
           added_at, updated_at)
        VALUES (?, '더불어민주당', '', '', '', ?, ?, 1, ?, ?)
        """,
        (name, tier, category, now, now),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM politicians WHERE name=?", (name,)
    ).fetchone()[0]


# ---------------------------------------------------------------------------
# 가중 합산 + 정규화
# ---------------------------------------------------------------------------


def test_combine_source_scores_weighted_sum():
    """R-06: 5개 소스 점수를 RANKING_SOURCE_WEIGHTS로 가중 합산."""
    from src.dem_shorts.ranking_batch import combine_source_scores

    # naver_news=0.30, google_trends=0.25, youtube_metrics=0.25,
    # wikipedia_pageviews=0.10, naver_datalab=0.10
    raw = {
        "naver_news": 100,
        "google_trends": 60,
        "youtube_metrics": 40,
        "wikipedia_pageviews": 20,
        "naver_datalab": 10,
    }
    result = combine_source_scores(raw)
    # 30 + 15 + 10 + 2 + 1 = 58
    assert result == pytest.approx(58.0, rel=1e-3)


def test_combine_source_scores_missing_source_treated_as_zero():
    from src.dem_shorts.ranking_batch import combine_source_scores

    raw = {"naver_news": 100}
    result = combine_source_scores(raw)
    # 100 * 0.30 = 30
    assert result == pytest.approx(30.0)


def test_normalize_scores_to_0_100():
    """z-score → sigmoid → 0~100 범위 정규화."""
    from src.dem_shorts.ranking_batch import normalize_scores

    raw = {1: 10.0, 2: 50.0, 3: 100.0, 4: 0.0, 5: 30.0}
    normalized = normalize_scores(raw)
    assert len(normalized) == 5
    for score in normalized.values():
        assert 0.0 <= score <= 100.0
    # 최댓값(100)이 최솟값(0)보다 정규화 점수가 높아야 함
    assert normalized[3] > normalized[4]


def test_normalize_scores_all_equal():
    """모두 같은 값이면 50점으로 균등 분포."""
    from src.dem_shorts.ranking_batch import normalize_scores

    raw = {1: 50.0, 2: 50.0, 3: 50.0}
    normalized = normalize_scores(raw)
    for score in normalized.values():
        assert score == pytest.approx(50.0, abs=1.0)


# ---------------------------------------------------------------------------
# 전체 배치 실행
# ---------------------------------------------------------------------------


def test_run_ranking_batch_upserts_weekly_rankings(db):
    """상위 N명 WeeklyRanking에 저장 + politician.tier='auto'."""
    from src.dem_shorts.ranking_batch import run_ranking_batch

    # 5명 후보 등록 (pending)
    ids = {name: _add_candidate(db, name) for name in ("A", "B", "C", "D", "E")}

    week_start = date(2026, 4, 13)

    # 각 소스가 dict[politician_name → raw_score]를 반환하도록 stub
    def fake_fetch_all(_conn, _names):
        return {
            "naver_news": {"A": 100, "B": 80, "C": 60, "D": 40, "E": 20},
            "google_trends": {"A": 90, "B": 70, "C": 50, "D": 30, "E": 10},
            "youtube_metrics": {"A": 80, "B": 60, "C": 40, "D": 20, "E": 5},
            "wikipedia_pageviews": {"A": 70, "B": 50, "C": 30, "D": 10, "E": 0},
            "naver_datalab": {"A": 60, "B": 40, "C": 20, "D": 5, "E": 0},
        }

    with mock.patch(
        "src.dem_shorts.ranking_batch.fetch_all_sources", side_effect=fake_fetch_all
    ):
        result = run_ranking_batch(
            db, week_start=week_start, top_n=3
        )

    # 상위 3명이 auto로 전환
    assert result["auto_updated"] == 3
    assert result["total_inserted"] == 5  # 전원 저장 (순위만 다름)

    rows = db.execute(
        "SELECT name, tier FROM politicians WHERE name IN ('A','B','C','D','E')"
    ).fetchall()
    tier_map = {r["name"]: r["tier"] for r in rows}
    # A, B, C가 상위 3 → auto
    assert tier_map["A"] == "auto"
    assert tier_map["B"] == "auto"
    assert tier_map["C"] == "auto"
    # 나머지는 pending 유지
    assert tier_map["D"] == "pending"
    assert tier_map["E"] == "pending"


def test_run_ranking_batch_is_idempotent(db):
    """동일 week_start로 재실행 시 UNIQUE 위반 없이 upsert."""
    from src.dem_shorts.ranking_batch import run_ranking_batch

    _add_candidate(db, "A")
    _add_candidate(db, "B")
    week_start = date(2026, 4, 13)

    fake_data = {
        "naver_news": {"A": 100, "B": 50},
        "google_trends": {"A": 100, "B": 50},
        "youtube_metrics": {"A": 100, "B": 50},
        "wikipedia_pageviews": {"A": 100, "B": 50},
        "naver_datalab": {"A": 100, "B": 50},
    }
    with mock.patch(
        "src.dem_shorts.ranking_batch.fetch_all_sources", return_value=fake_data
    ):
        run_ranking_batch(db, week_start=week_start, top_n=2)
        # 두 번째 실행 (재시도 시나리오)
        run_ranking_batch(db, week_start=week_start, top_n=2)

    # 중복 삽입 없이 2개만 존재
    count = db.execute(
        "SELECT COUNT(*) FROM weekly_rankings WHERE week_start=?",
        (week_start.isoformat(),),
    ).fetchone()[0]
    assert count == 2


def test_run_ranking_batch_removes_stale_auto_after_two_weeks(db):
    """이전에 auto였던 정치인이 2주 연속 상위 20에서 빠지면 pending → 삭제."""
    from src.dem_shorts.ranking_batch import run_ranking_batch

    _add_candidate(db, "A", tier="auto")  # 기존 auto
    _add_candidate(db, "B", tier="pending")

    week1 = date(2026, 4, 6)  # 지난주
    week2 = date(2026, 4, 13)  # 이번주

    fake_data_week1 = {
        "naver_news": {"A": 0, "B": 100},  # A가 빠짐
        "google_trends": {"A": 0, "B": 100},
        "youtube_metrics": {"A": 0, "B": 100},
        "wikipedia_pageviews": {"A": 0, "B": 100},
        "naver_datalab": {"A": 0, "B": 100},
    }
    fake_data_week2 = dict(fake_data_week1)  # 다시 2주차 빠짐

    with mock.patch(
        "src.dem_shorts.ranking_batch.fetch_all_sources",
        side_effect=[fake_data_week1, fake_data_week2],
    ):
        # week1: A는 하위라 pending 강등 예정
        run_ranking_batch(db, week_start=week1, top_n=1)
        # 1주 뒤 check
        tier1 = db.execute(
            "SELECT tier FROM politicians WHERE name='A'"
        ).fetchone()[0]
        # 1주만 빠진 상태 — 아직 삭제 안 됨
        assert tier1 in ("pending", "auto")

        # week2 실행 → A가 2주 연속 빠짐 → 삭제
        run_ranking_batch(db, week_start=week2, top_n=1)

    # A는 삭제되어야 함
    existing = db.execute(
        "SELECT 1 FROM politicians WHERE name='A'"
    ).fetchone()
    assert existing is None, "A should be deleted after 2 consecutive weeks out"


def test_run_ranking_batch_tags_rising_when_delta_over_15(db):
    """전주 대비 +15 점 이상 상승 시 tag='rising'."""
    from src.dem_shorts.ranking_batch import run_ranking_batch

    _add_candidate(db, "X")

    week1 = date(2026, 4, 6)
    week2 = date(2026, 4, 13)

    # week1은 하위
    data_week1 = {
        "naver_news": {"X": 10},
        "google_trends": {"X": 10},
        "youtube_metrics": {"X": 10},
        "wikipedia_pageviews": {"X": 10},
        "naver_datalab": {"X": 10},
    }
    # week2는 폭발적 상승
    data_week2 = {
        "naver_news": {"X": 100},
        "google_trends": {"X": 100},
        "youtube_metrics": {"X": 100},
        "wikipedia_pageviews": {"X": 100},
        "naver_datalab": {"X": 100},
    }
    with mock.patch(
        "src.dem_shorts.ranking_batch.fetch_all_sources",
        side_effect=[data_week1, data_week2],
    ):
        run_ranking_batch(db, week_start=week1, top_n=1)
        run_ranking_batch(db, week_start=week2, top_n=1)

    row = db.execute(
        """
        SELECT tag, delta_vs_prev_week FROM weekly_rankings
        WHERE week_start=? AND politician_id=(SELECT id FROM politicians WHERE name='X')
        """,
        (week2.isoformat(),),
    ).fetchone()
    assert row is not None
    assert row["delta_vs_prev_week"] >= 15.0
    assert row["tag"] == "rising"


def test_run_ranking_batch_tags_new_for_first_appearance(db):
    """처음 등장한 정치인은 tag='new'."""
    from src.dem_shorts.ranking_batch import run_ranking_batch

    _add_candidate(db, "Newbie")

    week1 = date(2026, 4, 13)

    data = {
        "naver_news": {"Newbie": 50},
        "google_trends": {"Newbie": 50},
        "youtube_metrics": {"Newbie": 50},
        "wikipedia_pageviews": {"Newbie": 50},
        "naver_datalab": {"Newbie": 50},
    }
    with mock.patch(
        "src.dem_shorts.ranking_batch.fetch_all_sources", return_value=data
    ):
        run_ranking_batch(db, week_start=week1, top_n=1)

    row = db.execute(
        "SELECT tag FROM weekly_rankings WHERE week_start=?",
        (week1.isoformat(),),
    ).fetchone()
    assert row["tag"] == "new"


def test_run_ranking_batch_dry_run_does_not_write(db):
    """dry_run=True일 때 DB 변경 없음."""
    from src.dem_shorts.ranking_batch import run_ranking_batch

    _add_candidate(db, "A")
    data = {
        "naver_news": {"A": 100},
        "google_trends": {"A": 100},
        "youtube_metrics": {"A": 100},
        "wikipedia_pageviews": {"A": 100},
        "naver_datalab": {"A": 100},
    }
    with mock.patch(
        "src.dem_shorts.ranking_batch.fetch_all_sources", return_value=data
    ):
        result = run_ranking_batch(
            db, week_start=date(2026, 4, 13), top_n=1, dry_run=True
        )

    count = db.execute("SELECT COUNT(*) FROM weekly_rankings").fetchone()[0]
    assert count == 0
    tier = db.execute(
        "SELECT tier FROM politicians WHERE name='A'"
    ).fetchone()[0]
    assert tier == "pending"  # unchanged
    assert result["dry_run"] is True


def test_run_ranking_batch_default_week_start_is_monday():
    """week_start=None 시 해당 주의 월요일 계산."""
    from src.dem_shorts.ranking_batch import resolve_week_start

    # 2026-04-16는 목요일 → 같은 주 월요일 = 2026-04-13
    assert resolve_week_start(date(2026, 4, 16)) == date(2026, 4, 13)
    # 월요일 당일은 그대로
    assert resolve_week_start(date(2026, 4, 13)) == date(2026, 4, 13)
    # 일요일은 다음주 월요일이 아니라 해당 주(지난주) 월요일
    assert resolve_week_start(date(2026, 4, 19)) == date(2026, 4, 13)
