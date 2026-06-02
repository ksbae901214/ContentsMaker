"""Phase 2 — 클러스터링 + 점수화 단위 테스트.

Gemini 호출은 모킹. 폴백 동작도 검증.
"""
from __future__ import annotations

import json

import pytest

from src.briefing.issue_clusterer import cluster_issues
from src.briefing.models import IssueCluster, NewsItem, VideoMeta
from src.briefing.scorer import rank_clusters, score_cluster


def _v(vid: str, title: str, views: int, comments: int) -> VideoMeta:
    return VideoMeta(
        video_id=vid, title=title,
        channel_id="UC1", channel_title="채널",
        published_at="2026-05-19T10:00:00Z",
        view_count=views, comment_count=comments,
    )


def _n(title: str, link: str) -> NewsItem:
    return NewsItem(title=title, link=link, description="", pub_date="")


# ─────────────── 점수화 ───────────────

class TestScorer:
    def test_score_views_only(self):
        cluster = IssueCluster(topic="t", videos=(_v("a", "t", 10000, 0),))
        # 10000 + 10*0 + 1000*0 = 10000
        assert score_cluster(cluster) == 10000.0

    def test_score_with_comments_and_news(self):
        cluster = IssueCluster(
            topic="t",
            videos=(_v("a", "t", 1000, 50), _v("b", "t", 500, 20)),
            news=(_n("n1", "x"), _n("n2", "y")),
        )
        # 1500 + 10*70 + 1000*2 = 1500 + 700 + 2000 = 4200
        assert score_cluster(cluster) == 4200.0

    def test_rank_clusters_descending(self):
        c_low = IssueCluster(topic="low", videos=(_v("a", "x", 100, 0),))
        c_high = IssueCluster(topic="high", videos=(_v("b", "y", 10000, 0),))
        c_mid = IssueCluster(topic="mid", videos=(_v("c", "z", 1000, 100),))

        ranked = rank_clusters([c_low, c_high, c_mid])
        assert ranked[0].rank == 1 and ranked[0].cluster.topic == "high"
        assert ranked[1].rank == 2 and ranked[1].cluster.topic == "mid"
        assert ranked[2].rank == 3 and ranked[2].cluster.topic == "low"

    def test_rank_empty(self):
        assert rank_clusters([]) == []


# ─────────────── 클러스터링 ───────────────

class TestClusterIssues:
    def test_empty_input(self):
        assert cluster_issues([], [], gemini_caller=lambda p: "{}") == []

    def test_basic_clustering(self):
        videos = [
            _v("a", "대선 토론 결과", 5000, 100),
            _v("b", "양당 후보 부동산 발언", 3000, 80),
            _v("c", "국회의장 사퇴", 8000, 200),
        ]
        news = [_n("부동산 정책 비교", "https://x/1")]

        def fake_gemini(prompt):
            return json.dumps({
                "clusters": [
                    {"topic": "대선 부동산", "member_ids": ["video_0", "video_1", "news_0"]},
                    {"topic": "국회의장 사퇴", "member_ids": ["video_2"]},
                ]
            })

        clusters = cluster_issues(videos, news, gemini_caller=fake_gemini)
        assert len(clusters) == 2
        topics = {c.topic for c in clusters}
        assert "대선 부동산" in topics
        assert "국회의장 사퇴" in topics

        # 첫 클러스터 멤버 확인
        main = next(c for c in clusters if c.topic == "대선 부동산")
        assert len(main.videos) == 2
        assert len(main.news) == 1

    def test_fallback_on_invalid_json(self):
        """폴백: 영상만 단일 클러스터로 생성. 뉴스만 있는 항목은 클러스터 안 만듦
        (대표 영상 없으면 plan 못 만드므로 UI 노이즈만 늘림 — 2026-05-21 fix).
        """
        videos = [_v("a", "영상", 100, 5)]
        news = [_n("기사", "https://x/1")]
        clusters = cluster_issues(
            videos, news,
            gemini_caller=lambda p: "INVALID JSON",
        )
        assert len(clusters) == 1  # 영상만 (뉴스 단일 클러스터 X)
        all_videos = sum((list(c.videos) for c in clusters), [])
        assert len(all_videos) == 1
        # 뉴스는 폴백 시 누락 (의도적 — Gemini 정상 작동 시에는 영상에 묶임)

    def test_fallback_on_gemini_exception(self):
        videos = [_v("a", "t", 100, 0)]
        clusters = cluster_issues(
            videos, [],
            gemini_caller=lambda p: (_ for _ in ()).throw(RuntimeError("api down")),
        )
        assert len(clusters) == 1
        assert clusters[0].videos[0].video_id == "a"

    def test_missing_members_added_as_singletons(self):
        """Gemini가 일부 멤버만 클러스터화하면, 누락된 항목은 단일 클러스터로 추가."""
        videos = [_v("a", "이슈1", 100, 5), _v("b", "이슈2", 200, 10)]

        def partial_gemini(prompt):
            return json.dumps({
                "clusters": [
                    {"topic": "이슈1 묶음", "member_ids": ["video_0"]},
                    # video_1 (b)은 누락
                ]
            })

        clusters = cluster_issues(videos, [], gemini_caller=partial_gemini)
        assert len(clusters) == 2  # 1개 명시 + 1개 폴백
        all_vids = {v.video_id for c in clusters for v in c.videos}
        assert all_vids == {"a", "b"}  # 모두 포함됨

    def test_unknown_member_id_ignored(self):
        """Gemini가 존재하지 않는 id를 반환해도 안전하게 무시."""
        videos = [_v("a", "t", 100, 0)]

        def gemini(prompt):
            return json.dumps({
                "clusters": [
                    {"topic": "유령", "member_ids": ["video_99", "news_99"]},
                    {"topic": "실재", "member_ids": ["video_0"]},
                ]
            })

        clusters = cluster_issues(videos, [], gemini_caller=gemini)
        # "유령" 클러스터는 멤버 0개 → 추가 안 됨. "실재"만.
        topics = {c.topic for c in clusters}
        assert "실재" in topics
        assert "유령" not in topics
