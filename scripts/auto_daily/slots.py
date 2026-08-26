"""039 — 하루 3편 자동 제작 슬롯 정의.

| 슬롯 | 시각(KST) | 카테고리 | 소재 범위 | 포맷 |
|---|---|---|---|---|
| morning | 07:00 | political | 전날 00:00~24:00 | V2.2 + V2.1 |
| noon | 12:00 | economic | 전날 00:00~24:00 | V2.2 + V2.1 |
| evening | 18:00 | entertainment | **당일** 00:00~현재 | V2.2만 |

연예가 V2.2만인 이유: V2.1은 영상의 65%가 TTS 논평이라 연예 소재에서 논평이 곧
단죄로 읽히고 명예훼손 노출이 크다 (036 사용자 확정).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config.settings import PROJECT_ROOT

KST = timezone(timedelta(hours=9))

#: 슬롯 산출물 루트. runner 가 하위에 {YYYYMMDD}_{slot}/ 을 만든다.
AUTO_DAILY_ROOT = PROJECT_ROOT / "data" / "auto_daily"


@dataclass(frozen=True)
class SlotSpec:
    """한 슬롯의 실행 규격. 조회만 한다 — 실행 중 바뀌지 않는다."""

    name: str
    hour: int
    category: str
    #: 소재 수집 기준일. -1 = 전날 하루치, 0 = 당일 00:00~현재.
    day_offset: int
    #: 제작할 포맷 (렌더 순서대로).
    formats: tuple[str, ...]
    #: 네이버 검색 API 쿼리. 연예는 랭킹 API를 쓰므로 라벨 용도에 가깝다.
    queries: tuple[str, ...]


_POLITICAL_QUERIES = (
    "정치", "국회", "대통령실", "여당", "야당", "국민의힘", "민주당",
    "특검", "대표", "장관", "공천",
)
_ECONOMIC_QUERIES = (
    "경제", "금리", "환율", "부동산", "물가", "증시", "세금", "고용",
    "한국은행", "기획재정부", "전세", "대출",
)
_ENTERTAINMENT_QUERIES = (
    "연예", "배우", "가수", "아이돌", "드라마", "예능", "소속사",
)

_SLOTS: tuple[SlotSpec, ...] = (
    SlotSpec(name="morning", hour=7, category="political", day_offset=-1,
             formats=("v2_2", "v2_1"), queries=_POLITICAL_QUERIES),
    SlotSpec(name="noon", hour=12, category="economic", day_offset=-1,
             formats=("v2_2", "v2_1"), queries=_ECONOMIC_QUERIES),
    # 연예는 V2.2만 (036 확정) — V2.1 자리는 비운다.
    SlotSpec(name="evening", hour=18, category="entertainment", day_offset=0,
             formats=("v2_2",), queries=_ENTERTAINMENT_QUERIES),
)

SLOT_NAMES: tuple[str, ...] = tuple(s.name for s in _SLOTS)
_BY_NAME = {s.name: s for s in _SLOTS}


def slot_for_name(name: str) -> SlotSpec:
    try:
        return _BY_NAME[name]
    except KeyError:
        raise ValueError(
            f"알 수 없는 슬롯: {name!r} (허용: {', '.join(SLOT_NAMES)})"
        ) from None


def all_slots() -> tuple[SlotSpec, ...]:
    return _SLOTS


def _as_kst(now: datetime) -> datetime:
    """naive datetime 은 KST 로 간주. 로컬 타임존 추정은 하지 않는다."""
    return now.replace(tzinfo=KST) if now.tzinfo is None else now.astimezone(KST)


def resolve_window(slot: SlotSpec, now: datetime) -> tuple[datetime, datetime]:
    """수집 시간창 (after, before) 을 KST 로 돌려준다.

    날짜 산술은 전부 timedelta — 월말·윤년을 손으로 계산하면 틀린다.
    """
    now = _as_kst(now)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if slot.day_offset == 0:
        return midnight, now
    start = midnight + timedelta(days=slot.day_offset)
    return start, start + timedelta(days=1)


def work_dir_for(slot: SlotSpec, now: datetime,
                 root: Path | None = None) -> Path:
    """슬롯 산출물 디렉터리 경로. **생성하지 않는다** — runner 가 만든다."""
    base = Path(root) if root is not None else AUTO_DAILY_ROOT
    return base / f"{_as_kst(now):%Y%m%d}_{slot.name}"
