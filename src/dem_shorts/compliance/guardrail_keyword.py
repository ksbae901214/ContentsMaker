"""T073: 계층1 키워드 기반 가드레일 스캐너 (FR-019, FR-027).

해설 자막 텍스트를 받아 카테고리별 매칭 카운트 + 가중 점수를 산출.
계층1은 빠르고 결정론적이므로 항상 계층2(LLM) 전에 실행.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.dem_shorts.compliance.keyword_dict import (
    CATEGORY_WEIGHTS,
    KEYWORDS,
)


@dataclass(frozen=True)
class KeywordHit:
    """매칭된 키워드 1건."""

    category: str
    keyword: str
    snippet: str  # 매칭 주변 문맥 (약 30자)


@dataclass(frozen=True)
class KeywordScanResult:
    """계층1 키워드 스캔 결과."""

    hits: tuple[KeywordHit, ...]
    counts: dict  # {"hate": 2, "defamation": 1, ...}
    score: float  # 0~100 (카테고리 가중치 × 카운트 합산, 상한 100)

    @property
    def has_blocking(self) -> bool:
        """명예훼손 또는 혐오 키워드가 1회 이상이면 차단 후보."""
        return self.counts.get("defamation", 0) >= 1 or self.counts.get("hate", 0) >= 2


def scan_text(text: str) -> KeywordScanResult:
    """텍스트를 카테고리별로 스캔."""
    if not text:
        return KeywordScanResult(hits=(), counts={}, score=0.0)

    hits: list[KeywordHit] = []
    counts: dict[str, int] = {k: 0 for k in KEYWORDS}

    for category, words in KEYWORDS.items():
        for word in words:
            pos = 0
            while True:
                idx = text.find(word, pos)
                if idx < 0:
                    break
                snippet_start = max(0, idx - 15)
                snippet_end = min(len(text), idx + len(word) + 15)
                hits.append(
                    KeywordHit(
                        category=category,
                        keyword=word,
                        snippet=text[snippet_start:snippet_end],
                    )
                )
                counts[category] += 1
                pos = idx + len(word)

    score = 0.0
    for cat, count in counts.items():
        score += CATEGORY_WEIGHTS.get(cat, 0.0) * count
    score = min(100.0, score)

    return KeywordScanResult(
        hits=tuple(hits),
        counts=counts,
        score=score,
    )


def scan_commentary_blocks(blocks: list[dict]) -> KeywordScanResult:
    """commentary_blocks 리스트(각 블록에 'text' 포함)를 전체 스캔."""
    all_text = "\n".join(b.get("text", "") for b in blocks if b.get("text"))
    return scan_text(all_text)
