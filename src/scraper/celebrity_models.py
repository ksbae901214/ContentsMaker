"""CelebrityInfo model for celebrity-introduction Shorts (Phase 9).

Frozen dataclass for facts extracted from Namuwiki. Source URL is restricted
to https://namu.wiki/... to preserve licensing (CC BY-NC-SA 3.0) provenance.
"""
from __future__ import annotations

from dataclasses import dataclass


class CelebrityInfoError(Exception):
    """Raised when CelebrityInfo validation fails."""


@dataclass(frozen=True)
class CelebrityInfo:
    """Facts about a celebrity, sourced from Namuwiki.

    All sequence fields are tuples to preserve immutability. The Claude
    analyzer rewrites these into scene text — never quote them verbatim in
    the final video to respect CC BY-NC-SA 3.0.
    """
    name: str
    summary: str
    source_url: str
    birth_date: str = ""
    profession: str = ""
    career_highlights: tuple[str, ...] = ()
    trivia: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.name.strip():
            raise CelebrityInfoError("이름은 비어 있을 수 없습니다")
        if not self.summary.strip():
            raise CelebrityInfoError("요약은 비어 있을 수 없습니다")
        if not self.source_url.startswith("https://"):
            raise CelebrityInfoError(
                f"source_url은 https로 시작해야 합니다: {self.source_url!r}"
            )
        if not self.source_url.startswith("https://namu.wiki/"):
            raise CelebrityInfoError(
                f"source_url은 namu.wiki 페이지여야 합니다: {self.source_url!r}"
            )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "summary": self.summary,
            "birth_date": self.birth_date,
            "profession": self.profession,
            "career_highlights": list(self.career_highlights),
            "trivia": list(self.trivia),
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CelebrityInfo:
        return cls(
            name=data["name"],
            summary=data["summary"],
            source_url=data["source_url"],
            birth_date=data.get("birth_date", ""),
            profession=data.get("profession", ""),
            career_highlights=tuple(data.get("career_highlights", ())),
            trivia=tuple(data.get("trivia", ())),
        )
