"""Tests for topic prompt template (T007).

TDD RED phase: these tests define the expected behavior of
build_topic_prompt before implementation exists.
"""
import pytest

from src.analyzer.prompt_template import build_topic_prompt


class TestBuildTopicPromptBasic:
    def test_build_topic_prompt_basic(self):
        prompt = build_topic_prompt(
            topic="과자",
            style="narration",
            tone="재밌게",
            details="설명",
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "과자" in prompt
        assert "narration" in prompt or "나레이션" in prompt


class TestBuildTopicPromptRules:
    def test_build_topic_prompt_contains_rules(self):
        prompt = build_topic_prompt(
            topic="과자",
            style="narration",
            tone="재밌게",
            details="설명",
        )
        assert "감정 타입" in prompt
        assert "줄바꿈" in prompt
        assert "highlight_words" in prompt
        assert "자연스러운 발화 리듬" in prompt

    def test_build_topic_prompt_no_blind_rules(self):
        prompt = build_topic_prompt(
            topic="과자",
            style="narration",
            tone="재밌게",
            details="설명",
        )
        assert "개인정보 제거" not in prompt
        assert "댓글:" not in prompt
        assert "작성자:" not in prompt


class TestBuildTopicPromptFormat:
    def test_build_topic_prompt_includes_json_format(self):
        prompt = build_topic_prompt(
            topic="과자",
            style="narration",
            tone="재밌게",
            details="설명",
        )
        assert '"metadata"' in prompt
        assert '"scenes"' in prompt
        assert '"audio"' in prompt
        assert '"background"' in prompt


class TestBuildTopicPromptStyles:
    def test_build_topic_prompt_style_variations(self):
        narration = build_topic_prompt(
            topic="과자", style="narration", tone="재밌게", details="",
        )
        skit = build_topic_prompt(
            topic="과자", style="skit", tone="재밌게", details="",
        )
        review = build_topic_prompt(
            topic="과자", style="review", tone="재밌게", details="",
        )
        assert narration != skit
        assert skit != review
        assert narration != review
