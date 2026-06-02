"""Phase 3+4 스모크 테스트 — 다중 화자, NotebookLM, 팩트체크."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.notebooklm_style import (
    NotebookLMStyleError,
    synthesize_from_sources,
)
from src.analyzer.political_fact_checker import (
    FactCheckError,
    FactCheckResult,
    extract_claims,
    verify_claim,
)
from src.tts.gemini_multi_voice import (
    MultiVoiceError,
    get_speaker,
)


class TestMultiVoice:
    def test_default_speaker_is_anchor(self):
        scene = SimpleNamespace(id=1, voice_text="hi")
        assert get_speaker(scene) == "anchor"

    def test_explicit_reporter(self):
        scene = SimpleNamespace(id=1, voice_text="hi", speaker="reporter")
        assert get_speaker(scene) == "reporter"

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from src.tts.gemini_multi_voice import generate_multi_voice_with_timing
        script = MagicMock()
        script.scenes = []
        with pytest.raises(MultiVoiceError, match="GEMINI_API_KEY"):
            generate_multi_voice_with_timing(script)


class TestNotebookLM:
    def test_empty_sources_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        with pytest.raises(NotebookLMStyleError, match="자료가 비어"):
            synthesize_from_sources([])

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(NotebookLMStyleError, match="GEMINI_API_KEY"):
            synthesize_from_sources(["test source"])

    def test_successful_call(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        mock_response = MagicMock()
        mock_response.text = '{"title": "테스트", "scenes": [{"id": 1, "speaker": "anchor", "text": "안녕", "duration": 3.0}]}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            data = synthesize_from_sources(["자료 1 내용"])
        assert data["title"] == "테스트"
        assert len(data["scenes"]) == 1

    def test_missing_scenes_key_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        mock_response = MagicMock()
        mock_response.text = '{"title": "x"}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            with pytest.raises(NotebookLMStyleError, match="scenes 키"):
                synthesize_from_sources(["x"])


class TestFactChecker:
    def test_result_badge_verified(self):
        r = FactCheckResult(
            claim="x", verdict="verified", confidence=0.9,
            sources=(), summary="ok",
        )
        assert r.badge == "🟢"

    def test_result_badge_partial(self):
        r = FactCheckResult(
            claim="x", verdict="partial", confidence=0.5,
            sources=(), summary="",
        )
        assert r.badge == "🟡"

    def test_result_badge_unverified(self):
        r = FactCheckResult(
            claim="x", verdict="unverified", confidence=0.0,
            sources=(), summary="",
        )
        assert r.badge == "🔴"

    def test_extract_claims_missing_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(FactCheckError, match="GEMINI_API_KEY"):
            extract_claims("transcript text")

    def test_verify_claim_missing_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(FactCheckError, match="GEMINI_API_KEY"):
            verify_claim("주장")

    def test_extract_claims_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        mock_response = MagicMock()
        mock_response.text = '["주장1", "주장2"]'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            claims = extract_claims("transcript here")
        assert claims == ["주장1", "주장2"]

    def test_verify_claim_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        mock_response = MagicMock()
        mock_response.text = '{"verdict": "verified", "confidence": 0.85, "summary": "확인됨"}'
        mock_response.candidates = []
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            r = verify_claim("테스트 주장")
        assert r.verdict == "verified"
        assert r.confidence == 0.85
        assert r.badge == "🟢"
