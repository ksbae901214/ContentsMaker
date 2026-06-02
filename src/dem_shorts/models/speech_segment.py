"""SpeechSegment — 영상 내 발언 구간.

Spec: specs/007-dem-shorts-studio/data-model.md §3
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpeechSegment:
    """단일 발언 구간. confidence<0.7 → politician_id=None (FR-014)."""

    id: int
    source_video_id: str
    start_sec: float
    end_sec: float
    politician_id: int | None
    confidence: float
    stt_text: str
    recommendation_score: float
    emotion_strength: float
    issue_keywords: tuple[str, ...]
    is_solo: bool
    has_profanity: bool

    def __post_init__(self) -> None:
        if self.end_sec <= self.start_sec:
            raise ValueError(f"end_sec must be > start_sec: {self.start_sec}-{self.end_sec}")
        if not (0 <= self.confidence <= 1):
            raise ValueError(f"confidence out of range: {self.confidence}")

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_video_id": self.source_video_id,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "politician_id": self.politician_id,
            "confidence": self.confidence,
            "stt_text": self.stt_text,
            "recommendation_score": self.recommendation_score,
            "emotion_strength": self.emotion_strength,
            "issue_keywords": list(self.issue_keywords),
            "is_solo": self.is_solo,
            "has_profanity": self.has_profanity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SpeechSegment:
        return cls(
            id=int(data["id"]),
            source_video_id=data["source_video_id"],
            start_sec=float(data["start_sec"]),
            end_sec=float(data["end_sec"]),
            politician_id=data.get("politician_id"),
            confidence=float(data.get("confidence", 0.0)),
            stt_text=data.get("stt_text", ""),
            recommendation_score=float(data.get("recommendation_score", 0.0)),
            emotion_strength=float(data.get("emotion_strength", 0.0)),
            issue_keywords=tuple(data.get("issue_keywords") or []),
            is_solo=bool(data.get("is_solo", False)),
            has_profanity=bool(data.get("has_profanity", False)),
        )
