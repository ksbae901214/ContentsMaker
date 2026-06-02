"""Tests for political plan data models (Feature 009).

Covers: ShortsPlan, Narration, ThreePlansResult — round-trip + validation.
"""
from __future__ import annotations

import pytest

from src.analyzer.political_plan_models import (
    Narration,
    ShortsPlan,
    ThreePlansResult,
    PlanValidationError,
)


# ─────────────────────────────── Narration ───────────────────────────────


def test_narration_round_trip():
    n = Narration(start_sec=0.0, end_sec=3.0, text="지금 이 장면, 그냥 넘어가면 안 됩니다")
    d = n.to_dict()
    assert d == {"start_sec": 0.0, "end_sec": 3.0, "text": "지금 이 장면, 그냥 넘어가면 안 됩니다"}
    restored = Narration.from_dict(d)
    assert restored == n


def test_narration_accepts_camel_case():
    n = Narration.from_dict({"startSec": 3.0, "endSec": 7.0, "text": "hello"})
    assert n.start_sec == 3.0
    assert n.end_sec == 7.0


def test_narration_rejects_empty_text():
    with pytest.raises(PlanValidationError):
        Narration(start_sec=0, end_sec=3, text="")


def test_narration_rejects_inverted_range():
    with pytest.raises(PlanValidationError):
        Narration(start_sec=5, end_sec=3, text="x")


def test_narration_speaker_and_tts_round_trip():
    """정치쇼츠 신포맷: speaker + tts_text 직렬화/역직렬화."""
    n = Narration(
        start_sec=0.0, end_sec=4.0, text="삼성역 부실시공, 안전불감증입니다",
        speaker="정원오",
        tts_text="정원오 후보는 삼성역 부실시공 대응이 안전불감증이라고 직격했습니다",
    )
    d = n.to_dict()
    assert d["speaker"] == "정원오"
    assert d["tts_text"].endswith("직격했습니다")
    restored = Narration.from_dict(d)
    assert restored == n


def test_narration_speaker_tts_default_empty():
    """누락 시 speaker/tts_text는 빈 문자열 (V1/V2 호환)."""
    n = Narration.from_dict({"start_sec": 0, "end_sec": 3, "text": "x"})
    assert n.speaker == ""
    assert n.tts_text == ""


def test_narration_to_dict_omits_empty_speaker_tts():
    """기본값일 때 speaker/tts_text 키는 직렬화하지 않음 (V1 JSON 호환)."""
    n = Narration(start_sec=0, end_sec=3, text="x")
    d = n.to_dict()
    assert "speaker" not in d
    assert "tts_text" not in d


# ─────────────────────────────── ShortsPlan ───────────────────────────────


def _make_plan(angle: str = "title_anchor", topic: str = "샘플 주제") -> ShortsPlan:
    return ShortsPlan(
        topic=topic,
        hook="이 발언, 무시할 수 없습니다",
        clip_start_sec=45.0,
        clip_end_sec=75.0,
        clip_reason="발언 강도가 가장 높은 구간",
        flow_intro="장면 시작",
        flow_middle="발언 클립",
        flow_climax="강조 마무리",
        narrations=(
            Narration(start_sec=0, end_sec=3, text="지금 이 장면"),
            Narration(start_sec=3, end_sec=7, text="발언 그대로"),
        ),
        cta="공감되시면 좋아요 부탁드립니다",
        angle=angle,
    )


def test_shortsplan_round_trip():
    p = _make_plan()
    d = p.to_dict()
    restored = ShortsPlan.from_dict(d)
    assert restored == p


def test_shortsplan_round_trip_camel_case():
    p = _make_plan()
    d = p.to_dict()
    # Convert to camelCase for cross-language compat (Remotion / TS client).
    camel = {
        "topic": d["topic"],
        "hook": d["hook"],
        "clipStartSec": d["clip_start_sec"],
        "clipEndSec": d["clip_end_sec"],
        "clipReason": d["clip_reason"],
        "flowIntro": d["flow_intro"],
        "flowMiddle": d["flow_middle"],
        "flowClimax": d["flow_climax"],
        "narrations": [
            {"startSec": n["start_sec"], "endSec": n["end_sec"], "text": n["text"]}
            for n in d["narrations"]
        ],
        "cta": d["cta"],
        "angle": d["angle"],
    }
    restored = ShortsPlan.from_dict(camel)
    assert restored == p


def test_shortsplan_rejects_empty_topic():
    with pytest.raises(PlanValidationError):
        ShortsPlan(
            topic="",
            hook="h",
            clip_start_sec=0,
            clip_end_sec=10,
            clip_reason="r",
            flow_intro="i",
            flow_middle="m",
            flow_climax="c",
            narrations=(Narration(start_sec=0, end_sec=3, text="t"),),
            cta="cta",
            angle="title_anchor",
        )


def test_shortsplan_rejects_inverted_clip_range():
    with pytest.raises(PlanValidationError):
        ShortsPlan(
            topic="t",
            hook="h",
            clip_start_sec=75,
            clip_end_sec=45,
            clip_reason="r",
            flow_intro="i",
            flow_middle="m",
            flow_climax="c",
            narrations=(Narration(start_sec=0, end_sec=3, text="t"),),
            cta="cta",
            angle="title_anchor",
        )


def test_shortsplan_rejects_invalid_angle():
    with pytest.raises(PlanValidationError):
        ShortsPlan(
            topic="t",
            hook="h",
            clip_start_sec=0,
            clip_end_sec=10,
            clip_reason="r",
            flow_intro="i",
            flow_middle="m",
            flow_climax="c",
            narrations=(Narration(start_sec=0, end_sec=3, text="t"),),
            cta="cta",
            angle="invalid_angle",
        )


def test_shortsplan_rejects_empty_narrations():
    with pytest.raises(PlanValidationError):
        ShortsPlan(
            topic="t",
            hook="h",
            clip_start_sec=0,
            clip_end_sec=10,
            clip_reason="r",
            flow_intro="i",
            flow_middle="m",
            flow_climax="c",
            narrations=(),
            cta="cta",
            angle="title_anchor",
        )


def test_shortsplan_frozen():
    p = _make_plan()
    with pytest.raises((AttributeError, Exception)):
        p.topic = "mutated"  # type: ignore[misc]


# ─────────────────────────────── ThreePlansResult ───────────────────────────────


def test_three_plans_result_round_trip():
    r = ThreePlansResult(
        plans=(
            _make_plan(angle="title_anchor"),
            _make_plan(angle="audience_resonance"),
            _make_plan(angle="comparison"),
        ),
        youtube_url="https://youtu.be/abc123",
        video_path="/tmp/source.mp4",
        video_duration_sec=612.4,
        transcript_path="/tmp/transcript.json",
        video_title="원본 영상 제목",
        generated_at="2026-05-13T18:45:00+09:00",
    )
    d = r.to_dict()
    restored = ThreePlansResult.from_dict(d)
    assert restored == r


def test_three_plans_result_requires_exactly_three():
    with pytest.raises(PlanValidationError):
        ThreePlansResult(
            plans=(_make_plan(),),  # type: ignore[arg-type]
            youtube_url="https://youtu.be/x",
            video_path="/tmp/x.mp4",
            video_duration_sec=60.0,
            transcript_path="/tmp/t.json",
            video_title="t",
            generated_at="2026-05-13T00:00:00+09:00",
        )


def test_three_plans_result_requires_distinct_angles():
    with pytest.raises(PlanValidationError):
        ThreePlansResult(
            plans=(
                _make_plan(angle="title_anchor"),
                _make_plan(angle="title_anchor"),  # duplicate
                _make_plan(angle="comparison"),
            ),
            youtube_url="https://youtu.be/x",
            video_path="/tmp/x.mp4",
            video_duration_sec=60.0,
            transcript_path="/tmp/t.json",
            video_title="t",
            generated_at="2026-05-13T00:00:00+09:00",
        )


# ════════════════════════ V2 (gemini-code 지침) — Feature 011 ════════════════════════
# A/B 포맷 분류 + 자막 색·강조 + 시각연출 지시. V1 호환은 default fallback으로 보장.


def test_narration_v2_subtitle_color_and_emphasis():
    n = Narration(
        start_sec=0, end_sec=3, text="t",
        subtitle_color="red", subtitle_emphasis=True,
    )
    d = n.to_dict()
    assert d.get("subtitle_color") == "red"
    assert d.get("subtitle_emphasis") is True
    restored = Narration.from_dict(d)
    assert restored == n


def test_narration_v1_backward_compat_default_color():
    """V1 JSON (color/emphasis 필드 없음) → default white/False."""
    n = Narration.from_dict({"start_sec": 0, "end_sec": 3, "text": "t"})
    assert n.subtitle_color == "white"
    assert n.subtitle_emphasis is False


def test_narration_subtitle_color_whitelist():
    """허용 색만 통과: white/red/yellow/blue."""
    for c in ["white", "red", "yellow", "blue"]:
        Narration(start_sec=0, end_sec=3, text="t", subtitle_color=c)  # ok
    with pytest.raises(PlanValidationError):
        Narration(start_sec=0, end_sec=3, text="t", subtitle_color="purple")


def test_shortsplan_v2_format_type_and_directives():
    plan = ShortsPlan(
        topic="t", hook="h",
        clip_start_sec=0, clip_end_sec=10, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(start_sec=0, end_sec=3, text="x"),),
        cta="cta", angle="title_anchor",
        format_type="A", format_reason="MBC 라디오 시사 스타일 — 논리 충돌이 명확",
        visual_directives=("0~3초 좌:과거 우:현재 분할", "핵심 키워드 붉은 자막"),
    )
    d = plan.to_dict()
    assert d.get("format_type") == "A"
    assert d.get("format_reason", "").startswith("MBC")
    assert "0~3초" in d.get("visual_directives", [])[0]
    restored = ShortsPlan.from_dict(d)
    assert restored == plan


def test_shortsplan_v1_backward_compat():
    """V1 JSON (format_type 등 부재) → default A타입, 빈 리스트."""
    v1_dict = {
        "topic": "t", "hook": "h",
        "clip_start_sec": 0, "clip_end_sec": 10, "clip_reason": "r",
        "flow_intro": "i", "flow_middle": "m", "flow_climax": "c",
        "narrations": [{"start_sec": 0, "end_sec": 3, "text": "x"}],
        "cta": "cta", "angle": "title_anchor",
    }
    plan = ShortsPlan.from_dict(v1_dict)
    assert plan.format_type == "A"  # default
    assert plan.format_reason == ""
    assert plan.visual_directives == ()
    # narrations도 V1 호환
    assert plan.narrations[0].subtitle_color == "white"


def test_shortsplan_format_type_only_a_or_b():
    with pytest.raises(PlanValidationError):
        ShortsPlan(
            topic="t", hook="h",
            clip_start_sec=0, clip_end_sec=10, clip_reason="r",
            flow_intro="i", flow_middle="m", flow_climax="c",
            narrations=(Narration(start_sec=0, end_sec=3, text="x"),),
            cta="cta", angle="title_anchor",
            format_type="C",  # invalid
        )


def test_shortsplan_v2_camel_case_round_trip():
    plan = ShortsPlan(
        topic="t", hook="h",
        clip_start_sec=0, clip_end_sec=10, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(Narration(start_sec=0, end_sec=3, text="x", subtitle_color="yellow"),),
        cta="cta", angle="title_anchor",
        format_type="B", format_reason="현장",
        visual_directives=("split",),
    )
    d = plan.to_dict()
    camel = {
        **d,
        "formatType": d["format_type"],
        "formatReason": d["format_reason"],
        "visualDirectives": d["visual_directives"],
        "narrations": [
            {**n, "subtitleColor": n.get("subtitle_color"),
             "subtitleEmphasis": n.get("subtitle_emphasis", False)}
            for n in d["narrations"]
        ],
    }
    # 양방향 호환
    restored = ShortsPlan.from_dict(camel)
    assert restored.format_type == "B"
    assert restored.narrations[0].subtitle_color == "yellow"
