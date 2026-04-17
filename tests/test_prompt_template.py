"""QW-01: 후킹 자막 첫 1.5초 강제.

3개 분석 프롬프트(ANALYZE/TOPIC/POLITICAL)에 후킹 카피 가이드와
클릭베이트 금지어가 포함되어야 한다.

출처: docs/dem-shorts/political-youtube-style-plan.md §1.2 (쇼츠 후킹).
"""
from __future__ import annotations

import pytest

from src.analyzer.prompt_template import (
    ANALYZE_PROMPT,
    POLITICAL_ANALYZE_PROMPT,
    TOPIC_ANALYZE_PROMPT,
    build_political_prompt,
    build_prompt,
    build_topic_prompt,
)


# QW-01 + QW-08 공통 금지어 (인라인 정의, 후속 PR에서 공통화 예정)
QW01_BANNED_HOOK_WORDS: tuple[str, ...] = (
    "충격",
    "잠깐만요",
    "이거 봤어",
    "절대",
    "100%",
    "믿을 수 없",
)


# ── Group 1: 후킹 가이드 포함 ────────────────────────────────────────


@pytest.mark.parametrize(
    "prompt,name",
    [
        (ANALYZE_PROMPT, "ANALYZE_PROMPT"),
        (TOPIC_ANALYZE_PROMPT, "TOPIC_ANALYZE_PROMPT"),
        (POLITICAL_ANALYZE_PROMPT, "POLITICAL_ANALYZE_PROMPT"),
    ],
)
class TestHookGuidanceInPrompts:
    def test_mentions_hook(self, prompt: str, name: str):
        """프롬프트 본문에 '후킹' 단어가 있어야 LLM이 지시를 인식한다."""
        assert "후킹" in prompt or "hook" in prompt.lower(), (
            f"{name}에 후킹 가이드 없음 (QW-01)"
        )

    def test_first_scene_short_duration(self, prompt: str, name: str):
        """첫 씬 duration 1.5~2.5초 가이드가 명시되어야 한다."""
        # 1.5 또는 2.5 둘 중 하나는 반드시 들어가야 함
        assert "1.5" in prompt or "2.5" in prompt, (
            f"{name}에 후킹 씬 duration(1.5~2.5초) 가이드 없음"
        )

    def test_hook_field_in_json_example(self, prompt: str, name: str):
        """JSON 출력 예시에 hook 필드가 포함되어야 한다."""
        assert '"hook"' in prompt, (
            f"{name} JSON 예시에 hook 필드 없음 — LLM이 출력 안 함"
        )


# ── Group 2: 클릭베이트 금지어 부재 ──────────────────────────────────


@pytest.mark.parametrize(
    "prompt,name",
    [
        (ANALYZE_PROMPT, "ANALYZE_PROMPT"),
        (TOPIC_ANALYZE_PROMPT, "TOPIC_ANALYZE_PROMPT"),
        (POLITICAL_ANALYZE_PROMPT, "POLITICAL_ANALYZE_PROMPT"),
    ],
)
class TestNoClickbaitInExamples:
    """프롬프트의 예시·가이드 부분에서 금지어가 사용되면 안 된다.

    단, '금지어 명시' 섹션 자체에는 등장할 수 있으므로 그 부분은 제외한다.
    """

    @pytest.mark.parametrize("banned", QW01_BANNED_HOOK_WORDS)
    def test_banned_word_only_in_ban_section(
        self, prompt: str, name: str, banned: str
    ):
        # 금지어 섹션 마커 — 이 마커 이후의 라인에서만 금지어 등장 허용
        ban_marker = "금지어"
        if ban_marker not in prompt:
            # 금지어 섹션 자체가 없으면 어디에도 금지어 있으면 안 됨
            assert banned not in prompt, (
                f"{name}에 금지어 '{banned}' 등장 — 금지어 가드 섹션 추가 필요"
            )
            return
        # 마커 이전 영역에는 금지어 등장 금지
        before_section = prompt[: prompt.index(ban_marker)]
        assert banned not in before_section, (
            f"{name}의 금지어 섹션 이전(예시·가이드)에 '{banned}' 등장 — "
            f"LLM이 후킹 카피로 사용할 수 있음"
        )


# ── Group 3: build_*() 함수가 가이드를 보존하는지 확인 ───────────────


class TestBuildersPreserveHookGuidance:
    def test_build_prompt_keeps_hook_guidance(self):
        out = build_prompt(
            title="제목", author="작성자", body="본문 내용 충분히 긴 텍스트", comments=[]
        )
        assert "후킹" in out or "hook" in out.lower()
        assert '"hook"' in out

    def test_build_topic_prompt_keeps_hook_guidance(self):
        out = build_topic_prompt(
            topic="과자 리뷰", style="narration", tone="재밌게", details=""
        )
        assert "후킹" in out or "hook" in out.lower()
        assert '"hook"' in out

    def test_build_political_prompt_keeps_hook_guidance(self):
        out = build_political_prompt(
            youtube_url="https://www.youtube.com/watch?v=abc",
            transcript=[{"start": 0.0, "end": 2.0, "text": "안녕하세요"}],
            clip_start=0.0,
            clip_end=10.0,
            tone="객관적",
            details="",
        )
        assert "후킹" in out or "hook" in out.lower()
        assert '"hook"' in out
