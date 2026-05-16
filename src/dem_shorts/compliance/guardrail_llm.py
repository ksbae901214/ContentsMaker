"""T074: 계층2 Claude CLI 기반 가드레일 LLM 분류 (FR-019, R-09).

4 카테고리(hate/defamation/bias/false_claim) 각각 0~100점 JSON 분류.
원칙 I: Claude CLI 재사용 → 비용 0원.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


GUARDRAIL_PROMPT = """당신은 정치 쇼츠 해설 자막 리스크 분류기입니다.

아래 해설 텍스트를 4가지 카테고리로 평가하여 각 0~100점 리스크 점수를 JSON으로 반환하세요.

## 카테고리 정의
- hate (혐오): 인신공격, 비하, 차별적 표현
- defamation (명예훼손): 특정인에 대한 허위/단정 범죄·부정 낙인
- bias (편향): 과장 형용사, 선동, 일방적 옹호/공격
- false_claim (근거없는 단정): 확실하지 않은 사안을 단정하는 표현

## 점수 기준
- 0~20: 문제없음
- 21~40: 경미한 주의
- 41~60: 경고 필요
- 61~100: 즉시 차단

## 해설 텍스트
{commentary_text}

## 출력 (JSON만, 코드 블록 없이)
{{
  "hate": 0~100,
  "defamation": 0~100,
  "bias": 0~100,
  "false_claim": 0~100,
  "overall_reason": "간단한 종합 코멘트 1줄"
}}
"""


class GuardrailLlmError(Exception):
    """Raised when LLM guardrail fails."""


@dataclass(frozen=True)
class LlmScanResult:
    hate: float
    defamation: float
    bias: float
    false_claim: float
    overall_reason: str

    @property
    def max_score(self) -> float:
        return max(self.hate, self.defamation, self.bias, self.false_claim)

    def to_dict(self) -> dict:
        return {
            "hate": self.hate,
            "defamation": self.defamation,
            "bias": self.bias,
            "false_claim": self.false_claim,
            "overall_reason": self.overall_reason,
        }


def _call_claude(prompt: str) -> str:
    """기존 analyzer의 Claude CLI 호출 재사용."""
    from src.analyzer.claude_analyzer import AnalyzerError
    from src.analyzer.claude_analyzer import _call_claude as _claude_cli

    try:
        return _claude_cli(prompt)
    except AnalyzerError as exc:
        raise GuardrailLlmError(f"Claude CLI 실패: {exc}") from exc


def parse_llm_response(raw: str) -> LlmScanResult:
    """LLM 응답 JSON 파싱. Markdown code block 허용."""
    data = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    if data is None:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    if data is None or not isinstance(data, dict):
        raise GuardrailLlmError(f"LLM 응답 파싱 실패: {raw[:200]}")

    def _score(key: str) -> float:
        val = data.get(key, 0)
        try:
            return max(0.0, min(100.0, float(val)))
        except (TypeError, ValueError):
            return 0.0

    return LlmScanResult(
        hate=_score("hate"),
        defamation=_score("defamation"),
        bias=_score("bias"),
        false_claim=_score("false_claim"),
        overall_reason=str(data.get("overall_reason", "")).strip(),
    )


def scan_with_llm(commentary_text: str) -> LlmScanResult:
    """해설 텍스트를 Claude CLI로 분류."""
    if not commentary_text.strip():
        return LlmScanResult(hate=0, defamation=0, bias=0, false_claim=0, overall_reason="empty")

    prompt = GUARDRAIL_PROMPT.format(commentary_text=commentary_text)
    raw = _call_claude(prompt)
    return parse_llm_response(raw)
