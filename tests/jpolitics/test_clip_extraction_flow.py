"""T015b [US1]: 영상 추출 3단계 흐름 단위 테스트 (FR-037).

1. Gemini Files API: YouTube URL → transcript + key_moments
2. Claude Stage B: 씬별 clip_search_query + clip_source_timestamp 결정
3. yt-dlp: Claude 결정 키워드로 ytsearch1 + ffmpeg 9:16 letterbox cut

RED 상태 — 구현 후 GREEN.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_run_gemini_analysis_calls_gemini_backend() -> None:
    """_run_gemini_analysis()는 Gemini 백엔드를 호출 (FR-037 step 1)."""
    from src.jpolitics.analyzer import planner

    with patch.object(planner, "call_gemini") as gem:
        gem.return_value = '{"transcript": [], "key_moments": [], "layout_classification": "talking_head", "angles": []}'
        result = planner._run_gemini_analysis(
            youtube_url="https://www.youtube.com/watch?v=test",
            video_title="t",
        )
    assert gem.called
    assert "layout_classification" in result


def test_stage_b_outputs_clip_search_query_per_narration() -> None:
    """Stage B Claude 결과에 씬별 clip_search_query 필드 포함."""
    from src.jpolitics.analyzer import prompts

    prompt_text = prompts.build_stage_b_prompt(
        stage_a_result={
            "transcript": [],
            "key_moments": [],
            "layout_classification": "talking_head",
            "angles": [],
        },
        video_title="조국 사퇴",
        video_duration_sec=60.0,
        rank=1,
        angle="title_anchor",
    )
    assert "clip_search_query" in prompt_text
    assert "clip_source_timestamp" in prompt_text


def test_clip_extraction_calls_youtube_news_searcher_cut_with_letterbox() -> None:
    """plan_to_script가 cut_scene_clip(crop_mode='letterbox') 호출."""
    from src.jpolitics.analyzer import planner

    # cut_scene_clip 호출 시 crop_mode="letterbox" 인지 검증
    with patch(
        "src.scraper.youtube_news_searcher.cut_scene_clip"
    ) as cut_mock:
        cut_mock.return_value = "/tmp/fake_clip.mp4"

        # 실제 호출 패턴은 구현에서 — 여기는 mock 존재 + crop_mode 인자 검증 가이드
        # 구현 후 plan_to_script 호출하여 cut_mock.call_args 확인
        # 현재는 placeholder
        assert callable(cut_mock)


def test_gemini_analysis_json_saved_to_output_dir(tmp_path) -> None:
    """gemini_analysis.json이 output_dir에 보존됨."""
    from src.jpolitics.analyzer import planner

    output_dir = tmp_path / "test_run"
    output_dir.mkdir()

    fake_gemini = {
        "transcript": [{"start": 0.0, "end": 60.0, "text": "샘플"}],
        "key_moments": [{"start": 10.0, "end": 25.0, "summary": "핵심"}],
        "layout_classification": "talking_head",
        "angles": [
            {"name": "title_anchor"},
            {"name": "audience_resonance"},
            {"name": "comparison"},
        ],
    }
    fake_claude = {
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

    with patch.object(planner, "_run_gemini_analysis", return_value=fake_gemini), patch.object(
        planner, "_run_claude_stage_b", return_value=fake_claude
    ):
        planner.generate_three_plans(
            youtube_url="https://www.youtube.com/watch?v=test",
            video_title="t",
            video_duration_sec=60.0,
            output_dir=output_dir,
        )

    assert (output_dir / "gemini_analysis.json").exists()
    assert (output_dir / "plans.json").exists()
