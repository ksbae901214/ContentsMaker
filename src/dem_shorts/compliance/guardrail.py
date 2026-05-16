"""T075: 계층1 (키워드) + 계층2 (LLM) 통합 가드레일 엔진 (FR-026).

리스크 점수 계산:
- 계층1 점수 × 0.4 + 계층2 max_score × 0.6 = 최종 risk_score
- risk_score ≥ 61 → 차단 (FR-026)
- risk_score ≥ 31 → 경고

계층2 LLM은 비싸므로 계층1에서 명백한 차단 키워드 발견 시 생략 가능.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.dem_shorts.compliance.guardrail_keyword import (
    KeywordScanResult,
    scan_commentary_blocks,
    scan_text,
)
from src.dem_shorts.compliance.guardrail_llm import (
    GuardrailLlmError,
    LlmScanResult,
    scan_with_llm,
)
from src.dem_shorts.config import RISK_SCORE_BLOCK, RISK_SCORE_WARN

logger = logging.getLogger(__name__)

KEYWORD_WEIGHT = 0.4
LLM_WEIGHT = 0.6


@dataclass(frozen=True)
class GuardrailResult:
    """통합 가드레일 결과."""

    risk_score: float  # 0~100
    keyword_result: KeywordScanResult
    llm_result: LlmScanResult | None  # None if LLM skipped or failed
    status: str  # "pass"/"warn"/"fail"
    reasons: tuple[str, ...]  # 사람이 읽을 사유들

    def to_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "status": self.status,
            "keyword": {
                "score": self.keyword_result.score,
                "counts": dict(self.keyword_result.counts),
                "hit_count": len(self.keyword_result.hits),
            },
            "llm": self.llm_result.to_dict() if self.llm_result else None,
            "reasons": list(self.reasons),
        }


def _classify_status(score: float) -> str:
    if score >= RISK_SCORE_BLOCK:
        return "fail"
    if score >= RISK_SCORE_WARN:
        return "warn"
    return "pass"


def run_guardrail(
    commentary_text: str,
    *,
    skip_llm: bool = False,
) -> GuardrailResult:
    """해설 텍스트 전체에 대한 통합 가드레일 실행.

    skip_llm=True이면 계층1 점수만 사용 (테스트/배치용).
    계층2가 실패해도 계층1 결과로 폴백.
    """
    kw_result = scan_text(commentary_text)

    llm_result: LlmScanResult | None = None
    if not skip_llm:
        try:
            llm_result = scan_with_llm(commentary_text)
        except GuardrailLlmError as exc:
            logger.warning("guardrail LLM 실패, 계층1만 사용: %s", exc)
            llm_result = None

    if llm_result is not None:
        final_score = (
            kw_result.score * KEYWORD_WEIGHT
            + llm_result.max_score * LLM_WEIGHT
        )
    else:
        final_score = kw_result.score

    final_score = max(0.0, min(100.0, final_score))

    # 사유 수집
    reasons: list[str] = []
    for hit in kw_result.hits[:5]:  # 상위 5개
        reasons.append(f"{hit.category}: '{hit.keyword}' - \"{hit.snippet}\"")
    if llm_result and llm_result.max_score >= RISK_SCORE_WARN:
        reasons.append(f"LLM 평가: {llm_result.overall_reason}")

    return GuardrailResult(
        risk_score=round(final_score, 2),
        keyword_result=kw_result,
        llm_result=llm_result,
        status=_classify_status(final_score),
        reasons=tuple(reasons),
    )


def run_guardrail_on_blocks(
    blocks: list[dict],
    *,
    skip_llm: bool = False,
) -> GuardrailResult:
    """commentary_blocks 리스트로 가드레일 실행."""
    text = "\n".join(b.get("text", "") for b in blocks if b.get("text"))
    return run_guardrail(text, skip_llm=skip_llm)
