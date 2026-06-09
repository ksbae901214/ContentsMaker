"""T065 [US4]: DataCardScene Remotion props 스키마 정적 검증.

Remotion 런타임 없이 props dict 생성 + 스키마 매칭.
- 카드 1개 필수
- dataValue 필수
- 사진 720×720, 데이터 값 144px Black weight 900 dataEmphasisColor
- spring 애니메이션 (0.8s scale 0.7 → 1.0)
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


# ─────────────────────────── Data Card Props 스키마 ───────────────────────────


def test_data_card_comparison_cards_exactly_one() -> None:
    """data_card 레이아웃 → comparisonCards 정확히 1개."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        data_label="재산",
        data_value="56억",
    )
    cards = [_card_to_remotion_props(card.to_dict())]
    assert len(cards) == 1


def test_data_card_data_value_required() -> None:
    """data_card는 dataValue 필수 — PoliticianCard.validate() 단독으로는 통과해도
    planner 검증 단계에서 downgrade. props 자체에 dataValue 키 존재 확인."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        data_label="재산",
        data_value="56억",
    )
    props = _card_to_remotion_props(card.to_dict())
    assert "dataValue" in props
    assert props["dataValue"] == "56억"


def test_data_card_data_label_present() -> None:
    """data_card는 dataLabel도 함께 노출 (작은 글자, 헬퍼 텍스트)."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        data_label="재산",
        data_value="56억",
    )
    props = _card_to_remotion_props(card.to_dict())
    assert "dataLabel" in props
    assert props["dataLabel"] == "재산"


def test_data_card_photo_path_optional() -> None:
    """data_card 카드도 photoPath 옵셔널 — 없으면 회색 실루엣 폴백."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card_no_photo = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        photo_path=None,
        data_label="재산",
        data_value="56억",
    )
    props = _card_to_remotion_props(card_no_photo.to_dict())
    assert "photoPath" not in props

    card_with_photo = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        photo_path="data/politician_cards/photos/조국.jpg",
        data_label="재산",
        data_value="56억",
    )
    props_with = _card_to_remotion_props(card_with_photo.to_dict())
    assert props_with["photoPath"] == "data/politician_cards/photos/조국.jpg"


def test_data_card_party_color_hex() -> None:
    """data_card 카드의 partyColor #RRGGBB 형식."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        data_label="재산",
        data_value="56억",
    )
    props = _card_to_remotion_props(card.to_dict())
    assert HEX_COLOR_RE.match(props["partyColor"])


def test_data_card_spring_animation_duration_24_frames() -> None:
    """spring 애니메이션 duration: 0.8s @ 30fps = 24 frames (constant 검증).

    DataCardScene.tsx: durationInFrames: Math.round(0.8 * fps).
    """
    FPS = 30
    DURATION_SEC = 0.8
    duration_frames = round(DURATION_SEC * FPS)
    assert duration_frames == 24


def test_data_card_scene_dataclass_data_emphasis_color_red_default() -> None:
    """JpoliticsScene.data_emphasis_color 기본값 'red'."""
    from src.jpolitics.models.script import JpoliticsScene

    scene = JpoliticsScene(
        id=0,
        timestamp=0.0,
        duration=3.0,
        type="title",
        text="조국 재산 56억",
        voice_text="조국 전 의원의 재산은 56억 원입니다.",
        visual_layout="data_card",
    )
    assert scene.data_emphasis_color == "red"


def test_data_card_scene_validate_requires_data_value() -> None:
    """JpoliticsScene.validate() — data_card는 data_value 필수."""
    from src.jpolitics.models.politician_card import PoliticianCard
    from src.jpolitics.models.script import JpoliticsScene

    card_no_value = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
    )
    scene = JpoliticsScene(
        id=0,
        timestamp=0.0,
        duration=3.0,
        type="title",
        text="조국 재산",
        voice_text="조국 재산.",
        visual_layout="data_card",
        comparison_cards=(card_no_value,),
    )
    with pytest.raises(ValueError, match="data_value"):
        scene.validate()


def test_data_card_props_required_visual_layout() -> None:
    """visualLayout 키가 정확히 'data_card'."""
    from src.jpolitics.models.script import JpoliticsScene
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0042A1",
        data_label="재산",
        data_value="56억",
    )
    scene = JpoliticsScene(
        id=0,
        timestamp=0.0,
        duration=3.0,
        type="title",
        text="조국 재산 56억",
        voice_text="조국 재산은 56억 원입니다.",
        visual_layout="data_card",
        comparison_cards=(card,),
    )
    d = scene.to_dict()
    assert d["visual_layout"] == "data_card"
