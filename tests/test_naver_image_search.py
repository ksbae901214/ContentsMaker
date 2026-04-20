"""Tests for NaverImageSearcher (Phase 9-2)."""
from __future__ import annotations

import json

import httpx
import pytest

from src.illustrator.naver_image_search import (
    NaverImage,
    NaverImageSearcher,
    NaverImageSearchError,
)


SAMPLE_API_RESPONSE = {
    "lastBuildDate": "Mon, 20 Apr 2026 10:00:00 +0900",
    "total": 12345,
    "start": 1,
    "display": 3,
    "items": [
        {
            "title": "손흥민 선수 프로필",
            "link": "https://example.com/son1.jpg",
            "thumbnail": "https://thumb.example.com/son1.jpg",
            "sizewidth": "1600",
            "sizeheight": "1200",
        },
        {
            "title": "손흥민 토트넘",
            "link": "https://example.com/son2.png",
            "thumbnail": "https://thumb.example.com/son2.png",
            "sizewidth": "800",
            "sizeheight": "600",
        },
        {
            "title": "세 번째",
            "link": "https://example.com/son3.webp",
            "thumbnail": "",
            "sizewidth": "0",
            "sizeheight": "0",
        },
    ],
}


def _search_transport(payload: dict, status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v1/search/image.json" in str(request.url):
            return httpx.Response(status, json=payload)
        return httpx.Response(404, text="not found")

    return httpx.MockTransport(handler)


class TestSearch:
    def test_basic_search(self):
        transport = _search_transport(SAMPLE_API_RESPONSE)
        searcher = NaverImageSearcher(
            client_id="id", client_secret="secret", transport=transport,
        )
        results = searcher.search("손흥민")
        assert len(results) == 3
        assert results[0].link == "https://example.com/son1.jpg"
        assert results[0].width == 1600

    def test_auth_headers_sent(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["id"] = request.headers.get("x-naver-client-id", "")
            captured["secret"] = request.headers.get("x-naver-client-secret", "")
            return httpx.Response(200, json=SAMPLE_API_RESPONSE)

        transport = httpx.MockTransport(handler)
        searcher = NaverImageSearcher(
            client_id="myid", client_secret="mysecret", transport=transport,
        )
        searcher.search("query")
        assert captured["id"] == "myid"
        assert captured["secret"] == "mysecret"

    def test_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
        monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)
        transport = _search_transport(SAMPLE_API_RESPONSE)
        searcher = NaverImageSearcher(transport=transport)
        with pytest.raises(NaverImageSearchError, match="NAVER_CLIENT_ID"):
            searcher.search("x")

    def test_empty_query_raises(self):
        searcher = NaverImageSearcher(client_id="x", client_secret="y")
        with pytest.raises(NaverImageSearchError, match="검색어"):
            searcher.search("   ")

    def test_invalid_count_raises(self):
        searcher = NaverImageSearcher(client_id="x", client_secret="y")
        with pytest.raises(NaverImageSearchError, match="count"):
            searcher.search("x", count=0)
        with pytest.raises(NaverImageSearchError, match="count"):
            searcher.search("x", count=101)

    def test_invalid_sort_raises(self):
        searcher = NaverImageSearcher(client_id="x", client_secret="y")
        with pytest.raises(NaverImageSearchError, match="sort"):
            searcher.search("x", sort="invalid")

    def test_http_error_raises(self):
        transport = _search_transport({"errorMessage": "rate limit"}, status=429)
        searcher = NaverImageSearcher(
            client_id="x", client_secret="y", transport=transport,
        )
        with pytest.raises(NaverImageSearchError, match="429"):
            searcher.search("x")


class TestDownload:
    def test_download_saves_files_and_metadata(self, tmp_path):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "search" in url:
                return httpx.Response(200, json=SAMPLE_API_RESPONSE)
            return httpx.Response(200, content=b"fake-jpg-bytes")

        transport = httpx.MockTransport(handler)
        searcher = NaverImageSearcher(
            client_id="x", client_secret="y", transport=transport,
        )
        results = searcher.search("손흥민")
        saved = searcher.download(results, tmp_path, filename_prefix="son")

        assert len(saved) == 3
        for p in saved:
            assert p.exists()
            assert p.read_bytes() == b"fake-jpg-bytes"

        meta = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
        assert len(meta) == 3
        assert meta[0]["saved_as"] == saved[0].name
        assert meta[0]["link"] == "https://example.com/son1.jpg"

    def test_download_skips_broken_links(self, tmp_path):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "search" in url:
                return httpx.Response(200, json=SAMPLE_API_RESPONSE)
            # Fail the second image only
            if "son2.png" in url:
                return httpx.Response(404)
            return httpx.Response(200, content=b"ok")

        transport = httpx.MockTransport(handler)
        searcher = NaverImageSearcher(
            client_id="x", client_secret="y", transport=transport,
        )
        results = searcher.search("손흥민")
        saved = searcher.download(results, tmp_path)
        assert len(saved) == 2  # broken one skipped


class TestImageFromApi:
    def test_from_api_item_handles_empty_dimensions(self):
        img = NaverImage.from_api_item({
            "title": "x",
            "link": "https://x/y.jpg",
            "thumbnail": "",
            "sizewidth": "",
            "sizeheight": "",
        })
        assert img.width == 0
        assert img.height == 0

    def test_extension_guessing_jpg_default(self, tmp_path):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x")

        transport = httpx.MockTransport(handler)
        searcher = NaverImageSearcher(
            client_id="a", client_secret="b", transport=transport,
        )
        images = (NaverImage(
            title="t", link="https://x/no-extension", thumbnail="",
            width=0, height=0,
        ),)
        saved = searcher.download(images, tmp_path)
        assert saved[0].suffix == ".jpg"
