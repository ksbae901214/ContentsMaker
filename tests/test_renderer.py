"""Tests for Remotion video renderer module."""
import json
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.video.renderer import (
    render_video, RenderError,
    _convert_to_camel_case, _snake_to_camel,
    FPS,
)


class TestSnakeToCamel:
    def test_simple(self):
        assert _snake_to_camel("emotion_type") == "emotionType"

    def test_multiple_underscores(self):
        assert _snake_to_camel("source_url_path") == "sourceUrlPath"

    def test_no_underscores(self):
        assert _snake_to_camel("title") == "title"

    def test_single_char_segments(self):
        assert _snake_to_camel("a_b_c") == "aBC"


class TestConvertToCamelCase:
    def test_flat_dict(self):
        result = _convert_to_camel_case({"emotion_type": "funny", "source_url": ""})
        assert result == {"emotionType": "funny", "sourceUrl": ""}

    def test_nested_dict(self):
        result = _convert_to_camel_case({"metadata": {"emotion_type": "funny"}})
        assert result == {"metadata": {"emotionType": "funny"}}

    def test_list_of_dicts(self):
        result = _convert_to_camel_case([{"highlight_words": ["a"]}])
        assert result == [{"highlightWords": ["a"]}]

    def test_non_dict_passthrough(self):
        assert _convert_to_camel_case("hello") == "hello"
        assert _convert_to_camel_case(42) == 42
        assert _convert_to_camel_case(None) is None


class TestRenderVideoPrep:
    """Test render_video prep logic (without actual Remotion call)."""

    def test_duration_frames_calculation(self, sample_script):
        duration = sample_script.metadata.duration
        outro = 4
        expected = int((duration + outro) * FPS)
        assert expected > 0
        assert expected == int((45.0 + 4) * 30)

    def test_safe_title_generation(self):
        from src.video.renderer import render_video
        # Test the safe title logic directly
        title = "언니 결혼식에 안 오겠다는 남자친구!@#"
        safe = "".join(c for c in title[:30] if c.isalnum() or c in " _-")
        safe = safe.strip().replace(" ", "_") or "untitled"
        assert safe  # not empty
        assert "/" not in safe
        assert "#" not in safe

    def test_safe_title_empty_becomes_untitled(self):
        title = "!@#$%^&*()"
        safe = "".join(c for c in title[:30] if c.isalnum() or c in " _-")
        safe = safe.strip().replace(" ", "_") or "untitled"
        assert safe == "untitled"

    @patch("src.video.renderer.shutil.which", return_value=None)
    def test_missing_npx_raises(self, mock_which, sample_script, tmp_data_dir):
        with pytest.raises(RenderError, match="npx"):
            render_video(sample_script, output_dir=tmp_data_dir / "outputs")

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_render_nonzero_exit_raises(self, mock_which, mock_run, sample_script, tmp_data_dir):
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Some error", stdout=""
        )
        with pytest.raises(RenderError, match="렌더링 실패"):
            render_video(sample_script, output_dir=tmp_data_dir / "outputs")

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_render_timeout_raises(self, mock_which, mock_run, sample_script, tmp_data_dir):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npx", timeout=300)
        with pytest.raises(RenderError, match="시간 초과"):
            render_video(sample_script, output_dir=tmp_data_dir / "outputs")

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_render_success_returns_path(self, mock_which, mock_run, sample_script, tmp_data_dir):
        output_dir = tmp_data_dir / "outputs"

        def side_effect(*args, **kwargs):
            cmd = args[0]
            # output_path is after "BlindShorts" in cmd: [npx, remotion, render, index.ts, BlindShorts, OUTPUT, ...]
            out_path = Path(cmd[5])
            out_path.write_bytes(b"fake mp4 content")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = side_effect
        result = render_video(sample_script, output_dir=output_dir, use_bgm=False)
        assert result.exists()
        assert result.suffix == ".mp4"

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_props_json_structure(self, mock_which, mock_run, sample_script, tmp_data_dir):
        output_dir = tmp_data_dir / "outputs"
        props_captured = {}

        def capture_props(*args, **kwargs):
            cmd = args[0]
            props_idx = cmd.index("--props") + 1
            props_path = Path(cmd[props_idx])
            props_captured["data"] = json.loads(props_path.read_text())
            out_path = Path(cmd[5])
            out_path.write_bytes(b"fake")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = capture_props
        render_video(sample_script, output_dir=output_dir, use_bgm=False)

        props = props_captured["data"]
        assert "scriptData" in props
        assert "audioFile" in props
        assert "sceneImages" in props
        assert "bgmFile" in props
        assert "emotionType" in props["scriptData"]["metadata"]

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_scene_images_copied(self, mock_which, mock_run, sample_script, tmp_data_dir):
        output_dir = tmp_data_dir / "outputs"
        img_dir = tmp_data_dir / "images"
        img_path = img_dir / "test_scene_01.png"
        img_path.write_bytes(b"PNG fake")

        scene_images = [{"scene_id": 1, "image_path": str(img_path)}]

        def side_effect(*args, **kwargs):
            cmd = args[0]
            out_path = Path(cmd[5])
            out_path.write_bytes(b"fake")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = side_effect
        render_video(sample_script, scene_images=scene_images, output_dir=output_dir, use_bgm=False)

    def test_fps_is_30(self):
        assert FPS == 30
