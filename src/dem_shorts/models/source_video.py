"""SourceVideo — NATV에서 수집된 원본 영상.

Spec: specs/007-dem-shorts-studio/data-model.md §1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

_SESSION_TYPES = {"plenary", "committee", "audit", "hearing", "press", "other"}
_STATUSES = {"new", "downloading", "stt_running", "ready", "archived", "excluded"}
_STT_STATUSES = {"pending", "running", "done", "failed"}
_EXCLUDED_REASONS = {None, "length_over_6h", "no_dem_politician", "dem_score_zero"}


@dataclass(frozen=True)
class SourceVideo:
    """NATV YouTube 영상. 수명주기: new → downloading → stt_running → ready."""

    video_id: str
    title: str
    description: str
    published_at: datetime
    duration_sec: int
    thumbnail_url: str
    session_type: str  # plenary/committee/audit/hearing/press/other
    download_path: str | None
    stt_status: str  # pending/running/done/failed
    diarization_status: str
    dem_score: float  # 0~100
    excluded_reason: str | None
    status: str  # new/downloading/stt_running/ready/archived/excluded
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.session_type not in _SESSION_TYPES:
            raise ValueError(f"invalid session_type: {self.session_type}")
        if self.status not in _STATUSES:
            raise ValueError(f"invalid status: {self.status}")
        if self.stt_status not in _STT_STATUSES:
            raise ValueError(f"invalid stt_status: {self.stt_status}")
        if self.diarization_status not in _STT_STATUSES:
            raise ValueError(f"invalid diarization_status: {self.diarization_status}")
        if self.excluded_reason not in _EXCLUDED_REASONS:
            raise ValueError(f"invalid excluded_reason: {self.excluded_reason}")
        if not (0 <= self.dem_score <= 100):
            raise ValueError(f"dem_score out of range: {self.dem_score}")
        if self.duration_sec < 0:
            raise ValueError(f"duration_sec must be >= 0: {self.duration_sec}")

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "description": self.description,
            "published_at": self.published_at.isoformat(),
            "duration_sec": self.duration_sec,
            "thumbnail_url": self.thumbnail_url,
            "session_type": self.session_type,
            "download_path": self.download_path,
            "stt_status": self.stt_status,
            "diarization_status": self.diarization_status,
            "dem_score": self.dem_score,
            "excluded_reason": self.excluded_reason,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SourceVideo:
        return cls(
            video_id=data["video_id"],
            title=data["title"],
            description=data.get("description", ""),
            published_at=_parse_dt(data["published_at"]),
            duration_sec=int(data["duration_sec"]),
            thumbnail_url=data.get("thumbnail_url", ""),
            session_type=data["session_type"],
            download_path=data.get("download_path"),
            stt_status=data.get("stt_status", "pending"),
            diarization_status=data.get("diarization_status", "pending"),
            dem_score=float(data.get("dem_score", 0.0)),
            excluded_reason=data.get("excluded_reason"),
            status=data.get("status", "new"),
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]),
        )


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)
