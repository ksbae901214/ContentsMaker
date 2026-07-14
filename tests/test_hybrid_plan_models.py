"""Tests for src/analyzer/hybrid_plan_models.py.

Coverage targets: HybridBeat and HybridShortsPlan validation, serialization,
and round-trip integrity. No external API calls.
"""
from __future__ import annotations

import pytest

from src.analyzer.hybrid_plan_models import (
    MAX_KIND_SECONDS,
    MAX_TOTAL_SECONDS,
    MIN_KIND_SECONDS,
    HybridBeat,
    HybridShortsPlan,
    PlanValidationError,
    ThreeHybridPlansResult,
)


# ─── HybridBeat fixtures ──────────────────────────────────────────────────────

def _tts_beat(**kw) -> HybridBeat:
    defaults = dict(
        kind="tts",
        duration_sec=4.0,
        subtitle="이재명을 추궁한 국민의힘",
        tts_text="이 발언이 파장을 불러일으켰습니다.",
    )
    defaults.update(kw)
    return HybridBeat(**defaults)


def _orig_beat(**kw) -> HybridBeat:
    defaults = dict(
        kind="original",
        duration_sec=5.0,
        clip_start_sec=10.0,
        clip_end_sec=15.0,
        quote_lines=("저는 그렇게 말한 적 없습니다.",),
    )
    defaults.update(kw)
    return HybridBeat(**defaults)


# ─── valid plan fixture ────────────────────────────────────────────────────────

def _valid_plan(**kw) -> HybridShortsPlan:
    """Minimal valid plan: hook(TTS 4s) + orig(12s) + tts(8s) + orig(12s) + cta(4s).

    tts_sec = 4+8+4 = 16   ✓ [12, 32]
    orig_sec = 12+12 = 24  ✓ [12, 32]
    total = 40              ✓ ≤ 50
    """
    hook = _tts_beat(duration_sec=4.0)
    orig1 = _orig_beat(duration_sec=12.0, clip_start_sec=0.0, clip_end_sec=12.0)
    tts_mid = _tts_beat(duration_sec=8.0)
    orig2 = _orig_beat(duration_sec=12.0, clip_start_sec=20.0, clip_end_sec=32.0)
    cta = _tts_beat(duration_sec=4.0)
    defaults = dict(
        topic="이재명 발언 논란",
        hook=hook,
        beats=(orig1, tts_mid, orig2),
        cta=cta,
        angle="title_anchor",
        source_url="https://www.youtube.com/watch?v=test",
        source_channel="OBS뉴스",
        source_title="국감 장면",
    )
    defaults.update(kw)
    return HybridShortsPlan(**defaults)


# ────────────────────────────────────────────────────────────────────────────
# HybridBeat — TTS beat validation
# ────────────────────────────────────────────────────────────────────────────

class TestHybridBeatTts:
    def test_valid_tts_beat(self):
        b = _tts_beat()
        assert b.kind == "tts"
        assert b.duration_sec == 4.0
        assert b.subtitle == "이재명을 추궁한 국민의힘"

    def test_tts_beat_missing_subtitle_raises(self):
        with pytest.raises(PlanValidationError, match="subtitle"):
            _tts_beat(subtitle="")

    def test_tts_beat_missing_tts_text_raises(self):
        with pytest.raises(PlanValidationError, match="tts_text"):
            _tts_beat(tts_text="")

    def test_tts_beat_invalid_color_raises(self):
        with pytest.raises(PlanValidationError, match="subtitle_color"):
            _tts_beat(subtitle_color="purple")

    def test_tts_beat_all_valid_colors(self):
        for color in ("white", "red", "yellow", "blue"):
            b = _tts_beat(subtitle_color=color)
            assert b.subtitle_color == color

    def test_tts_beat_zero_duration_raises(self):
        with pytest.raises(PlanValidationError, match="duration_sec"):
            _tts_beat(duration_sec=0.0)

    def test_tts_beat_negative_duration_raises(self):
        with pytest.raises(PlanValidationError, match="duration_sec"):
            _tts_beat(duration_sec=-1.0)

    def test_tts_beat_emphasis_default_false(self):
        b = _tts_beat()
        assert b.subtitle_emphasis is False

    def test_tts_beat_emphasis_set(self):
        b = _tts_beat(subtitle_emphasis=True)
        assert b.subtitle_emphasis is True


# ────────────────────────────────────────────────────────────────────────────
# HybridBeat — original beat validation
# ────────────────────────────────────────────────────────────────────────────

class TestHybridBeatOriginal:
    def test_valid_original_beat(self):
        b = _orig_beat()
        assert b.kind == "original"
        assert b.clip_start_sec == 10.0
        assert b.clip_end_sec == 15.0

    def test_original_beat_clip_end_equal_start_raises(self):
        with pytest.raises(PlanValidationError, match="clip_end > clip_start"):
            _orig_beat(clip_start_sec=5.0, clip_end_sec=5.0)

    def test_original_beat_clip_end_before_start_raises(self):
        with pytest.raises(PlanValidationError, match="clip_end > clip_start"):
            _orig_beat(clip_start_sec=10.0, clip_end_sec=5.0)

    def test_original_beat_empty_quote_lines_raises(self):
        with pytest.raises(PlanValidationError, match="quote_lines"):
            _orig_beat(quote_lines=())

    def test_original_beat_too_many_quote_lines_raises(self):
        with pytest.raises(PlanValidationError, match="quote_lines"):
            _orig_beat(quote_lines=("A", "B", "C", "D"))

    def test_original_beat_max_3_quote_lines_ok(self):
        b = _orig_beat(quote_lines=("A", "B", "C"))
        assert len(b.quote_lines) == 3

    def test_original_beat_invalid_bgm_mode_raises(self):
        with pytest.raises(PlanValidationError, match="bgm_mode"):
            _orig_beat(bgm_mode="silent")

    def test_original_beat_all_bgm_modes(self):
        for mode in ("mute", "duck", "keep"):
            b = _orig_beat(bgm_mode=mode)
            assert b.bgm_mode == mode

    def test_original_beat_optional_source_label(self):
        b = _orig_beat(source_label="장동혁 대표 (Channel A)")
        assert b.source_label == "장동혁 대표 (Channel A)"

    def test_original_beat_optional_source_clip_path(self):
        b = _orig_beat(source_clip_path="/tmp/extra.mp4")
        assert b.source_clip_path == "/tmp/extra.mp4"


# ────────────────────────────────────────────────────────────────────────────
# HybridBeat — serialization (to_dict / from_dict)
# ────────────────────────────────────────────────────────────────────────────

class TestHybridBeatSerialization:
    def test_tts_beat_round_trip(self):
        b = _tts_beat(subtitle_color="yellow", subtitle_emphasis=True)
        d = b.to_dict()
        b2 = HybridBeat.from_dict(d)
        assert b == b2

    def test_original_beat_round_trip(self):
        b = _orig_beat(bgm_mode="duck", quote_lines=("A", "B"))
        d = b.to_dict()
        b2 = HybridBeat.from_dict(d)
        assert b == b2

    def test_tts_beat_dict_has_expected_keys(self):
        d = _tts_beat().to_dict()
        assert set(d.keys()) >= {"kind", "duration_sec", "subtitle", "tts_text"}
        assert "clip_start_sec" not in d

    def test_original_beat_dict_has_expected_keys(self):
        d = _orig_beat().to_dict()
        assert set(d.keys()) >= {"kind", "duration_sec", "clip_start_sec", "clip_end_sec"}
        assert "tts_text" not in d

    def test_original_beat_source_label_omitted_when_empty(self):
        d = _orig_beat(source_label="").to_dict()
        assert "source_label" not in d

    def test_original_beat_source_label_present_when_set(self):
        d = _orig_beat(source_label="OBS뉴스").to_dict()
        assert d["source_label"] == "OBS뉴스"

    def test_original_beat_source_clip_path_omitted_when_empty(self):
        d = _orig_beat(source_clip_path="").to_dict()
        assert "source_clip_path" not in d

    def test_original_beat_source_clip_path_present_when_set(self):
        d = _orig_beat(source_clip_path="/tmp/x.mp4").to_dict()
        assert d["source_clip_path"] == "/tmp/x.mp4"


# ────────────────────────────────────────────────────────────────────────────
# HybridShortsPlan — validation
# ────────────────────────────────────────────────────────────────────────────

class TestHybridShortsPlanValidation:
    def test_valid_plan(self):
        p = _valid_plan()
        assert p.topic == "이재명 발언 논란"

    def test_empty_topic_raises(self):
        with pytest.raises(PlanValidationError, match="topic"):
            _valid_plan(topic="")

    def test_hook_must_be_tts(self):
        with pytest.raises(PlanValidationError, match="hook"):
            _valid_plan(hook=_orig_beat())

    def test_cta_must_be_tts(self):
        with pytest.raises(PlanValidationError, match="cta"):
            _valid_plan(cta=_orig_beat())

    def test_empty_beats_raises(self):
        with pytest.raises(PlanValidationError, match="beats"):
            _valid_plan(beats=())

    def test_consecutive_original_beats_raises(self):
        orig1 = _orig_beat(clip_start_sec=0.0, clip_end_sec=12.0)
        orig2 = _orig_beat(clip_start_sec=15.0, clip_end_sec=27.0)
        with pytest.raises(PlanValidationError, match="연속된 두 .original. 비트"):
            _valid_plan(beats=(orig1, orig2))

    def test_consecutive_tts_beats_ok(self):
        # Two consecutive TTS beats is allowed
        tts1 = _tts_beat(duration_sec=8.0)
        tts2 = _tts_beat(duration_sec=8.0)
        orig = _orig_beat(duration_sec=12.0, clip_start_sec=0.0, clip_end_sec=12.0)
        _valid_plan(beats=(tts1, tts2, orig))  # should not raise

    def test_invalid_angle_raises(self):
        with pytest.raises(PlanValidationError, match="angle"):
            _valid_plan(angle="unknown_angle")  # type: ignore[arg-type]

    def test_all_valid_angles(self):
        for angle in ("title_anchor", "audience_resonance", "comparison"):
            p = _valid_plan(angle=angle)
            assert p.angle == angle

    def test_total_seconds_over_limit_raises(self):
        # tts: hook(15) + cta(15) = 30s (within range)
        # orig: 27s (within range)
        # total: 30+27 = 57s > MAX_TOTAL (50s)
        big_hook = _tts_beat(duration_sec=15.0)
        big_cta = _tts_beat(duration_sec=15.0)
        big_orig = _orig_beat(duration_sec=27.0, clip_start_sec=0.0, clip_end_sec=27.0)
        with pytest.raises(PlanValidationError, match="총합"):
            HybridShortsPlan(
                topic="test",
                hook=big_hook,
                beats=(big_orig,),
                cta=big_cta,
                angle="title_anchor",
            )

    def test_tts_too_low_raises(self):
        # hook(1s) + cta(1s) + beats all orig = tts total = 2s < MIN_KIND_SECONDS
        short_hook = _tts_beat(duration_sec=1.0)
        short_cta = _tts_beat(duration_sec=1.0)
        orig = _orig_beat(duration_sec=MAX_KIND_SECONDS, clip_start_sec=0.0, clip_end_sec=MAX_KIND_SECONDS)
        with pytest.raises(PlanValidationError, match="TTS 합산"):
            HybridShortsPlan(
                topic="test",
                hook=short_hook,
                beats=(orig,),
                cta=short_cta,
                angle="title_anchor",
            )

    def test_original_too_low_raises(self):
        # All TTS beats — orig total = 0
        tts1 = _tts_beat(duration_sec=15.0)
        tts2 = _tts_beat(duration_sec=10.0)
        with pytest.raises(PlanValidationError, match="원본 합산"):
            HybridShortsPlan(
                topic="test",
                hook=_tts_beat(duration_sec=4.0),
                beats=(tts1, tts2),
                cta=_tts_beat(duration_sec=3.0),
                angle="title_anchor",
            )


# ────────────────────────────────────────────────────────────────────────────
# HybridShortsPlan — properties
# ────────────────────────────────────────────────────────────────────────────

class TestHybridShortsPlanProperties:
    def test_tts_seconds_sums_hook_beats_cta(self):
        p = _valid_plan()
        # hook=4, tts_mid=8, cta=4
        assert p.tts_seconds == pytest.approx(16.0)

    def test_original_seconds_sums_orig_beats(self):
        p = _valid_plan()
        # orig1=12, orig2=12
        assert p.original_seconds == pytest.approx(24.0)

    def test_total_seconds(self):
        p = _valid_plan()
        assert p.total_seconds == pytest.approx(40.0)

    def test_all_beats_order(self):
        p = _valid_plan()
        all_b = p.all_beats()
        # hook, orig1, tts_mid, orig2, cta
        assert len(all_b) == 5
        assert all_b[0].kind == "tts"   # hook
        assert all_b[-1].kind == "tts"  # cta


# ────────────────────────────────────────────────────────────────────────────
# HybridShortsPlan — serialization
# ────────────────────────────────────────────────────────────────────────────

class TestHybridShortsPlanSerialization:
    def test_round_trip(self):
        p = _valid_plan()
        d = p.to_dict()
        p2 = HybridShortsPlan.from_dict(d)
        assert p.topic == p2.topic
        assert p.angle == p2.angle
        assert len(p.beats) == len(p2.beats)
        assert p.tts_seconds == pytest.approx(p2.tts_seconds)
        assert p.original_seconds == pytest.approx(p2.original_seconds)

    def test_to_dict_has_meta(self):
        d = _valid_plan().to_dict()
        assert "_meta" in d
        assert "tts_sec" in d["_meta"]
        assert "original_sec" in d["_meta"]
        assert "total_sec" in d["_meta"]

    def test_to_dict_meta_ignored_on_from_dict(self):
        d = _valid_plan().to_dict()
        d["_meta"]["tts_sec"] = 9999.0  # corrupt meta
        p2 = HybridShortsPlan.from_dict(d)  # should still validate from beat data
        assert p2.tts_seconds != 9999.0

    def test_extra_clip_sources_round_trip(self):
        p = _valid_plan(extra_clip_sources={"장동혁": "/tmp/jdh.mp4"})
        d = p.to_dict()
        p2 = HybridShortsPlan.from_dict(d)
        assert p2.extra_clip_sources == {"장동혁": "/tmp/jdh.mp4"}

    def test_source_fields_round_trip(self):
        p = _valid_plan(
            source_url="https://yt.com/test",
            source_channel="OBS뉴스",
            source_title="국감 장면",
        )
        d = p.to_dict()
        p2 = HybridShortsPlan.from_dict(d)
        assert p2.source_url == "https://yt.com/test"
        assert p2.source_channel == "OBS뉴스"
        assert p2.source_title == "국감 장면"


# ────────────────────────────────────────────────────────────────────────────
# ThreeHybridPlansResult — serialization
# ────────────────────────────────────────────────────────────────────────────

class TestThreeHybridPlansResult:
    def _make_result(self) -> ThreeHybridPlansResult:
        p1 = _valid_plan(angle="title_anchor")
        p2 = _valid_plan(angle="audience_resonance")
        p3 = _valid_plan(angle="comparison")
        return ThreeHybridPlansResult(
            plans=(p1, p2, p3),
            candidates_pool=({"id": 1}, {"id": 2}),
            youtube_url="https://yt.com/v",
            video_title="국감 장면",
            video_channel="OBS뉴스",
        )

    def test_round_trip(self):
        r = self._make_result()
        d = r.to_dict()
        r2 = ThreeHybridPlansResult.from_dict(d)
        assert len(r2.plans) == 3
        assert r2.youtube_url == "https://yt.com/v"
        assert r2.video_channel == "OBS뉴스"

    def test_schema_version_in_dict(self):
        d = self._make_result().to_dict()
        assert d.get("schema_version") == "v3-hybrid-1"

    def test_plans_wrong_count_raises(self):
        d = self._make_result().to_dict()
        d["plans"] = d["plans"][:2]  # only 2 plans
        with pytest.raises(PlanValidationError, match="3개 필요"):
            ThreeHybridPlansResult.from_dict(d)
