"""Popular female National Assembly lawmakers database.

Note: Party affiliation reflects 22nd National Assembly (elected June 2024).
Update this list as needed when assembly composition changes.
"""
from __future__ import annotations

from typing import TypedDict


class Lawmaker(TypedDict):
    name: str
    party: str
    role: str
    description: str
    emoji: str
    search_query: str
    natv_query: str


POPULAR_FEMALE_LAWMAKERS: list[Lawmaker] = [
    {
        "name": "나경원",
        "party": "국민의힘",
        "role": "의원",
        "description": "전 원내대표, 장기 경력 보수 중진",
        "emoji": "🎤",
        "search_query": "나경원 국회 발언",
        "natv_query": "나경원",
    },
    {
        "name": "배현진",
        "party": "국민의힘",
        "role": "의원",
        "description": "전 MBC 앵커 출신, 날카로운 언변",
        "emoji": "📺",
        "search_query": "배현진 의원 국회 발언",
        "natv_query": "배현진",
    },
    {
        "name": "김예지",
        "party": "국민의힘",
        "role": "의원",
        "description": "올림픽 펜싱 은메달리스트 출신",
        "emoji": "🤺",
        "search_query": "김예지 의원 국회 발언",
        "natv_query": "김예지",
    },
    {
        "name": "한지아",
        "party": "국민의힘",
        "role": "의원",
        "description": "의사 출신, 보건복지위 전문 활동",
        "emoji": "👩‍⚕️",
        "search_query": "한지아 의원 국회 발언",
        "natv_query": "한지아",
    },
    {
        "name": "진선미",
        "party": "더불어민주당",
        "role": "의원",
        "description": "전 장관, 여성가족위 활발 활동",
        "emoji": "⚖️",
        "search_query": "진선미 의원 국회 발언",
        "natv_query": "진선미",
    },
    {
        "name": "남인순",
        "party": "더불어민주당",
        "role": "의원",
        "description": "보건복지위 여성의원 베테랑",
        "emoji": "🏥",
        "search_query": "남인순 의원 국회 발언",
        "natv_query": "남인순",
    },
    {
        "name": "서영교",
        "party": "더불어민주당",
        "role": "의원",
        "description": "4선 여성의원, 법제사법위 활동",
        "emoji": "🔨",
        "search_query": "서영교 의원 국회 발언",
        "natv_query": "서영교",
    },
    {
        "name": "고민정",
        "party": "더불어민주당",
        "role": "의원",
        "description": "전 청와대 대변인 출신",
        "emoji": "💬",
        "search_query": "고민정 의원 국회 발언",
        "natv_query": "고민정",
    },
]


def get_by_party(party: str) -> list[Lawmaker]:
    """Filter lawmakers by party name."""
    return [lm for lm in POPULAR_FEMALE_LAWMAKERS if lm["party"] == party]


def get_by_name(name: str) -> Lawmaker | None:
    """Find a lawmaker by exact name."""
    for lm in POPULAR_FEMALE_LAWMAKERS:
        if lm["name"] == name:
            return lm
    return None
