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


# --- Bugfix 2026-04-21: Namuwiki HTML 구조 변경 대응 ---------------------
# 실제 namu.wiki 페이지는 <p> 대신 <div class="wiki-paragraph">로 문단을 감싸며,
# 섹션 제목은 <h2> 대신 <div class="wiki-heading">를 사용한다. 장동혁 케이스에서
# 기존 _extract_summary가 <p>만 찾아 요약 추출 실패 → "페이지에서 요약을 찾을
# 수 없습니다" 에러로 파이프라인이 exit 1.

SAMPLE_HTML_WIKI_PARAGRAPH = """
<!DOCTYPE html>
<html>
<head><title>장동혁 - 나무위키</title></head>
<body>
<div class="wiki-heading-content">
  <div class="wiki-paragraph">대한민국의 판사 출신 정치인. 제4대 국민의힘 대표이자 제21·22대 국회의원이다.</div>
  <div class="wiki-paragraph">1969년 충청남도 보령에서 태어났다.</div>
  <table>
    <tr><th>출생</th><td>1969년</td></tr>
    <tr><th>직업</th><td>정치인</td></tr>
  </table>
</div>
</body></html>
"""


class TestWikiParagraphStructure:
    """namuwiki 신규 HTML 구조 (div.wiki-paragraph) 대응."""

    def test_extracts_summary_from_wiki_paragraph_div(self, tmp_path):
        transport = _make_transport({
            "/w/장동혁": (200, SAMPLE_HTML_WIKI_PARAGRAPH),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache",
            rate_limit_s=0.0,
            transport=transport,
        )
        info = scraper.fetch_person("장동혁")
        assert "판사 출신 정치인" in info.summary
        assert info.summary.startswith("대한민국")

    def test_falls_back_gracefully_when_only_p_exists(self, tmp_path):
        """기존 <p> 구조도 계속 동작 (하위호환)."""
        old_html = """
        <html><body>
          <div class="wiki-heading-content">
            <p>구식 p 태그로만 구성된 문서.</p>
          </div>
        </body></html>
        """
        transport = _make_transport({"/w/old": (200, old_html)})
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache", rate_limit_s=0.0, transport=transport,
        )
        info = scraper.fetch_person("old")
        assert info.summary == "구식 p 태그로만 구성된 문서."

    def test_qualifier_tries_disambiguation_page_first(self, tmp_path):
        """qualifier 주면 `{name}(qualifier)` 페이지를 먼저 시도."""
        ambiguous_html = SAMPLE_HTML_WIKI_PARAGRAPH.replace(
            "판사 출신 정치인", "정치인 장동혁 (동명이인 분기)"
        )
        transport = _make_transport({
            "/w/장동혁(정치인)": (200, ambiguous_html),
            "/w/장동혁": (200, SAMPLE_HTML_WIKI_PARAGRAPH),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache", rate_limit_s=0.0, transport=transport,
        )
        info = scraper.fetch_person("장동혁", qualifier="정치인")
        assert "정치인 장동혁" in info.summary or "동명이인 분기" in info.summary

    def test_qualifier_falls_back_to_plain_when_disambig_missing(self, tmp_path):
        """`{name}(qualifier)` 404이면 일반 `{name}` 페이지 사용."""
        transport = _make_transport({
            "/w/장동혁(배우)": (404, "not found"),
            "/w/장동혁": (200, SAMPLE_HTML_WIKI_PARAGRAPH),
        })
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache", rate_limit_s=0.0, transport=transport,
        )
        info = scraper.fetch_person("장동혁", qualifier="배우")
        # 일반 페이지 내용이 반환돼야 함
        assert "판사 출신 정치인" in info.summary

    def test_skips_empty_wiki_paragraphs(self, tmp_path):
        """첫 번째 wiki-paragraph가 공백이면 다음 것을 시도."""
        html = """
        <html><body>
          <div class="wiki-heading-content">
            <div class="wiki-paragraph"></div>
            <div class="wiki-paragraph">   </div>
            <div class="wiki-paragraph">실제 요약 내용이 충분히 길게 들어갑니다. 정치인 소개입니다.</div>
          </div>
        </body></html>
        """
        transport = _make_transport({"/w/x": (200, html)})
        scraper = NamuwikiScraper(
            cache_dir=tmp_path / "cache", rate_limit_s=0.0, transport=transport,
        )
        info = scraper.fetch_person("x")
        # 빈 문단 2개를 스킵하고 실제 내용 있는 문단을 가져왔는지 확인
        assert "실제 요약 내용" in info.summary
