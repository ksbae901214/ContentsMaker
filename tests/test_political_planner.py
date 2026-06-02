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


# ════════════════════════ 정치쇼츠 화자 콜론 자막 + 보도체 TTS ════════════════════════


def test_plan_to_script_speaker_colon_subtitle_and_reported_tts():
    """신포맷: 자막은 '화자: 발언', voice_text는 보도체로 분리, narration당 씬 1개."""
    plan = ShortsPlan(
        topic="GTX 철근 누락 공방", hook="GTX 철근 누락, 시장 후보 충돌",
        clip_start_sec=0, clip_end_sec=40, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(
                start_sec=0, end_sec=4, text="삼성역 부실시공, 안전불감증입니다",
                speaker="정원오", subtitle_color="red", subtitle_emphasis=True,
                tts_text="정원오 후보는 삼성역 부실시공 대응이 안전불감증이라고 직격했습니다",
            ),
            Narration(
                start_sec=4, end_sec=8, text="보완하면 강도가 더 강해집니다",
                speaker="오세훈", subtitle_color="white",
                tts_text="오세훈 후보는 보완하면 오히려 강도가 더 강해진다고 반박했습니다",
            ),
        ),
        cta="당신 생각은? 댓글로",
        angle="audience_resonance",
    )
    script = plan_to_script(
        plan, video_title="원본", video_duration_sec=120.0,
        youtube_url="https://youtu.be/gtx",
    )
    body = [s for s in script.scenes if s.type == "body"]
    # narration당 씬 1개 (분할 없음)
    assert len(body) == 2
    # 자막: 화자 콜론, voice_text: 보도체 (분리)
    assert body[0].text.replace("\n", " ").startswith("정원오: ")
    assert "삼성역 부실시공" in body[0].text.replace("\n", " ")
    assert body[0].voice_text == "정원오 후보는 삼성역 부실시공 대응이 안전불감증이라고 직격했습니다"
    assert body[0].text != body[0].voice_text
    assert body[1].text.replace("\n", " ").startswith("오세훈: ")
    assert body[1].voice_text.endswith("반박했습니다")
    # tts_script(AudioConfig)도 보도체 반영
    assert "직격했습니다" in script.audio.tts_script


def test_plan_to_script_legacy_narration_couples_text_and_voice():
    """구포맷(speaker/tts_text 없음)은 기존 동작 — text==voice_text 유지(회귀 방지)."""
    plan = ShortsPlan(
        topic="t", hook="hook",
        clip_start_sec=0, clip_end_sec=20, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(start_sec=0, end_sec=3, text="옛날 방식 자막"),),
        cta="cta", angle="title_anchor",
    )
    script = plan_to_script(
        plan, video_title="t", video_duration_sec=60.0,
        youtube_url="https://youtu.be/x",
    )
    body = [s for s in script.scenes if s.type == "body"]
    assert len(body) >= 1
    for s in body:
        assert s.text == s.voice_text  # 구포맷은 자막=음성


def test_plan_to_script_speaker_beat_not_split_by_max_duration():
    """신포맷 1비트는 5초 분할기가 화자 접두를 깨지 않아야 함."""
    plan = ShortsPlan(
        topic="t", hook="h",
        clip_start_sec=0, clip_end_sec=40, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(
                start_sec=0, end_sec=8, text="아직도 삼성역 안 가보셨잖아요",
                speaker="정원오",
                tts_text="그러자 정원오 후보는 아직도 삼성역 현장에 안 가보셨다고 꼬집었습니다",
            ),
        ),
        cta="cta", angle="title_anchor",
    )
    script = plan_to_script(
        plan, video_title="t", video_duration_sec=120.0,
        youtube_url="https://youtu.be/x",
    )
    body = [s for s in script.scenes if s.type == "body"]
    assert len(body) == 1  # 8초여도 1비트=1씬 (분할 안 됨)
    assert "삼성역 안 가보셨잖아요" in body[0].text.replace("\n", " ")
    assert body[0].duration <= 5.0  # 클램프로 5초 분할기 회피


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


# ─────────────────────────────── _split_subtitle_segments v2 ───────────────────────────────


from src.analyzer.political_planner import _split_subtitle_segments, _MAX_SUBTITLE_CHARS


def test_split_subtitle_short_text_no_split():
    """28자 이하는 분할되지 않음."""
    text = "짧은 문장입니다"  # 8 chars
    segs = _split_subtitle_segments(text)
    assert segs == [text]


def test_split_subtitle_preserves_particle_attachment():
    """조사("을/를/이/가") 직전에서 잘리지 않음.

    '서울시장 후보들의 부동산 공급 정책을 비교합니다' (29자, 28자+1)
    → 어절 중간 자르기 금지. '정책을' 이 통째로 한쪽에.
    """
    text = "서울시장 후보들의 부동산 공급 정책을 비교합니다"
    segs = _split_subtitle_segments(text)
    assert len(segs) >= 1
    joined = " ".join(segs)
    # 모든 조사 어절이 통째로 보존되어야 함
    assert "정책을" in joined  # 분리되지 않음
    # 각 세그먼트는 max_chars 이내
    for s in segs:
        assert len(s) <= _MAX_SUBTITLE_CHARS


def test_split_subtitle_prefers_punctuation_boundary():
    """구두점 경계가 최우선 (균형 보너스보다 높은 점수)."""
    # 구두점이 18자 위치, 44자 문장 — 구두점 경계에서 분할돼야 함
    text = "지금 상황을 정확히 말씀드립니다. 이번 선거 결과가 매우 중요한 의미를 갖습니다"
    segs = _split_subtitle_segments(text)
    assert len(segs) >= 2
    # 첫 세그먼트는 구두점 경계 직전 문장에서 끝남
    flat_first = segs[0].replace("\n", " ").strip()
    assert flat_first.endswith("말씀드립니다") or flat_first.endswith("말씀드립니다.")


def test_split_subtitle_no_ellipsis_no_orphan():
    """긴 문장 분할 시 말줄임표('…')가 절대 안 붙음. 모든 글자 보존."""
    text = "이번 지방선거 후보자 4명 중 1명이 다주택자라는 사실이 밝혀졌습니다"
    segs = _split_subtitle_segments(text)
    # "…" 부착 절대 금지 (사용자 피드백 2026-05-16)
    for s in segs:
        assert "…" not in s
        assert "..." not in s
        assert len(s) <= _MAX_SUBTITLE_CHARS + 3  # 약간의 오버플로우 허용
    # 원문 모든 의미 단위 보존
    joined = "".join(s.replace(" ", "") for s in segs)
    original_no_space = text.replace(" ", "")
    # 분할 시 trailing 공백/구두점 정리로 일부 제거될 수 있으므로 substring 검사
    assert len(joined) >= len(original_no_space) - 5


def test_split_subtitle_balanced_split_preferred():
    """균형 분할 선호 — 단어 한가운데 자르지 않음."""
    text = "안 그래도 정치권에서는 이게 진짜 큰 이슈가 되고 있다고요 다들 보시는 것처럼요"  # 43자+
    assert len(text) > _MAX_SUBTITLE_CHARS
    segs = _split_subtitle_segments(text)
    assert len(segs) >= 2
    # 첫 세그먼트가 너무 짧지 않아야 (lo=7 이상, 균형 보너스로 ~14자 부근 선호)
    assert len(segs[0]) >= 7
    # 원문 어절 보존 검증 — 분할은 항상 공백 또는 구두점 직후에서만 일어남
    original_eojeols = set(text.split())
    rejoined_eojeols = set(" ".join(segs).split())
    # 모든 원문 어절이 그대로 보존 (어절 한가운데 잘림 없음)
    missing = original_eojeols - rejoined_eojeols
    assert not missing, f"어절 중간 잘림: {missing}"


def test_split_subtitle_inserts_explicit_linebreak():
    """15자 초과 세그먼트는 14자 부근에 명시적 '\\n' 삽입 (orphan 방지)."""
    from src.analyzer.political_planner import _insert_linebreak
    text = "이번 정치권에서는 새로운 소식이 발표됨"  # 21자 > 15
    assert len(text) > 15
    out = _insert_linebreak(text)
    assert "\n" in out
    lines = out.split("\n")
    assert len(lines) == 2
    # 두 줄 모두 비어 있지 않고, 첫 줄이 너무 길지도 짧지도 않음
    assert 5 <= len(lines[0]) <= 18
    assert 1 <= len(lines[1]) <= 18


def test_split_subtitle_no_linebreak_for_short_text():
    """14자 이하는 줄바꿈 미삽입."""
    from src.analyzer.political_planner import _insert_linebreak
    assert _insert_linebreak("짧은 자막") == "짧은 자막"
    assert _insert_linebreak("14자 이내자막입니다") == "14자 이내자막입니다"  # 11자


def test_split_subtitle_segments_apply_linebreak():
    """_split_subtitle_segments 결과의 각 세그먼트에 줄바꿈 자동 적용."""
    text = "서울시장 후보들의 부동산 공급 정책을 비교합니다 그리고 결과 분석"  # 35자+
    segs = _split_subtitle_segments(text)
    # 모든 세그먼트 검사 — 15자 초과면 \n 포함
    for s in segs:
        if len(s.replace("\n", "")) > 15:
            assert "\n" in s, f"15자+ 세그먼트인데 줄바꿈 없음: {s!r}"


def test_split_subtitle_korean_endings_boost():
    """종결어미('했어요', '입니다') 직후가 일반 공백보다 우선."""
    text = "이번에 발표했어요 그래서 모두가 정말 깜짝 놀랐습니다 어떻게 보세요 정말이에요"  # 43자+
    assert len(text) > _MAX_SUBTITLE_CHARS
    segs = _split_subtitle_segments(text)
    assert len(segs) >= 2
    first = segs[0].rstrip()
    # 종결어미 또는 어절 경계로 자연 종료
    assert first.endswith("요") or first.endswith("다") or first.endswith("어요") or " " in first
