"""T056 [US3]: Planner — comparison_grid (grid_2x2) 분류 + 카드 3~4개 페치 + 데이터 매핑.

Stage B 모킹 (layout_classification=comparison_grid, narration.cards_metadata 3~4인 + data_label/data_value)
plan_to_script() 결과 검증:
- scenes[0].visual_layout == "grid_2x2"
- scenes[0].comparison_cards 길이 3 또는 4
- 각 카드의 data_label/data_value 보존
- 카드 < 3 또는 > 4 → normal 다운그레이드
- 일부 사진 미발견 시 photo_path=None (회색 실루엣 폴백)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def _make_stage_b_result_grid(
    *,
    rank: int = 1,
    card_count: int = 4,
    layout_classification: str = "comparison_grid",
) -> dict:
    """grid_2x2 레이아웃의 plan dict (Stage B 모킹용)."""
    all_cards = [
        {
            "name": "이재명",
            "party": "더불어민주당",
            "data_label": "재산",
            "data_value": "127억",
        },
        {
            "name": "한동훈",
            "party": "국민의힘",
            "data_label": "재산",
            "data_value": "98억",
        },
        {
            "name": "이준석",
            "party": "개혁신당",
            "data_label": "재산",
            "data_value": "32억",
        },
        {
            "name": "조국",
            "party": "조국혁신당",
            "data_label": "재산",
            "data_value": "56억",
        },
    ]
    return {
        "rank": rank,
        "angle": ["title_anchor", "audience_resonance", "comparison"][rank - 1],
        "format_type": "C",
        "layout_classification": layout_classification,
        "topic": "평택을 후보 4명 재산 비교",
        "hook": "누가 가장 부자인가",
        "clip_section": "00:00~00:30",
        "reason": "후보 다인 비교 구도",
        "flow_intro": "도입",
        "flow_middle": "중간",
        "flow_climax": "클라이맥스",
        "narrations": [
            {
                "scene_id": 0,
                "text": "평택을 후보 비교",
                "voice_text": "평택을 후보 4명을 비교합니다.",
                "visual_layout": "grid_2x2",
                "subtitle_color": "yellow",
                "subtitle_emphasis": True,
                "cards_metadata": all_cards[:card_count],
            },
            {
                "scene_id": 1,
                "text": "본문",
                "voice_text": "각 후보의 재산은 다음과 같습니다.",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            },
            {
                "scene_id": 2,
                "text": "마무리",
                "voice_text": "구독해주세요.",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            },
        ],
        "cta": "구독해주세요",
        "headline_pin": "평택을 후보 비교",  # 8자
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


# ─────────────────────────── plan_to_script grid_2x2 ───────────────────────────


def test_plan_to_script_grid_fetches_four_cards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """grid_2x2 레이아웃 + 4인 → comparison_cards 4개 + data 보존."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(_make_stage_b_result_grid(card_count=4))
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "grid_2x2"
    assert scene0.comparison_cards is not None
    assert len(scene0.comparison_cards) == 4

    by_name = {c.name: c for c in scene0.comparison_cards}
    assert "이재명" in by_name
    assert by_name["이재명"].data_label == "재산"
    assert by_name["이재명"].data_value == "127억"
    assert by_name["조국"].data_value == "56억"


def test_plan_to_script_grid_three_cards_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """grid_2x2 + 3인 (4번째 셀 비어도 렌더 OK) → 3개 카드 유지."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(_make_stage_b_result_grid(card_count=3))
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "grid_2x2"
    assert scene0.comparison_cards is not None
    assert len(scene0.comparison_cards) == 3


def test_plan_to_script_grid_two_cards_downgrades_to_normal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """grid_2x2 + 2인 (3 미만) → normal 다운그레이드 + comparison_cards None."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(_make_stage_b_result_grid(card_count=2))
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.visual_layout == "normal"
    assert scene0.comparison_cards is None


def test_plan_to_script_grid_photo_missing_falls_back_to_no_photo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """일부 사진 미발견 → 해당 카드 photo_path=None (회색 실루엣 폴백 신호)."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(_make_stage_b_result_grid(card_count=4))
        script = planner.plan_to_script(plan)

    scene0 = script.scenes[0]
    assert scene0.comparison_cards is not None
    for card in scene0.comparison_cards:
        assert card.photo_path is None  # Naver 호출 실패 → None
        # 회색 실루엣은 Remotion 컴포넌트가 photo_path 부재로 분기


def test_plan_to_script_grid_layout_classification_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """narration.visual_layout='normal' + classification='comparison_grid'
    → 첫 씬이 grid_2x2로 자동 승격."""
    from src.jpolitics.analyzer import planner
    from src.jpolitics.models.plan import JpoliticsPlan
    from src.jpolitics.scraper import politician_card as pc_mod

    _isolate_card_dirs(tmp_path, monkeypatch)

    raw = _make_stage_b_result_grid(card_count=4)
    raw["narrations"][0]["visual_layout"] = "normal"  # narration은 normal
    # 단 classification은 comparison_grid 유지

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        plan = JpoliticsPlan.from_dict(raw)
        script = planner.plan_to_script(plan)

    # 첫 씬은 grid_2x2로 승격
    assert script.scenes[0].visual_layout == "grid_2x2"
    assert script.scenes[0].comparison_cards is not None
    assert len(script.scenes[0].comparison_cards) == 4
