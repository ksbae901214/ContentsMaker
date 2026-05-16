"""T096: 선거 가드 테스트 (FR-030, FR-031).

검증 시나리오:
1. D-181 이전은 선거기간 아님
2. D-180 경계 진입 시 선거기간 시작 (대선)
3. D-179 이하는 계속 선거기간
4. D-1, D-0(당일)도 선거기간
5. 선거일 다음날은 선거기간 종료
6. 대선 D-180 / 총선 D-120 구분
7. 배너 플래그 생성 (get_election_status)
8. 두 선거가 겹칠 때 가장 가까운 활성 선거 선택
"""
from __future__ import annotations

from datetime import date
from unittest import mock

import pytest

from src.dem_shorts.compliance.election_dates import (
    ELECTION_DATES,
    ElectionEntry,
    get_upcoming_elections,
)
from src.dem_shorts.compliance.election_guard import (
    ElectionGuardResult,
    get_election_status,
    is_in_election_period,
)

# ---------------------------------------------------------------------------
# 선거 일정 테이블
# ---------------------------------------------------------------------------


def test_election_dates_table_populated():
    """R-10: 하드코딩된 선거 일정 테이블이 존재해야 함."""
    assert len(ELECTION_DATES) >= 2
    types = {e.type for e in ELECTION_DATES}
    assert "presidential_election" in types
    assert "general_election" in types


def test_election_dates_entry_shape():
    """각 엔트리는 type / date / guard_days 를 가져야 함."""
    for e in ELECTION_DATES:
        assert isinstance(e, ElectionEntry)
        assert e.type in ("presidential_election", "general_election")
        assert isinstance(e.date, date)
        assert e.guard_days in (120, 180)


def test_presidential_guard_days_is_180():
    for e in ELECTION_DATES:
        if e.type == "presidential_election":
            assert e.guard_days == 180


def test_general_election_guard_days_is_120():
    for e in ELECTION_DATES:
        if e.type == "general_election":
            assert e.guard_days == 120


# ---------------------------------------------------------------------------
# is_in_election_period: D-181/D-180/D-179 경계
# ---------------------------------------------------------------------------


def _use_election(election_date: date, etype: str, guard_days: int, monkeypatch):
    """테스트 격리를 위해 ELECTION_DATES 를 단일 엔트리로 교체."""
    import src.dem_shorts.compliance.election_dates as ed

    monkeypatch.setattr(
        ed,
        "ELECTION_DATES",
        [ElectionEntry(type=etype, date=election_date, guard_days=guard_days)],
    )


def test_presidential_d181_not_in_election(monkeypatch):
    """대선 D-181 은 선거기간 아님."""
    election = date(2027, 5, 3)
    today = date(2026, 11, 3)  # D-181
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert (election - today).days == 181
    assert is_in_election_period(today=today) is False


def test_presidential_d180_enters_election(monkeypatch):
    """대선 D-180 에 선거기간 진입."""
    election = date(2027, 5, 3)
    today = date(2026, 11, 4)  # D-180
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert (election - today).days == 180
    assert is_in_election_period(today=today) is True


def test_presidential_d179_in_election(monkeypatch):
    """대선 D-179 은 여전히 선거기간."""
    election = date(2027, 5, 3)
    today = date(2026, 11, 5)
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert is_in_election_period(today=today) is True


def test_presidential_d1_in_election(monkeypatch):
    election = date(2027, 5, 3)
    today = date(2027, 5, 2)
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert is_in_election_period(today=today) is True


def test_presidential_d0_in_election(monkeypatch):
    """선거 당일은 선거기간."""
    election = date(2027, 5, 3)
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert is_in_election_period(today=election) is True


def test_presidential_after_election_not_in_period(monkeypatch):
    """선거일 다음날은 선거기간 종료."""
    election = date(2027, 5, 3)
    today = date(2027, 5, 4)
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert is_in_election_period(today=today) is False


# ---------------------------------------------------------------------------
# 총선 D-120 경계
# ---------------------------------------------------------------------------


def test_general_election_d121_not_in_election(monkeypatch):
    """총선 D-121 은 선거기간 아님."""
    election = date(2028, 4, 12)
    today = date(2027, 12, 12)  # D-122
    _use_election(election, "general_election", 120, monkeypatch)
    assert (election - today).days == 122
    assert is_in_election_period(today=today) is False


def test_general_election_d120_enters_election(monkeypatch):
    """총선 D-120 에 선거기간 진입."""
    election = date(2028, 4, 12)
    today = date(2027, 12, 14)  # D-120
    _use_election(election, "general_election", 120, monkeypatch)
    assert (election - today).days == 120
    assert is_in_election_period(today=today) is True


def test_general_d180_not_in_period(monkeypatch):
    """총선 D-180 은 120일 가드 기준으로 아직 선거기간 아님."""
    election = date(2028, 4, 12)
    today = election.replace()
    # today = D-180
    import datetime as _dt

    today = election - _dt.timedelta(days=180)
    _use_election(election, "general_election", 120, monkeypatch)
    assert is_in_election_period(today=today) is False


# ---------------------------------------------------------------------------
# get_election_status: 배너 플래그 + D-day
# ---------------------------------------------------------------------------


def test_status_outside_election_period(monkeypatch):
    election = date(2027, 5, 3)
    today = date(2026, 1, 1)  # 훨씬 이전
    _use_election(election, "presidential_election", 180, monkeypatch)
    result = get_election_status(today=today)
    assert isinstance(result, ElectionGuardResult)
    assert result.in_election_period is False
    assert result.next_election_type == "presidential_election"
    assert result.next_election_date == election
    assert result.days_until == (election - today).days
    assert result.guard_threshold_days == 180


def test_status_inside_election_period(monkeypatch):
    election = date(2027, 5, 3)
    today = date(2026, 11, 4)  # D-180
    _use_election(election, "presidential_election", 180, monkeypatch)
    result = get_election_status(today=today)
    assert result.in_election_period is True
    assert result.days_until == 180


def test_status_picks_nearest_upcoming(monkeypatch):
    """두 개의 선거가 있을 때 가장 가까운(미래의) 선거 선택."""
    import src.dem_shorts.compliance.election_dates as ed

    monkeypatch.setattr(
        ed,
        "ELECTION_DATES",
        [
            ElectionEntry("presidential_election", date(2027, 5, 3), 180),
            ElectionEntry("general_election", date(2028, 4, 12), 120),
        ],
    )
    today = date(2026, 12, 1)
    result = get_election_status(today=today)
    assert result.next_election_type == "presidential_election"
    assert result.next_election_date == date(2027, 5, 3)


def test_status_skips_past_elections(monkeypatch):
    """지난 선거는 건너뛰고 다음 선거 선택."""
    import src.dem_shorts.compliance.election_dates as ed

    monkeypatch.setattr(
        ed,
        "ELECTION_DATES",
        [
            ElectionEntry("presidential_election", date(2027, 5, 3), 180),
            ElectionEntry("general_election", date(2028, 4, 12), 120),
        ],
    )
    today = date(2027, 6, 1)  # 대선 이후
    result = get_election_status(today=today)
    assert result.next_election_type == "general_election"


def test_status_no_future_election(monkeypatch):
    """모든 선거가 지난 경우 → next=None."""
    import src.dem_shorts.compliance.election_dates as ed

    monkeypatch.setattr(
        ed,
        "ELECTION_DATES",
        [ElectionEntry("general_election", date(2020, 4, 15), 120)],
    )
    today = date(2030, 1, 1)
    result = get_election_status(today=today)
    assert result.in_election_period is False
    assert result.next_election_type is None
    assert result.next_election_date is None
    assert result.days_until is None


# ---------------------------------------------------------------------------
# get_upcoming_elections
# ---------------------------------------------------------------------------


def test_get_upcoming_elections_sorted(monkeypatch):
    import src.dem_shorts.compliance.election_dates as ed

    monkeypatch.setattr(
        ed,
        "ELECTION_DATES",
        [
            ElectionEntry("general_election", date(2028, 4, 12), 120),
            ElectionEntry("presidential_election", date(2027, 5, 3), 180),
        ],
    )
    today = date(2026, 1, 1)
    upcoming = get_upcoming_elections(today=today)
    assert len(upcoming) == 2
    assert upcoming[0].date < upcoming[1].date


def test_get_upcoming_elections_excludes_past(monkeypatch):
    import src.dem_shorts.compliance.election_dates as ed

    monkeypatch.setattr(
        ed,
        "ELECTION_DATES",
        [
            ElectionEntry("general_election", date(2020, 4, 15), 120),
            ElectionEntry("presidential_election", date(2027, 5, 3), 180),
        ],
    )
    today = date(2026, 1, 1)
    upcoming = get_upcoming_elections(today=today)
    assert len(upcoming) == 1
    assert upcoming[0].type == "presidential_election"


# ---------------------------------------------------------------------------
# 기본 호출 (today=None) 은 시스템 today 사용
# ---------------------------------------------------------------------------


def test_is_in_election_period_default_today(monkeypatch):
    """today=None 일 때 date.today() 를 사용."""
    election = date(2099, 12, 31)  # 먼 미래
    _use_election(election, "presidential_election", 180, monkeypatch)
    assert is_in_election_period() is False


def test_get_election_status_default_today(monkeypatch):
    election = date(2099, 12, 31)
    _use_election(election, "presidential_election", 180, monkeypatch)
    result = get_election_status()
    assert result.in_election_period is False
    assert result.next_election_date == election
