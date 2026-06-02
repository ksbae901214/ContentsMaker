"""Phase 3 — plan_runner 통합 테스트.

YouTube/Naver/Gemini/Claude 모두 모킹 — 실제 외부 호출 없음.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from src.briefing.models import BriefingResult, IssueCluster, NewsItem, VideoMeta
from src.briefing.plan_runner import load_briefing, run_briefing
from src.briefing.youtube_collector import KST


def _v(vid, title, views, comments):
    return VideoMeta(
        video_id=vid, title=title,
        channel_id="UC1234567890123456789012", channel_title="채널",
        published_at=(datetime.now(KST) - timedelta(days=1)).astimezone(ZoneInfo("UTC"))
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        view_count=views, comment_count=comments,
    )


class TestRunBriefing:
    @pytest.fixture
    def fake_youtube_service(self):
        """playlistItems + videos.list 가짜 응답."""
        iso = (datetime.now(KST) - timedelta(days=1)) \
            .replace(hour=10, minute=0, second=0, microsecond=0) \
            .astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

        service = MagicMock()
        service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_x"}}}]
        }
        service.playlistItems.return_value.list.return_value.execute.return_value = {
            "items": [
                {"contentDetails": {"videoId": "vid1", "videoPublishedAt": iso},
                 "snippet": {"publishedAt": iso}},
                {"contentDetails": {"videoId": "vid2", "videoPublishedAt": iso},
                 "snippet": {"publishedAt": iso}},
            ],
            "nextPageToken": None,
        }
        service.videos.return_value.list.return_value.execute.return_value = {
            "items": [
                {"id": "vid1", "snippet": {
                    "title": "이슈 핫한 영상", "channelId": "UC1",
                    "channelTitle": "테스트채널", "publishedAt": iso,
                    "thumbnails": {"high": {"url": "https://thumb1"}}},
                 "statistics": {"viewCount": "50000", "commentCount": "1500"}},
                {"id": "vid2", "snippet": {
                    "title": "이슈 보통 영상", "channelId": "UC1",
                    "channelTitle": "테스트채널", "publishedAt": iso,
                    "thumbnails": {"high": {"url": "https://thumb2"}}},
                 "statistics": {"viewCount": "10000", "commentCount": "100"}},
            ]
        }
        return service

    def test_basic_run_with_mocks(self, fake_youtube_service, tmp_path, monkeypatch):
        # 출력 디렉토리를 tmp_path로 redirect
        monkeypatch.setattr(
            "src.briefing.plan_runner.BRIEFING_DATA_DIR", tmp_path / "daily_briefing"
        )
        monkeypatch.setenv("NAVER_CLIENT_ID", "x")
        monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")

        # Naver 응답 모킹
        def fake_naver(url, headers, timeout=10.0):
            return {"items": []}  # 뉴스 없음 (간소화)

        # Gemini 클러스터링 모킹 — 두 영상을 한 클러스터로
        def fake_gemini(prompt):
            return json.dumps({
                "clusters": [
                    {"topic": "테스트 이슈 합침", "member_ids": ["video_0", "video_1"]}
                ]
            })

        # transcript 모킹
        def fake_transcript(url):
            return [
                {"start": 0.0, "end": 5.0, "text": "발언1"},
                {"start": 5.0, "end": 12.0, "text": "발언2"},
            ]

        # plan_generator 모킹 — 진짜 Claude 호출 안 함
        plan_calls = []
        def fake_plan_gen(**kwargs):
            plan_calls.append(kwargs)
            result = MagicMock()
            result.plans = [MagicMock(), MagicMock(), MagicMock()]
            return result

        result = run_briefing(
            top_n=5,
            channels=[{"channel_id": "UC1234567890123456789012", "name": "테스트"}],
            youtube_service=fake_youtube_service,
            news_http_get=fake_naver,
            gemini_caller=fake_gemini,
            transcript_fetcher=fake_transcript,
            plan_generator=fake_plan_gen,
        )

        assert isinstance(result, BriefingResult)
        assert result.raw_video_count == 2
        assert result.raw_news_count == 0
        assert len(result.ranked_issues) >= 1
        assert result.ranked_issues[0].rank == 1
        # 첫 클러스터 점수: 60000 + 10*1600 + 0 = 76000
        assert result.ranked_issues[0].score == pytest.approx(76000.0)

        # plan_generator 호출됨 (대표 영상 = vid1, 50k views)
        assert len(plan_calls) == 1
        assert plan_calls[0]["video_title"] == "이슈 핫한 영상"

        # issues.json 저장 확인
        issues_file = tmp_path / "daily_briefing" / result.date / "issues.json"
        assert issues_file.exists()
        loaded = json.loads(issues_file.read_text(encoding="utf-8"))
        assert loaded["raw_video_count"] == 2

    def test_no_transcript_creates_manual_required(self, fake_youtube_service, tmp_path, monkeypatch):
        """자막 없는 영상은 manual_required 파일 생성, plan 스킵."""
        monkeypatch.setattr(
            "src.briefing.plan_runner.BRIEFING_DATA_DIR", tmp_path / "daily_briefing"
        )
        monkeypatch.setenv("NAVER_CLIENT_ID", "x")
        monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")

        plan_calls = []
        def fake_plan_gen(**kwargs):
            plan_calls.append(kwargs)
            return MagicMock()

        result = run_briefing(
            channels=[{"channel_id": "UC1234567890123456789012", "name": "x"}],
            youtube_service=fake_youtube_service,
            news_http_get=lambda u, h, timeout=10: {"items": []},
            gemini_caller=lambda p: json.dumps({
                "clusters": [{"topic": "t", "member_ids": ["video_0"]}]
            }),
            transcript_fetcher=lambda url: None,  # 자막 없음
            plan_generator=fake_plan_gen,
        )

        # plan_generator 호출 안 됨
        assert plan_calls == []

        # manual_required 파일 생성
        manual_file = tmp_path / "daily_briefing" / result.date / "plans" / "01_manual_required.json"
        assert manual_file.exists()
        data = json.loads(manual_file.read_text(encoding="utf-8"))
        assert "자막 없음" in data["reason"]

    def test_load_briefing_roundtrip(self, fake_youtube_service, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.briefing.plan_runner.BRIEFING_DATA_DIR", tmp_path / "daily_briefing"
        )
        monkeypatch.setenv("NAVER_CLIENT_ID", "x")
        monkeypatch.setenv("NAVER_CLIENT_SECRET", "y")

        result = run_briefing(
            channels=[{"channel_id": "UC1234567890123456789012", "name": "x"}],
            youtube_service=fake_youtube_service,
            news_http_get=lambda u, h, timeout=10: {"items": []},
            gemini_caller=lambda p: json.dumps({"clusters": []}),  # 폴백
            transcript_fetcher=lambda url: None,
            plan_generator=lambda **kw: MagicMock(),
        )
        loaded = load_briefing(result.date)
        assert loaded is not None
        assert loaded.date == result.date
        assert loaded.raw_video_count == result.raw_video_count

    def test_load_missing_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.briefing.plan_runner.BRIEFING_DATA_DIR", tmp_path / "daily_briefing"
        )
        assert load_briefing("1999-01-01") is None
