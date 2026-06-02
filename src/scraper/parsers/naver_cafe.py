"""Naver Cafe post parser.

Extracts title, body, and comments from Naver Cafe posts.
Note: Only public (non-login-required) posts are supported.
Naver Cafe renders content inside an iframe.
"""
from __future__ import annotations

import logging

from src.scraper.parsers import ParseError

logger = logging.getLogger(__name__)


def parse(url: str) -> dict:
    """Parse a Naver Cafe post URL and return BlindPost-compatible dict."""
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    logger.info("네이버 카페 파싱: %s", url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Check for login wall
            login_el = page.query_selector(".LoginRequired, .login_required, .error_content")
            if login_el:
                raise ParseError("로그인이 필요한 게시글입니다. 공개 게시글만 지원합니다.")

            # Naver Cafe content is inside an iframe
            iframe_el = page.query_selector("iframe#cafe_main")
            frame = iframe_el.content_frame() if iframe_el else None

            # If no iframe, try direct page content (mobile URL)
            target = frame if frame else page

            # Title
            title = ""
            for sel in [".article_header .title_text", "h3.title_text", ".ArticleTitle", ".tit_area .title"]:
                el = target.query_selector(sel)
                if el:
                    title = el.inner_text().strip()
                    break

            if not title:
                # Try page-level title as fallback
                page_title = page.title()
                if page_title and "카페" in page_title:
                    title = page_title.split(" : ")[0].strip() if " : " in page_title else page_title
                if not title:
                    raise ParseError("게시글 제목을 찾을 수 없습니다. 비공개 게시글이거나 URL이 잘못되었습니다.")

            # Body
            body = ""
            for sel in [".article_viewer", "div.se-main-container", ".ContentRenderer", ".content_area"]:
                el = target.query_selector(sel)
                if el:
                    body = el.inner_text().strip()
                    break
            if not body:
                raise ParseError("게시글 본문을 찾을 수 없습니다.")

            # Comments
            comments = []
            comment_els = target.query_selector_all(".comment_text_box span, .text_comment")
            for cel in comment_els[:10]:
                text = cel.inner_text().strip()
                if text and len(text) > 1:
                    comments.append({"text": text, "likes": 0, "author": "익명"})

            logger.info("네이버 카페 추출: 제목=%s, 본문=%d자, 댓글=%d개", title, len(body), len(comments))

            return {
                "title": title,
                "author": "네이버 카페",
                "body": body,
                "comments": comments,
                "url": url,
            }
        except PwTimeout:
            raise ParseError("페이지 로딩 시간 초과. URL을 확인해주세요.")
        finally:
            browser.close()
