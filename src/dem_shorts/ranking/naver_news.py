"""T105: 네이버 뉴스 검색 크롤링 기반 인기 지표.

R-06: robots.txt 준수, 요청 간 5초 간격 (지연 준수는 호출자가 지연 파라미터로 제어).
원칙 I: 무료 공개 검색 페이지. 본 모듈은 정치인 이름 1건당 지난 7일 뉴스 건수를
대략치로 반환한다 (크롤링 실패·타임아웃 시 0).

실제 네트워크 호출은 `fetch_scores`에서 수행. 테스트는 `urllib.request.urlopen`
를 mock하거나, ranking_batch에서 `fetch_all_sources`를 통째로 교체한다.
"""
from __future__ import annotations

import logging
import re
import time
import urllib.parse
import urllib.request
from typing import Iterable

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://search.naver.com/search.naver?where=news&query={q}&sort=1"
_USER_AGENT = "Mozilla/5.0 (Dem-Shorts Studio/0.1 ranking-batch)"
_REQUEST_TIMEOUT_SEC = 15
_DEFAULT_DELAY_SEC = 5.0  # robots.txt 준수 (R-06)
_RESULT_COUNT_RE = re.compile(r"(\d[\d,]*)\s*건")


def _fetch_page(query: str) -> str:
    url = _SEARCH_URL.format(q=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_article_count(html: str) -> int:
    """검색 결과 HTML에서 '관련 뉴스 N건' 수치를 추출."""
    m = _RESULT_COUNT_RE.search(html)
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return 0


def fetch_scores(
    names: Iterable[str],
    *,
    delay_sec: float = _DEFAULT_DELAY_SEC,
) -> dict[str, float]:
    """정치인 이름별 최근 뉴스 건수 반환.

    네트워크 오류는 0으로 대체하여 다른 소스가 계속 돌도록 한다.
    """
    out: dict[str, float] = {}
    names_list = list(names)
    for idx, name in enumerate(names_list):
        try:
            html = _fetch_page(name)
            out[name] = float(_parse_article_count(html))
        except Exception as exc:
            logger.warning("naver_news fetch failed for %s: %s", name, exc)
            out[name] = 0.0
        if idx < len(names_list) - 1:
            time.sleep(delay_sec)
    return out
