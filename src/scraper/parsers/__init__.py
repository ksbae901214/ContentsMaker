"""Site parsers for URL-based content extraction.

Detects the site from a URL and routes to the appropriate parser.
Each parser returns a BlindPost-compatible dict.
"""
from __future__ import annotations

from urllib.parse import urlparse


class UnsupportedSiteError(Exception):
    """Raised when URL belongs to an unsupported site."""


class ParseError(Exception):
    """Raised when content extraction fails."""


SITE_PATTERNS: dict[str, str] = {
    "dcinside.com": "dcinside",
    "pann.nate.com": "natepann",
    "cafe.naver.com": "naver_cafe",
}


def detect_site(url: str) -> str:
    """Detect which site a URL belongs to. Returns parser module name."""
    host = urlparse(url).netloc.lower().replace("www.", "")
    for pattern, parser_name in SITE_PATTERNS.items():
        if pattern in host or pattern in url.lower():
            return parser_name
    raise UnsupportedSiteError(
        f"지원하지 않는 사이트입니다: {host}\n"
        f"지원 사이트: 디시인사이드, 네이트판, 네이버 카페"
    )


def parse_url(url: str) -> dict:
    """Parse a URL and return BlindPost-compatible dict."""
    parser_name = detect_site(url)

    if parser_name == "dcinside":
        from src.scraper.parsers.dcinside import parse
    elif parser_name == "natepann":
        from src.scraper.parsers.natepann import parse
    elif parser_name == "naver_cafe":
        from src.scraper.parsers.naver_cafe import parse
    else:
        raise UnsupportedSiteError(f"파서 없음: {parser_name}")

    return parse(url)
