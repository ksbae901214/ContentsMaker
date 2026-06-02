"""Tests for Gemini TTS generator — Phase 1 MVP."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.tts.gemini_tts_generator import (
    GeminiTTSError,
    _pcm_duration_ms,
    compute_scene_timings,
    generate_voice_with_timing_gemini,
)


def _make_scene(sid: int, voice_text: str) -> Scene:
    return Scene(
        id=sid,
        timestamp=0.0,
        duration=3.0,
        type="body",
        text=voice_text,
        voice_text=voice_text,
        emphasis="medium",
        highlight_words=(),
    )


def _make_script(scenes: list[Scene]) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title="테스트",
            emotion_type="funny",
            duration=sum(s.duration for s in scenes),
        ),
        scenes=tuple(scenes),
        audio=AudioConfig(tts_script=" ".join(s.voice_text for s in scenes)),
        background=BackgroundConfig(type="gradient", colors=("#000", "#fff")),
    )


class TestComputeSceneTimings:
    def test_equal_char_counts_equal_durations(self):
        scenes = [_make_scene(1, "abc"), _make_scene(2, "def")]
        timings = compute_scene_timings(scenes, total_duration_ms=1000)
        assert len(timings) == 2
        assert timings[0]["scene_id"] == 1
        assert timings[0]["start_ms"] == 0
        assert timings[0]["end_ms"] == 500
        assert timings[1]["scene_id"] == 2
        assert timings[1]["start_ms"] == 500
        assert timings[1]["end_ms"] == 1000

    def test_proportional_distribution(self):
        scenes = [_make_scene(1, "a"), _make_scene(2, "bbb")]
        timings = compute_scene_timings(scenes, total_duration_ms=4000)
        assert timings[0]["end_ms"] - timings[0]["start_ms"] == 1000
        assert timings[1]["end_ms"] - timings[1]["start_ms"] == 3000

    def test_outro_has_separate_entry(self):
        scenes = [_make_scene(1, "abc")]
        timings = compute_scene_timings(
            scenes, total_duration_ms=2000, outro_duration_ms=500
        )
        assert len(timings) == 2
        assert timings[0]["scene_id"] == 1
        assert timings[1]["scene_id"] == -1
        assert timings[1]["end_ms"] - timings[1]["start_ms"] == 500

    def test_empty_voice_text_skipped(self):
        scenes = [_make_scene(1, "abc"), _make_scene(2, "")]
        timings = compute_scene_timings(scenes, total_duration_ms=1000)
        assert len(timings) == 1
        assert timings[0]["scene_id"] == 1

    def test_all_empty_returns_empty(self):
        scenes = [_make_scene(1, ""), _make_scene(2, "")]
        timings = compute_scene_timings(scenes, total_duration_ms=1000)
        assert timings == []

    def test_timings_are_contiguous(self):
        """No gaps between adjacent scenes."""
        scenes = [_make_scene(1, "aa"), _make_scene(2, "bbb"), _make_scene(3, "c")]
        timings = compute_scene_timings(scenes, total_duration_ms=6000)
        for i in range(len(timings) - 1):
            assert timings[i]["end_ms"] == timings[i + 1]["start_ms"]


class TestPcmDurationMs:
    def test_1_second_at_24khz_16bit_mono(self):
        # 24000 samples/sec × 2 bytes × 1 channel = 48000 bytes/sec
        pcm = b"\x00" * 48000
        assert _pcm_duration_ms(pcm) == 1000

    def test_500ms(self):
        assert _pcm_duration_ms(b"\x00" * 24000) == 500

    def test_empty(self):
        assert _pcm_duration_ms(b"") == 0


class TestGenerateVoiceWithTimingGemini:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        scenes = [_make_scene(1, "test")]
        script = _make_script(scenes)
        with pytest.raises(GeminiTTSError, match="GEMINI_API_KEY"):
            generate_voice_with_timing_gemini(script, api_key="", include_outro=False)

    def test_all_empty_scenes_raises(self):
        scenes = [_make_scene(1, ""), _make_scene(2, "")]
        script = _make_script(scenes)
        with pytest.raises(GeminiTTSError, match="음성 텍스트가 없습니다"):
            generate_voice_with_timing_gemini(
                script, api_key="dummy", include_outro=False
            )

    @patch("src.tts.gemini_tts_generator._call_gemini_tts")
    @patch("src.tts.gemini_tts_generator._pcm_to_mp3")
    def test_mocked_flow_produces_timings(self, mock_convert, mock_call, tmp_path):
        # 2 seconds of fake PCM
        mock_call.return_value = b"\x00" * 96000
        mock_convert.side_effect = lambda pcm, path: path.write_bytes(b"fake")

        scenes = [_make_scene(1, "abc"), _make_scene(2, "def")]
        script = _make_script(scenes)

        out_path, timings = generate_voice_with_timing_gemini(
            script,
            output_dir=tmp_path,
            api_key="dummy",
            include_outro=False,
        )

        assert out_path.exists()
        assert out_path.suffix == ".mp3"
        assert len(timings) == 2
        total = timings[-1]["end_ms"] - timings[0]["start_ms"]
        assert 1990 <= total <= 2010

    @patch("src.tts.gemini_tts_generator._call_gemini_tts")
    @patch("src.tts.gemini_tts_generator._pcm_to_mp3")
    def test_timing_json_saved(self, mock_convert, mock_call, tmp_path):
        mock_call.return_value = b"\x00" * 48000
        mock_convert.side_effect = lambda pcm, path: path.write_bytes(b"fake")

        scenes = [_make_scene(1, "hello")]
        script = _make_script(scenes)
        out_path, _ = generate_voice_with_timing_gemini(
            script,
            output_dir=tmp_path,
            api_key="dummy",
            include_outro=False,
        )

        timing_path = out_path.with_suffix(".timing.json")
        assert timing_path.exists()

    @patch("src.tts.gemini_tts_generator._call_gemini_tts")
    @patch("src.tts.gemini_tts_generator._pcm_to_mp3")
    def test_includes_outro_timing(self, mock_convert, mock_call, tmp_path):
        # 3 seconds of fake PCM (with outro)
        mock_call.return_value = b"\x00" * 144000
        mock_convert.side_effect = lambda pcm, path: path.write_bytes(b"fake")

        scenes = [_make_scene(1, "abc")]
        script = _make_script(scenes)
        _, timings = generate_voice_with_timing_gemini(
            script,
            output_dir=tmp_path,
            api_key="dummy",
            include_outro=True,
        )

        outro_entries = [t for t in timings if t["scene_id"] == -1]
        assert len(outro_entries) == 1
        assert outro_entries[0]["end_ms"] > outro_entries[0]["start_ms"]
