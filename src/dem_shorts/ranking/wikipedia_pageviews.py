"""T108: 위키백과 한국어 페이지뷰 API 래퍼.

API: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ko.wikipedia/all-access/all-agents/{title}/daily/{start}/{end}
무료. 앱 식별용 User-Agent 권장.

R-06: 10% 가중치 (트위터 대체).
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Iterable

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "ko.wikipedia/all-access/all-agents/{title}/daily/{start}/{end}"
)
_USER_AGENT = "DemShortsStudio/0.1 (contact: admin@example.com)"
_WINDOW_DAYS = 7
_REQUEST_TIMEOUT_SEC = 15


def _build_url(title: str, start: date, end: date) -> str:
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    return _BASE_URL.format(
        title=encoded,
        start=start.strftime("%Y%m%d"),
        end=end.strftime("%Y%m%d"),
    )


def _fetch_views(title: str, *, today: date | None = None) -> float:
    """지난 7일간 페이지뷰 합계."""
    today = today or date.today()
    start = today - timedelta(days=_WINDOW_DAYS)
    url = _build_url(title, start, today)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        logger.warning("wikipedia_pageviews fetch failed for %s: %s", title, exc)
        return 0.0

    items = data.get("items", [])
    return float(sum(it.get("views", 0) for it in items))


def fetch_scores(names: Iterable[str]) -> dict[str, float]:
    """한국어 위키백과 페이지뷰 집계."""
    return {name: _fetch_views(name) for name in names}
