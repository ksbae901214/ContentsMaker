"""Tests for category="political"|"economic" branching in the topic-mode prompt builders.

2026-07-02 경제쇼츠 지원 — 정치쇼츠 V2 파이프라인 확장.
회귀 방지: category 미지정(기본값 "political")은 기존 프롬프트와 바이트 단위로 동일해야 함.
"""
from __future__ import annotations

from src.analyzer.political_planner_stage_a_prompt import (
    STAGE_A_TOPIC_SYSTEM_PROMPT,
    build_stage_a_topic_prompt,
)
from src.analyzer.political_planner_stage_b_prompt import (
    STAGE_B_TOPIC_SYSTEM_PROMPT,
    build_stage_b_topic_prompt,
)


# ─────────────────────────── Stage A ───────────────────────────


def test_stage_a_topic_prompt_default_category_matches_no_category_call():
    """category 인자를 아예 안 넘긴 기존 호출부와 바이트 동일해야 회귀 없음."""
    no_category = build_stage_a_topic_prompt(topic="주제", tone="분노·격앙", details="상세")
    explicit_political = build_stage_a_topic_prompt(
        topic="주제", tone="분노·격앙", details="상세", category="political",
    )
    assert no_category == explicit_political


def test_stage_a_topic_prompt_political_uses_original_system_prompt():
    prompt = build_stage_a_topic_prompt(topic="주제", tone="분노·격앙")
    assert STAGE_A_TOPIC_SYSTEM_PROMPT in prompt
    assert "title_anchor / audience_resonance / comparison" in prompt


def test_stage_a_topic_prompt_economic_uses_economic_persona_and_angles():
    prompt = build_stage_a_topic_prompt(
        topic="6월 CPI 3.2% 상승", tone="차분·분석적", category="economic",
    )
    assert "경제" in prompt
    assert "wallet_impact" in prompt
    assert "cause_analysis" in prompt
    assert "outlook_action" in prompt
    # 정치 전용 문구가 섞여 들어가면 안 됨
    assert "title_anchor / audience_resonance / comparison" not in prompt


def test_stage_a_topic_prompt_economic_has_investment_guardrail():
    prompt = build_stage_a_topic_prompt(topic="금리", category="economic")
    assert "투자 권유 금지" in prompt


# ─────────────────────────── Stage B ───────────────────────────


def test_stage_b_topic_prompt_default_category_matches_no_category_call():
    candidate = {"format_type": "A", "format_reason": "r", "topic": "t", "hook": "h", "angle": "title_anchor"}
    no_category = build_stage_b_topic_prompt(
        topic="주제", tone="분노·격앙", details="", candidate=candidate,
    )
    explicit_political = build_stage_b_topic_prompt(
        topic="주제", tone="분노·격앙", details="", candidate=candidate, category="political",
    )
    assert no_category == explicit_political


def test_stage_b_topic_prompt_political_keeps_comment_whale_cta():
    candidate = {"format_type": "A", "format_reason": "r", "topic": "t", "hook": "h", "angle": "title_anchor"}
    prompt = build_stage_b_topic_prompt(
        topic="주제", tone="분노·격앙", details="", candidate=candidate,
    )
    assert STAGE_B_TOPIC_SYSTEM_PROMPT in prompt
    assert "댓글 고래잡기" in prompt


def test_stage_b_topic_prompt_economic_has_no_investment_solicitation_language():
    candidate = {"format_type": "A", "format_reason": "r", "topic": "물가", "hook": "h", "angle": "wallet_impact"}
    prompt = build_stage_b_topic_prompt(
        topic="6월 CPI", tone="차분·분석적", details="", candidate=candidate, category="economic",
    )
    assert "투자 권유 금지" in prompt
    assert "매수/매도" in prompt
    # 정치 전용 CTA 문구는 섞이지 않아야 함
    assert "댓글 고래잡기" not in prompt


def test_stage_b_topic_prompt_economic_requests_youtube_keywords():
    candidate = {"format_type": "B", "format_reason": "r", "topic": "금리", "hook": "h", "angle": "cause_analysis"}
    prompt = build_stage_b_topic_prompt(
        topic="한국은행 기준금리", tone="차분·분석적", details="", candidate=candidate, category="economic",
    )
    assert "youtube_search_keywords" in prompt
