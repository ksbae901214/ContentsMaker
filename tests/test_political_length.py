"""정치쇼츠 길이 게이트 (035) 테스트 — scripts/political_length.py."""
from __future__ import annotations

import pytest

from scripts.political_length import (
    CHARS_PER_SEC_1X, DEFAULT_TTS_SPEED, OUTRO_SEC, TARGET_MAX_SEC,
    enforce_length, estimate_total_sec, estimate_tts_sec, excess_chars,
    final_video_sec, length_warnings, scene_duration_estimates,
)


def v21_cfg(**over) -> dict:
    """V2.1 형태 — top-level hook + tts 씬만 (mode 키 없음)."""
    cfg = {
        "slug": "test_len_v21",
        "title": "배너",
        "sources": {"a": {"query": "q"}},
        "hook": {"source": "a", "start_sec": 1.0, "duration": 4.0},
        "scenes": [
            {"source": "a", "text": "t1", "voice": "가" * 74},
            {"source": "a", "text": "t2", "voice": "나" * 74},
        ],
    }
    cfg.update(over)
    return cfg


def v22_cfg(**over) -> dict:
    """V2.2 형태 — clip + tts 혼합, top-level hook 없음."""
    cfg = {
        "slug": "test_len_v22",
        "title": "배너",
        "sources": {"a": {"query": "q"}},
        "scenes": [
            {"mode": "clip", "source": "a", "duration": 5.0, "text": "훅"},
            {"mode": "clip", "source": "a", "duration": 6.0, "text": "반박"},
            {"mode": "tts", "source": "a", "text": "정리", "voice": "다" * 74},
        ],
    }
    cfg.update(over)
    return cfg


# ── TTS 길이 추정 ───────────────────────────────────────────────────
class TestEstimateTtsSec:
    def test_zero_chars_is_zero(self):
        assert estimate_tts_sec(0) == 0.0

    def test_base_rate_at_1x(self):
        # 7.4자/초 × 10초 = 74자
        assert estimate_tts_sec(74, speed=1.0) == pytest.approx(10.0, abs=0.01)

    def test_speed_shortens_proportionally(self):
        assert estimate_tts_sec(74, speed=1.1) == pytest.approx(74 / (CHARS_PER_SEC_1X * 1.1), abs=0.01)

    def test_default_speed_is_v21_standard(self):
        assert DEFAULT_TTS_SPEED == 1.1
        assert estimate_tts_sec(74) == estimate_tts_sec(74, speed=1.1)

    def test_negative_chars_clamped_to_zero(self):
        assert estimate_tts_sec(-10) == 0.0


# ── 씬별 추정 ───────────────────────────────────────────────────────
class TestSceneDurationEstimates:
    def test_clip_scene_uses_declared_duration(self):
        est = scene_duration_estimates(v22_cfg())
        assert est[0] == 5.0
        assert est[1] == 6.0

    def test_tts_scene_uses_char_estimate(self):
        est = scene_duration_estimates(v22_cfg())
        assert est[2] == pytest.approx(estimate_tts_sec(74), abs=0.01)

    def test_v21_scenes_default_to_tts_mode(self):
        est = scene_duration_estimates(v21_cfg())
        assert len(est) == 2
        assert all(e == pytest.approx(estimate_tts_sec(74), abs=0.01) for e in est)

    def test_respects_config_tts_speed(self):
        slow = scene_duration_estimates(v21_cfg(tts_speed=1.0))
        fast = scene_duration_estimates(v21_cfg(tts_speed=1.5))
        assert slow[0] > fast[0]

    def test_missing_scenes_returns_empty(self):
        assert scene_duration_estimates({"slug": "x"}) == []


# ── 총 길이 추정 ────────────────────────────────────────────────────
class TestEstimateTotalSec:
    def test_v21_includes_top_level_hook(self):
        cfg = v21_cfg()
        scenes_only = sum(scene_duration_estimates(cfg))
        assert estimate_total_sec(cfg) == pytest.approx(scenes_only + 4.0, abs=0.01)

    def test_v22_has_no_hook_offset(self):
        cfg = v22_cfg()
        assert estimate_total_sec(cfg) == pytest.approx(sum(scene_duration_estimates(cfg)), abs=0.01)

    def test_no_hook_key_is_zero_offset(self):
        cfg = v21_cfg()
        del cfg["hook"]
        assert estimate_total_sec(cfg) == pytest.approx(sum(scene_duration_estimates(cfg)), abs=0.01)


# ── 초과분 → 잘라낼 글자 수 ─────────────────────────────────────────
class TestExcessChars:
    def test_converts_seconds_to_chars(self):
        assert excess_chars(10.0, speed=1.0) == 74

    def test_zero_or_negative_is_zero(self):
        assert excess_chars(0.0) == 0
        assert excess_chars(-5.0) == 0


# ── validate 단계 경고 (추정 기반, 초과만) ──────────────────────────
class TestLengthWarnings:
    def test_under_cap_no_warning(self):
        assert length_warnings(v22_cfg()) == []

    def test_short_video_does_not_warn(self):
        """38초 미만도 경고하지 않는다 — 현행 문제는 과장(過長)뿐."""
        cfg = v22_cfg(scenes=[{"mode": "clip", "source": "a", "duration": 5.0, "text": "훅"}])
        assert length_warnings(cfg) == []

    def test_over_cap_warns_with_chars_to_cut(self):
        cfg = v21_cfg(scenes=[{"source": "a", "text": "t", "voice": "가" * 600}])
        warns = length_warnings(cfg)
        assert len(warns) == 1
        assert "42" in warns[0]
        assert "자" in warns[0]

    def test_gate_off_suppresses_warning(self):
        cfg = v21_cfg(scenes=[{"source": "a", "text": "t", "voice": "가" * 600}],
                      duration_gate="off")
        assert length_warnings(cfg) == []


# ── 아웃트로 보정 (Remotion이 항상 4초를 덧붙인다) ──────────────────
class TestOutro:
    def test_outro_is_four_seconds(self):
        assert OUTRO_SEC == 4.0

    def test_final_adds_outro_to_timeline(self):
        assert final_video_sec(30.0) == pytest.approx(34.0, abs=0.01)

    def test_estimate_total_excludes_outro(self):
        """CTA 위치 계산은 씬 타임라인 기준 — 아웃트로를 포함하면 안 된다."""
        cfg = v22_cfg()
        assert estimate_total_sec(cfg) == pytest.approx(sum(scene_duration_estimates(cfg)), abs=0.01)


# ── 렌더 단계 하드 게이트 (실측 기반) ───────────────────────────────
class TestEnforceLength:
    def test_within_cap_passes(self):
        enforce_length(TARGET_MAX_SEC - OUTRO_SEC, v22_cfg())

    def test_over_cap_raises(self):
        with pytest.raises(ValueError, match="42"):
            enforce_length(TARGET_MAX_SEC - OUTRO_SEC + 0.5, v22_cfg())

    def test_timeline_at_cap_now_fails_due_to_outro(self):
        """타임라인이 42초면 최종은 46초 — 회귀 방지 (2026-08-05 실측 결함)."""
        with pytest.raises(ValueError, match="아웃트로"):
            enforce_length(TARGET_MAX_SEC, v22_cfg())

    def test_error_message_states_how_much_to_cut(self):
        with pytest.raises(ValueError, match="8.0초"):
            enforce_length(46.0, v22_cfg())

    def test_gate_off_bypasses(self):
        enforce_length(90.0, v22_cfg(duration_gate="off"))
