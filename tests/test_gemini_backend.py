"""Phase 1B: Gemini 백엔드 + ANALYZER_BACKEND 토글 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.gemini_backend import (
    GeminiBackendError,
    call_analyzer,
    call_gemini,
    get_backend,
)


class TestGetBackend:
    def test_default_is_claude(self, monkeypatch):
        monkeypatch.delenv("ANALYZER_BACKEND", raising=False)
        assert get_backend() == "claude"

    def test_gemini_explicit(self, monkeypatch):
        monkeypatch.setenv("ANALYZER_BACKEND", "gemini")
        assert get_backend() == "gemini"

    def test_unknown_falls_back_to_claude(self, monkeypatch):
        monkeypatch.setenv("ANALYZER_BACKEND", "openai")
        assert get_backend() == "claude"

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ANALYZER_BACKEND", "GEMINI")
        assert get_backend() == "gemini"


class TestCallGemini:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(GeminiBackendError, match="GEMINI_API_KEY"):
            call_gemini("test")

    def test_successful_call(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        mock_response = MagicMock()
        mock_response.text = '{"ok": true}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            out = call_gemini("hello")
        assert out == '{"ok": true}'

    def test_empty_response_retries_then_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.candidates = []
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            with patch("time.sleep"):
                with pytest.raises(GeminiBackendError, match="모두 실패"):
                    call_gemini("hello", max_attempts=2)
        assert mock_client.models.generate_content.call_count == 2


class TestCallAnalyzer:
    def test_default_backend_uses_claude(self, monkeypatch):
        monkeypatch.delenv("ANALYZER_BACKEND", raising=False)
        claude_mock = MagicMock(return_value="claude_response")
        out = call_analyzer("p", claude_caller=claude_mock)
        assert out == "claude_response"
        claude_mock.assert_called_once_with("p")

    def test_gemini_backend_uses_gemini(self, monkeypatch):
        monkeypatch.setenv("ANALYZER_BACKEND", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        claude_mock = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "gemini_response"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            out = call_analyzer("p", claude_caller=claude_mock)
        assert out == "gemini_response"
        claude_mock.assert_not_called()

    def test_gemini_failure_falls_back_to_claude(self, monkeypatch):
        monkeypatch.setenv("ANALYZER_BACKEND", "gemini")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        claude_mock = MagicMock(return_value="claude_fallback")
        out = call_analyzer("p", claude_caller=claude_mock)
        assert out == "claude_fallback"
        claude_mock.assert_called_once_with("p")

    def test_explicit_backend_override(self, monkeypatch):
        monkeypatch.setenv("ANALYZER_BACKEND", "gemini")
        claude_mock = MagicMock(return_value="claude")
        out = call_analyzer("p", claude_caller=claude_mock, backend="claude")
        assert out == "claude"
