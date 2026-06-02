"""T107: YouTube Data API 기반 인기 지표.

search.list?q=<이름>으로 지난 30일 업로드된 영상 N개의 조회수·업로드 건수 집계.
쿼터 소비: 정치인 1명당 search.list 100 units + videos.list 1 unit = ~100/인.
주 1회 batch (일 10,000 unit 여유 범위 내).

`YOUTUBE_API_KEY` 미설정 시 0.0 반환.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

from src.dem_shorts.config import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)

_MAX_RESULTS = 10
_WINDOW_DAYS = 30


def _build_service():
    if not YOUTUBE_API_KEY:
        return None
    try:
        from googleapiclient.discovery import build  # type: ignore

        return build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)
    except Exception as exc:
        logger.warning("youtube api init failed: %s", exc)
        return None


def _search_and_sum_views(svc, keyword: str) -> float:
    """search.list → videos.list → Σ view_count."""
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=_WINDOW_DAYS)
    ).isoformat().replace("+00:00", "Z")
    try:
        search_resp = (
            svc.search()
            .list(
                q=keyword,
                part="id",
                type="video",
                maxResults=_MAX_RESULTS,
                publishedAfter=published_after,
                regionCode="KR",
                relevanceLanguage="ko",
            )
            .execute()
        )
    except Exception as exc:
        logger.warning("youtube search failed for %s: %s", keyword, exc)
        return 0.0

    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return 0.0

    try:
        stat_resp = (
            svc.videos()
            .list(id=",".join(video_ids), part="statistics")
            .execute()
        )
    except Exception as exc:
        logger.warning("youtube videos.list failed for %s: %s", keyword, exc)
        return 0.0

    total_views = 0
    for item in stat_resp.get("items", []):
        stats = item.get("statistics", {})
        try:
            total_views += int(stats.get("viewCount", 0))
        except (TypeError, ValueError):
            pass
    # 영상 1개 평균 조회수 (log 스케일 효과: 상위를 완만하게)
    return float(total_views) / max(len(video_ids), 1)


def fetch_scores(names: Iterable[str]) -> dict[str, float]:
    names_list = list(names)
    svc = _build_service()
    if svc is None:
        return {n: 0.0 for n in names_list}
    return {name: _search_and_sum_views(svc, name) for name in names_list}
