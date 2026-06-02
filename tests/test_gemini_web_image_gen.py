"""Phase 2A: gemini_web_image_gen 모듈 스모크 테스트.

실제 브라우저는 실행하지 않고, 모듈 임포트·예외·세션 검사 로직만 검증.
실 selector 통합 테스트는 ``gemini_login`` 후 수동으로 진행.
"""
from __future__ import annotations

import pytest

from src.illustrator.gemini_web_image_gen import (
    GeminiWebImageError,
    GeminiWebImageGenerator,
)
from src.illustrator.gemini_web_selectors import (
    GEMINI_SELECTORS,
    IMAGE_ASPECT_HINT,
    IMAGE_PROMPT_PREFIX,
)


class TestSelectors:
    def test_required_keys_present(self):
        for key in (
            "chat_input",
            "send_button",
            "image_in_response",
            "login_required_marker",
        ):
            assert key in GEMINI_SELECTORS, f"missing selector: {key}"

    def test_aspect_hint_specifies_9_16(self):
        assert "9:16" in IMAGE_ASPECT_HINT

    def test_image_prompt_prefix_is_str(self):
        # 2026-05-19 UI 탐색 결과 도구 버튼 활성화 방식이라 prefix 불필요 (빈 문자열 OK)
        assert isinstance(IMAGE_PROMPT_PREFIX, str)

    def test_image_tool_button_selector_present(self):
        assert "image_tool_button" in GEMINI_SELECTORS
        assert "이미지 만들기" in GEMINI_SELECTORS["image_tool_button"]


class TestSessionCheck:
    def test_missing_session_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.illustrator.gemini_web_image_gen.GEMINI_PROFILE_DIR",
            tmp_path / "nope",
        )
        import asyncio

        gen = GeminiWebImageGenerator()
        with pytest.raises(GeminiWebImageError, match="세션 없음"):
            asyncio.run(gen._ensure_session())
