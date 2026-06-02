"""DCInside gallery post parser.

Extracts title, body, and comments from DC gallery posts
using Playwright for JavaScript-rendered content.
"""
from __future__ import annotations

import logging

from src.scraper.parsers import ParseError

logger = logging.getLogger(__name__)


def parse(url: str) -> dict:
    """Parse a DCInside post URL and return BlindPost-compatible dict."""
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    logger.info("디시인사이드 파싱: %s", url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "ko-KR,ko"})
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Title
            title = ""
            for sel in [".title_subject", "h3.title span.title_subject", "span.title_subject"]:
                el = page.query_selector(sel)
                if el:
                    title = el.inner_text().strip()
                    break
            if not title:
                raise ParseError("게시글 제목을 찾을 수 없습니다. URL을 확인해주세요.")

            # Body
            body = ""
            for sel in [".write_div", ".writing_view_box", "div.write_div"]:
                el = page.query_selector(sel)
                if el:
                    body = el.inner_text().strip()
                    break
            if not body:
                raise ParseError("게시글 본문을 찾을 수 없습니다.")

            # Comments
            comments = []
            comment_els = page.query_selector_all(".cmt_txtbox p, .usertxt")
            for cel in comment_els[:10]:
                text = cel.inner_text().strip()
                if text and len(text) > 1:
                    comments.append({"text": text, "likes": 0, "author": "익명"})

            logger.info("디시인사이드 추출: 제목=%s, 본문=%d자, 댓글=%d개", title, len(body), len(comments))

            return {
                "title": title,
                "author": "디시인사이드",
                "body": body,
                "comments": comments,
                "url": url,
            }
        except PwTimeout:
            raise ParseError("페이지 로딩 시간 초과. URL을 확인해주세요.")
        finally:
            browser.close()
