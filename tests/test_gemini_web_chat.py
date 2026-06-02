"""gemini_web_chat — JSON 추출 + 폴백 시그널 단위 테스트.

웹 자동화 실행 자체는 Playwright + 브라우저 필요라 e2e 별도. 여기는 순수 함수만.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.gemini_web_chat import (
    GeminiWebChatError,
    extract_json_block,
)


class TestExtractJsonBlock:
    def test_json_fence(self):
        text = '여기 결과입니다:\n```json\n{"a": 1, "b": "x"}\n```\n끝.'
        assert json.loads(extract_json_block(text)) == {"a": 1, "b": "x"}

    def test_bare_fence(self):
        text = '응답:\n```\n{"key": "value"}\n```'
        assert json.loads(extract_json_block(text)) == {"key": "value"}

    def test_inline_braces(self):
        text = '여기 결과: {"name": "Bob", "age": 30} 였습니다'
        assert json.loads(extract_json_block(text)) == {"name": "Bob", "age": 30}

    def test_nested_braces(self):
        text = '{"outer": {"inner": [1, 2, 3]}, "k": "v"}'
        result = json.loads(extract_json_block(text))
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_plain_json(self):
        text = '{"a": 1}'
        assert json.loads(extract_json_block(text)) == {"a": 1}

    def test_no_json_returns_original(self):
        text = "그냥 텍스트입니다."
        assert extract_json_block(text) == "그냥 텍스트입니다."


def _make_failing_client(error: Exception, call_counter: dict):
    """genai.Client(api_key=...) 가 반환할 mock — generate_content가 항상 error raise."""
    fake_client = MagicMock()

    def fake_gen(*args, **kwargs):
        call_counter["count"] += 1
        raise error

    fake_client.models.generate_content = fake_gen
    return fake_client


class TestApiFallbackTriggers:
    """call_gemini가 API 실패 시 웹 폴백을 호출하는지 검증.

    google.genai 는 실제 설치된 모듈이므로 `unittest.mock.patch("google.genai.Client", ...)`
    로 깔끔 모킹 (sys.modules 글로벌 변경 없음 → 다른 테스트 영향 없음).
    """

    def test_503_triggers_web_fallback(self, monkeypatch):
        """503 일시적 오류 → API 재시도 모두 실패 → 웹 폴백 호출."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        monkeypatch.delenv("GEMINI_WEB_FALLBACK", raising=False)
        # 빠른 backoff
        monkeypatch.setattr("src.analyzer.gemini_backend._BACKOFF_SCHEDULE", (0.01,))

        api_calls = {"count": 0}
        web_calls = {"count": 0}

        def fake_web(prompt, json_mode=False, **kwargs):
            web_calls["count"] += 1
            return '{"result": "ok"}'

        with patch("google.genai.Client") as mock_client_cls, \
             patch("src.analyzer.gemini_web_chat.chat", side_effect=fake_web):
            mock_client_cls.return_value = _make_failing_client(
                Exception("503 UNAVAILABLE — high demand"), api_calls,
            )
            from src.analyzer.gemini_backend import call_gemini
            result = call_gemini("test prompt", max_attempts=2)

        assert result == '{"result": "ok"}'
        assert api_calls["count"] == 2  # API 2회 시도
        assert web_calls["count"] == 1  # 웹 폴백 1회

    def test_fallback_disabled_by_env(self, monkeypatch):
        """GEMINI_WEB_FALLBACK=0 이면 API 실패 후 폴백 시도 안 함."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        monkeypatch.setenv("GEMINI_WEB_FALLBACK", "0")
        monkeypatch.setattr("src.analyzer.gemini_backend._BACKOFF_SCHEDULE", (0.01,))

        api_calls = {"count": 0}
        web_calls = {"count": 0}

        def fake_web(*a, **k):
            web_calls["count"] += 1
            return ""

        with patch("google.genai.Client") as mock_client_cls, \
             patch("src.analyzer.gemini_web_chat.chat", side_effect=fake_web):
            mock_client_cls.return_value = _make_failing_client(
                Exception("503 UNAVAILABLE"), api_calls,
            )
            from src.analyzer.gemini_backend import call_gemini, GeminiBackendError
            with pytest.raises(GeminiBackendError):
                call_gemini("test", max_attempts=2)

        assert web_calls["count"] == 0  # 폴백 시도 안 됨

    def test_non_transient_error_no_fallback(self, monkeypatch):
        """일시적 오류 아닌 에러(예: schema)는 폴백 안 함."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        monkeypatch.delenv("GEMINI_WEB_FALLBACK", raising=False)
        monkeypatch.setattr("src.analyzer.gemini_backend._BACKOFF_SCHEDULE", (0.01,))

        api_calls = {"count": 0}
        web_calls = {"count": 0}

        def fake_web(*a, **k):
            web_calls["count"] += 1
            return ""

        with patch("google.genai.Client") as mock_client_cls, \
             patch("src.analyzer.gemini_web_chat.chat", side_effect=fake_web):
            mock_client_cls.return_value = _make_failing_client(
                Exception("INVALID_ARGUMENT: bad schema"), api_calls,
            )
            from src.analyzer.gemini_backend import call_gemini, GeminiBackendError
            with pytest.raises(GeminiBackendError):
                call_gemini("test", max_attempts=2)

        assert web_calls["count"] == 0
