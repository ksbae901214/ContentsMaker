"""URL scraper — extracts post content from supported sites.

Supported: DCInside, Nate Pann, Naver Cafe.
Returns BlindPost object for the existing pipeline.
"""
from __future__ import annotations

import logging

from src.scraper.models import BlindPost, Comment
from src.scraper.parsers import UnsupportedSiteError, ParseError, parse_url

logger = logging.getLogger(__name__)


class UrlScrapeError(Exception):
    """Raised when URL scraping fails."""


def extract_from_url(url: str) -> BlindPost:
    """Extract post content from a URL and return BlindPost.

    Detects the site, parses the page, and converts to BlindPost.
    """
    url = url.strip()
    if not url.startswith("http"):
        url = f"https://{url}"

    logger.info("URL 파싱 시작: %s", url)

    try:
        data = parse_url(url)
    except UnsupportedSiteError as e:
        raise UrlScrapeError(str(e)) from e
    except ParseError as e:
        raise UrlScrapeError(f"게시글을 찾을 수 없습니다: {e}") from e
    except Exception as e:
        raise UrlScrapeError(f"URL 파싱 오류: {e}") from e

    if not data.get("body") or len(data["body"].strip()) < 10:
        raise UrlScrapeError("텍스트 콘텐츠가 부족합니다. 이미지만 있는 게시글은 지원하지 않습니다.")

    comments = tuple(
        Comment(
            text=c["text"],
            likes=c.get("likes", 0),
            author=c.get("author", "익명"),
        )
        for c in data.get("comments", [])
        if c.get("text", "").strip()
    )

    post = BlindPost(
        title=data["title"],
        author=data.get("author", ""),
        body=data["body"],
        comments=comments,
        url=url,
    )

    logger.info("URL 추출 완료: %s (본문 %d자, 댓글 %d개)", post.title, len(post.body), len(post.comments))
    return post
