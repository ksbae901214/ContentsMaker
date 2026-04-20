"""perspective별 점유도(FR-004) · 쇼츠 추천 점수(FR-016) 계산.

Spec: research.md R-05, R-04 · data-model.md §1, §3 · FR-004, FR-016
2026-04-20: perspective 축 도입 — TOP 인물 목록은 PERSPECTIVE_TOP_NAMES에서 조회.
기존 dem 하드코딩 별칭은 하위호환 유지.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.dem_shorts.config import (
    DEFAULT_PERSPECTIVE,
    DEM_SCORE_FEMALE_YOUTH_BONUS,
    DEM_SCORE_ISSUE_KEYWORD,
    DEM_SCORE_ISSUE_KEYWORD_CAP,
    DEM_SCORE_OVER_6H_PENALTY,
    DEM_SCORE_PER_PERSON,
    DEM_SCORE_PER_PERSON_CAP,
    DEM_SCORE_REPEAT_PENALTY_MAX,
    DEM_SCORE_TOP3_BONUS,
    DEM_SCORE_TOP3_CAP,
    DEM_SCORE_TOP_WHITELIST,
    MAX_VIDEO_DURATION_SEC,
    PERSPECTIVE_TOP_NAMES,
    SUPPORTED_PERSPECTIVES,
)


def get_top_names(perspective: str | None = None) -> tuple[str, ...]:
    """perspective별 TOP 인물 이름 목록 반환."""
    persp = perspective or DEFAULT_PERSPECTIVE
    if persp not in SUPPORTED_PERSPECTIVES:
        raise ValueError(f"invalid perspective: {persp}")
    return PERSPECTIVE_TOP_NAMES[persp]


# 하위호환: 기존 `from src.dem_shorts.scoring import TOP3_NAMES` 호출부 유지.
# 값은 DEFAULT_PERSPECTIVE 기준 (2026-04-20부터 ppp 6명).
TOP3_NAMES = get_top_names(DEFAULT_PERSPECTIVE)


@dataclass(frozen=True)
class DemScoreInputs:
    """FR-004 점수 계산에 필요한 입력 집합.

    naming은 하위호환 유지(`DemScoreInputs`, `dem_person_count`). perspective 인자를
    전달하면 해당 perspective TOP 인물 기준으로 계산된다. 기본값은 DEFAULT_PERSPECTIVE.
    """

    dem_person_count: int  # 활성 perspective 식별 인물 수 (이름은 레거시)
    has_top_whitelist: bool  # pinned or auto 등급 인물 1명 이상
    top3_present: dict  # {인물명: bool} — 활성 perspective의 TOP 인물 기준
    female_or_youth_present: bool
    issue_keyword_matches: int
    duration_sec: int
    recent_repeat_count: int
    perspective: str = DEFAULT_PERSPECTIVE


def calculate_dem_score(x: DemScoreInputs) -> float:
    """research.md R-05 공식 구현 (perspective-aware). 0~100 clamp.

    기본 점수 =
      min(perspective 식별 인물 수 × 10, 40)
    + Whitelist 상위 인물 포함 시 20
    + min(활성 perspective TOP 인물 등장 × 15, 30)
    + 여성/청년 포함 시 10
    + min(이슈 키워드 × 5, 20)
    - 6h 초과 시 10
    - 최근 반복 인물 페널티 (최대 30)
    """
    score = 0.0
    score += min(x.dem_person_count * DEM_SCORE_PER_PERSON, DEM_SCORE_PER_PERSON_CAP)
    if x.has_top_whitelist:
        score += DEM_SCORE_TOP_WHITELIST
    top_names = get_top_names(x.perspective)
    top3_hits = sum(1 for name in top_names if x.top3_present.get(name))
    score += min(top3_hits * DEM_SCORE_TOP3_BONUS, DEM_SCORE_TOP3_CAP)
    if x.female_or_youth_present:
        score += DEM_SCORE_FEMALE_YOUTH_BONUS
    score += min(
        x.issue_keyword_matches * DEM_SCORE_ISSUE_KEYWORD, DEM_SCORE_ISSUE_KEYWORD_CAP
    )
    if x.duration_sec > MAX_VIDEO_DURATION_SEC:
        score -= DEM_SCORE_OVER_6H_PENALTY
    repeat_penalty = min(x.recent_repeat_count * 3, DEM_SCORE_REPEAT_PENALTY_MAX)
    score -= repeat_penalty

    return max(0.0, min(100.0, score))


# 가독성 위한 별칭
calculate_perspective_score = calculate_dem_score


# ─────────────── Recommendation score (FR-016) ───────────────


@dataclass(frozen=True)
class RecommendationInputs:
    """쇼츠 추천 점수 계산 입력."""

    is_top_whitelist: bool  # Whitelist 상위(pinned/auto) 인물
    duration_sec: float
    emotion_strength: float  # 0~1 (!·? 빈도 + 볼륨 변화)
    issue_keyword_count: int
    is_solo: bool  # 단독 발언 구간
    has_profanity: bool  # 욕설 감지 → -50


def calculate_recommendation_score(x: RecommendationInputs) -> float:
    """FR-016 공식.

    score =
      (Whitelist 상위 인물 × 20)
    + (발언 길이 30~90초 만점 40, 벗어나면 감점)
    + (emotion_strength × 30)
    + (issue_keyword_count × 5)
    + (is_solo × 10)
    - (has_profanity × 50)

    Clamp to [0, 100].
    """
    score = 0.0
    if x.is_top_whitelist:
        score += 20

    # Duration adequacy (ideal: 30~90s)
    if 30.0 <= x.duration_sec <= 90.0:
        score += 40
    else:
        # Fall off linearly from the nearest boundary, max 40 penalty
        if x.duration_sec < 30.0:
            score += max(0.0, 40 - (30.0 - x.duration_sec) * 2)
        else:
            score += max(0.0, 40 - (x.duration_sec - 90.0))

    score += x.emotion_strength * 30
    score += x.issue_keyword_count * 5
    if x.is_solo:
        score += 10
    if x.has_profanity:
        score -= 50

    return max(0.0, min(100.0, score))


# ─────────────── Keyword detection helpers (FR-016 part) ───────────────

# 이슈 키워드 사전 (확장 가능) — Phase 2 운영 중 갱신
ISSUE_KEYWORDS: tuple[str, ...] = (
    "연금개혁",
    "국민연금",
    "민생",
    "경제",
    "부동산",
    "검찰개혁",
    "법사위",
    "대정부질문",
    "탄핵",
    "예산안",
    "노동",
    "복지",
    "교육",
    "의료",
    "남북관계",
    "기후",
)

# 최소한의 한국어 욕설·비속어 사전. 운영 중 확장.
PROFANITY_WORDS: tuple[str, ...] = (
    "시발", "씨발", "개새끼", "병신", "꺼져", "지랄",
)


def detect_issue_keywords(text: str, vocab: Iterable[str] = ISSUE_KEYWORDS) -> list[str]:
    """텍스트에서 이슈 키워드를 찾아 list로 반환 (중복 제거)."""
    found = {kw for kw in vocab if kw in text}
    return sorted(found)


def detect_profanity(text: str, vocab: Iterable[str] = PROFANITY_WORDS) -> bool:
    """욕설 감지. 하나라도 매칭되면 True."""
    return any(w in text for w in vocab)
