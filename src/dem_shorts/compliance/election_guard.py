"""T098: 선거법 가드 실제 구현 (FR-030, FR-031).

T077 Stub을 실제 로직으로 교체.

R-10: 대선 D-180, 총선 D-120 경계 자동 감지.
FR-030: 선거기간 진입 시 배너 표시용 플래그 제공.
FR-031: 선거기간 중 편향 임계값 하향 (RISK_SCORE_BLOCK → 30).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.dem_shorts.compliance.election_dates import (
    ElectionEntry,
    get_upcoming_elections,
)
from src.dem_shorts.config import (
    PRESIDENTIAL_GUARD_DAYS,
    RISK_SCORE_BLOCK,
    RISK_SCORE_BLOCK_ELECTION,
)


@dataclass(frozen=True)
class ElectionGuardResult:
    """선거기간 가드 결과."""

    in_election_period: bool  # 현재 선거기간 여부
    next_election_type: str | None  # "presidential_election"/"general_election"/None
    next_election_date: date | None
    days_until: int | None
    guard_threshold_days: int  # 180 (대선) / 120 (총선) / 기본값


def _pick_active_election(today: date) -> ElectionEntry | None:
    """오늘 기준 가장 가까운 '미래' 선거 중 가드가 활성인 선거를 우선.

    여러 선거가 미래에 있을 때:
    1. 가드가 이미 활성 (days_until <= guard_days) 이면 그 선거를 반환
    2. 없으면 가장 가까운 다가오는 선거를 반환
    """
    upcoming = get_upcoming_elections(today=today)
    if not upcoming:
        return None

    # 활성 가드 먼저
    for e in upcoming:
        days_until = (e.date - today).days
        if 0 <= days_until <= e.guard_days:
            return e

    # 아니면 가장 가까운 선거
    return upcoming[0]


def is_in_election_period(*, today: date | None = None) -> bool:
    """현재 선거기간 여부 (FR-030).

    가장 가까운 미래 선거의 guard_days 이내면 True.
    선거 당일도 포함. 선거일 다음날은 False.
    """
    ref = today if today is not None else date.today()
    upcoming = get_upcoming_elections(today=ref)
    for e in upcoming:
        days_until = (e.date - ref).days
        if 0 <= days_until <= e.guard_days:
            return True
    return False


def get_election_status(*, today: date | None = None) -> ElectionGuardResult:
    """현재 선거 상태 + 다가오는 선거 정보 (API/배너용).

    Args:
        today: 기준 날짜. None 이면 system today.

    Returns:
        ElectionGuardResult: 미래 선거가 없으면 next_* 필드는 None.
    """
    ref = today if today is not None else date.today()
    active = _pick_active_election(ref)

    if active is None:
        return ElectionGuardResult(
            in_election_period=False,
            next_election_type=None,
            next_election_date=None,
            days_until=None,
            guard_threshold_days=PRESIDENTIAL_GUARD_DAYS,
        )

    days_until = (active.date - ref).days
    in_period = 0 <= days_until <= active.guard_days
    return ElectionGuardResult(
        in_election_period=in_period,
        next_election_type=active.type,
        next_election_date=active.date,
        days_until=days_until,
        guard_threshold_days=active.guard_days,
    )


def get_bias_threshold(*, today: date | None = None) -> float:
    """현재 적용해야 할 편향 리스크 임계값 (FR-031).

    - 선거기간 중: RISK_SCORE_BLOCK_ELECTION (기본 30.0)
    - 평시: RISK_SCORE_BLOCK (기본 61.0)

    gate.py item_5_bias_guardrail 및 risk_ok 판정에서 이 함수를 호출한다.
    """
    return (
        RISK_SCORE_BLOCK_ELECTION
        if is_in_election_period(today=today)
        else RISK_SCORE_BLOCK
    )
