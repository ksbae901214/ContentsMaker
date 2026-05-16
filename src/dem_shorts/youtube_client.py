"""YouTube Data API v3 래퍼 — NATV 채널 폴링용.

Research: research.md R-01 (YouTube Data API v3 폴링)
설정: config.YOUTUBE_API_KEY, NATV_CHANNEL_HANDLE

Heavy lifting은 google-api-python-client에 위임. 본 모듈은 쿼터 추적과 에러 정규화만.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.dem_shorts.config import NATV_CHANNEL_HANDLE, YOUTUBE_API_KEY

logger = logging.getLogger(__name__)


class YoutubeQuotaExceeded(Exception):
    """YouTube Data API 일일 쿼터 초과."""


class YoutubeApiError(Exception):
    """기타 API 오류."""


@dataclass(frozen=True)
class ChannelVideo:
    """YouTube search.list / videos.list에서 수집된 최소 필드 집합."""

    video_id: str
    title: str
    description: str
    published_at: str  # ISO8601
    duration_iso: str  # ISO8601 duration e.g., "PT1H30M"
    thumbnail_url: str


def _build_service():
    """google-api-python-client 지연 로딩. 개발환경에서만 필요."""
    try:
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as exc:  # pragma: no cover — runtime-only dep
        raise YoutubeApiError(
            "google-api-python-client not installed. "
            "Run: pip install -r requirements-dem-shorts.txt"
        ) from exc

    if not YOUTUBE_API_KEY:
        raise YoutubeApiError("YOUTUBE_API_KEY not configured in .env")

    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def resolve_channel_id(handle: str = NATV_CHANNEL_HANDLE) -> str:
    """@NATV_korea → UCxxxx 변환."""
    svc = _build_service()
    try:
        resp = svc.channels().list(part="id", forHandle=handle.lstrip("@")).execute()
    except Exception as exc:  # pragma: no cover
        raise YoutubeApiError(f"channel resolution failed: {exc}") from exc
    items = resp.get("items", [])
    if not items:
        raise YoutubeApiError(f"channel not found: {handle}")
    return items[0]["id"]


def list_recent_videos(channel_id: str, max_results: int = 50) -> list[ChannelVideo]:
    """Step 1: search.list로 최근 영상 ID 수집.
    Step 2: videos.list로 duration 등 상세 정보 일괄 조회 (쿼터 효율).
    """
    svc = _build_service()
    try:
        search_resp = svc.search().list(
            channelId=channel_id,
            part="id",
            order="date",
            maxResults=min(max_results, 50),
            type="video",
        ).execute()
    except Exception as exc:
        msg = str(exc)
        if "quotaExceeded" in msg:
            raise YoutubeQuotaExceeded(msg) from exc
        raise YoutubeApiError(msg) from exc

    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return []

    try:
        videos_resp = svc.videos().list(
            id=",".join(video_ids),
            part="snippet,contentDetails",
        ).execute()
    except Exception as exc:
        raise YoutubeApiError(f"videos.list failed: {exc}") from exc

    return [_parse_video_item(item) for item in videos_resp.get("items", [])]


def _parse_video_item(item: dict[str, Any]) -> ChannelVideo:
    snippet = item.get("snippet", {})
    details = item.get("contentDetails", {})
    thumbs = snippet.get("thumbnails", {})
    thumb = (
        thumbs.get("high", {}).get("url")
        or thumbs.get("medium", {}).get("url")
        or thumbs.get("default", {}).get("url")
        or ""
    )
    return ChannelVideo(
        video_id=item["id"],
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        published_at=snippet.get("publishedAt", ""),
        duration_iso=details.get("duration", "PT0S"),
        thumbnail_url=thumb,
    )
