"""YouTube 채널 구독 목록에서 KST 어제 업로드된 영상 수집.

YouTube Data API v3 사용. 인증 우선순위:
    1. YOUTUBE_API_KEY 환경변수 (권장, 읽기 전용 API key)
    2. data/.youtube_token.json OAuth 토큰 (업로드용 — 폴백)

quota 비용 (10,000/일 한도 대비):
    - channels.list: 1 unit / 호출
    - playlistItems.list: 1 unit / 호출 (페이지당 50개 영상)
    - videos.list: 1 unit / 호출 (페이지당 50개 영상)
    채널 20개 × 어제 영상 평균 3개 → 약 60 units (0.6% 사용)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from src.briefing.models import VideoMeta

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class YouTubeCollectorError(Exception):
    """Raised when YouTube API access fails."""


def yesterday_kst_range() -> tuple[datetime, datetime]:
    """KST 기준 "어제" 00:00:00 ~ 23:59:59 (timezone-aware datetime)."""
    now_kst = datetime.now(KST)
    yesterday_date = (now_kst - timedelta(days=1)).date()
    start = datetime.combine(yesterday_date, time(0, 0, 0), KST)
    end = datetime.combine(yesterday_date, time(23, 59, 59, 999999), KST)
    return start, end


def _build_youtube_service():
    """API Key 우선, OAuth 폴백."""
    from googleapiclient.discovery import build

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if api_key:
        logger.info("YouTube API: API Key 사용")
        return build("youtube", "v3", developerKey=api_key)

    # OAuth 폴백
    try:
        from src.upload.youtube_uploader import _get_credentials
        creds = _get_credentials()
    except Exception as e:
        raise YouTubeCollectorError(
            "YouTube API 인증이 필요합니다.\n"
            "1) 권장: export YOUTUBE_API_KEY='AIza...' (Google Cloud Console → API Key)\n"
            "2) 폴백: python3 -m src.main youtube-auth 로 OAuth 인증\n"
            f"원인: {e}"
        ) from e
    logger.info("YouTube API: OAuth 토큰 사용")
    return build("youtube", "v3", credentials=creds)


def _channel_uploads_playlist_id(youtube, channel_id: str) -> str | None:
    """채널의 uploads 플레이리스트 ID 반환. 없으면 None."""
    resp = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()
    items = resp.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _list_recent_video_ids(
    youtube,
    playlist_id: str,
    *,
    after_kst: datetime,
    before_kst: datetime,
    max_pages: int = 4,  # 최대 200개 영상까지만 (안전 한도)
) -> list[str]:
    """uploads 플레이리스트에서 after~before 범위의 video_id 추출.

    YouTube playlistItems는 최신순. published_at이 after보다 오래되면 조기 종료.
    """
    video_ids: list[str] = []
    page_token: str | None = None
    pages = 0
    while pages < max_pages:
        resp = youtube.playlistItems().list(
            part="contentDetails,snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        items = resp.get("items", [])
        stop = False
        for it in items:
            published_at_str = it["contentDetails"].get("videoPublishedAt") \
                or it["snippet"].get("publishedAt", "")
            if not published_at_str:
                continue
            # YouTube는 UTC ISO 8601 — Python 3.11+ 의 fromisoformat은 'Z' 지원
            pub = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            pub_kst = pub.astimezone(KST)
            if pub_kst < after_kst:
                stop = True
                break
            if pub_kst > before_kst:
                continue  # 오늘 이후 영상은 제외 (어제 범위만)
            vid = it["contentDetails"].get("videoId")
            if vid:
                video_ids.append(vid)
        if stop:
            break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
        pages += 1
    return video_ids


def _fetch_video_stats(youtube, video_ids: list[str]) -> list[VideoMeta]:
    """videos.list로 statistics + snippet 가져오기. 50개씩 배치."""
    out: list[VideoMeta] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(batch),
        ).execute()
        for v in resp.get("items", []):
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            thumb = (snippet.get("thumbnails", {})
                     .get("high", snippet.get("thumbnails", {}).get("default", {}))
                     .get("url", ""))
            out.append(VideoMeta(
                video_id=v["id"],
                title=snippet.get("title", ""),
                channel_id=snippet.get("channelId", ""),
                channel_title=snippet.get("channelTitle", ""),
                published_at=snippet.get("publishedAt", ""),
                view_count=int(stats.get("viewCount", 0)),
                comment_count=int(stats.get("commentCount", 0)),
                description=snippet.get("description", ""),
                thumbnail_url=thumb,
            ))
    return out


def collect_yesterday_videos(
    channels: Iterable[dict],
    *,
    after_kst: datetime | None = None,
    before_kst: datetime | None = None,
    youtube_service=None,  # 주입용 (테스트)
) -> list[VideoMeta]:
    """모니터링 채널들에서 KST 어제 업로드된 영상 수집.

    Args:
        channels: load_channels()의 반환값 (list of dict with channel_id).
        after_kst / before_kst: 명시 시 그 범위, 아니면 yesterday_kst_range() 사용.
        youtube_service: 주입된 service (테스트). None이면 _build_youtube_service().

    Returns:
        VideoMeta 리스트. 채널당 영상 합쳐서 반환. 정렬 X (호출자 책임).
    """
    if after_kst is None or before_kst is None:
        after_kst, before_kst = yesterday_kst_range()

    if youtube_service is None:
        youtube_service = _build_youtube_service()

    all_videos: list[VideoMeta] = []
    for ch in channels:
        cid = ch.get("channel_id", "")
        if not cid:
            continue
        try:
            playlist_id = _channel_uploads_playlist_id(youtube_service, cid)
            if not playlist_id:
                logger.warning("채널 uploads 플레이리스트 없음: %s", cid)
                continue
            vids = _list_recent_video_ids(
                youtube_service, playlist_id,
                after_kst=after_kst, before_kst=before_kst,
            )
            if not vids:
                continue
            videos = _fetch_video_stats(youtube_service, vids)
            all_videos.extend(videos)
            logger.info(
                "  채널 %s (%s): %d 영상 수집",
                ch.get("name", cid), cid, len(videos),
            )
        except Exception as e:
            logger.warning("채널 %s 수집 실패: %s", cid, e)
            continue

    return all_videos
