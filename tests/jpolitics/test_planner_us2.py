"""T043 [US2]: Planner — vs_card 분류 + 카드 페치 + 정당 컬러 매핑.

Stage A 모킹 (layout=vs_2way)
Stage B 모킹 (narrations[0].cards_metadata에 2인 포함)
plan_to_script() 결과 검증:
- scenes[0].visual_layout == "vs_card"
- scenes[0].comparison_cards == 2개
- 각 카드의 party_color가 PARTY_COLORS 정확 매핑
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def _make_stage_b_result(rank: int, layout: str = "vs_card") -> dict:
    """vs_card 레이아웃의 plan dict (Stage B 모킹용)."""
    return {
        "rank": rank,
        "angle": ["title_anchor", "audience_resonance", "comparison"][rank - 1],
        "format_type": "A",
        "layout_classification": "vs_2way",
        "topic": "양향자 vs 추미애",
        "hook": "두 거물의 대결",
        "clip_section": "00:00~00:30",
        "reason": "대립 구도",
        "flow_intro": "도입",
        "flow_middle": "중간",
        "flow_climax": "클라이맥스",
        "narrations": [
            {
                "scene_id": 0,
                "text": "양향자 vs 추미애",
                "voice_text": "경기지사 대결이 시작됩니다.",
                "visual_layout": layout,
                "subtitle_color": "yellow",
                "subtitle_emphasis": True,
                "cards_metadata": [
                    {"name": "양향자", "party": "국민의힘"},
                    {"name": "추미애", "party": "더불어민주당"},
                ],
            },
            {
                "scene_id": 1,
                "text": "양향자 측 입장",
                "voice_text": "양향자 측 입장입니다.",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            },
            {
                "scene_id": 2,
                "text": "추미애 측 반박",
                "voice_text": "추미애 측 반박입니다.",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            },
        ],
        "cta": "구독해주세요",
        "headline_pin": "양향자 추미애",  # 7자... 8~14자 보장 위해 늘림
    }


def _make_stage_a_result() -> dict:
    return {
        "transcript": [{"start": 0.0, "end": 30.0, "text": "샘플"}],
        "key_moments": [{"start": 5.0, "end": 15.0, "summary": "핵심"}],
        "layout_classification": "vs_2way",
        "angles": [
            {"name": "title_anchor", "topic": "양향자 vs 추미애"},
            {"name": "audience_resonance", "topic": "양향자 vs 추미애"},
            {"name": "comparison", "topic": "양향자 vs 추미애"},
        ],
    }


# ─────────────────────────── plan_to_script vs_card ───────────────────────────


def test_plan_to_script_vs_card_fetches_two_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vs_card 레이아웃 → comparison_cards에 정확히 2개 카드 + 정당 컬러 매핑."""
    from src.jpolitics import constants
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    # 카드 캐시/사진 디렉토리 격리
    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(
        pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos"
    )

    # Naver/Claude 호출 모킹 — 사진 없음, 정당은 사전 제공
    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        raw = _make_stage_b_result(rank=1)
        # headline_pin 8자 보장
        raw["headline_pin"] = "양향자 추미애 대결"  # 9자
        plan = JpoliticsPlan.from_dict(raw)
        # plan.layout_classification은 vs_2way 이지만, plan_to_script가 처리하는
        # narration.visual_layout이 "vs_card"이므로 직접 카드 페치 발동
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "vs_card"
    assert scene0.comparison_cards is not None
    assert len(scene0.comparison_cards) == 2

    names = {c.name for c in scene0.comparison_cards}
    assert names == {"양향자", "추미애"}

    by_name = {c.name: c for c in scene0.comparison_cards}
    assert by_name["양향자"].party == "국민의힘"
    assert by_name["양향자"].party_color == "#E61E2B"
    assert by_name["추미애"].party == "더불어민주당"
    assert by_name["추미애"].party_color == "#004EA2"


def test_plan_to_script_vs_card_layout_propagates_from_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan.layout_classification == 'vs_2way' + narration visual_layout == 'normal'
    이어도 첫 씬은 자동으로 vs_card 로 승격."""
    from src.jpolitics import constants
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(
        pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos"
    )

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        # narration.visual_layout은 'normal'이지만 layout_classification은 vs_2way + cards_metadata 2명
        raw = _make_stage_b_result(rank=1, layout="normal")
        raw["headline_pin"] = "양향자 추미애 대결"  # 9자
        plan = JpoliticsPlan.from_dict(raw)
        script = planner.plan_to_script(plan)

    # 첫 씬은 vs_card로 승격
    scene0 = script.scenes[0]
    assert scene0.visual_layout == "vs_card"
    assert scene0.comparison_cards is not None
    assert len(scene0.comparison_cards) == 2


def test_layout_classification_to_visual_layout_mapping() -> None:
    """_layout_classification_to_visual_layout 헬퍼 매핑."""
    from src.jpolitics.analyzer import planner

    assert planner._layout_classification_to_visual_layout("talking_head") == "normal"
    assert planner._layout_classification_to_visual_layout("vs_2way") == "vs_card"
    assert (
        planner._layout_classification_to_visual_layout("comparison_grid") == "grid_2x2"
    )
    assert (
        planner._layout_classification_to_visual_layout("data_comparison") == "data_card"
    )
    # 알 수 없는 값 → normal 폴백
    assert planner._layout_classification_to_visual_layout("unknown") == "normal"


# ─────────────────────────── 정당 컬러 매핑 정확성 ───────────────────────────


def test_plan_to_script_party_color_matches_party_colors_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """각 정당의 party_color가 PARTY_COLORS 표와 정확히 일치 (FR-024)."""
    from src.jpolitics import constants
    from src.jpolitics.analyzer import planner
    from src.jpolitics.constants import PARTY_COLORS
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path / "cards")
    monkeypatch.setattr(
        pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "cards" / "photos"
    )

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        raw = _make_stage_b_result(rank=1)
        raw["headline_pin"] = "양향자 추미애 대결"  # 9자
        plan = JpoliticsPlan.from_dict(raw)
        script = planner.plan_to_script(plan)

    for card in script.scenes[0].comparison_cards or ():
        assert card.party_color == PARTY_COLORS[card.party]
