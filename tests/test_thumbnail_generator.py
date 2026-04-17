"""Tests for thumbnail_generator (MID-05).

Covers:
- capture_hook_frame: ffmpeg subprocess invocation + fallback
- compose_thumbnail: 1280x720 PNG output with title overlay
- compute_text_position: pure function for text y-coordinate (top 50% + 20px offset)
- generate_thumbnail_from_script: end-to-end orchestrator
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from src.upload.thumbnail_generator import (
    capture_hook_frame,
    compose_thumbnail,
    compute_text_position,
    generate_thumbnail_from_script,
    TEXT_Y_OFFSET,
    THUMB_WIDTH,
    THUMB_HEIGHT,
)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


def test_thumbnail_dimensions_are_1280x720():
    assert THUMB_WIDTH == 1280
    assert THUMB_HEIGHT == 720


def test_text_y_offset_is_20_pixels():
    """Title clears YouTube Shorts navigation bar: top 50% + 20px."""
    assert TEXT_Y_OFFSET == 20


# ---------------------------------------------------------------------------
# compute_text_position (pure function)
# ---------------------------------------------------------------------------


class TestComputeTextPosition:
    def test_default_top_percent_and_offset(self):
        # 720 * 0.50 = 360, + 20 = 380
        assert compute_text_position(canvas_height=720) == 380

    def test_custom_offset(self):
        assert compute_text_position(canvas_height=720, y_offset=0) == 360

    def test_custom_top_percent(self):
        # 720 * 0.5 = 360, + 20 = 380 (default percent is 0.50 so same)
        assert compute_text_position(canvas_height=720, top_percent=0.5) == 380

    def test_scales_with_canvas_height(self):
        # 1920 * 0.50 = 960, + 20 = 980
        assert compute_text_position(canvas_height=1920) == 980


# ---------------------------------------------------------------------------
# capture_hook_frame (ffmpeg subprocess)
# ---------------------------------------------------------------------------


class TestCaptureHookFrame:
    def test_raises_when_video_missing(self, tmp_path):
        missing = tmp_path / "nonexistent.mp4"
        with pytest.raises(FileNotFoundError):
            capture_hook_frame(missing, output_path=tmp_path / "frame.png")

    def test_calls_ffmpeg_with_seek_and_one_frame(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "frame.png"

        def fake_run(*args, **kwargs):
            # Simulate ffmpeg writing the output
            output.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            return subprocess.CompletedProcess(args=args, returncode=0)

        with patch("subprocess.run", side_effect=fake_run) as mock_run:
            result = capture_hook_frame(video, time_sec=0.8, output_path=output)

        assert result == output
        assert output.exists()
        # Inspect first call args
        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1]["args"]
        assert "ffmpeg" in cmd[0]
        assert "-ss" in cmd
        idx = cmd.index("-ss")
        assert cmd[idx + 1] == "0.8"
        assert "-frames:v" in cmd or "-vframes" in cmd

    def test_falls_back_to_earlier_timestamp_when_first_fails(self, tmp_path):
        """If -ss 0.8 fails (short hook), retry with 0.3."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "frame.png"

        call_count = {"n": 0}

        def fake_run(*args, **kwargs):
            call_count["n"] += 1
            cmd = args[0] if args else kwargs["args"]
            idx = cmd.index("-ss")
            t = cmd[idx + 1]
            if t == "0.8":
                # First attempt fails
                return subprocess.CompletedProcess(args=cmd, returncode=1, stderr=b"err")
            # Second attempt succeeds
            output.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            result = capture_hook_frame(video, time_sec=0.8, output_path=output)

        assert call_count["n"] == 2
        assert result == output

    def test_raises_when_both_attempts_fail(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "frame.png"

        with patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=1, stderr=b"err"),
        ):
            with pytest.raises(RuntimeError, match="ffmpeg"):
                capture_hook_frame(video, output_path=output)


# ---------------------------------------------------------------------------
# compose_thumbnail (PIL)
# ---------------------------------------------------------------------------


def _make_fake_frame(path: Path, width: int = 1920, height: int = 1080) -> Path:
    """Create a solid-color PNG to stand in as a captured frame."""
    img = Image.new("RGB", (width, height), (40, 60, 120))
    img.save(path, "PNG")
    return path


class TestComposeThumbnail:
    def test_output_is_1280x720_png(self, tmp_path):
        frame = _make_fake_frame(tmp_path / "frame.png")
        output = tmp_path / "thumb.png"

        result = compose_thumbnail(frame, title="테스트 제목", output_path=output)

        assert result == output
        assert output.exists()
        with Image.open(output) as img:
            assert img.size == (1280, 720)
            assert img.format == "PNG"

    def test_handles_empty_title(self, tmp_path):
        """Empty title should not crash — renders frame only."""
        frame = _make_fake_frame(tmp_path / "frame.png")
        output = tmp_path / "thumb.png"
        result = compose_thumbnail(frame, title="", output_path=output)
        assert result.exists()

    def test_accepts_highlight_words(self, tmp_path):
        frame = _make_fake_frame(tmp_path / "frame.png")
        output = tmp_path / "thumb.png"
        result = compose_thumbnail(
            frame,
            title="긴급 속보\n충격 발언",
            output_path=output,
            highlight_words=("충격",),
        )
        assert result.exists()
        with Image.open(output) as img:
            assert img.size == (1280, 720)

    def test_raises_when_frame_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            compose_thumbnail(
                tmp_path / "missing.png",
                title="제목",
                output_path=tmp_path / "thumb.png",
            )

    def test_preserves_aspect_by_cropping(self, tmp_path):
        """Vertical 1080x1920 source → crop center to 1280x720 canvas."""
        frame = _make_fake_frame(tmp_path / "frame.png", width=1080, height=1920)
        output = tmp_path / "thumb.png"

        result = compose_thumbnail(frame, title="제목", output_path=output)

        with Image.open(result) as img:
            assert img.size == (1280, 720)


# ---------------------------------------------------------------------------
# generate_thumbnail_from_script (integration)
# ---------------------------------------------------------------------------


class TestGenerateThumbnailFromScript:
    def test_creates_thumb_png_next_to_video(self, tmp_path, sample_script):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")

        def fake_run(*args, **kwargs):
            # Simulate ffmpeg writing the frame
            cmd = args[0] if args else kwargs["args"]
            # Last arg is the output path
            out = Path(cmd[-1])
            _make_fake_frame(out)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            result = generate_thumbnail_from_script(
                sample_script, video_path=video, output_dir=tmp_path
            )

        assert result.exists()
        assert result.suffix == ".png"
        with Image.open(result) as img:
            assert img.size == (1280, 720)

    def test_raises_when_video_missing(self, tmp_path, sample_script):
        with pytest.raises(FileNotFoundError):
            generate_thumbnail_from_script(
                sample_script,
                video_path=tmp_path / "missing.mp4",
                output_dir=tmp_path,
            )

    def test_uses_hook_scene_timestamp_when_hook_flag_set(self, tmp_path, sample_script):
        """When a scene has hook=True, capture from its timestamp, not 0.8."""
        from dataclasses import replace
        from src.analyzer.script_models import ShortsScript

        hooked_scene = replace(sample_script.scenes[0], hook=True, timestamp=1.2)
        script = ShortsScript(
            metadata=sample_script.metadata,
            scenes=(hooked_scene,) + sample_script.scenes[1:],
            audio=sample_script.audio,
            background=sample_script.background,
        )
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")

        seen_seeks: list[str] = []

        def fake_run(*args, **kwargs):
            cmd = args[0] if args else kwargs["args"]
            idx = cmd.index("-ss")
            seen_seeks.append(cmd[idx + 1])
            out = Path(cmd[-1])
            _make_fake_frame(out)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            generate_thumbnail_from_script(script, video_path=video, output_dir=tmp_path)

        # Seek should be hook_timestamp + small offset (mid-scene), not 0.8
        assert seen_seeks, "ffmpeg was not invoked"
        assert float(seen_seeks[0]) >= 1.2

    def test_uses_metadata_title_for_overlay(self, tmp_path, sample_script):
        """Thumbnail title text comes from script.metadata.title."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")

        def fake_run(*args, **kwargs):
            cmd = args[0] if args else kwargs["args"]
            out = Path(cmd[-1])
            _make_fake_frame(out)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with patch("subprocess.run", side_effect=fake_run):
            with patch(
                "src.upload.thumbnail_generator.compose_thumbnail",
                wraps=compose_thumbnail,
            ) as mock_compose:
                generate_thumbnail_from_script(
                    sample_script, video_path=video, output_dir=tmp_path
                )

        # compose_thumbnail was called with the metadata title
        assert mock_compose.called
        kwargs = mock_compose.call_args.kwargs
        assert sample_script.metadata.title in (kwargs.get("title") or "")
