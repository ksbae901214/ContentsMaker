"""Tests for audio stitcher module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.analyzer.script_models import Scene, ShortsScript, Metadata, AudioConfig, BackgroundConfig


def _make_script(scenes):
    return ShortsScript(
        metadata=Metadata(title="test", emotion_type="relatable", duration=30, source_type="political"),
        scenes=tuple(scenes),
        audio=AudioConfig(tts_script="test", voice="", rate="", pitch=""),
        background=BackgroundConfig(type="gradient", colors=()),
    )


class TestStitchPoliticalAudio:
    @patch("src.tts.audio_stitcher._create_silence")
    @patch("src.tts.audio_stitcher.asyncio.run")
    @patch("src.tts.audio_stitcher._extract_audio_segment")
    @patch("src.tts.audio_stitcher._get_mp3_duration_ms", return_value=3000)
    @patch("src.tts.audio_stitcher._concat_mp3")
    def test_alternating_scenes(self, mock_concat, mock_dur, mock_extract, mock_tts, mock_silence, tmp_path):
        scenes = [
            Scene(id=1, timestamp=0, duration=3, type="title", text="제목", voice_text="제목입니다"),
            Scene(id=2, timestamp=3, duration=5, type="clip", text="발언", voice_text="",
                  clip_start=0.0, clip_end=5.0),
            Scene(id=3, timestamp=8, duration=4, type="commentary", text="해설", voice_text="해설입니다"),
        ]
        script = _make_script(scenes)

        # Create fake segment files so _get_mp3_duration_ms works
        def create_seg(audio_path, start, end, output):
            output.write_bytes(b"fake_audio")
            return output

        def create_tts(*args, **kwargs):
            # The seg path is determined in the function
            pass

        mock_extract.side_effect = create_seg

        clip_audio = tmp_path / "clip.mp3"
        clip_audio.write_bytes(b"fake_clip_audio")

        from src.tts.audio_stitcher import stitch_political_audio
        audio_path, timings = stitch_political_audio(
            script, clip_audio, output_dir=tmp_path
        )

        # Should have called extract for clip scene
        assert mock_extract.called
        extract_call = mock_extract.call_args
        assert extract_call[0][1] == 0.0  # clip_start
        assert extract_call[0][2] == 5.0  # clip_end

        # Should have called TTS for title and commentary
        assert mock_tts.call_count == 2  # title + commentary

        # Timings should be monotonic
        assert len(timings) == 3
        for i in range(1, len(timings)):
            assert timings[i]["start_ms"] >= timings[i - 1]["start_ms"]

    @patch("src.tts.audio_stitcher._create_silence")
    @patch("src.tts.audio_stitcher.asyncio.run")
    @patch("src.tts.audio_stitcher._extract_audio_segment")
    @patch("src.tts.audio_stitcher._get_mp3_duration_ms", return_value=4000)
    @patch("src.tts.audio_stitcher._concat_mp3")
    def test_timings_are_contiguous(self, mock_concat, mock_dur, mock_extract, mock_tts, mock_silence, tmp_path):
        scenes = [
            Scene(id=1, timestamp=0, duration=3, type="title", text="T", voice_text="Title"),
            Scene(id=2, timestamp=3, duration=4, type="clip", text="C", voice_text="",
                  clip_start=0.0, clip_end=4.0),
        ]
        script = _make_script(scenes)

        def create_seg(audio_path, start, end, output):
            output.write_bytes(b"fake")
            return output

        mock_extract.side_effect = create_seg

        clip_audio = tmp_path / "clip.mp3"
        clip_audio.write_bytes(b"fake")

        from src.tts.audio_stitcher import stitch_political_audio
        _, timings = stitch_political_audio(script, clip_audio, output_dir=tmp_path)

        assert timings[0]["start_ms"] == 0
        assert timings[0]["end_ms"] == timings[1]["start_ms"]  # contiguous


class TestExtractAudioSegment:
    @patch("src.tts.audio_stitcher.subprocess.run")
    def test_ffmpeg_command(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)

        from src.tts.audio_stitcher import _extract_audio_segment
        src = tmp_path / "audio.mp3"
        out = tmp_path / "segment.mp3"
        _extract_audio_segment(src, 5.0, 10.0, out)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-ss" in cmd
        assert "5.0" in cmd
        assert "10.0" in cmd
