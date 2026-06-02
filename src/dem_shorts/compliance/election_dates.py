"""T097: 하드코딩된 선거 일정 테이블 (R-10).

중앙선관위 공개 API는 없으므로, 공식 선거일 발표 시 수동 갱신한다.
보궐·지방선거 등도 필요 시 본 테이블에 추가.

guard_days:
- 대선 (presidential_election): 180일
- 총선 (general_election): 120일
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ElectionEntry:
    """단일 선거 엔트리 (R-10)."""

    type: str  # "presidential_election" | "general_election"
    date: date
    guard_days: int  # 선거법 가드 적용 일수 (대선=180, 총선=120)


# ── Hardcoded election schedule (R-10) ─────────────────────────
# 선거일 발표 시 본 리스트를 갱신하고 커밋. 과거 선거도 레퍼런스로 남겨두되
# get_upcoming_elections() 가 today 기준으로 필터링한다.
ELECTION_DATES: list[ElectionEntry] = [
    ElectionEntry(
        type="presidential_election",
        date=date(2027, 5, 3),
        guard_days=180,
    ),
    ElectionEntry(
        type="general_election",
        date=date(2028, 4, 12),
        guard_days=120,
    ),
]


def get_upcoming_elections(*, today: date | None = None) -> list[ElectionEntry]:
    """오늘 이후(당일 포함)의 선거만 반환, 날짜 오름차순.

    Args:
        today: 기준 날짜. None 이면 system today.
    """
    ref = today if today is not None else date.today()
    future = [e for e in ELECTION_DATES if e.date >= ref]
    return sorted(future, key=lambda e: e.date)
