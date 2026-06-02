"""T106: Google Trends 인기 지표 (pytrends 래퍼).

R-06: pytrends는 비공식 무료 라이브러리. rate limit 방지를 위해
정치인 1명당 최대 3 키워드, 1초당 1 요청 미만 유지.

pytrends 미설치 환경 / 네트워크 실패 시 모두 0.0을 반환해 다른 소스가
계속 돌도록 한다.
"""
from __future__ import annotations

import logging
import time
from typing import Iterable

logger = logging.getLogger(__name__)

_TIMEFRAME = "now 7-d"  # 지난 7일
_GEO = "KR"
_REQUEST_DELAY_SEC = 1.1


def _build_trendreq():
    """pytrends TrendReq 인스턴스 (lazy import)."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.warning("pytrends not installed — google_trends returns 0.0 for all")
        return None
    try:
        return TrendReq(hl="ko-KR", tz=540)
    except Exception as exc:
        logger.warning("pytrends init failed: %s", exc)
        return None


def _fetch_single(trend, keyword: str) -> float:
    """단일 키워드 지난 7일 평균 관심도 (0~100)."""
    try:
        trend.build_payload([keyword], cat=0, timeframe=_TIMEFRAME, geo=_GEO)
        df = trend.interest_over_time()
        if df is None or df.empty:
            return 0.0
        return float(df[keyword].mean())
    except Exception as exc:
        logger.warning("pytrends fetch failed for %s: %s", keyword, exc)
        return 0.0


def fetch_scores(names: Iterable[str]) -> dict[str, float]:
    """정치인 이름별 Google Trends 관심도 평균."""
    names_list = list(names)
    trend = _build_trendreq()
    out: dict[str, float] = {}
    if trend is None:
        return {n: 0.0 for n in names_list}
    for idx, name in enumerate(names_list):
        out[name] = _fetch_single(trend, name)
        if idx < len(names_list) - 1:
            time.sleep(_REQUEST_DELAY_SEC)
    return out
