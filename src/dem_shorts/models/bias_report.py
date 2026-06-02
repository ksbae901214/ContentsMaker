"""BiasReport — 월별 편향 밸런스 리포트.

Spec: specs/007-dem-shorts-studio/data-model.md §8
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class BiasReport:
    """월간 인물·정당·템플릿 편향 집계. SC-011, SC-012 검증에 사용."""

    id: int
    month: date  # 해당 월 1일
    total_uploads: int
    person_shares: dict  # {"이재명": 0.20, ...}
    party_shares: dict
    template_usage: dict
    avg_risk_score: float
    top_n_person_warning: tuple[str, ...]  # 30% 초과 인물
    recommendations: tuple[str, ...]
    generated_at: datetime

    def __post_init__(self) -> None:
        if self.total_uploads < 0:
            raise ValueError(f"total_uploads must be >= 0: {self.total_uploads}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "month": self.month.isoformat(),
            "total_uploads": self.total_uploads,
            "person_shares": self.person_shares,
            "party_shares": self.party_shares,
            "template_usage": self.template_usage,
            "avg_risk_score": self.avg_risk_score,
            "top_n_person_warning": list(self.top_n_person_warning),
            "recommendations": list(self.recommendations),
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> BiasReport:
        m = data["month"]
        if isinstance(m, str):
            m = date.fromisoformat(m)
        return cls(
            id=int(data["id"]),
            month=m,
            total_uploads=int(data["total_uploads"]),
            person_shares=dict(data.get("person_shares") or {}),
            party_shares=dict(data.get("party_shares") or {}),
            template_usage=dict(data.get("template_usage") or {}),
            avg_risk_score=float(data.get("avg_risk_score", 0.0)),
            top_n_person_warning=tuple(data.get("top_n_person_warning") or []),
            recommendations=tuple(data.get("recommendations") or []),
            generated_at=_parse_dt(data["generated_at"]),
        )


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)
