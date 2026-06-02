"""T061: Segment cutter 테스트 — ffmpeg 구간 자르기 + 9:16 크롭/패딩 (FR-017, FR-018).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from src.dem_shorts.editor.segment_cutter import (
    SegmentCutError,
    build_ffmpeg_cmd,
    cut_segment,
    validate_cut_duration,
)


class TestValidateCutDuration:
    def test_accepts_60_seconds_exact(self):
        validate_cut_duration(0.0, 60.0)  # no exception

    def test_accepts_30_seconds(self):
        validate_cut_duration(10.0, 40.0)

    def test_rejects_over_60_seconds(self):
        with pytest.raises(SegmentCutError) as ei:
            validate_cut_duration(0.0, 60.5)
        assert "FR-018" in str(ei.value) or "60" in str(ei.value)

    def test_rejects_negative_or_zero_duration(self):
        with pytest.raises(SegmentCutError):
            validate_cut_duration(10.0, 10.0)
        with pytest.raises(SegmentCutError):
            validate_cut_duration(10.0, 5.0)

    def test_rejects_negative_start(self):
        with pytest.raises(SegmentCutError):
            validate_cut_duration(-1.0, 30.0)


class TestBuildFfmpegCmd:
    def test_contains_crop_to_9x16(self):
        cmd = build_ffmpeg_cmd(
            input_path=Path("/in.mp4"),
            output_path=Path("/out.mp4"),
            start_sec=10.0,
            end_sec=50.0,
        )
        # 9:16 변환 vf 포함
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        vf_arg = cmd[vf_idx + 1]
        # 크롭/스케일/패딩 — 세로형 변환
        assert "1080" in vf_arg or "1920" in vf_arg

    def test_uses_ss_and_t(self):
        cmd = build_ffmpeg_cmd(
            input_path=Path("/in.mp4"),
            output_path=Path("/out.mp4"),
            start_sec=12.5,
            end_sec=42.5,
        )
        assert "-ss" in cmd
        ss_idx = cmd.index("-ss")
        assert cmd[ss_idx + 1] == "12.5"
        # duration = 30.0
        assert "-t" in cmd
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "30.0"

    def test_rejects_invalid_duration(self):
        with pytest.raises(SegmentCutError):
            build_ffmpeg_cmd(
                input_path=Path("/in.mp4"),
                output_path=Path("/out.mp4"),
                start_sec=0.0,
                end_sec=90.0,  # > 60 (FR-018)
            )


def _make_sample_video(path: Path, duration: float = 5.0) -> Path:
    """Generate a tiny test video for ffmpeg integration tests."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s=320x240:d={duration}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=1000:duration={duration}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


class TestCutSegmentErrorReporting:
    """Bug: stderr[:500] only shows ffmpeg version banner — actual error
    (e.g. 'start past end of file') is at the END of stderr and gets cut off."""

    def test_start_past_video_end_raises_clear_error(self, tmp_path):
        """When start_sec exceeds the input video duration, ffmpeg silently
        produces an empty container. Must raise a CLEAR error instead of
        leaking ffmpeg's version banner."""
        video = _make_sample_video(tmp_path / "in.mp4", duration=3.0)
        out = tmp_path / "out.mp4"
        with pytest.raises(SegmentCutError) as ei:
            cut_segment(
                input_path=video,
                output_path=out,
                start_sec=10.0,  # video is only 3s
                end_sec=12.0,
            )
        msg = str(ei.value)
        # Error must clearly mention the start/duration mismatch
        assert (
            "start" in msg.lower()
            or "duration" in msg.lower()
            or "exceeds" in msg.lower()
            or "beyond" in msg.lower()
        ), f"Unclear error message: {msg}"
        # Must NOT just dump the ffmpeg version banner
        assert not msg.strip().endswith("--enable-audiot"), (
            f"Error message leaks ffmpeg version banner: {msg}"
        )

    def test_clip_end_past_video_end_clamps_or_warns(self, tmp_path):
        """When end_sec exceeds video length, ffmpeg truncates output —
        we should either succeed (clamped) or fail with a clear message."""
        video = _make_sample_video(tmp_path / "in.mp4", duration=3.0)
        out = tmp_path / "out.mp4"
        # start within video, end past video → should still produce a valid clip
        result = cut_segment(
            input_path=video,
            output_path=out,
            start_sec=1.0,
            end_sec=5.0,  # only 2s of actual content available
        )
        assert result.exists()
        assert result.stat().st_size > 1000

    def test_error_shows_end_of_stderr_not_version_banner(self, tmp_path):
        """When ffmpeg fails, the error should show the meaningful tail of
        stderr (the actual error line), not the leading version banner."""
        # Construct a clearly invalid input
        bad_input = tmp_path / "definitely_not_a_video.mp4"
        bad_input.write_bytes(b"not a video at all" * 100)
        out = tmp_path / "out.mp4"
        with pytest.raises(SegmentCutError) as ei:
            cut_segment(
                input_path=bad_input,
                output_path=out,
                start_sec=0.0,
                end_sec=2.0,
            )
        msg = str(ei.value)
        # Real failure reasons live near the end of stderr — must be visible
        assert "Invalid" in msg or "moov" in msg or "Error" in msg or "error" in msg, (
            f"Error doesn't contain ffmpeg's actual failure reason: {msg}"
        )
