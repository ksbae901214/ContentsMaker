"""Tests for Namuwiki scraper (Phase 9-1).

Uses httpx.MockTransport to simulate network responses. Never hits the real
namu.wiki during tests — that would be both slow and ethically questionable
given their rate-limit policies.
"""
from __future__ import annotations

import time

import httpx
import pytest

from src.scraper.celebrity_models import CelebrityInfo
from src.scraper.namuwiki_scraper import (
    NamuwikiScraper,
    NamuwikiScraperError,
)


# --- Fixture HTML -----------------------------------------------------------
# Minimal HTML that mimics the parts of a namu.wiki page we care about.
# Real pages have far more markup but we only extract a few specific sections.

SAMPLE_HTML_SON = """
<!DOCTYPE html>
<html>
<head><title>손흥민 - 나무위키</title></head>
<body>
<div class="wiki-heading-content">
  <p>대한민국의 축구 선수. 현재 토트넘 홋스퍼에서 활약 중이다.</p>
  <div class="wiki-table">
    <tr><th>출생</th><td>1992년 7월 8일</td></tr>
    <tr><th>직업</th><td>축구 선수</td></tr>
  </div>
  <h2 id="s-3">경력</h2>
  <ul>
    <li>함부르크 SV 유스 입단 (2008)</li>
    <li>토트넘 홋스퍼 이적 (2015)</li>
    <li>EPL 득점왕 (2022)</li>
  </ul>
  <h2 id="s-4">여담</h2>
  <ul>
    <li>아버지 손웅정은 축구 감독 출신이다.</li>
    <li>왼발잡이지만 양발을 모두 능숙하게 쓴다.</li>
  </ul>
</div>
</body>
</html>
"""

SAMPLE_HTML_404 = "<html><body><h1>문서가 존재하지 않습니다</h1></body></html>"


def _make_transport(routes: dict[str, tuple[int, str]]) -> httpx.MockTransport:
    """Build a mock transport that dispatches by URL path."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path
        if key not in routes:
            return httpx.Response(500, text="unexpected url")
        status, body = routes[key]
        return httpx.Response(status, text=body)

    return httpx.MockTransport(handler)


# --- Tests ------------------------------------------------------------------


class TestFetchPerson:
    def test_successful_fetch(self, tmp_path):
        transport = _make_transport({
            "/w/손흥민": (200, SAMPLE_HTML_SON),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        info = scraper.fetch_person("손흥민")

        assert isinstance(info, CelebrityInfo)
        assert info.name == "손흥민"
        assert "축구 선수" in info.summary
        assert info.source_url == "https://namu.wiki/w/%EC%86%90%ED%9D%A5%EB%AF%BC"
        assert len(info.career_highlights) >= 1
        assert any("토트넘" in h for h in info.career_highlights)

    def test_404_raises(self, tmp_path):
        transport = _make_transport({
            "/w/존재하지않는인물": (404, SAMPLE_HTML_404),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        with pytest.raises(NamuwikiScraperError, match="404|찾을 수 없"):
            scraper.fetch_person("존재하지않는인물")

    def test_empty_name_rejected(self, tmp_path):
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=_make_transport({}),
        )
        with pytest.raises(NamuwikiScraperError, match="이름"):
            scraper.fetch_person("")

    def test_user_agent_header_set(self, tmp_path):
        """Without a User-Agent, namu.wiki refuses requests."""
        captured: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request.headers.get("user-agent", ""))
            return httpx.Response(200, text=SAMPLE_HTML_SON)

        transport = httpx.MockTransport(handler)
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        scraper.fetch_person("손흥민")
        assert captured and captured[0], "User-Agent must be set"
        assert "ContentsMaker" in captured[0] or "Mozilla" in captured[0]


class TestCaching:
    def test_second_call_uses_cache(self, tmp_path):
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(200, text=SAMPLE_HTML_SON)

        transport = httpx.MockTransport(handler)
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        first = scraper.fetch_person("손흥민")
        second = scraper.fetch_person("손흥민")

        assert call_count["n"] == 1, "Second call should hit cache"
        assert first == second

    def test_cache_file_created(self, tmp_path):
        cache_dir = tmp_path / "cache"
        transport = _make_transport({
            "/w/손흥민": (200, SAMPLE_HTML_SON),
        })
        scraper = NamuwikiScraper(
            cache_dir=cache_dir,
            rate_limit_s=0.0,
            transport=transport,
        )
        scraper.fetch_person("손흥민")
        files = list(cache_dir.glob("*.json"))
        assert len(files) == 1


class TestRateLimit:
    def test_rate_limit_delays_second_call(self, tmp_path):
        """Rate limit enforcement — no concurrent calls within window."""
        transport = _make_transport({
            "/w/손흥민": (200, SAMPLE_HTML_SON),
            "/w/유재석": (200, SAMPLE_HTML_SON.replace("손흥민", "유재석")),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.3,
            transport=transport,
        )
        start = time.monotonic()
        scraper.fetch_person("손흥민")
        scraper.fetch_person("유재석")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.3, f"Expected ≥0.3s but got {elapsed:.3f}s"


class TestParseFields:
    def test_extracts_trivia(self, tmp_path):
        transport = _make_transport({
            "/w/손흥민": (200, SAMPLE_HTML_SON),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        info = scraper.fetch_person("손흥민")
        assert len(info.trivia) >= 1
        assert any("아버지" in t for t in info.trivia)

    def test_missing_sections_are_empty(self, tmp_path):
        minimal_html = """
        <html><body>
          <div class="wiki-heading-content">
            <p>간단한 설명.</p>
          </div>
        </body></html>
        """
        transport = _make_transport({
            "/w/간단": (200, minimal_html),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        info = scraper.fetch_person("간단")
        assert info.summary == "간단한 설명."
        assert info.career_highlights == ()
        assert info.trivia == ()
