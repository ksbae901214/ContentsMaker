"""Tests for political_planner_prompt — RTF 절대 준수 4항목 인코딩 검증.

Spec FR-007, SC-005: 시스템 프롬프트에 4가지 절대 준수 항목이 명시적으로 포함되어야 함.
"""
from __future__ import annotations

from src.analyzer.political_planner_prompt import (
    POLITICAL_PLANNER_SYSTEM_PROMPT,
    build_political_planner_prompt,
)


def test_prompt_contains_fact_only_rule():
    """절대 준수 #1: 영상에서 확인 가능한 사실만 사용."""
    p = POLITICAL_PLANNER_SYSTEM_PROMPT
    assert "사실" in p, "프롬프트에 '사실' 키워드 부재"
    assert "확인 가능한 사실만" in p or "확인 가능한 사실" in p, \
        "'영상에서 확인 가능한 사실만' 명시 부재"


def test_prompt_contains_no_opinion_rule():
    """절대 준수 #2: 개인 의견·해석·추측·루머 금지."""
    p = POLITICAL_PLANNER_SYSTEM_PROMPT
    assert "의견" in p and "금지" in p, "의견 금지 항목 부재"
    # 키워드 4종 중 최소 3개 포함
    keywords = ["의견", "해석", "추측", "루머"]
    present = sum(1 for kw in keywords if kw in p)
    assert present >= 3, f"'의견/해석/추측/루머' 중 {present}개만 발견 (3개 이상 필요)"


def test_prompt_contains_political_neutrality_rule():
    """절대 준수 #3: 정치적 편향 금지 (지지/비판 금지)."""
    p = POLITICAL_PLANNER_SYSTEM_PROMPT
    assert "편향" in p, "'편향' 키워드 부재"
    assert "지지" in p and "비판" in p, "'지지/비판 금지' 표현 부재"


def test_prompt_contains_no_distortion_rule():
    """절대 준수 #4: 자극은 허용·왜곡은 금지."""
    p = POLITICAL_PLANNER_SYSTEM_PROMPT
    assert "왜곡" in p, "'왜곡' 키워드 부재"
    assert "왜곡" in p and "금지" in p, "'왜곡 금지' 표현 부재"


def test_prompt_requires_three_distinct_angles():
    """3개 기획안은 서로 다른 angle 명시 — FR-006."""
    p = POLITICAL_PLANNER_SYSTEM_PROMPT
    assert "3" in p, "3개 기획안 요청 부재"
    # angle / 관점 / angle types 중 하나 이상
    assert any(kw in p for kw in ["angle", "관점", "title_anchor", "audience_resonance", "comparison"]), \
        "3개 plan의 서로 다른 angle 요구 부재"


def test_prompt_requires_six_elements():
    """RTF 6요소 모두 명시 — FR-005."""
    p = POLITICAL_PLANNER_SYSTEM_PROMPT
    # 한국어 또는 영문 키워드 둘 다 검사
    elements_check = [
        any(kw in p for kw in ["주제", "topic"]),
        any(kw in p for kw in ["후킹", "hook", "Hook"]),
        any(kw in p for kw in ["구간", "clip", "사용 구간"]),
        any(kw in p for kw in ["흐름", "flow", "클라이맥스"]),
        any(kw in p for kw in ["나레이션", "narration", "타이밍"]),
        any(kw in p for kw in ["CTA", "마무리", "행동 유도"]),
    ]
    missing = [i for i, ok in enumerate(elements_check) if not ok]
    assert not missing, f"RTF 6요소 중 missing index={missing}"


def test_build_prompt_includes_transcript_and_title():
    transcript = [
        {"start": 0.0, "end": 3.0, "text": "안녕하세요"},
        {"start": 3.0, "end": 7.0, "text": "오늘은 중요한 발언이 있었습니다"},
    ]
    full = build_political_planner_prompt(
        video_title="국회 본회의 발언",
        transcript=transcript,
        video_duration_sec=120.5,
    )
    assert "국회 본회의 발언" in full
    assert "안녕하세요" in full
    assert "중요한 발언" in full
    # 영상 길이도 포함되어야 클램프 검증 가능
    assert "120" in full


def test_build_prompt_includes_all_system_rules():
    """build_political_planner_prompt 결과에도 4종 규칙이 모두 포함되어야."""
    full = build_political_planner_prompt(
        video_title="t",
        transcript=[{"start": 0.0, "end": 1.0, "text": "x"}],
        video_duration_sec=10.0,
    )
    assert "사실" in full
    assert "편향" in full
    assert "왜곡" in full
    assert "의견" in full


# ════════════════════════ V2 (Feature 011) — Stage A·B 업그레이드 ════════════════════════


def test_stage_a_prompt_includes_format_classification():
    """Stage A 프롬프트는 A타입(인터뷰/논평) vs B타입(현장 밀착) 분류를 안내해야 함."""
    from src.analyzer.political_planner_stage_a_prompt import STAGE_A_SYSTEM_PROMPT
    p = STAGE_A_SYSTEM_PROMPT
    assert "A타입" in p or "A type" in p.lower(), "A타입 분류 가이드 부재"
    assert "B타입" in p or "B type" in p.lower(), "B타입 분류 가이드 부재"


def test_stage_a_prompt_includes_format_examples():
    """A/B 분류 기준 예시(MBC 라디오, 뉴스핌, 국회, 기자회견 등) 포함."""
    from src.analyzer.political_planner_stage_a_prompt import STAGE_A_SYSTEM_PROMPT
    p = STAGE_A_SYSTEM_PROMPT
    a_examples = ["MBC 라디오", "인터뷰", "논평"]
    b_examples = ["뉴스핌", "현장", "기자회견", "국회"]
    assert any(kw in p for kw in a_examples), f"A타입 예시 부재 ({a_examples})"
    assert any(kw in p for kw in b_examples), f"B타입 예시 부재 ({b_examples})"


def test_stage_a_prompt_outputs_format_fields():
    """Stage A 출력 스키마에 format_type/format_reason 필드 명시."""
    from src.analyzer.political_planner_stage_a_prompt import STAGE_A_SYSTEM_PROMPT
    p = STAGE_A_SYSTEM_PROMPT
    assert "format_type" in p
    assert "format_reason" in p


def test_stage_b_prompt_requires_subtitle_color():
    """Stage B 출력에 narrations[].subtitle_color 필드 명시."""
    from src.analyzer.political_planner_stage_b_prompt import STAGE_B_SYSTEM_PROMPT
    p = STAGE_B_SYSTEM_PROMPT
    assert "subtitle_color" in p, "subtitle_color 필드 출력 지시 부재"
    # 색 프리셋 가이드
    color_keywords = ["red", "yellow", "white", "blue"]
    present = sum(1 for c in color_keywords if c in p)
    assert present >= 3, f"색 프리셋(red/yellow/white/blue) 중 {present}/4만 발견"


def test_stage_b_prompt_requires_visual_directives():
    """visual_directives 배열 출력 지시 (대조 연출 등)."""
    from src.analyzer.political_planner_stage_b_prompt import STAGE_B_SYSTEM_PROMPT
    p = STAGE_B_SYSTEM_PROMPT
    assert "visual_directives" in p
    # 대조 연출 가이드 (좌·우 분할 또는 split 등)
    assert any(kw in p for kw in ["대조", "split", "분할", "좌", "우"]), \
        "대조 연출(split) 가이드 부재"


def test_stage_b_prompt_requires_question_cta():
    """CTA 톤은 '댓글 고래잡기' — 도발적·공감형 질문."""
    from src.analyzer.political_planner_stage_b_prompt import STAGE_B_SYSTEM_PROMPT
    p = STAGE_B_SYSTEM_PROMPT
    assert "댓글" in p, "'댓글' 키워드 부재"
    # 질문 형태 가이드
    assert any(kw in p for kw in ["질문", "어떻게 생각", "공감", "도발"]), \
        "질문형 CTA 가이드 부재"
