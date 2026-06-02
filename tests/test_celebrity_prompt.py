"""Tests for celebrity prompt template (Phase 9-3)."""
from __future__ import annotations

from src.analyzer.celebrity_prompt import build_celebrity_prompt
from src.scraper.celebrity_models import CelebrityInfo


def _sample_info() -> CelebrityInfo:
    return CelebrityInfo(
        name="손흥민",
        summary="대한민국의 축구 선수",
        birth_date="1992-07-08",
        profession="축구 선수",
        career_highlights=("토트넘 이적 (2015)", "EPL 득점왕 (2022)"),
        trivia=("아버지는 축구 감독 출신",),
        source_url="https://namu.wiki/w/손흥민",
    )


class TestBuildCelebrityPrompt:
    def test_includes_core_fields(self):
        prompt = build_celebrity_prompt(_sample_info())
        assert "손흥민" in prompt
        assert "대한민국의 축구 선수" in prompt
        assert "1992-07-08" in prompt
        assert "축구 선수" in prompt

    def test_includes_highlights_and_trivia(self):
        prompt = build_celebrity_prompt(_sample_info())
        assert "토트넘 이적 (2015)" in prompt
        assert "EPL 득점왕 (2022)" in prompt
        assert "아버지는 축구 감독 출신" in prompt

    def test_includes_source_url(self):
        prompt = build_celebrity_prompt(_sample_info())
        assert "https://namu.wiki/w/손흥민" in prompt

    def test_empty_highlights_handled_gracefully(self):
        info = CelebrityInfo(
            name="세종",
            summary="조선의 제4대 국왕",
            source_url="https://namu.wiki/w/세종",
        )
        prompt = build_celebrity_prompt(info)
        assert "제공된 정보 없음" in prompt

    def test_attribution_mandate_present(self):
        """Prompt must force the final scene to include 출처: 나무위키."""
        prompt = build_celebrity_prompt(_sample_info())
        assert "출처: 나무위키" in prompt

    def test_factuality_rule_present(self):
        prompt = build_celebrity_prompt(_sample_info())
        assert "절대로 추가하지 마세요" in prompt or "절대로 추가하지" in prompt

    def test_rewrite_mandate_present(self):
        prompt = build_celebrity_prompt(_sample_info())
        assert "재구성" in prompt
