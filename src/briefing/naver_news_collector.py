"""네이버 검색 API로 KST 어제 발행된 정치 뉴스 수집.

API 한도: 25,000 req/일 (무료). 검색당 max 100건.

환경변수: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (이미 celebrity 모드에 등록됨).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib import parse, request

from src.briefing.models import NewsItem
from src.briefing.youtube_collector import KST, yesterday_kst_range

logger = logging.getLogger(__name__)


class NaverNewsCollectorError(Exception):
    """Raised when 네이버 검색 API access fails."""


def _http_get_json(url: str, headers: dict, timeout: float = 10.0) -> dict:
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _strip_html_tags(text: str) -> str:
    """네이버 응답의 <b>, </b> 태그 + HTML entity 제거."""
    import html
    import re
    cleaned = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(cleaned)


def _parse_pub_date(s: str) -> datetime | None:
    """RFC 822 (예: 'Mon, 19 May 2025 14:30:00 +0900') 파싱."""
    try:
        return parsedate_to_datetime(s)
    except Exception:
        return None


def collect_yesterday_news(
    queries: list[str] | None = None,
    *,
    display: int = 100,
    max_pages: int = 11,  # start=1, 101, ..., 1001 (네이버 API 한도)
    after_kst: datetime | None = None,
    before_kst: datetime | None = None,
    http_get=None,  # 주입용 (테스트)
) -> list[NewsItem]:
    """KST 어제 발행된 정치 뉴스 수집.

    네이버 검색 API의 `sort=date`는 최신순 → 첫 100건이 모두 오늘인 경우가 많음.
    어제 발행 기사에 도달하려면 페이지네이션 필요 (start=1, 101, 201, ...).
    어제보다 더 오래된 기사가 나오면 그 쿼리는 조기 종료 (불필요 호출 절약).

    Args:
        queries: 검색어 리스트. 기본 ["정치", "국회", "대통령", "선거"].
        display: 검색어당 페이지 크기 (네이버 API 한도 100).
        max_pages: 최대 페이지 수 (네이버 한도 start ≤ 1000 → 11페이지).
        after_kst / before_kst: 명시 안 하면 yesterday_kst_range() 사용.
        http_get: 주입된 GET 함수 (테스트용). None이면 urllib 사용.

    Returns:
        NewsItem 리스트. 중복 제거(link 기준). pub_date가 KST 어제 범위 내인 것만.
    """
    client_id = os.environ.get("NAVER_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise NaverNewsCollectorError(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수 필요. "
            "https://developers.naver.com/apps/ → 애플리케이션 등록 → 검색"
        )

    if after_kst is None or before_kst is None:
        after_kst, before_kst = yesterday_kst_range()

    if queries is None:
        queries = ["정치", "국회", "대통령", "선거"]

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    fetch = http_get if http_get is not None else _http_get_json

    seen_links: set[str] = set()
    out: list[NewsItem] = []
    for q in queries:
        q_added = 0
        for page in range(max_pages):
            start = page * display + 1
            # 네이버 API: start ≤ 1000. start=1001은 거부.
            if start > 1000:
                break
            # 마지막 페이지에서 start+display-1 > 1000이면 display 조정
            cur_display = min(display, 1000 - start + 1)
            params = parse.urlencode({
                "query": q,
                "display": cur_display,
                "start": start,
                "sort": "date",
            })
            url = f"https://openapi.naver.com/v1/search/news.json?{params}"
            try:
                data = fetch(url, headers)
            except Exception as e:
                logger.warning("네이버 '%s' page %d 실패: %s", q, page + 1, e)
                break

            items = data.get("items", [])
            if not items:
                break

            page_added = 0
            stopped_early = False
            for it in items:
                link = it.get("link", "").strip()
                if not link or link in seen_links:
                    continue
                pub = _parse_pub_date(it.get("pubDate", ""))
                if pub is None:
                    continue
                pub_kst = pub.astimezone(KST)
                if pub_kst > before_kst:
                    # 어제 범위보다 늦음 (오늘 또는 미래) — 더 새로운 페이지는 스킵
                    continue
                if pub_kst < after_kst:
                    # 어제 범위보다 오래됨 — 이 쿼리는 더 이상 어제 기사 없음 (sort=date)
                    stopped_early = True
                    break
                seen_links.add(link)
                page_added += 1
                out.append(NewsItem(
                    title=_strip_html_tags(it.get("title", "")),
                    link=link,
                    description=_strip_html_tags(it.get("description", "")),
                    pub_date=it.get("pubDate", ""),
                    source="naver",
                ))
            q_added += page_added
            if stopped_early:
                break
            if len(items) < cur_display:
                # 결과 끝 — 더 이상 페이지 없음
                break
        logger.info("  네이버 '%s': %d 어제 기사", q, q_added)
    return out
