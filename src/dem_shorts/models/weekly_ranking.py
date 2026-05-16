"""WeeklyRanking — 여성·청년 정치인 주간 인기도 랭킹.

Spec: specs/007-dem-shorts-studio/data-model.md §6
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

_TAGS = {None, "new", "rising", "pending"}


@dataclass(frozen=True)
class WeeklyRanking:
    """주간 랭킹 한 행. 상위 20위까지 Politician.tier=auto 자동 등록."""

    id: int
    week_start: date
    politician_id: int
    rank: int
    score: float
    delta_vs_prev_week: float
    tag: str | None
    data_sources: dict

    def __post_init__(self) -> None:
        if self.tag not in _TAGS:
            raise ValueError(f"invalid tag: {self.tag}")
        if self.rank < 1:
            raise ValueError(f"rank must be >= 1: {self.rank}")
        if not (0 <= self.score <= 100):
            raise ValueError(f"score out of range: {self.score}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "week_start": self.week_start.isoformat(),
            "politician_id": self.politician_id,
            "rank": self.rank,
            "score": self.score,
            "delta_vs_prev_week": self.delta_vs_prev_week,
            "tag": self.tag,
            "data_sources": self.data_sources,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WeeklyRanking:
        ws = data["week_start"]
        if isinstance(ws, str):
            ws = date.fromisoformat(ws)
        return cls(
            id=int(data["id"]),
            week_start=ws,
            politician_id=int(data["politician_id"]),
            rank=int(data["rank"]),
            score=float(data["score"]),
            delta_vs_prev_week=float(data.get("delta_vs_prev_week", 0.0)),
            tag=data.get("tag"),
            data_sources=dict(data.get("data_sources") or {}),
        )
