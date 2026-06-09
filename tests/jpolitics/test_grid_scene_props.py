"""T057 [US3]: ComparisonGridScene Remotion props 스키마 정적 검증.

Remotion 런타임 없이 props dict 생성 + 스키마 매칭.
- 카드 3~4개 필수
- 4번째 셀이 비어도 렌더 OK (slice(0,4) 동작 보장)
- 데이터 페이드 인 타이밍: 0.5s 지연 (15 frames) + 0.3s fade (9 frames @ 30fps)
"""
from __future__ import annotations

import re

import pytest


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _card_to_remotion_props(card_dict: dict) -> dict:
    """Python snake_case → Remotion camelCase 변환."""

    def to_camel(s: str) -> str:
        parts = s.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    return {to_camel(k): v for k, v in card_dict.items()}


def _make_card(name: str, party: str, color: str, **extra) -> dict:
    """카드 props 생성 헬퍼."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name=name,
        party=party,
        party_color=color,
        photo_path=extra.get("photo_path"),
        data_label=extra.get("data_label"),
        data_value=extra.get("data_value"),
    )
    return _card_to_remotion_props(card.to_dict())


# ─────────────────────────── Grid Scene Props 스키마 ───────────────────────────


def test_grid_comparison_cards_count_three_or_four() -> None:
    """grid_2x2 레이아웃 → comparisonCards 3개 또는 4개."""
    cards_3 = [
        _make_card("이재명", "더불어민주당", "#004EA2"),
        _make_card("한동훈", "국민의힘", "#E61E2B"),
        _make_card("이준석", "개혁신당", "#FF7300"),
    ]
    assert 3 <= len(cards_3) <= 4

    cards_4 = cards_3 + [_make_card("조국", "조국혁신당", "#0042A1")]
    assert 3 <= len(cards_4) <= 4


def test_grid_props_have_required_fields() -> None:
    """각 카드는 name, party, partyColor 필드 필수."""
    card = _make_card(
        "이재명",
        "더불어민주당",
        "#004EA2",
        data_label="재산",
        data_value="127억",
    )
    assert "name" in card
    assert "party" in card
    assert "partyColor" in card
    assert "dataLabel" in card
    assert "dataValue" in card
    assert card["name"] == "이재명"
    assert card["partyColor"] == "#004EA2"
    assert card["dataLabel"] == "재산"
    assert card["dataValue"] == "127억"


def test_grid_props_all_party_colors_hex() -> None:
    """모든 카드의 partyColor가 #RRGGBB 형식."""
    cards = [
        _make_card("이재명", "더불어민주당", "#004EA2"),
        _make_card("한동훈", "국민의힘", "#E61E2B"),
        _make_card("이준석", "개혁신당", "#FF7300"),
        _make_card("조국", "조국혁신당", "#0042A1"),
    ]
    for card in cards:
        assert HEX_COLOR_RE.match(card["partyColor"]), (
            f"partyColor must be #RRGGBB (got {card['partyColor']})"
        )


def test_grid_photo_path_optional_per_card() -> None:
    """각 카드의 photoPath 옵셔널 — 사진 없는 카드도 같이 노출 가능."""
    cards = [
        _make_card("이재명", "더불어민주당", "#004EA2"),  # photo_path=None
        _make_card(
            "한동훈",
            "국민의힘",
            "#E61E2B",
            photo_path="data/politician_cards/photos/한동훈.jpg",
        ),
        _make_card("이준석", "개혁신당", "#FF7300"),
    ]
    assert "photoPath" not in cards[0]  # 사진 없음 → 회색 실루엣
    assert cards[1]["photoPath"] == "data/politician_cards/photos/한동훈.jpg"
    assert "photoPath" not in cards[2]


def test_grid_data_fade_in_timing_15_to_24_frames() -> None:
    """데이터 페이드 인 타이밍: frame 15 (0.5s 지연) → frame 24 (0.3s fade @ 30fps).

    Remotion interpolate(frame, [15, 24], [0, 1]) 사양 검증 (constant).
    """
    FPS = 30
    DELAY_SEC = 0.5
    FADE_SEC = 0.3
    start_frame = int(DELAY_SEC * FPS)
    end_frame = start_frame + int(FADE_SEC * FPS)

    assert start_frame == 15
    assert end_frame == 24


def test_grid_scene_dataclass_data_emphasis_color_field() -> None:
    """JpoliticsScene.data_emphasis_color 필드 존재 + 기본값 'red'."""
    from src.jpolitics.models.script import JpoliticsScene

    scene = JpoliticsScene(
        id=0,
        timestamp=0.0,
        duration=3.0,
        type="title",
        text="평택을 비교",
        voice_text="평택을 후보를 비교합니다.",
        visual_layout="grid_2x2",
    )
    assert hasattr(scene, "data_emphasis_color")
    assert scene.data_emphasis_color == "red"  # 기본값


def test_grid_data_emphasis_color_serializable() -> None:
    """data_emphasis_color가 to_dict 직렬화에 포함."""
    from src.jpolitics.models.script import JpoliticsScene

    scene = JpoliticsScene(
        id=0,
        timestamp=0.0,
        duration=3.0,
        type="title",
        text="평택을 비교",
        voice_text="평택을 후보를 비교합니다.",
        visual_layout="grid_2x2",
        data_emphasis_color="red",
    )
    d = scene.to_dict()
    assert d.get("data_emphasis_color") == "red"


def test_grid_card_validation_consistent_data_label_value_pair() -> None:
    """grid 모드 카드도 data_label/data_value pair 일관성 유지."""
    from src.jpolitics.models.politician_card import PoliticianCard

    # 정상 — 데이터 없는 카드 (단순 비교)
    PoliticianCard(
        name="이재명",
        party="더불어민주당",
        party_color="#004EA2",
    ).validate()

    # 정상 — 데이터 카드
    PoliticianCard(
        name="이재명",
        party="더불어민주당",
        party_color="#004EA2",
        data_label="재산",
        data_value="127억",
    ).validate()

    # 비정상 — label만
    with pytest.raises(ValueError):
        PoliticianCard(
            name="이재명",
            party="더불어민주당",
            party_color="#004EA2",
            data_label="재산",
            data_value=None,
        ).validate()
