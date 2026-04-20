"""Politician — Whitelist 관리 대상.

Spec: specs/007-dem-shorts-studio/data-model.md §2 + spec.md (v2) §FR-006
Perspective axis: docs/politics-bias-charter.md §2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

_TIERS = {"pinned", "auto", "pending", "blocked"}
_CATEGORIES = {"fixed", "female", "youth", "alliance"}
_PERSPECTIVES = {"dem", "ppp"}


@dataclass(frozen=True)
class Politician:
    """Whitelist 정치인. tier로 하이라이트 동작, category로 랭킹 대상 구분.

    `affiliation_perspective`로 dem/ppp 소속을 구분 (2026-04-20 추가).
    """

    id: int
    name: str
    party: str
    role: str
    photo_url: str | None
    bio: str
    tone_guide: str
    tier: str  # pinned/auto/pending/blocked
    category: str  # fixed/female/youth/alliance
    is_active: bool
    ranking_score: float | None
    added_at: datetime
    updated_at: datetime
    affiliation_perspective: str = "dem"  # 하위호환: 기존 row는 dem

    def __post_init__(self) -> None:
        if self.tier not in _TIERS:
            raise ValueError(f"invalid tier: {self.tier}")
        if self.category not in _CATEGORIES:
            raise ValueError(f"invalid category: {self.category}")
        if self.affiliation_perspective not in _PERSPECTIVES:
            raise ValueError(
                f"invalid affiliation_perspective: {self.affiliation_perspective}"
            )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "party": self.party,
            "role": self.role,
            "photo_url": self.photo_url,
            "bio": self.bio,
            "tone_guide": self.tone_guide,
            "tier": self.tier,
            "category": self.category,
            "is_active": self.is_active,
            "ranking_score": self.ranking_score,
            "added_at": self.added_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "affiliation_perspective": self.affiliation_perspective,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Politician:
        return cls(
            id=int(data["id"]),
            name=data["name"],
            party=data["party"],
            role=data.get("role", ""),
            photo_url=data.get("photo_url"),
            bio=data.get("bio", ""),
            tone_guide=data.get("tone_guide", ""),
            tier=data["tier"],
            category=data["category"],
            is_active=bool(data.get("is_active", True)),
            ranking_score=data.get("ranking_score"),
            added_at=_parse_dt(data["added_at"]),
            updated_at=_parse_dt(data["updated_at"]),
            affiliation_perspective=data.get("affiliation_perspective", "dem"),
        )


# FR-006: perspective별 초기 고정 인물
# dem 시드 (민주당·조국혁신당, 3명) — 2026-04-16 최초 정의
SEED_POLITICIANS_DEM = [
    {
        "name": "이재명",
        "party": "더불어민주당",
        "role": "당대표",
        "bio": "前 경기도지사·성남시장, 제21대 대선 출마",
        "tone_guide": "민생·개혁 리더 톤. 직설적이되 공격성 자제",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "dem",
    },
    {
        "name": "조국",
        "party": "조국혁신당",
        "role": "당대표",
        "bio": "前 법무부장관, 서울대 법학전문대학원 교수",
        "tone_guide": "검찰개혁·법치 중심. 논리적 담담함",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "dem",
    },
    {
        "name": "정청래",
        "party": "더불어민주당",
        "role": "법제사법위원장",
        "bio": "4선 국회의원, 법사위원장",
        "tone_guide": "법사위 중심 날카로운 질의. 사실 기반",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "dem",
    },
]

# ppp 시드 (국민의힘, 6명) — 2026-04-20 추가 (Q1 확정)
SEED_POLITICIANS_PPP = [
    {
        "name": "한동훈",
        "party": "국민의힘",
        "role": "前 당대표",
        "bio": "前 법무부장관, 前 당대표",
        "tone_guide": "법치·원칙 강조. 논리적·단정적 어조",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "ppp",
    },
    {
        "name": "김기현",
        "party": "국민의힘",
        "role": "前 당대표·원내대표",
        "bio": "5선 국회의원, 前 당대표·원내대표",
        "tone_guide": "중진 정치인 안정감. 전통 보수 정책 강조",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "ppp",
    },
    {
        "name": "권성동",
        "party": "국민의힘",
        "role": "前 원내대표",
        "bio": "중진 국회의원, 前 원내대표",
        "tone_guide": "원내 전략통. 냉정한 정치 평가",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "ppp",
    },
    {
        "name": "추경호",
        "party": "국민의힘",
        "role": "前 원내대표",
        "bio": "前 기획재정부 장관·원내대표, 경제통",
        "tone_guide": "경제 정책 중심. 수치·데이터 기반",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "ppp",
    },
    {
        "name": "나경원",
        "party": "국민의힘",
        "role": "4선 의원",
        "bio": "4선 중진, 前 원내대표",
        "tone_guide": "보수 여성 대표 주자. 원칙·가족 가치 강조",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "ppp",
    },
    {
        "name": "오세훈",
        "party": "국민의힘",
        "role": "서울시장",
        "bio": "現 서울시장, 정치 복귀 후 서울시 3선",
        "tone_guide": "시정 실적 중심. 중도보수 포지셔닝",
        "tier": "pinned",
        "category": "fixed",
        "affiliation_perspective": "ppp",
    },
]

# 하위호환 별칭 (기존 import `from src.dem_shorts.models.politician import SEED_POLITICIANS`)
SEED_POLITICIANS = SEED_POLITICIANS_DEM


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)
