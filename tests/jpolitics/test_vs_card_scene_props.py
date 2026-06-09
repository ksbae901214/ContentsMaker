"""T044 [US2]: VsCardScene Remotion props 스키마 정적 검증.

Remotion 런타임 없이 props dict 생성 + 스키마 매칭.
data-model.md E3 PoliticianCard 기준.
"""
from __future__ import annotations

import re

import pytest


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _card_to_remotion_props(card_dict: dict) -> dict:
    """Python snake_case → Remotion camelCase 변환 (V3 renderer 패턴).

    renderer.py의 _convert_to_camel_case 와 등가 (테스트 격리용 인라인 구현).
    """

    def to_camel(s: str) -> str:
        parts = s.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    return {to_camel(k): v for k, v in card_dict.items()}


# ─────────────────────────── VS Card Props 스키마 ───────────────────────────


def test_vs_card_comparison_cards_exactly_two() -> None:
    """vs_card 레이아웃 → comparisonCards 정확히 2개."""
    from src.jpolitics.models.politician_card import PoliticianCard

    cards = [
        PoliticianCard(
            name="양향자", party="국민의힘", party_color="#E61E2B", photo_path=None
        ),
        PoliticianCard(
            name="추미애", party="더불어민주당", party_color="#004EA2", photo_path=None
        ),
    ]
    comparison_cards = [_card_to_remotion_props(c.to_dict()) for c in cards]
    assert len(comparison_cards) == 2


def test_vs_card_props_have_required_fields() -> None:
    """각 카드는 name, party, partyColor 필드 필수."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="양향자", party="국민의힘", party_color="#E61E2B", photo_path=None
    )
    props = _card_to_remotion_props(card.to_dict())
    assert "name" in props
    assert "party" in props
    assert "partyColor" in props
    assert props["name"] == "양향자"
    assert props["party"] == "국민의힘"
    assert props["partyColor"] == "#E61E2B"


def test_vs_card_props_party_color_is_hex() -> None:
    """partyColor는 #RRGGBB 형식."""
    from src.jpolitics.constants import PARTY_COLORS
    from src.jpolitics.models.politician_card import PoliticianCard

    for party, color in PARTY_COLORS.items():
        card = PoliticianCard(
            name="홍길동", party=party, party_color=color, photo_path=None
        )
        props = _card_to_remotion_props(card.to_dict())
        assert HEX_COLOR_RE.match(props["partyColor"]), (
            f"partyColor must be #RRGGBB (party={party}, got {props['partyColor']})"
        )


def test_vs_card_props_photo_path_optional() -> None:
    """photoPath는 옵셔널 — None이면 키 자체가 없어야 함 (Remotion props 정합)."""
    from src.jpolitics.models.politician_card import PoliticianCard

    # photo_path=None → to_dict()에서 키 제외
    card = PoliticianCard(
        name="홍길동", party="더불어민주당", party_color="#004EA2", photo_path=None
    )
    props = _card_to_remotion_props(card.to_dict())
    assert "photoPath" not in props

    # photo_path=경로 → 키 존재
    card_with_photo = PoliticianCard(
        name="홍길동",
        party="더불어민주당",
        party_color="#004EA2",
        photo_path="data/politician_cards/photos/홍길동.jpg",
    )
    props = _card_to_remotion_props(card_with_photo.to_dict())
    assert props["photoPath"] == "data/politician_cards/photos/홍길동.jpg"


def test_vs_card_validate_requires_hex_party_color() -> None:
    """PoliticianCard.validate() — 잘못된 헥스 형식 거부."""
    from src.jpolitics.models.politician_card import PoliticianCard

    bad = PoliticianCard(
        name="홍길동", party="국민의힘", party_color="red", photo_path=None
    )
    with pytest.raises(ValueError, match="party_color"):
        bad.validate()


def test_vs_card_name_length_range() -> None:
    """name 길이 1~20자."""
    from src.jpolitics.models.politician_card import PoliticianCard

    PoliticianCard(
        name="홍", party="국민의힘", party_color="#E61E2B", photo_path=None
    ).validate()
    PoliticianCard(
        name="이름" * 10, party="국민의힘", party_color="#E61E2B", photo_path=None
    ).validate()  # 20자

    # 0자 (빈 문자열)
    with pytest.raises(ValueError):
        PoliticianCard(
            name="", party="국민의힘", party_color="#E61E2B", photo_path=None
        ).validate()

    # 21자
    with pytest.raises(ValueError):
        PoliticianCard(
            name="가" * 21, party="국민의힘", party_color="#E61E2B", photo_path=None
        ).validate()


def test_vs_card_data_label_value_pair_consistency() -> None:
    """data_label/data_value는 함께 또는 둘 다 None."""
    from src.jpolitics.models.politician_card import PoliticianCard

    # 정상 — 둘 다 None
    PoliticianCard(
        name="홍길동", party="국민의힘", party_color="#E61E2B"
    ).validate()
    # 정상 — 둘 다 set
    PoliticianCard(
        name="홍길동",
        party="국민의힘",
        party_color="#E61E2B",
        data_label="재산",
        data_value="127억",
    ).validate()
    # 비정상 — 한쪽만
    with pytest.raises(ValueError):
        PoliticianCard(
            name="홍길동",
            party="국민의힘",
            party_color="#E61E2B",
            data_label="재산",
            data_value=None,
        ).validate()
