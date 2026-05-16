"""T076: 가드레일 (계층1 키워드 + 계층2 LLM) 테스트.

- 카테고리별 점수 산출
- 임계값 분류 (pass/warn/fail, 30/60)
- LLM 응답 mock + 실패 시 계층1 폴백
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from src.dem_shorts.compliance.guardrail import (
    GuardrailResult,
    run_guardrail,
    run_guardrail_on_blocks,
)
from src.dem_shorts.compliance.guardrail_keyword import scan_text
from src.dem_shorts.compliance.guardrail_llm import (
    LlmScanResult,
    parse_llm_response,
)
from src.dem_shorts.config import RISK_SCORE_BLOCK, RISK_SCORE_WARN


class TestKeywordScanner:
    def test_clean_text_zero_score(self):
        result = scan_text("민생 경제 회복을 위한 정책을 발표했습니다.")
        assert result.score == 0.0
        assert len(result.hits) == 0

    def test_single_hate_word(self):
        result = scan_text("이 발언은 극혐 수준입니다.")
        assert result.counts.get("hate", 0) >= 1
        assert result.score > 0

    def test_defamation_word_high_weight(self):
        result = scan_text("그는 분명한 범죄자입니다.")
        # 'defamation' weight 30 + 'false_claim' weight 15 (분명)
        assert result.counts.get("defamation", 0) >= 1
        assert result.score >= 30

    def test_multiple_bias_words(self):
        result = scan_text("역대급 처참한 결과 경악스럽다 최악의 상황")
        assert result.counts.get("bias", 0) >= 3
        assert result.score >= 30

    def test_score_capped_at_100(self):
        # 매우 많은 키워드
        text = "범죄자 사기꾼 뇌물 " * 10
        result = scan_text(text)
        assert result.score <= 100.0

    def test_has_blocking_property(self):
        r1 = scan_text("그는 범죄자다")
        assert r1.has_blocking is True
        r2 = scan_text("역대급")
        assert r2.has_blocking is False


class TestLlmResponseParser:
    def test_parses_clean_json(self):
        raw = json.dumps({
            "hate": 10,
            "defamation": 5,
            "bias": 15,
            "false_claim": 8,
            "overall_reason": "대체로 양호",
        })
        r = parse_llm_response(raw)
        assert r.hate == 10
        assert r.defamation == 5
        assert r.bias == 15
        assert r.false_claim == 8
        assert r.overall_reason == "대체로 양호"

    def test_parses_markdown_codeblock(self):
        raw = (
            "```json\n"
            + json.dumps({"hate": 40, "defamation": 0, "bias": 20, "false_claim": 10,
                          "overall_reason": "경계 필요"})
            + "\n```"
        )
        r = parse_llm_response(raw)
        assert r.hate == 40
        assert r.max_score == 40

    def test_clamps_scores(self):
        raw = json.dumps({"hate": 200, "defamation": -5, "bias": "invalid",
                          "false_claim": 50, "overall_reason": ""})
        r = parse_llm_response(raw)
        assert r.hate == 100.0  # clamped
        assert r.defamation == 0.0  # clamped to min
        assert r.bias == 0.0  # non-numeric → 0

    def test_rejects_garbage(self):
        with pytest.raises(Exception):
            parse_llm_response("not json at all")


class TestRunGuardrail:
    def test_skip_llm_uses_keyword_only(self):
        result = run_guardrail("민생 회복 정책", skip_llm=True)
        assert result.status == "pass"
        assert result.risk_score == 0.0
        assert result.llm_result is None

    def test_hate_word_triggers_warn_or_fail(self):
        result = run_guardrail("이건 극혐 쓰레기 발언이다", skip_llm=True)
        # 극혐(25) + 쓰레기(25) = 50 keyword score → risk_score * 0.4 없이 50
        assert result.risk_score >= RISK_SCORE_WARN
        assert result.status in ("warn", "fail")

    @mock.patch("src.dem_shorts.compliance.guardrail.scan_with_llm")
    def test_llm_combined_weighting(self, mock_llm):
        mock_llm.return_value = LlmScanResult(
            hate=10, defamation=60, bias=20, false_claim=15, overall_reason="defamation risk"
        )
        result = run_guardrail("중립적 텍스트", skip_llm=False)
        # keyword=0 × 0.4 + llm_max=60 × 0.6 = 36
        assert 35 <= result.risk_score <= 37
        assert result.status == "warn"

    @mock.patch("src.dem_shorts.compliance.guardrail.scan_with_llm")
    def test_llm_failure_falls_back_to_keyword(self, mock_llm):
        from src.dem_shorts.compliance.guardrail_llm import GuardrailLlmError
        mock_llm.side_effect = GuardrailLlmError("mock failure")
        result = run_guardrail("극혐 쓰레기", skip_llm=False)
        assert result.llm_result is None
        # 계층1만 사용해도 점수 계산됨
        assert result.risk_score > 0

    @mock.patch("src.dem_shorts.compliance.guardrail.scan_with_llm")
    def test_high_risk_triggers_fail(self, mock_llm):
        mock_llm.return_value = LlmScanResult(
            hate=90, defamation=95, bias=50, false_claim=40, overall_reason="matched high risk"
        )
        result = run_guardrail("범죄자 범죄자", skip_llm=False)
        assert result.status == "fail"
        assert result.risk_score >= RISK_SCORE_BLOCK

    def test_run_on_blocks(self):
        blocks = [
            {"text": "민생 경제 강조", "start": 0, "end": 3},
            {"text": "정치 개혁 촉구", "start": 3, "end": 6},
        ]
        result = run_guardrail_on_blocks(blocks, skip_llm=True)
        assert result.status == "pass"
