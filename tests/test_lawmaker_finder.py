"""Tests for lawmaker video finder module."""
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.scraper.lawmaker_video_finder import (
    VideoSearchError,
    _build_query,
    _parse_results,
    format_duration,
    format_upload_date,
    search_lawmaker_videos,
)


class TestBuildQuery:
    def test_all_source(self):
        q = _build_query("나경원", "all", 10)
        assert "나경원" in q
        assert "발언" in q
        assert "ytsearch10" in q

    def test_natv_source(self):
        q = _build_query("배현진", "natv", 5)
        assert "배현진" in q
        assert "NATV" in q
        assert "ytsearch5" in q

    def test_news_source(self):
        q = _build_query("김예지", "news", 8)
        assert "김예지" in q
        assert "뉴스" in q
        assert "ytsearch8" in q


class TestParseResults:
    def test_parses_valid_line(self):
        line = json.dumps({
            "id": "abc123",
            "title": "나경원 의원 발언",
            "url": "https://www.youtube.com/watch?v=abc123",
            "duration": 180,
            "view_count": 50000,
            "upload_date": "20240315",
            "channel": "국회TV",
            "thumbnail": "https://i.ytimg.com/vi/abc123/hq.jpg",
        })
        results = _parse_results([line])
        assert len(results) == 1
        assert results[0]["title"] == "나경원 의원 발언"
        assert results[0]["duration_seconds"] == 180
        assert results[0]["view_count"] == 50000
        assert results[0]["channel"] == "국회TV"

    def test_skips_invalid_json(self):
        results = _parse_results(["not-json", "{}"])
        # {} has no url or id, should be skipped
        assert len(results) == 0

    def test_fallback_url_from_id(self):
        line = json.dumps({"id": "xyz789", "title": "테스트"})
        results = _parse_results([line])
        assert len(results) == 1
        assert "xyz789" in results[0]["url"]

    def test_empty_lines_skipped(self):
        results = _parse_results(["", "   "])
        assert results == []


class TestFormatDuration:
    def test_minutes_seconds(self):
        assert format_duration(125) == "2:05"

    def test_hours(self):
        assert format_duration(3665) == "1:01:05"

    def test_zero(self):
        assert format_duration(0) == "--:--"

    def test_negative(self):
        assert format_duration(-1) == "--:--"


class TestFormatUploadDate:
    def test_yyyymmdd(self):
        assert format_upload_date("20240315") == "2024.03.15"

    def test_non_standard(self):
        assert format_upload_date("2024-03") == "2024-03"


class TestSearchLawmakerVideos:
    @patch("src.scraper.lawmaker_video_finder.subprocess.run")
    def test_success(self, mock_run):
        fake_line = json.dumps({
            "id": "abc", "title": "나경원 발언",
            "url": "https://www.youtube.com/watch?v=abc",
            "duration": 300, "view_count": 10000,
            "upload_date": "20240101", "channel": "뉴스채널",
            "thumbnail": "",
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=fake_line + "\n", stderr="")
        results = search_lawmaker_videos("나경원")
        assert len(results) == 1
        assert results[0]["title"] == "나경원 발언"

    @patch("src.scraper.lawmaker_video_finder.subprocess.run")
    def test_raises_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
        with pytest.raises(VideoSearchError):
            search_lawmaker_videos("나경원")

    @patch("src.scraper.lawmaker_video_finder.subprocess.run")
    def test_raises_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("yt-dlp", 30)
        with pytest.raises(VideoSearchError, match="시간 초과"):
            search_lawmaker_videos("나경원")

    @patch("src.scraper.lawmaker_video_finder.subprocess.run")
    def test_raises_when_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(VideoSearchError, match="yt-dlp"):
            search_lawmaker_videos("나경원")
