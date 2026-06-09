"""T012 [US1]: Planner Stage A/B 모킹 — 3 plans 다양성 + headline_pin 검증.

RED 상태 — T019/T020/T021/T022 구현 후 GREEN.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_generate_three_plans_returns_three_distinct_angles() -> None:
    from src.jpolitics.analyzer import planner

    mock_gemini_result = {
        "transcript": [{"start": 0.0, "end": 60.0, "text": "샘플"}],
        "key_moments": [{"start": 10.0, "end": 25.0, "summary": "핵심"}],
        "layout_classification": "talking_head",
        "angles": [
            {"name": "title_anchor", "topic": "주제1", "hook": "후크1"},
            {"name": "audience_resonance", "topic": "주제2", "hook": "후크2"},
            {"name": "comparison", "topic": "주제3", "hook": "후크3"},
        ],
    }

    mock_claude_result = lambda rank: {
        "rank": rank,
        "angle": ["title_anchor", "audience_resonance", "comparison"][rank - 1],
        "format_type": "A",
        "layout_classification": "talking_head",
        "topic": f"주제{rank}",
        "hook": f"후크{rank}",
        "clip_section": "00:10~00:25",
        "reason": "이유",
        "flow_intro": "도입",
        "flow_middle": "중간",
        "flow_climax": "클라이맥스",
        "narrations": [
            {
                "scene_id": 0,
                "text": "자막",
                "voice_text": "음성",
                "visual_layout": "normal",
                "subtitle_color": "white",
                "subtitle_emphasis": False,
            }
        ],
        "cta": "구독해주세요",
        "headline_pin": "조국 사퇴 충격",
    }

    with patch.object(
        planner, "_run_gemini_analysis", return_value=mock_gemini_result
    ), patch.object(
        planner,
        "_run_claude_stage_b",
        side_effect=[mock_claude_result(1), mock_claude_result(2), mock_claude_result(3)],
    ):
        result = planner.generate_three_plans(
            youtube_url="https://www.youtube.com/watch?v=test",
            video_title="테스트 영상",
            video_duration_sec=60.0,
            output_dir=None,
        )

    assert len(result.plans) == 3
    angles = {p.angle for p in result.plans}
    assert angles == {"title_anchor", "audience_resonance", "comparison"}


def test_headline_pin_length_8_to_14_chars() -> None:
    """FR-011: headline_pin 8~14자."""
    from src.jpolitics.models.plan import JpoliticsPlan, validate_headline_pin

    # 정상
    validate_headline_pin("조국 사퇴 충격")  # 8자

    # 너무 짧음
    with pytest.raises(ValueError):
        validate_headline_pin("짧다")

    # 너무 김
    with pytest.raises(ValueError):
        validate_headline_pin("이것은 매우 매우 매우 긴 헤드라인입니다")


def test_plan_to_script_sets_lockin_audio_config() -> None:
    """plan_to_script가 AudioConfig 락인 필드를 강제 설정."""
    from src.jpolitics.analyzer import planner

    # 임의 plan 객체로 호출 → 결과 script.audio.sfx_enabled == False
    # 자세한 구현은 T022에서. 여기는 시그니처 확인만.
    assert hasattr(planner, "plan_to_script")


def test_three_plans_runs_3_stage_b_calls() -> None:
    """Stage B Claude 호출이 정확히 3회 (각 angle별)."""
    from src.jpolitics.analyzer import planner

    with patch.object(planner, "_run_gemini_analysis") as gemini, patch.object(
        planner, "_run_claude_stage_b"
    ) as claude:
        gemini.return_value = {
            "transcript": [],
            "key_moments": [],
            "layout_classification": "talking_head",
            "angles": [
                {"name": "title_anchor"},
                {"name": "audience_resonance"},
                {"name": "comparison"},
            ],
        }
        claude.return_value = {
            "rank": 1,
            "angle": "title_anchor",
            "format_type": "A",
            "layout_classification": "talking_head",
            "topic": "t",
            "hook": "h",
            "clip_section": "0~1",
            "reason": "r",
            "flow_intro": "i",
            "flow_middle": "m",
            "flow_climax": "c",
            "narrations": [],
            "cta": "c",
            "headline_pin": "조국 사퇴 충격",
        }
        planner.generate_three_plans(
            youtube_url="https://www.youtube.com/watch?v=t",
            video_title="t",
            video_duration_sec=60.0,
            output_dir=None,
        )

    assert gemini.call_count == 1, "Stage A Gemini는 1회만"
    assert claude.call_count == 3, "Stage B Claude는 3회 (각 angle별)"
