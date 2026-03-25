"""Tests for URL scraper and site parser detection."""
import pytest
from unittest.mock import patch

from src.scraper.url_scraper import extract_from_url, UrlScrapeError
from src.scraper.parsers import detect_site, UnsupportedSiteError, SITE_PATTERNS


class TestDetectSite:
    def test_dcinside(self):
        assert detect_site("https://gall.dcinside.com/mgallery/board/view/?id=test") == "dcinside"

    def test_natepann(self):
        assert detect_site("https://pann.nate.com/talk/123456") == "natepann"

    def test_naver_cafe(self):
        assert detect_site("https://cafe.naver.com/somecafe/12345") == "naver_cafe"

    def test_www_prefix_stripped(self):
        assert detect_site("https://www.dcinside.com/board/view") == "dcinside"

    def test_unsupported_raises(self):
        with pytest.raises(UnsupportedSiteError, match="지원하지 않는"):
            detect_site("https://example.com/post/123")

    def test_all_patterns_have_parsers(self):
        assert "dcinside.com" in SITE_PATTERNS
        assert "pann.nate.com" in SITE_PATTERNS
        assert "cafe.naver.com" in SITE_PATTERNS


class TestExtractFromUrl:
    def test_adds_https_if_missing(self):
        with patch("src.scraper.url_scraper.parse_url") as mock_parse:
            mock_parse.return_value = {
                "title": "테스트",
                "body": "본문 내용입니다 충분히 긴 텍스트",
                "comments": [],
            }
            post = extract_from_url("gall.dcinside.com/test")
            assert post.url.startswith("https://")

    @patch("src.scraper.url_scraper.parse_url")
    def test_returns_blind_post(self, mock_parse):
        mock_parse.return_value = {
            "title": "테스트 제목",
            "author": "작성자",
            "body": "충분히 긴 본문 텍스트입니다 여기에 내용이 있어요",
            "comments": [
                {"text": "댓글 1", "likes": 10, "author": "익명"},
                {"text": "댓글 2", "likes": 5},
            ],
        }
        post = extract_from_url("https://gall.dcinside.com/test")
        assert post.title == "테스트 제목"
        assert post.author == "작성자"
        assert len(post.comments) == 2
        assert post.comments[0].likes == 10
        assert post.comments[1].author == "익명"

    @patch("src.scraper.url_scraper.parse_url")
    def test_short_body_raises(self, mock_parse):
        mock_parse.return_value = {
            "title": "제목",
            "body": "짧음",
            "comments": [],
        }
        with pytest.raises(UrlScrapeError, match="콘텐츠가 부족"):
            extract_from_url("https://gall.dcinside.com/test")

    @patch("src.scraper.url_scraper.parse_url")
    def test_empty_body_raises(self, mock_parse):
        mock_parse.return_value = {
            "title": "제목",
            "body": "",
            "comments": [],
        }
        with pytest.raises(UrlScrapeError, match="콘텐츠가 부족"):
            extract_from_url("https://gall.dcinside.com/test")

    @patch("src.scraper.url_scraper.parse_url", side_effect=UnsupportedSiteError("지원 안함"))
    def test_unsupported_site_wraps_error(self, _):
        with pytest.raises(UrlScrapeError):
            extract_from_url("https://unknown.com/post")

    @patch("src.scraper.url_scraper.parse_url")
    def test_empty_comments_filtered(self, mock_parse):
        mock_parse.return_value = {
            "title": "제목",
            "body": "충분히 긴 본문 텍스트입니다 여기에 내용",
            "comments": [
                {"text": "유효한 댓글", "likes": 1},
                {"text": "", "likes": 0},
                {"text": "   ", "likes": 0},
            ],
        }
        post = extract_from_url("https://gall.dcinside.com/test")
        assert len(post.comments) == 1

    @patch("src.scraper.url_scraper.parse_url")
    def test_url_preserved(self, mock_parse):
        mock_parse.return_value = {
            "title": "테스트",
            "body": "충분히 긴 본문 텍스트입니다 여기에 내용이 있어요",
            "comments": [],
        }
        post = extract_from_url("https://pann.nate.com/talk/123")
        assert post.url == "https://pann.nate.com/talk/123"
