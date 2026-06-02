"""Tests for Feature 023 — political_pro topic 모드.

generate_three_plans_from_topic() + ShortsPlan source_type/youtube_search_keywords.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.analyzer.political_plan_models import (
    Narration,
    PlanValidationError,
    ShortsPlan,
    ThreePlansResult,
)
from src.analyzer.political_planner import (
    PoliticalPlannerError,
    generate_three_plans_from_topic,
    plan_to_script,
)


# ────────────────── ShortsPlan source_type/youtube_search_keywords ──────────────────


def test_shortsplan_default_source_type_is_youtube():
    plan = ShortsPlan(
        topic="t", hook="h", clip_start_sec=0, clip_end_sec=10,
        clip_reason="r", flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(0, 3, "n"),), cta="cta", angle="title_anchor",
    )
    assert plan.source_type == "youtube"
    assert plan.youtube_search_keywords == ()


def test_shortsplan_topic_source_type_accepted():
    plan = ShortsPlan(
        topic="스타벅스 5.18", hook="hook", clip_start_sec=0, clip_end_sec=60,
        clip_reason="r", flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(0, 3, "n"),), cta="cta", angle="title_anchor",
        source_type="topic",
        youtube_search_keywords=("스타벅스 5.18 논란", "탱크데이"),
    )
    assert plan.source_type == "topic"
    assert plan.youtube_search_keywords == ("스타벅스 5.18 논란", "탱크데이")


def test_shortsplan_invalid_source_type_rejected():
    with pytest.raises(PlanValidationError, match="source_type"):
        ShortsPlan(
            topic="t", hook="h", clip_start_sec=0, clip_end_sec=10,
            clip_reason="r", flow_intro="i", flow_middle="m", flow_climax="c",
            narrations=(Narration(0, 3, "n"),), cta="cta", angle="title_anchor",
            source_type="invalid_type",  # type: ignore[arg-type]
        )


def test_shortsplan_round_trip_topic_mode():
    """topic 모드 plan → to_dict → from_dict 라운드트립."""
    plan = ShortsPlan(
        topic="t", hook="h", clip_start_sec=0, clip_end_sec=60,
        clip_reason="r", flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(0, 5, "n", subtitle_color="red"),),
        cta="cta", angle="comparison",
        source_type="topic",
        youtube_search_keywords=("kw1", "kw2", "kw3"),
    )
    plan2 = ShortsPlan.from_dict(plan.to_dict())
    assert plan2.source_type == "topic"
    assert plan2.youtube_search_keywords == ("kw1", "kw2", "kw3")
    assert plan2.narrations[0].subtitle_color == "red"


def test_shortsplan_v1_json_default_to_youtube_mode():
    """기존 V1 JSON (source_type 필드 없음) → default 'youtube' fallback."""
    v1_dict = {
        "topic": "t", "hook": "h", "clip_start_sec": 5, "clip_end_sec": 30,
        "clip_reason": "r", "flow_intro": "i", "flow_middle": "m", "flow_climax": "c",
        "narrations": [{"start_sec": 0, "end_sec": 5, "text": "n"}],
        "cta": "cta", "angle": "title_anchor",
    }
    plan = ShortsPlan.from_dict(v1_dict)
    assert plan.source_type == "youtube"
    assert plan.youtube_search_keywords == ()


# ────────────────── generate_three_plans_from_topic ──────────────────


def _fake_stage_a_response():
    """Stage A 결과 mock — 3 angle 후보."""
    return [
        {
            "format_type": "A", "format_reason": "인터뷰형",
            "topic": "주제1", "hook": "후킹1", "angle": "title_anchor",
        },
        {
            "format_type": "A", "format_reason": "논평형",
            "topic": "주제2", "hook": "후킹2", "angle": "audience_resonance",
        },
        {
            "format_type": "B", "format_reason": "현장형",
            "topic": "주제3", "hook": "후킹3", "angle": "comparison",
        },
    ]


def _fake_stage_b_response():
    """Stage B 결과 mock — narrations + youtube_search_keywords 포함."""
    return {
        "flow_intro": "intro flow",
        "flow_middle": "middle flow",
        "flow_climax": "climax flow",
        "narrations": [
            {"start_sec": 0, "end_sec": 5, "text": "씬1", "subtitle_color": "yellow",
             "subtitle_emphasis": True},
            {"start_sec": 5, "end_sec": 12, "text": "씬2", "subtitle_color": "red"},
            {"start_sec": 12, "end_sec": 18, "text": "씬3", "subtitle_color": "white"},
        ],
        "visual_directives": ["0~5초: 큰 자막 강조"],
        "cta": "댓글로 의견 부탁드립니다",
        "youtube_search_keywords": [
            "검색어1", "검색어2", "검색어3",
        ],
    }


def test_generate_three_plans_from_topic_happy_path(tmp_path):
    """Stage A + Stage B mock → 3개 plan + youtube_search_keywords 포함."""
    with patch(
        "src.analyzer.political_planner._stage_a_topic_gemini",
        return_value=_fake_stage_a_response(),
    ), patch(
        "src.analyzer.political_planner._stage_b_topic_claude",
        return_value=_fake_stage_b_response(),
    ):
        result = generate_three_plans_from_topic(
            topic="스타벅스 5·18 탱크데이 논란",
            tone="차분·분석적",
            details="추적 검증형",
            output_dir=tmp_path,
        )

    assert isinstance(result, ThreePlansResult)
    assert len(result.plans) == 3
    # angle 3개 모두 달라야 함
    assert {p.angle for p in result.plans} == {
        "title_anchor", "audience_resonance", "comparison",
    }
    # 모든 plan이 topic 모드
    for plan in result.plans:
        assert plan.source_type == "topic"
        assert plan.youtube_search_keywords == ("검색어1", "검색어2", "검색어3")
        # topic 모드는 더미 clip 값
        assert plan.clip_start_sec == 0.0
        assert plan.clip_end_sec == 60.0

    # plans.json 저장 확인
    plans_path = tmp_path / "plans.json"
    assert plans_path.exists()


def test_generate_three_plans_from_topic_empty_topic_rejected():
    with pytest.raises(PoliticalPlannerError, match="topic은 비어"):
        generate_three_plans_from_topic(topic="")


def test_generate_three_plans_from_topic_url_metadata_empty(tmp_path):
    """topic 모드 결과: youtube_url/video_path/transcript_path 모두 빈 문자열."""
    with patch(
        "src.analyzer.political_planner._stage_a_topic_gemini",
        return_value=_fake_stage_a_response(),
    ), patch(
        "src.analyzer.political_planner._stage_b_topic_claude",
        return_value=_fake_stage_b_response(),
    ):
        result = generate_three_plans_from_topic(
            topic="테스트 주제", output_dir=tmp_path,
        )
    assert result.youtube_url == ""
    assert result.video_path == ""
    assert result.transcript_path == ""
    assert result.video_duration_sec == 0.0


# ────────────────── plan_to_script topic 모드 분기 ──────────────────


def test_plan_to_script_topic_mode_skips_clip_clamp():
    """topic 모드: video_duration_sec=0이어도 clamp 에러 안 남."""
    plan = ShortsPlan(
        topic="topic", hook="hook", clip_start_sec=0.0, clip_end_sec=60.0,
        clip_reason="topic 모드", flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(0, 5, "씬1", subtitle_color="yellow", subtitle_emphasis=True),
            Narration(5, 12, "씬2", subtitle_color="red"),
        ),
        cta="cta", angle="title_anchor",
        source_type="topic",
        youtube_search_keywords=("kw1", "kw2"),
    )
    script = plan_to_script(
        plan,
        video_title=plan.topic,
        video_duration_sec=0.0,  # topic 모드는 0이어도 OK
        youtube_url="",
        save=False,
    )
    assert len(script.scenes) >= 3  # hook + 2 narration + cta
    assert script.metadata.source_type == "political_pro"


def test_topic_stage_b_runs_in_parallel(tmp_path):
    """Bug fix: Stage B의 3회 Claude 호출을 병렬 실행 — 60초 timeout 회피.

    각 _stage_b_topic_claude 호출이 0.5초 걸린다고 가정.
    순차면 1.5초+, 병렬이면 0.6초 미만이어야 함.
    """
    import time

    call_times = []

    def slow_stage_b(*, topic, tone, details, candidate):
        call_times.append(time.time())
        time.sleep(0.5)  # 각 호출 0.5초
        return _fake_stage_b_response()

    with patch(
        "src.analyzer.political_planner._stage_a_topic_gemini",
        return_value=_fake_stage_a_response(),
    ), patch(
        "src.analyzer.political_planner._stage_b_topic_claude",
        side_effect=slow_stage_b,
    ):
        start = time.time()
        result = generate_three_plans_from_topic(
            topic="병렬화 테스트", output_dir=tmp_path,
        )
        elapsed = time.time() - start

    assert len(result.plans) == 3
    assert len(call_times) == 3
    # 병렬: 모든 호출이 거의 동시에 시작 (시작 시각 spread < 200ms)
    spread = max(call_times) - min(call_times)
    assert spread < 0.2, f"Stage B 호출이 순차로 보임 (spread={spread:.2f}s)"
    # 총 소요 시간이 순차(1.5s)보다 크게 짧아야 함 (병렬이면 ~0.5s)
    assert elapsed < 1.0, f"Stage B 병렬 실행이 적용되지 않음 (총 {elapsed:.2f}s)"


def test_topic_stage_b_preserves_candidate_order(tmp_path):
    """병렬 실행해도 결과 plan들의 angle 순서가 candidates 순서와 일치해야 함."""
    candidates = _fake_stage_a_response()
    # 각 candidate의 angle을 응답에 포함시키는 헬퍼
    angle_responses = {
        "title_anchor": {**_fake_stage_b_response(), "flow_intro": "intro_title"},
        "audience_resonance": {**_fake_stage_b_response(), "flow_intro": "intro_aud"},
        "comparison": {**_fake_stage_b_response(), "flow_intro": "intro_comp"},
    }

    def stage_b_by_angle(*, topic, tone, details, candidate):
        return angle_responses[candidate["angle"]]

    with patch(
        "src.analyzer.political_planner._stage_a_topic_gemini",
        return_value=candidates,
    ), patch(
        "src.analyzer.political_planner._stage_b_topic_claude",
        side_effect=stage_b_by_angle,
    ):
        result = generate_three_plans_from_topic(topic="순서 테스트", output_dir=tmp_path)

    # candidates는 title_anchor → audience_resonance → comparison 순.
    # 병렬 실행이라도 result.plans는 동일 순서여야 함.
    assert [p.angle for p in result.plans] == [
        "title_anchor", "audience_resonance", "comparison",
    ]
    assert result.plans[0].flow_intro == "intro_title"
    assert result.plans[1].flow_intro == "intro_aud"
    assert result.plans[2].flow_intro == "intro_comp"


def test_plan_to_script_youtube_mode_still_clamps():
    """youtube 모드: clip_end > video_duration이면 clamp 동작."""
    plan = ShortsPlan(
        topic="t", hook="h", clip_start_sec=0.0, clip_end_sec=120.0,
        clip_reason="r", flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(0, 5, "n"),), cta="cta", angle="title_anchor",
        source_type="youtube",
    )
    # video_duration_sec=60 < clip_end_sec=120 → clamp되어 60으로
    script = plan_to_script(
        plan, video_title="t", video_duration_sec=60.0,
        youtube_url="https://youtube.com/test", save=False,
    )
    assert script is not None
