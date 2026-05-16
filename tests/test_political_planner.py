"""Tests for political_planner — generate_three_plans + plan_to_script.

Covers FR-004, FR-006, FR-008, FR-011, FR-012, FR-013.
Claude CLI is mocked via subprocess monkey-patching (no real network calls).
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.analyzer.political_plan_models import (
    Narration,
    ShortsPlan,
    ThreePlansResult,
)
from src.analyzer.political_planner import (
    PoliticalPlannerError,
    generate_three_plans,
    plan_to_script,
)


# ─────────────────────────────── Fixtures ───────────────────────────────


SAMPLE_TRANSCRIPT = [
    {"start": 0.0, "end": 5.0, "text": "안녕하세요 국회의원 ○○○입니다"},
    {"start": 5.0, "end": 12.0, "text": "오늘 본회의에서 중요한 사안에 대해 발언하겠습니다"},
    {"start": 12.0, "end": 30.0, "text": "이번 법안은 국민에게 직접적인 영향을 미칩니다"},
    {"start": 30.0, "end": 60.0, "text": "구체적인 통계는 다음과 같습니다 — 작년 대비 30% 증가"},
    {"start": 60.0, "end": 90.0, "text": "이에 대해 정부의 책임 있는 답변을 요구합니다"},
]


def _build_plan_dict(angle: str, topic: str = "샘플 주제", clip_start: float = 0.0, clip_end: float = 30.0) -> dict:
    return {
        "topic": topic,
        "hook": f"이것이 ({angle}) 핵심입니다",
        "clip_start_sec": clip_start,
        "clip_end_sec": clip_end,
        "clip_reason": "강도 높은 구간",
        "flow_intro": "시작 묘사",
        "flow_middle": "중간 묘사",
        "flow_climax": "클라이맥스 묘사",
        "narrations": [
            {"start_sec": 0, "end_sec": 3, "text": "지금 이 장면"},
            {"start_sec": 3, "end_sec": 7, "text": "발언 그대로"},
        ],
        "cta": "공감되시면 좋아요",
        "angle": angle,
    }


def _claude_response(plans: list[dict]) -> str:
    return json.dumps({"plans": plans}, ensure_ascii=False)


# ─────────────────────────────── generate_three_plans ───────────────────────────────


def test_generate_three_plans_happy_path():
    """정상 응답 → 3개 ShortsPlan 파싱."""
    mock_raw = _claude_response([
        _build_plan_dict("title_anchor"),
        _build_plan_dict("audience_resonance"),
        _build_plan_dict("comparison"),
    ])

    with patch("src.analyzer.political_planner._call_claude", return_value=mock_raw):
        result = generate_three_plans(
            use_hybrid=False,
            youtube_url="https://youtu.be/abc",
            transcript=SAMPLE_TRANSCRIPT,
            video_title="국회 본회의",
            video_duration_sec=90.0,
        )

    assert isinstance(result, ThreePlansResult)
    assert len(result.plans) == 3
    angles = {p.angle for p in result.plans}
    assert angles == {"title_anchor", "audience_resonance", "comparison"}


def test_generate_three_plans_retry_on_first_failure():
    """첫 호출 JSON 파싱 실패 → 1회 자동 재시도 후 성공."""
    valid = _claude_response([
        _build_plan_dict("title_anchor"),
        _build_plan_dict("audience_resonance"),
        _build_plan_dict("comparison"),
    ])
    responses = iter(["NOT_JSON_GARBAGE", valid])

    with patch(
        "src.analyzer.political_planner._call_claude",
        side_effect=lambda *a, **kw: next(responses),
    ):
        result = generate_three_plans(
            use_hybrid=False,
            youtube_url="https://youtu.be/abc",
            transcript=SAMPLE_TRANSCRIPT,
            video_title="t",
            video_duration_sec=90.0,
        )

    assert len(result.plans) == 3


def test_generate_three_plans_fails_after_retries():
    """두 번 모두 실패 → PoliticalPlannerError."""
    with patch(
        "src.analyzer.political_planner._call_claude",
        return_value="STILL_NOT_JSON",
    ):
        with pytest.raises(PoliticalPlannerError):
            generate_three_plans(
                use_hybrid=False,
                youtube_url="https://youtu.be/abc",
                transcript=SAMPLE_TRANSCRIPT,
                video_title="t",
                video_duration_sec=90.0,
            )


def test_generate_three_plans_rejects_duplicate_angles():
    """3개 plan의 angle이 중복이면 ThreePlansResult 검증에서 실패."""
    mock_raw = _claude_response([
        _build_plan_dict("title_anchor"),
        _build_plan_dict("title_anchor"),  # duplicate
        _build_plan_dict("comparison"),
    ])
    with patch("src.analyzer.political_planner._call_claude", return_value=mock_raw):
        with pytest.raises(PoliticalPlannerError):
            generate_three_plans(
                use_hybrid=False,
                youtube_url="https://youtu.be/abc",
                transcript=SAMPLE_TRANSCRIPT,
                video_title="t",
                video_duration_sec=90.0,
            )


def test_generate_three_plans_clamps_clip_end_to_video_duration():
    """clip_end_sec이 video_duration을 초과하면 자동 클램프 — FR-013."""
    mock_raw = _claude_response([
        _build_plan_dict("title_anchor", clip_start=0, clip_end=999.0),  # over
        _build_plan_dict("audience_resonance", clip_start=10, clip_end=40),
        _build_plan_dict("comparison", clip_start=20, clip_end=50),
    ])
    with patch("src.analyzer.political_planner._call_claude", return_value=mock_raw):
        result = generate_three_plans(
            use_hybrid=False,
            youtube_url="https://youtu.be/abc",
            transcript=SAMPLE_TRANSCRIPT,
            video_title="t",
            video_duration_sec=90.0,
        )

    assert result.plans[0].clip_end_sec <= 90.0
    assert result.plans[0].clip_end_sec == 90.0  # clamped


# ─────────────────────────────── plan_to_script ───────────────────────────────


def test_plan_to_script_basic_mapping(tmp_path):
    plan = ShortsPlan(
        topic="중요 사안 발언",
        hook="이 장면 놓치면 안 됩니다",
        clip_start_sec=10.0,
        clip_end_sec=40.0,
        clip_reason="강조 발언 구간",
        flow_intro="시작",
        flow_middle="중간",
        flow_climax="강조",
        narrations=(
            Narration(start_sec=0, end_sec=3, text="첫 나레이션"),
            Narration(start_sec=3, end_sec=7, text="두 번째"),
            Narration(start_sec=7, end_sec=10, text="세 번째"),
        ),
        cta="공감되시면 좋아요",
        angle="title_anchor",
    )

    script = plan_to_script(
        plan,
        video_title="원본 영상",
        video_duration_sec=120.0,
        youtube_url="https://youtu.be/abc",
    )

    assert script.metadata.source_type == "political_pro"
    assert script.metadata.source_url == "https://youtu.be/abc"
    assert script.metadata.title == "중요 사안 발언"

    # 첫 씬과 마지막 씬은 hook/cta로 시작·끝
    assert "이 장면" in script.scenes[0].text or script.scenes[0].text == plan.hook
    assert plan.cta in script.scenes[-1].text


def test_plan_to_script_enforces_max_scene_duration():
    """5초 초과 씬은 자동 분할 — FR-012."""
    plan = ShortsPlan(
        topic="t",
        hook="hook",
        clip_start_sec=0,
        clip_end_sec=30,
        clip_reason="r",
        flow_intro="i",
        flow_middle="m",
        flow_climax="c",
        narrations=(
            Narration(start_sec=0, end_sec=8, text="긴 나레이션 하나 둘 셋 넷 다섯 여섯 일곱 여덟"),
        ),
        cta="cta",
        angle="title_anchor",
    )
    script = plan_to_script(
        plan,
        video_title="t",
        video_duration_sec=120.0,
        youtube_url="https://youtu.be/x",
    )
    # 모든 씬의 duration ≤ 5.0
    for s in script.scenes:
        assert s.duration <= 5.0, f"Scene {s.id} duration {s.duration} > 5.0"


def test_plan_to_script_clamps_clip_end_to_video_duration():
    """clip_end_sec이 video_duration 초과 시 클램프 — FR-013."""
    plan = ShortsPlan(
        topic="t",
        hook="h",
        clip_start_sec=0,
        clip_end_sec=120,  # will be clamped to video_duration
        clip_reason="r",
        flow_intro="i",
        flow_middle="m",
        flow_climax="c",
        narrations=(Narration(start_sec=0, end_sec=3, text="x"),),
        cta="cta",
        angle="title_anchor",
    )
    # plan_to_script는 ShortsScript를 반환; 클램프된 clip 정보가 어딘가에 들어가야 함.
    # video_duration_sec=60 → clip_end 60으로 클램프되어야.
    script = plan_to_script(
        plan,
        video_title="t",
        video_duration_sec=60.0,
        youtube_url="https://youtu.be/x",
    )
    # script.metadata.duration은 clip 길이를 반영해야 하며 최대 60초
    assert script.metadata.duration <= 60.0


# ════════════════════════ V2 통합 테스트 (Feature 011) ════════════════════════


def test_plan_to_script_preserves_v2_fields():
    """V2 필드(format_type, format_reason, visual_directives)가 ShortsScript.metadata에 보존."""
    plan = ShortsPlan(
        topic="V2 테스트", hook="hook",
        clip_start_sec=0, clip_end_sec=20, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(start_sec=0, end_sec=3, text="첫줄", subtitle_color="red", subtitle_emphasis=True),
            Narration(start_sec=3, end_sec=6, text="둘째", subtitle_color="yellow"),
        ),
        cta="이 발언, 어떻게 보세요? 댓글 남겨주세요",
        angle="title_anchor",
        format_type="B",
        format_reason="현장 발화 — 뉴스핌 스타일",
        visual_directives=(
            "0~3초: 좌(과거 발언) 우(현재 발언) 분할",
            "12초 부근 핵심 키워드 붉은 자막",
        ),
    )
    script = plan_to_script(
        plan, video_title="원본",
        video_duration_sec=120.0,
        youtube_url="https://youtu.be/v2",
    )
    assert script.metadata.format_type == "B"
    assert "뉴스핌" in script.metadata.format_reason
    assert len(script.metadata.visual_directives) == 2
    assert "0~3초" in script.metadata.visual_directives[0]


def test_generate_three_plans_legacy_with_v2_fields():
    """Legacy(_call_claude mock) 경로에서 V2 필드 포함된 응답을 정상 파싱."""
    import json
    from unittest.mock import patch
    from src.analyzer.political_planner import generate_three_plans

    def _v2_plan(angle, fmt="A"):
        return {
            "topic": f"주제-{angle}", "hook": "hook",
            "clip_start_sec": 0, "clip_end_sec": 30, "clip_reason": "r",
            "flow_intro": "i", "flow_middle": "m", "flow_climax": "c",
            "narrations": [
                {"start_sec": 0, "end_sec": 3, "text": "x", "subtitle_color": "red", "subtitle_emphasis": True},
            ],
            "cta": "어떻게 보세요? 댓글 남겨주세요",
            "angle": angle,
            "format_type": fmt,
            "format_reason": "분류 이유",
            "visual_directives": ["좌우 분할"],
        }

    mock_raw = json.dumps({
        "plans": [_v2_plan("title_anchor", "A"), _v2_plan("audience_resonance", "B"), _v2_plan("comparison", "A")],
    }, ensure_ascii=False)

    with patch("src.analyzer.political_planner._call_claude", return_value=mock_raw):
        result = generate_three_plans(
            use_hybrid=False,
            youtube_url="https://youtu.be/x",
            transcript=SAMPLE_TRANSCRIPT,
            video_title="t",
            video_duration_sec=120.0,
        )

    assert result.plans[0].format_type == "A"
    assert result.plans[1].format_type == "B"
    assert result.plans[0].narrations[0].subtitle_color == "red"
    assert result.plans[0].narrations[0].subtitle_emphasis is True
    assert "좌우 분할" in result.plans[0].visual_directives[0]


def test_v1_plans_json_loads_with_v2_models(tmp_path):
    """V1 JSON 파일(V2 필드 부재) → V2 모델로 정상 로드 (default 적용)."""
    from src.analyzer.political_plan_models import ShortsPlan
    v1_only_dict = {
        "topic": "V1 plan", "hook": "h",
        "clip_start_sec": 0, "clip_end_sec": 10, "clip_reason": "r",
        "flow_intro": "i", "flow_middle": "m", "flow_climax": "c",
        "narrations": [{"start_sec": 0, "end_sec": 3, "text": "x"}],
        "cta": "cta", "angle": "title_anchor",
    }
    plan = ShortsPlan.from_dict(v1_only_dict)
    # V2 default가 자동 적용
    assert plan.format_type == "A"
    assert plan.format_reason == ""
    assert plan.visual_directives == ()
    assert plan.narrations[0].subtitle_color == "white"
    assert plan.narrations[0].subtitle_emphasis is False
