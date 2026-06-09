"""T064 [US4]: Planner — data_comparison (data_card) 분류 + 단일 인물 + data_value 강조.

Stage B 모킹 (layout_classification=data_comparison, narration.cards_metadata 1인 + data_value)
plan_to_script() 결과 검증:
- scenes[0].visual_layout == "data_card"
- scenes[0].comparison_cards 정확히 1개
- 카드의 data_label/data_value 필수 (없으면 normal 다운그레이드)
- data_value 비어있으면 normal 다운그레이드
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def _make_stage_b_result_data_card(
    *,
    rank: int = 1,
    include_data_value: bool = True,
    card_count: int = 1,
) -> dict:
    """data_card 레이아웃의 plan dict (Stage B 모킹용)."""
    card_metadata: dict = {
        "name": "조국",
        "party": "조국혁신당",
        "data_label": "재산",
    }
    if include_data_value:
        card_metadata["data_value"] = "56억"
    cards = [card_metadata]
    # 카드 추가 (downgrade 테스트용)
    if card_count >= 2:
        cards.append(
            {
                "name": "이재명",
                "party": "더불어민주당",
                "data_label": "재산",
                "data_value": "127억",
            }
        )

    return {
        "rank": rank,
        "angle": ["title_anchor", "audience_resonance", "comparison"][rank - 1],
        "format_type": "D",
        "layout_classification": "data_comparison",
        "topic": "조국 재산 5년간 0원",
        "hook": "충격적인 데이터",
        "clip_section": "00:00~00:30",
        "reason": "단일 인물 데이터 강조",
        "flow_intro": "도입",
        "flow_middle": "중간",
        "flow_climax": "클라이맥스",
        "narrations": [
            {
                "scene_id": 0,
                "text": "조국 재산 56억",
                "voice_text": "조국 전 의원의 재산은 56억 원입니다.",
                "visual_layout": "data_card",
                "subtitle_color": "yellow",
                "subtitle_emphasis": True,
                "cards_metadata": cards,
            },
            {
                "scene_id": 1,
                "text": "5년간 변동",
                "voice_text": "지난 5년간 거의 변동이 없었습니다.",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            },
            {
                "scene_id": 2,
                "text": "결론",
                "voice_text": "그 이유를 살펴봅니다.",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            },
        ],
        "cta": "구독해주세요",
        "headline_pin": "조국 재산 56억",  # 8자
    }


def _isolate_card_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """politician_card 모듈의 캐시·사진 경로를 tmp로 격리."""
    from src.jpolitics import constants
    from src.jpolitics.scraper import politician_card as pc_mod

    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(
        constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos"
    )
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(
        pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos"
    )


# ─────────────────────────── plan_to_script data_card ───────────────────────────


def test_plan_to_script_data_card_single_card_with_data_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """data_card 레이아웃 + 1인 + data_value → 정상 카드 1개."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(_make_stage_b_result_data_card())
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "data_card"
    assert scene0.comparison_cards is not None
    assert len(scene0.comparison_cards) == 1

    card = scene0.comparison_cards[0]
    assert card.name == "조국"
    assert card.data_label == "재산"
    assert card.data_value == "56억"


def test_plan_to_script_data_card_missing_data_value_downgrades(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """data_card + 카드의 data_value 없음 → normal 다운그레이드.

    PoliticianCard.validate() — data_label만 있고 value 없으면 fetch 실패하므로
    유효한 케이스는 둘 다 None (label도 없음). 이 경우 data_card 다운그레이드 발동.
    """
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    raw = _make_stage_b_result_data_card(include_data_value=False)
    # data_label도 제거 — 페어 일관성 유지
    raw["narrations"][0]["cards_metadata"][0].pop("data_label", None)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(raw)
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "normal"
    assert scene0.comparison_cards is None


def test_plan_to_script_data_card_two_cards_downgrades(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """data_card + 2인 (1명 초과) → normal 다운그레이드."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(
            _make_stage_b_result_data_card(card_count=2)
        )
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "normal"
    assert scene0.comparison_cards is None


def test_plan_to_script_data_card_classification_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """narration.visual_layout='normal' + classification='data_comparison'
    → 첫 씬이 data_card로 자동 승격."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    raw = _make_stage_b_result_data_card()
    raw["narrations"][0]["visual_layout"] = "normal"

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(raw)
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "data_card"
    assert scene0.comparison_cards is not None
    assert len(scene0.comparison_cards) == 1


def test_plan_to_script_data_card_party_color_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """data_card 카드의 party_color가 PARTY_COLORS 테이블에서 정확 매핑."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.constants import PARTY_COLORS
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(_make_stage_b_result_data_card())
        script = planner.plan_to_script(plan)

    card = script.scenes[0].comparison_cards[0]  # type: ignore[index]
    assert card.party == "조국혁신당"
    assert card.party_color == PARTY_COLORS["조국혁신당"]
