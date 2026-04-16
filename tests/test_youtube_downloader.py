"""Tests for YouTube downloader module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.scraper.youtube_downloader import (
    parse_vtt_subtitles,
    YouTubeDownloadError,
)


SAMPLE_VTT = """\
WEBVTT
Kind: captions
Language: ko

00:00:01.000 --> 00:00:03.500
존경하는 국민 여러분

00:00:03.500 --> 00:00:06.000
존경하는 국민 여러분

00:00:06.000 --> 00:00:09.500
오늘 이 자리에서 말씀드리겠습니다

00:00:09.500 --> 00:00:13.000
경제 위기를 극복하기 위한 방안을
"""


class TestParseVttSubtitles:
    def test_basic_parsing(self, tmp_path):
        vtt = tmp_path / "test.ko.vtt"
        vtt.write_text(SAMPLE_VTT, encoding="utf-8")

        segments = parse_vtt_subtitles(vtt)
        assert len(segments) >= 2
        assert segments[0]["text"] == "존경하는 국민 여러분"
        assert segments[0]["start"] == 1.0
        assert segments[0]["end"] == 3.5

    def test_deduplication(self, tmp_path):
        """Consecutive identical text should be deduplicated."""
        vtt = tmp_path / "test.ko.vtt"
        vtt.write_text(SAMPLE_VTT, encoding="utf-8")

        segments = parse_vtt_subtitles(vtt)
        texts = [s["text"] for s in segments]
        # "존경하는 국민 여러분" appears twice in VTT but should appear once
        assert texts.count("존경하는 국민 여러분") == 1

    def test_timestamps_increasing(self, tmp_path):
        vtt = tmp_path / "test.ko.vtt"
        vtt.write_text(SAMPLE_VTT, encoding="utf-8")

        segments = parse_vtt_subtitles(vtt)
        for i in range(1, len(segments)):
            assert segments[i]["start"] >= segments[i - 1]["start"]

    def test_empty_vtt(self, tmp_path):
        vtt = tmp_path / "empty.ko.vtt"
        vtt.write_text("WEBVTT\n\n", encoding="utf-8")
        segments = parse_vtt_subtitles(vtt)
        assert segments == []

    def test_strips_vtt_tags(self, tmp_path):
        vtt_content = """\
WEBVTT

00:00:01.000 --> 00:00:03.000
<c>태그가</c> 있는 <c>텍스트</c>
"""
        vtt = tmp_path / "tags.ko.vtt"
        vtt.write_text(vtt_content, encoding="utf-8")

        segments = parse_vtt_subtitles(vtt)
        assert segments[0]["text"] == "태그가 있는 텍스트"


class TestDownloadVideo:
    @patch("src.scraper.youtube_downloader.subprocess.run")
    def test_command_construction(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        # Create a fake mp4 so glob finds it
        fake = tmp_path / "abc123.mp4"
        fake.write_bytes(b"fake")

        from src.scraper.youtube_downloader import download_video
        result = download_video("https://youtube.com/watch?v=abc123", tmp_path)

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "yt-dlp"
        assert "--merge-output-format" in call_args
        assert "mp4" in call_args
        assert result == fake

    @patch("src.scraper.youtube_downloader.subprocess.run")
    def test_download_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stderr="Error: video not found")

        from src.scraper.youtube_downloader import download_video
        with pytest.raises(YouTubeDownloadError, match="yt-dlp"):
            download_video("https://youtube.com/watch?v=bad", tmp_path)


class TestExtractClip:
    @patch("src.scraper.youtube_downloader.subprocess.run")
    def test_extract_clip_copy(self, mock_run, tmp_path):
        src = tmp_path / "source.mp4"
        src.write_bytes(b"x" * 2000)
        out = tmp_path / "clip.mp4"

        def side_effect(cmd, **kwargs):
            out.write_bytes(b"x" * 2000)
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        from src.scraper.youtube_downloader import extract_clip
        result = extract_clip(src, 10.0, 20.0, out)
        assert result == out

        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0]
        assert "-ss" in call_args
        assert "10.0" in call_args


class TestExtractAudio:
    @patch("src.scraper.youtube_downloader.subprocess.run")
    def test_extract_audio_command(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        src = tmp_path / "clip.mp4"
        src.write_bytes(b"fake")
        out = tmp_path / "audio.mp3"

        from src.scraper.youtube_downloader import extract_audio
        extract_audio(src, out)

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert "-vn" in call_args
        assert "libmp3lame" in call_args
