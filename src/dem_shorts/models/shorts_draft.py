"""ShortsDraft — 제작 중인 쇼츠 초안.

Spec: specs/007-dem-shorts-studio/data-model.md §4
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_STATUSES = {
    "draft",
    "gate_pending",
    "gate_passed",
    "gate_failed",
    "rendering",
    "rendered",
    "uploaded",
    "failed",
}
_PRESETS = {"leejaemyung", "jungcheongrae", "youth", "hotissue", "default"}
_VOICES = {None, "male_strong", "male_stable", "female_calm", "female_young"}

CUT_MAX_SEC = 60.0
COMMENTARY_MIN_CHARS = 50
FACT_URLS_MIN = 2


@dataclass(frozen=True)
class ShortsDraft:
    """쇼츠 초안. cut_duration≤60, commentary≥50자, 팩트 URL≥2개 강제."""

    id: int
    segment_id: int
    cut_start_sec: float
    cut_end_sec: float
    commentary_blocks: tuple[dict, ...]
    commentary_char_count: int
    tts_voice: str | None
    tts_enabled: bool
    subtitle_preset: str
    bgm_filename: str | None
    fact_source_urls: tuple[str, ...]
    risk_score: float
    status: str
    rendered_path: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.cut_end_sec <= self.cut_start_sec:
            raise ValueError(
                f"cut_end_sec must be > cut_start_sec: {self.cut_start_sec}-{self.cut_end_sec}"
            )
        if self.cut_duration_sec > CUT_MAX_SEC:
            raise ValueError(
                f"cut duration exceeds {CUT_MAX_SEC}s: {self.cut_duration_sec}s (FR-018)"
            )
        if self.status not in _STATUSES:
            raise ValueError(f"invalid status: {self.status}")
        if self.subtitle_preset not in _PRESETS:
            raise ValueError(f"invalid subtitle_preset: {self.subtitle_preset}")
        if self.tts_voice not in _VOICES:
            raise ValueError(f"invalid tts_voice: {self.tts_voice}")

    @property
    def cut_duration_sec(self) -> float:
        return self.cut_end_sec - self.cut_start_sec

    def meets_commentary_minimum(self) -> bool:
        """FR-024, 게이트 item_1."""
        return self.commentary_char_count >= COMMENTARY_MIN_CHARS

    def meets_fact_urls_minimum(self) -> bool:
        """FR-029."""
        return len(self.fact_source_urls) >= FACT_URLS_MIN

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "cut_start_sec": self.cut_start_sec,
            "cut_end_sec": self.cut_end_sec,
            "commentary_blocks": list(self.commentary_blocks),
            "commentary_char_count": self.commentary_char_count,
            "tts_voice": self.tts_voice,
            "tts_enabled": self.tts_enabled,
            "subtitle_preset": self.subtitle_preset,
            "bgm_filename": self.bgm_filename,
            "fact_source_urls": list(self.fact_source_urls),
            "risk_score": self.risk_score,
            "status": self.status,
            "rendered_path": self.rendered_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ShortsDraft:
        return cls(
            id=int(data["id"]),
            segment_id=int(data["segment_id"]),
            cut_start_sec=float(data["cut_start_sec"]),
            cut_end_sec=float(data["cut_end_sec"]),
            commentary_blocks=tuple(data.get("commentary_blocks") or []),
            commentary_char_count=int(data.get("commentary_char_count", 0)),
            tts_voice=data.get("tts_voice"),
            tts_enabled=bool(data.get("tts_enabled", False)),
            subtitle_preset=data.get("subtitle_preset", "default"),
            bgm_filename=data.get("bgm_filename"),
            fact_source_urls=tuple(data.get("fact_source_urls") or []),
            risk_score=float(data.get("risk_score", 0.0)),
            status=data.get("status", "draft"),
            rendered_path=data.get("rendered_path"),
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]),
        )


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)
