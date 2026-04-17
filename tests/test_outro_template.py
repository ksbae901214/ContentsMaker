"""Tests for QW-05 — standardized CTA outro template.

The outro_template module is the single source of truth for the outro:
- TTS voice text (read aloud at the end)
- Visual CTA lines (rendered by Remotion Outro.tsx)
- Duration / scene_id contract

Both edge_tts_generator and Remotion props derive from this module so the
spoken text and the on-screen text stay in sync.
"""
import pytest

from src.video.outro_template import (
    OUTRO_VOICE_TEXT,
    OUTRO_CTA_LINES,
    OUTRO_DURATION_SECONDS,
    OUTRO_SCENE_ID,
    build_outro_props,
)


class TestOutroConstants:
    def test_outro_voice_text_non_empty(self):
        assert OUTRO_VOICE_TEXT
        assert isinstance(OUTRO_VOICE_TEXT, str)

    def test_outro_voice_text_includes_subscribe_cta(self):
        # Subscribe / like CTA must be spoken
        assert "구독" in OUTRO_VOICE_TEXT
        assert "좋아요" in OUTRO_VOICE_TEXT

    def test_outro_cta_lines_is_tuple_of_strings(self):
        assert isinstance(OUTRO_CTA_LINES, tuple)
        assert len(OUTRO_CTA_LINES) >= 2
        for line in OUTRO_CTA_LINES:
            assert isinstance(line, str) and line.strip()

    def test_outro_cta_lines_include_required_actions(self):
        joined = " ".join(OUTRO_CTA_LINES)
        # Standardized CTA must mention 구독 + 좋아요 + 알림(or 다음 영상)
        assert "구독" in joined
        assert "좋아요" in joined
        assert ("알림" in joined) or ("다음 영상" in joined)

    def test_outro_cta_line_length_within_korean_readability(self):
        # 한 줄 9~22자 권장. 30자 넘으면 모바일 가독성 저하.
        for line in OUTRO_CTA_LINES:
            assert len(line) <= 30, f"too long: {line!r}"

    def test_outro_duration_seconds_is_positive_float(self):
        assert isinstance(OUTRO_DURATION_SECONDS, float)
        assert OUTRO_DURATION_SECONDS >= 3.0
        assert OUTRO_DURATION_SECONDS <= 6.0

    def test_outro_scene_id_is_negative_one(self):
        # Contract: scene_id=-1 is the outro across the pipeline (CLAUDE.md).
        assert OUTRO_SCENE_ID == -1


class TestBuildOutroProps:
    def test_returns_dict_with_required_keys(self):
        props = build_outro_props()
        assert "ctaLines" in props
        assert "durationSeconds" in props

    def test_cta_lines_match_constant(self):
        props = build_outro_props()
        assert tuple(props["ctaLines"]) == OUTRO_CTA_LINES

    def test_duration_matches_constant(self):
        props = build_outro_props()
        assert props["durationSeconds"] == OUTRO_DURATION_SECONDS


class TestEdgeTTSIntegration:
    def test_edge_tts_uses_shared_outro_voice_text(self):
        """edge_tts_generator must import OUTRO_TEXT from outro_template
        so spoken text and visual CTA stay in sync.
        """
        from src.tts import edge_tts_generator

        assert edge_tts_generator.OUTRO_TEXT == OUTRO_VOICE_TEXT
