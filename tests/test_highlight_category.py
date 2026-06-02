"""QW-02: 키워드 색 카테고리 매핑.

씬 별 highlight_category에 따라 강조 키워드 색을 달리한다:
- fact → 노랑 (정보·숫자·일자 강조)
- criticism → 빨강 (날카로운 비판)
- neutral → emotion 색 (기본 동작 유지)

출처: docs/dem-shorts/political-youtube-style-plan.md §2.3, §8.2 QW-02.
"""
from __future__ import annotations

import pytest

from src.analyzer.script_models import Scene
from src.tts.voice_config import (
    CATEGORY_HIGHLIGHT_COLORS,
    HIGHLIGHT_COLORS,
    resolve_highlight_color,
)


class TestSceneHighlightCategoryField:
    def test_default_is_neutral(self):
        s = Scene(id=1, timestamp=0, duration=4, type="body",
                  text="t", voice_text="t")
        assert s.highlight_category == "neutral"

    def test_fact_roundtrip(self):
        original = Scene(id=1, timestamp=0, duration=4, type="body",
                         text="t", voice_text="t",
                         highlight_category="fact")
        restored = Scene.from_dict(original.to_dict())
        assert restored.highlight_category == "fact"

    def test_criticism_roundtrip(self):
        original = Scene(id=1, timestamp=0, duration=4, type="body",
                         text="t", voice_text="t",
                         highlight_category="criticism")
        restored = Scene.from_dict(original.to_dict())
        assert restored.highlight_category == "criticism"

    def test_neutral_omitted_from_dict(self):
        """neutral은 기본값이라 키 생략 — 기존 JSON 호환."""
        s = Scene(id=1, timestamp=0, duration=4, type="body",
                  text="t", voice_text="t", highlight_category="neutral")
        assert "highlight_category" not in s.to_dict()

    def test_legacy_json_loads_as_neutral(self):
        data = {"id": 1, "timestamp": 0, "duration": 4, "type": "body",
                "text": "t", "voice_text": "t"}
        s = Scene.from_dict(data)
        assert s.highlight_category == "neutral"


class TestCategoryHighlightColors:
    def test_fact_color_is_yellow(self):
        assert CATEGORY_HIGHLIGHT_COLORS["fact"] == "#FFD54F"

    def test_criticism_color_is_red(self):
        assert CATEGORY_HIGHLIGHT_COLORS["criticism"] == "#F44336"

    def test_all_categories_present(self):
        assert set(CATEGORY_HIGHLIGHT_COLORS.keys()) >= {"fact", "criticism"}


class TestResolveHighlightColor:
    """resolve_highlight_color(category, emotion_type) → 우선순위 검증."""

    def test_fact_overrides_emotion(self):
        assert resolve_highlight_color("fact", "angry") == "#FFD54F"

    def test_criticism_overrides_emotion(self):
        assert resolve_highlight_color("criticism", "funny") == "#F44336"

    def test_neutral_falls_back_to_emotion(self):
        assert resolve_highlight_color("neutral", "angry") == HIGHLIGHT_COLORS["angry"]
        assert resolve_highlight_color("neutral", "funny") == HIGHLIGHT_COLORS["funny"]

    def test_unknown_category_falls_back_to_emotion(self):
        """미지의 category 들어와도 깨지지 않고 emotion 색 사용."""
        assert resolve_highlight_color("xxx", "angry") == HIGHLIGHT_COLORS["angry"]

    def test_unknown_emotion_falls_back_to_default(self):
        # neutral + unknown emotion → relatable 디폴트
        result = resolve_highlight_color("neutral", "unknown_emo")
        assert result == HIGHLIGHT_COLORS["relatable"]


class TestPromptIncludesCategoryGuidance:
    """프롬프트에 highlight_category 가이드가 포함되어야 한다."""

    def test_analyze_prompt_mentions_category(self):
        from src.analyzer.prompt_template import ANALYZE_PROMPT
        assert "highlight_category" in ANALYZE_PROMPT
        assert "fact" in ANALYZE_PROMPT and "criticism" in ANALYZE_PROMPT

    def test_topic_prompt_mentions_category(self):
        from src.analyzer.prompt_template import TOPIC_ANALYZE_PROMPT
        assert "highlight_category" in TOPIC_ANALYZE_PROMPT

    def test_political_prompt_mentions_category(self):
        from src.analyzer.prompt_template import POLITICAL_ANALYZE_PROMPT
        assert "highlight_category" in POLITICAL_ANALYZE_PROMPT
