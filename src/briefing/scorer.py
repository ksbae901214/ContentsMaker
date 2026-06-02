"""클러스터 점수화 — 핫함 정량화.

공식 (사용자 확정 2026-05-20):
    score = Σviews + 10 × Σcomments + 1000 × news_count

근거:
- 조회수: 기본 도달
- 댓글수×10: 참여도 (조회 1만 ≒ 댓글 1000)
- 기사수×1000: 여러 매체 다루면 큰 이슈 (기사 1건 ≒ 조회 1000)
"""
from __future__ import annotations

from src.briefing.models import IssueCluster, RankedIssue

COMMENT_WEIGHT = 10.0
NEWS_WEIGHT = 1000.0


def score_cluster(cluster: IssueCluster) -> float:
    return float(
        cluster.total_views
        + COMMENT_WEIGHT * cluster.total_comments
        + NEWS_WEIGHT * cluster.news_count
    )


def rank_clusters(clusters: list[IssueCluster]) -> list[RankedIssue]:
    """점수 내림차순 정렬 → RankedIssue 리스트 (rank=1이 가장 핫)."""
    scored = [(c, score_cluster(c)) for c in clusters]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        RankedIssue(cluster=c, score=s, rank=i + 1)
        for i, (c, s) in enumerate(scored)
    ]
