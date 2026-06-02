"""Phase 1 — briefing 수집 모듈 단위 테스트.

YouTube/네이버 API는 모킹. KST 시간 계산은 실제 검증.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from src.briefing.models import (
    BriefingResult,
    IssueCluster,
    NewsItem,
    RankedIssue,
    VideoMeta,
)
from src.briefing.youtube_collector import (
    KST,
    collect_yesterday_videos,
    yesterday_kst_range,
)
from src.briefing.naver_news_collector import (
    NaverNewsCollectorError,
    collect_yesterday_news,
)


# ─────────────── 모델 ───────────────

class TestModels:
    def test_video_meta_roundtrip(self):
        v = VideoMeta(
            video_id="abc123", title="제목", channel_id="UC1", channel_title="채널",
            published_at="2026-05-19T10:00:00Z", view_count=1000, comment_count=50,
        )
        restored = VideoMeta.from_dict(v.to_dict())
        assert restored == v

    def test_video_meta_url(self):
        v = VideoMeta(
            video_id="xyz", title="t", channel_id="UC1", channel_title="c",
            published_at="2026-05-19T00:00:00Z", view_count=0, comment_count=0,
        )
        assert v.url == "https://www.youtube.com/watch?v=xyz"

    def test_issue_cluster_totals(self):
        videos = (
            VideoMeta(video_id="a", title="t1", channel_id="UC1", channel_title="c",
                      published_at="2026-05-19T10:00:00Z",
                      view_count=1000, comment_count=20),
            VideoMeta(video_id="b", title="t2", channel_id="UC2", channel_title="c",
                      published_at="2026-05-19T11:00:00Z",
                      view_count=500, comment_count=10),
        )
        cluster = IssueCluster(topic="대선 토론", videos=videos)
        assert cluster.total_views == 1500
        assert cluster.total_comments == 30
        assert cluster.top_video.video_id == "a"  # 조회수 최대

    def test_issue_cluster_empty(self):
        cluster = IssueCluster(topic="빈 클러스터")
        assert cluster.total_views == 0
        assert cluster.top_video is None

    def test_briefing_result_roundtrip(self):
        cluster = IssueCluster(topic="t", videos=(), news=())
        result = BriefingResult(
            date="2026-05-19", generated_at="2026-05-20T07:00:00Z",
            ranked_issues=(RankedIssue(cluster=cluster, score=100.0, rank=1),),
            channel_count=5, raw_video_count=15, raw_news_count=42,
        )
        restored = BriefingResult.from_dict(result.to_dict())
        assert restored.date == "2026-05-19"
        assert restored.ranked_issues[0].rank == 1


# ─────────────── 시간 ───────────────

class TestYesterdayRange:
    def test_returns_kst_aware(self):
        start, end = yesterday_kst_range()
        assert start.tzinfo is KST
        assert end.tzinfo is KST

    def test_yesterday_24h_span(self):
        start, end = yesterday_kst_range()
        assert start.hour == 0 and start.minute == 0 and start.second == 0
        assert end.hour == 23 and end.minute == 59 and end.second == 59
        # 같은 날짜
        assert start.date() == end.date()
        # 어제 = 오늘 - 1일
        now_kst = datetime.now(KST)
        assert start.date() == (now_kst - timedelta(days=1)).date()


# ─────────────── YouTube ───────────────

def _mock_youtube_service(*, channel_id="UC1234567890123456789012", videos: list[dict]):
    """간단한 모킹: channels.list / playlistItems.list / videos.list 응답."""
    youtube = MagicMock()
    youtube.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_test"}}}]
    }

    playlist_items = []
    video_items = []
    for v in videos:
        playlist_items.append({
            "contentDetails": {
                "videoId": v["id"],
                "videoPublishedAt": v["published_at"],
            },
            "snippet": {"publishedAt": v["published_at"]},
        })
        video_items.append({
            "id": v["id"],
            "snippet": {
                "title": v["title"],
                "channelId": channel_id,
                "channelTitle": v.get("channel_title", "채널"),
                "publishedAt": v["published_at"],
                "description": v.get("description", ""),
                "thumbnails": {"high": {"url": "https://thumb"}},
            },
            "statistics": {
                "viewCount": str(v["view_count"]),
                "commentCount": str(v["comment_count"]),
            },
        })

    youtube.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": playlist_items,
        "nextPageToken": None,
    }
    youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": video_items,
    }
    return youtube


class TestYouTubeCollector:
    def test_collect_yesterday_videos_basic(self):
        now_kst = datetime.now(KST)
        yesterday_10am = (now_kst - timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        iso = yesterday_10am.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

        youtube = _mock_youtube_service(videos=[
            {"id": "v1", "title": "이슈 영상 1", "published_at": iso,
             "view_count": 10000, "comment_count": 200},
            {"id": "v2", "title": "이슈 영상 2", "published_at": iso,
             "view_count": 5000, "comment_count": 100},
        ])

        videos = collect_yesterday_videos(
            [{"channel_id": "UC1234567890123456789012", "name": "테스트"}],
            youtube_service=youtube,
        )
        assert len(videos) == 2
        assert videos[0].video_id == "v1"
        assert videos[0].view_count == 10000
        assert videos[0].comment_count == 200

    def test_collect_filters_out_old_videos(self):
        """3일 전 영상은 어제 범위 밖이므로 제외."""
        now_kst = datetime.now(KST)
        three_days_ago = (now_kst - timedelta(days=3)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        iso_old = three_days_ago.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

        youtube = _mock_youtube_service(videos=[
            {"id": "old", "title": "오래된 영상", "published_at": iso_old,
             "view_count": 99999, "comment_count": 999},
        ])

        videos = collect_yesterday_videos(
            [{"channel_id": "UC1234567890123456789012", "name": "테스트"}],
            youtube_service=youtube,
        )
        assert len(videos) == 0

    def test_invalid_channel_id_skipped(self):
        """잘못된 channel_id는 스킵 (수집 안 함). 빈 channel_id도 안전."""
        youtube = MagicMock()
        videos = collect_yesterday_videos(
            [{"channel_id": "", "name": "빈"}],
            youtube_service=youtube,
        )
        assert videos == []


# ─────────────── Naver ───────────────

class TestNaverNewsCollector:
    def test_requires_env_vars(self, monkeypatch):
        monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
        monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)
        with pytest.raises(NaverNewsCollectorError, match="NAVER_CLIENT_ID"):
            collect_yesterday_news(queries=["정치"])

    def test_filters_by_yesterday(self, monkeypatch):
        monkeypatch.setenv("NAVER_CLIENT_ID", "x")
        monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")

        now_kst = datetime.now(KST)
        yesterday_noon = (now_kst - timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        two_days_ago = (now_kst - timedelta(days=2)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )

        def rfc822(d: datetime) -> str:
            return d.strftime("%a, %d %b %Y %H:%M:%S %z")

        def fake_http(url, headers, timeout=10.0):
            return {
                "items": [
                    {"title": "<b>어제</b> 기사", "link": "https://news/1",
                     "description": "내용", "pubDate": rfc822(yesterday_noon)},
                    {"title": "이틀 전 기사", "link": "https://news/2",
                     "description": "내용", "pubDate": rfc822(two_days_ago)},
                    {"title": "어제 기사 2 (dup link)", "link": "https://news/1",
                     "description": "x", "pubDate": rfc822(yesterday_noon)},
                ]
            }

        news = collect_yesterday_news(queries=["정치"], http_get=fake_http)
        # 어제 1건 + 중복 제외 = 1건
        assert len(news) == 1
        assert news[0].link == "https://news/1"
        # HTML 태그 strip
        assert "<b>" not in news[0].title
        assert news[0].title == "어제 기사"

    def test_multiple_queries_dedup(self, monkeypatch):
        monkeypatch.setenv("NAVER_CLIENT_ID", "x")
        monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")

        now_kst = datetime.now(KST)
        yesterday_noon = (now_kst - timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )

        def rfc822(d):
            return d.strftime("%a, %d %b %Y %H:%M:%S %z")

        def fake_http(url, headers, timeout=10.0):
            # 두 쿼리 모두 같은 기사 반환 → link 기준 dedup
            return {
                "items": [
                    {"title": "공통 기사", "link": "https://shared/1",
                     "description": "x", "pubDate": rfc822(yesterday_noon)},
                ]
            }

        news = collect_yesterday_news(
            queries=["정치", "국회", "대통령"],
            http_get=fake_http,
        )
        assert len(news) == 1  # 3번 검색했지만 중복 제거
