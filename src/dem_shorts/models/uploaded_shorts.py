"""UploadedShorts — 게이트 통과 후 YouTube에 발행된 최종 쇼츠.

Spec: specs/007-dem-shorts-studio/data-model.md §7
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

NATV_SOURCE_LABEL = "NATV 국회방송"  # FR-029
FACT_LINKS_MIN = 2


@dataclass(frozen=True)
class UploadedShorts:
    """최종 쇼츠 업로드 이력. 설명란에 NATV 출처 + 팩트 링크 2개↑ 필수."""

    id: int
    draft_id: int
    final_mp4_path: str
    youtube_video_id: str
    title: str
    description: str
    tags: tuple[str, ...]
    scheduled_publish_at: datetime | None
    published_at: datetime | None
    fact_links: tuple[str, ...]
    view_count: int
    like_count: int
    comment_count: int
    est_revenue: float | None
    is_taken_down: bool
    takedown_reason: str | None
    uploaded_at: datetime
    metrics_updated_at: datetime

    def __post_init__(self) -> None:
        if NATV_SOURCE_LABEL not in self.description:
            raise ValueError(
                f"description must include '{NATV_SOURCE_LABEL}' (FR-029)"
            )
        if len(self.fact_links) < FACT_LINKS_MIN:
            raise ValueError(
                f"fact_links must have >= {FACT_LINKS_MIN} entries (FR-029)"
            )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "draft_id": self.draft_id,
            "final_mp4_path": self.final_mp4_path,
            "youtube_video_id": self.youtube_video_id,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "scheduled_publish_at": self.scheduled_publish_at.isoformat()
            if self.scheduled_publish_at
            else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fact_links": list(self.fact_links),
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "est_revenue": self.est_revenue,
            "is_taken_down": self.is_taken_down,
            "takedown_reason": self.takedown_reason,
            "uploaded_at": self.uploaded_at.isoformat(),
            "metrics_updated_at": self.metrics_updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> UploadedShorts:
        return cls(
            id=int(data["id"]),
            draft_id=int(data["draft_id"]),
            final_mp4_path=data["final_mp4_path"],
            youtube_video_id=data["youtube_video_id"],
            title=data["title"],
            description=data["description"],
            tags=tuple(data.get("tags") or []),
            scheduled_publish_at=_parse_dt(data.get("scheduled_publish_at")),
            published_at=_parse_dt(data.get("published_at")),
            fact_links=tuple(data.get("fact_links") or []),
            view_count=int(data.get("view_count", 0)),
            like_count=int(data.get("like_count", 0)),
            comment_count=int(data.get("comment_count", 0)),
            est_revenue=data.get("est_revenue"),
            is_taken_down=bool(data.get("is_taken_down", False)),
            takedown_reason=data.get("takedown_reason"),
            uploaded_at=_parse_dt(data["uploaded_at"]),
            metrics_updated_at=_parse_dt(data["metrics_updated_at"]),
        )


def _parse_dt(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)
