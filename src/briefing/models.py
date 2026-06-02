"""Data models for daily political briefing pipeline.

Frozen dataclasses for KST 어제(00:00~23:59) 수집 → 클러스터링 → 점수화 → 기획안.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class VideoMeta:
    """YouTube 영상 단일 메타데이터.

    statistics는 API 호출 시점 기준. published_at은 ISO 8601 (UTC).
    """
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: str       # ISO 8601 UTC, e.g. "2026-05-19T12:34:56Z"
    view_count: int
    comment_count: int
    description: str = ""
    thumbnail_url: str = ""

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "published_at": self.published_at,
            "view_count": self.view_count,
            "comment_count": self.comment_count,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VideoMeta:
        return cls(
            video_id=data["video_id"],
            title=data["title"],
            channel_id=data["channel_id"],
            channel_title=data["channel_title"],
            published_at=data["published_at"],
            view_count=int(data["view_count"]),
            comment_count=int(data["comment_count"]),
            description=data.get("description", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
        )


@dataclass(frozen=True)
class NewsItem:
    """네이버/다음 정치 뉴스 단일 기사."""
    title: str
    link: str
    description: str
    pub_date: str  # RFC 822 또는 ISO 8601
    source: str = "naver"  # naver | daum

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "pub_date": self.pub_date,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NewsItem:
        return cls(
            title=data["title"],
            link=data["link"],
            description=data.get("description", ""),
            pub_date=data["pub_date"],
            source=data.get("source", "naver"),
        )


@dataclass(frozen=True)
class IssueCluster:
    """동일 이슈로 묶인 영상 + 기사 그룹.

    Gemini 클러스터링 결과 — 같은 사건을 다루는 영상들과 기사들의 묶음.
    """
    topic: str                              # 대표 토픽 (Gemini 생성)
    videos: tuple[VideoMeta, ...] = ()
    news: tuple[NewsItem, ...] = ()

    @property
    def total_views(self) -> int:
        return sum(v.view_count for v in self.videos)

    @property
    def total_comments(self) -> int:
        return sum(v.comment_count for v in self.videos)

    @property
    def news_count(self) -> int:
        return len(self.news)

    @property
    def top_video(self) -> VideoMeta | None:
        """클러스터 내 조회수 최대 영상 (대표 클립)."""
        if not self.videos:
            return None
        return max(self.videos, key=lambda v: v.view_count)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "videos": [v.to_dict() for v in self.videos],
            "news": [n.to_dict() for n in self.news],
            "total_views": self.total_views,
            "total_comments": self.total_comments,
            "news_count": self.news_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> IssueCluster:
        return cls(
            topic=data["topic"],
            videos=tuple(VideoMeta.from_dict(v) for v in data.get("videos", ())),
            news=tuple(NewsItem.from_dict(n) for n in data.get("news", ())),
        )


@dataclass(frozen=True)
class RankedIssue:
    """점수화된 이슈 클러스터. score 내림차순으로 정렬되어 상위 N개 선정."""
    cluster: IssueCluster
    score: float
    rank: int  # 1 = 가장 핫함

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "score": round(self.score, 1),
            "cluster": self.cluster.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> RankedIssue:
        return cls(
            cluster=IssueCluster.from_dict(data["cluster"]),
            score=float(data["score"]),
            rank=int(data["rank"]),
        )


@dataclass(frozen=True)
class BriefingResult:
    """매일 브리핑의 최종 결과물.

    저장 위치: data/daily_briefing/YYYY-MM-DD/issues.json
    """
    date: str  # KST 기준 "어제" YYYY-MM-DD
    generated_at: str  # ISO 8601 UTC, 실행 시각
    ranked_issues: tuple[RankedIssue, ...]
    channel_count: int  # 모니터링한 채널 수
    raw_video_count: int  # 어제 수집된 영상 총수
    raw_news_count: int  # 어제 수집된 기사 총수

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "generated_at": self.generated_at,
            "ranked_issues": [r.to_dict() for r in self.ranked_issues],
            "channel_count": self.channel_count,
            "raw_video_count": self.raw_video_count,
            "raw_news_count": self.raw_news_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BriefingResult:
        return cls(
            date=data["date"],
            generated_at=data["generated_at"],
            ranked_issues=tuple(RankedIssue.from_dict(r) for r in data.get("ranked_issues", ())),
            channel_count=int(data.get("channel_count", 0)),
            raw_video_count=int(data.get("raw_video_count", 0)),
            raw_news_count=int(data.get("raw_news_count", 0)),
        )
