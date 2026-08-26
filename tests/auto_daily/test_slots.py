"""039 Phase 1 — 슬롯 정의와 수집 시간창 테스트."""
from datetime import datetime

import pytest

from scripts.auto_daily.slots import (
    KST, SLOT_NAMES, SlotSpec, resolve_window, slot_for_name, work_dir_for,
)


def test_세_슬롯이_정의되어_있다():
    assert SLOT_NAMES == ("morning", "noon", "evening")


@pytest.mark.parametrize(
    "name,hour,category",
    [("morning", 7, "political"), ("noon", 12, "economic"),
     ("evening", 18, "entertainment")],
)
def test_슬롯별_시각과_카테고리(name, hour, category):
    slot = slot_for_name(name)
    assert (slot.hour, slot.category) == (hour, category)


def test_알수없는_슬롯이름은_ValueError():
    with pytest.raises(ValueError, match="알 수 없는 슬롯"):
        slot_for_name("midnight")


def test_연예_슬롯은_v2_2만_제작한다():
    """036 확정 — 연예는 TTS 논평이 단죄로 읽혀 V2.1을 만들지 않는다."""
    assert slot_for_name("evening").formats == ("v2_2",)


def test_정치_경제_슬롯은_v2_2와_v2_1_둘다():
    for name in ("morning", "noon"):
        assert slot_for_name(name).formats == ("v2_2", "v2_1")


def test_카테고리는_shorts_category의_값과_일치한다():
    from scripts.shorts_category import CATEGORIES
    for name in SLOT_NAMES:
        assert slot_for_name(name).category in CATEGORIES


# ── 시간창 ──────────────────────────────────────────────────────────
def test_아침슬롯은_전날_00시부터_24시까지():
    now = datetime(2026, 8, 26, 7, 0, tzinfo=KST)
    after, before = resolve_window(slot_for_name("morning"), now)
    assert after == datetime(2026, 8, 25, 0, 0, tzinfo=KST)
    assert before == datetime(2026, 8, 26, 0, 0, tzinfo=KST)


def test_점심슬롯도_전날_범위다():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=KST)
    after, before = resolve_window(slot_for_name("noon"), now)
    assert after == datetime(2026, 8, 25, 0, 0, tzinfo=KST)
    assert before == datetime(2026, 8, 26, 0, 0, tzinfo=KST)


def test_저녁슬롯은_당일_00시부터_현재까지():
    now = datetime(2026, 8, 26, 18, 30, tzinfo=KST)
    after, before = resolve_window(slot_for_name("evening"), now)
    assert after == datetime(2026, 8, 26, 0, 0, tzinfo=KST)
    assert before == now


def test_월초_저녁슬롯도_당일_자정이_기준():
    now = datetime(2026, 9, 1, 18, 0, tzinfo=KST)
    after, _ = resolve_window(slot_for_name("evening"), now)
    assert after == datetime(2026, 9, 1, 0, 0, tzinfo=KST)


def test_월초_아침슬롯은_전달_말일을_집는다():
    """날짜 산술은 timedelta로 — 손으로 빼면 월말·윤년에서 틀린다."""
    now = datetime(2026, 9, 1, 7, 0, tzinfo=KST)
    after, before = resolve_window(slot_for_name("morning"), now)
    assert after == datetime(2026, 8, 31, 0, 0, tzinfo=KST)
    assert before == datetime(2026, 9, 1, 0, 0, tzinfo=KST)


def test_naive_datetime은_KST로_간주한다():
    after, _ = resolve_window(slot_for_name("morning"), datetime(2026, 8, 26, 7, 0))
    assert after == datetime(2026, 8, 25, 0, 0, tzinfo=KST)


# ── 작업 디렉터리 ───────────────────────────────────────────────────
def test_작업디렉터리는_실행일_기준_슬롯별로_갈린다(tmp_path):
    now = datetime(2026, 8, 26, 7, 0, tzinfo=KST)
    wd = work_dir_for(slot_for_name("morning"), now, root=tmp_path)
    assert wd == tmp_path / "20260826_morning"


def test_작업디렉터리는_생성하지_않는다(tmp_path):
    """경로 계산만 — 실제 mkdir은 runner가 한다."""
    wd = work_dir_for(slot_for_name("noon"), datetime(2026, 8, 26, tzinfo=KST),
                      root=tmp_path)
    assert not wd.exists()


def test_SlotSpec은_불변이다():
    with pytest.raises(Exception):
        slot_for_name("morning").hour = 9  # type: ignore[misc]


def test_모든_슬롯이_검색쿼리를_가진다():
    for name in SLOT_NAMES:
        assert len(slot_for_name(name).queries) >= 3


def test_SlotSpec_직접생성도_가능하다():
    s = SlotSpec(name="test", hour=3, category="political", day_offset=-1,
                 formats=("v2_2",), queries=("정치",))
    assert s.day_offset == -1
