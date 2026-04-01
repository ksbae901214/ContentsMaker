"""Nate Pann post parser.

Extracts title, body, and comments from Nate Pann posts.
"""
from __future__ import annotations

import logging

from src.scraper.parsers import ParseError

logger = logging.getLogger(__name__)


def parse(url: str) -> dict:
    """Parse a Nate Pann post URL and return BlindPost-compatible dict."""
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    logger.info("네이트판 파싱: %s", url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Title
            title = ""
            for sel in ["h3.aTitle", ".post-tit h3", "h3.tit"]:
                el = page.query_selector(sel)
                if el:
                    title = el.inner_text().strip()
                    break
            if not title:
                raise ParseError("게시글 제목을 찾을 수 없습니다. URL을 확인해주세요.")

            # Body
            body = ""
            for sel in ["#contentArea", "div#contentArea", ".post-content"]:
                el = page.query_selector(sel)
                if el:
                    body = el.inner_text().strip()
                    break
            if not body:
                raise ParseError("게시글 본문을 찾을 수 없습니다.")

            # Comments
            comments = []
            comment_els = page.query_selector_all(".cmt_list .txt, .comment-list .txt")
            for cel in comment_els[:10]:
                text = cel.inner_text().strip()
                if text and len(text) > 1:
                    comments.append({"text": text, "likes": 0, "author": "익명"})

            logger.info("네이트판 추출: 제목=%s, 본문=%d자, 댓글=%d개", title, len(body), len(comments))

            return {
                "title": title,
                "author": "네이트판",
                "body": body,
                "comments": comments,
                "url": url,
            }
        except PwTimeout:
            raise ParseError("페이지 로딩 시간 초과. URL을 확인해주세요.")
        finally:
            browser.close()
