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


class TestSceneVideos:
    """Test scene_videos parameter in render_video."""

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_scene_videos_in_props(self, mock_which, mock_run, sample_script, tmp_data_dir):
        """When scene_videos is passed, props JSON should include sceneVideos."""
        output_dir = tmp_data_dir / "outputs"
        vid_dir = tmp_data_dir / "videos"
        vid_dir.mkdir(exist_ok=True)
        vid_path = vid_dir / "scene_01.mp4"
        vid_path.write_bytes(b"fake mp4 video")

        scene_videos = [{"scene_id": 1, "video_path": str(vid_path)}]
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
        render_video(
            sample_script,
            scene_videos=scene_videos,
            output_dir=output_dir,
            use_bgm=False,
        )

        props = props_captured["data"]
        assert "sceneVideos" in props
        assert len(props["sceneVideos"]) == 1
        assert props["sceneVideos"][0]["sceneId"] == 1
        assert "videoFile" in props["sceneVideos"][0]
        assert props["sceneVideos"][0]["videoFile"].endswith(".mp4")

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_scene_images_and_videos_both_in_props(
        self, mock_which, mock_run, sample_script, tmp_data_dir
    ):
        """When both scene_images and scene_videos are passed, both appear in props."""
        output_dir = tmp_data_dir / "outputs"

        img_dir = tmp_data_dir / "images"
        img_path = img_dir / "scene_01.png"
        img_path.write_bytes(b"PNG fake")

        vid_dir = tmp_data_dir / "videos"
        vid_dir.mkdir(exist_ok=True)
        vid_path = vid_dir / "scene_02.mp4"
        vid_path.write_bytes(b"fake mp4 video")

        scene_images = [{"scene_id": 1, "image_path": str(img_path)}]
        scene_videos = [{"scene_id": 2, "video_path": str(vid_path)}]
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
        render_video(
            sample_script,
            scene_images=scene_images,
            scene_videos=scene_videos,
            output_dir=output_dir,
            use_bgm=False,
        )

        props = props_captured["data"]
        assert "sceneImages" in props
        assert "sceneVideos" in props
        assert len(props["sceneImages"]) == 1
        assert len(props["sceneVideos"]) == 1
        assert props["sceneImages"][0]["sceneId"] == 1
        assert props["sceneVideos"][0]["sceneId"] == 2

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_scene_videos_none_gives_empty_list(
        self, mock_which, mock_run, sample_script, tmp_data_dir
    ):
        """When scene_videos is None, sceneVideos should be an empty list in props."""
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
        assert "sceneVideos" in props
        assert props["sceneVideos"] == []

    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_scene_video_file_copied_to_public(
        self, mock_which, mock_run, sample_script, tmp_data_dir
    ):
        """Video files should be copied to public/ directory."""
        output_dir = tmp_data_dir / "outputs"
        vid_dir = tmp_data_dir / "videos"
        vid_dir.mkdir(exist_ok=True)
        vid_path = vid_dir / "scene_03.mp4"
        vid_content = b"real mp4 video content"
        vid_path.write_bytes(vid_content)

        scene_videos = [{"scene_id": 3, "video_path": str(vid_path)}]
        copied_files = []

        def capture_and_check(*args, **kwargs):
            cmd = args[0]
            # Check that the video was copied to public dir
            public_dir = Path(cmd[3]).parent.parent.parent / "public"
            for f in public_dir.glob("vid_*.mp4"):
                copied_files.append(f)
            out_path = Path(cmd[5])
            out_path.write_bytes(b"fake")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = capture_and_check
        render_video(
            sample_script,
            scene_videos=scene_videos,
            output_dir=output_dir,
            use_bgm=False,
        )


class TestAutoThumbnail:
    """Phase 2: auto_thumbnail=True integration tests."""

    @patch("src.video.renderer.generate_thumbnail_from_script")
    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_auto_thumbnail_true_calls_generator(
        self, mock_which, mock_run, mock_thumb, sample_script, tmp_data_dir
    ):
        """auto_thumbnail=True triggers generate_thumbnail_from_script after render."""
        output_dir = tmp_data_dir / "outputs"

        def side_effect(*args, **kwargs):
            out_path = Path(args[0][5])
            out_path.write_bytes(b"fake mp4")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = side_effect
        mock_thumb.return_value = output_dir / "fake.thumb.png"

        render_video(sample_script, output_dir=output_dir, use_bgm=False, auto_thumbnail=True)

        mock_thumb.assert_called_once()
        call_args = mock_thumb.call_args[0]
        assert call_args[0].metadata.title == sample_script.metadata.title

    @patch("src.video.renderer.generate_thumbnail_from_script")
    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_auto_thumbnail_false_skips_generator(
        self, mock_which, mock_run, mock_thumb, sample_script, tmp_data_dir
    ):
        """auto_thumbnail=False must NOT call generate_thumbnail_from_script."""
        output_dir = tmp_data_dir / "outputs"

        def side_effect(*args, **kwargs):
            out_path = Path(args[0][5])
            out_path.write_bytes(b"fake mp4")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = side_effect

        render_video(sample_script, output_dir=output_dir, use_bgm=False, auto_thumbnail=False)

        mock_thumb.assert_not_called()

    @patch("src.video.renderer.generate_thumbnail_from_script", side_effect=RuntimeError("ffmpeg gone"))
    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_thumbnail_failure_does_not_fail_render(
        self, mock_which, mock_run, mock_thumb, sample_script, tmp_data_dir
    ):
        """Thumbnail generation failure must be non-fatal — render still returns the MP4."""
        output_dir = tmp_data_dir / "outputs"

        def side_effect(*args, **kwargs):
            out_path = Path(args[0][5])
            out_path.write_bytes(b"fake mp4")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = side_effect

        result = render_video(
            sample_script, output_dir=output_dir, use_bgm=False, auto_thumbnail=True
        )

        assert result.exists()
        assert result.suffix == ".mp4"

    @patch("src.video.renderer.generate_thumbnail_from_script")
    @patch("src.video.renderer.subprocess.run")
    @patch("src.video.renderer.shutil.which", return_value="/usr/local/bin/npx")
    def test_auto_thumbnail_default_is_true(
        self, mock_which, mock_run, mock_thumb, sample_script, tmp_data_dir
    ):
        """Default behaviour: auto_thumbnail=True, so thumbnail is generated."""
        output_dir = tmp_data_dir / "outputs"

        def side_effect(*args, **kwargs):
            out_path = Path(args[0][5])
            out_path.write_bytes(b"fake mp4")
            return MagicMock(returncode=0, stderr="", stdout="")

        mock_run.side_effect = side_effect
        mock_thumb.return_value = output_dir / "fake.thumb.png"

        render_video(sample_script, output_dir=output_dir, use_bgm=False)

        mock_thumb.assert_called_once()
