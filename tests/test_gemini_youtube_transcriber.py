"""Phase 1A: Gemini 멀티모달 transcript 추출 테스트."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.scraper.gemini_youtube_transcriber import (
    GeminiTranscribeError,
    _parse_response,
    gemini_transcribe_video,
)


class TestParseResponse:
    def test_clean_json_array(self):
        text = '[{"start": 0.0, "end": 1.5, "text": "안녕"}]'
        out = _parse_response(text)
        assert out == [{"start": 0.0, "end": 1.5, "text": "안녕"}]

    def test_with_code_fence(self):
        text = '```json\n[{"start": 0, "end": 2, "text": "hi"}]\n```'
        out = _parse_response(text)
        assert len(out) == 1
        assert out[0]["text"] == "hi"

    def test_with_leading_explanation(self):
        text = '다음과 같습니다: [{"start": 0, "end": 1, "text": "a"}]'
        out = _parse_response(text)
        assert len(out) == 1

    def test_invalid_json_raises(self):
        with pytest.raises(GeminiTranscribeError):
            _parse_response("not json at all")

    def test_filters_empty_text(self):
        text = json.dumps([
            {"start": 0, "end": 1, "text": "  "},
            {"start": 1, "end": 2, "text": "안녕"},
        ])
        out = _parse_response(text)
        assert out == [{"start": 1.0, "end": 2.0, "text": "안녕"}]

    def test_filters_invalid_timing(self):
        text = json.dumps([
            {"start": 5, "end": 3, "text": "역순"},
            {"start": 0, "end": 1, "text": "정상"},
        ])
        out = _parse_response(text)
        assert len(out) == 1
        assert out[0]["text"] == "정상"

    def test_coerces_types(self):
        text = json.dumps([{"start": "0.5", "end": "1.2", "text": "ok"}])
        out = _parse_response(text)
        assert out[0]["start"] == 0.5


class TestGeminiTranscribeVideo:
    def test_missing_api_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        video = tmp_path / "v.mp4"
        video.write_bytes(b"x")
        with pytest.raises(GeminiTranscribeError, match="GEMINI_API_KEY"):
            gemini_transcribe_video(video)

    def test_missing_video_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        with pytest.raises(GeminiTranscribeError, match="영상 파일 없음"):
            gemini_transcribe_video(tmp_path / "nope.mp4")

    def test_oversize_video_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        from src.scraper import gemini_youtube_transcriber as mod
        monkeypatch.setattr(mod, "MAX_VIDEO_BYTES", 10)
        video = tmp_path / "v.mp4"
        video.write_bytes(b"x" * 100)
        with pytest.raises(GeminiTranscribeError, match="너무 큽니다"):
            gemini_transcribe_video(video)

    def test_successful_call(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        video = tmp_path / "v.mp4"
        video.write_bytes(b"x" * 100)

        mock_uploaded = MagicMock()
        mock_uploaded.state.name = "ACTIVE"
        mock_uploaded.name = "files/test"

        mock_response = MagicMock()
        mock_response.text = '[{"start": 0, "end": 2, "text": "테스트"}]'

        mock_client = MagicMock()
        mock_client.files.upload.return_value = mock_uploaded
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            result = gemini_transcribe_video(video)

        assert len(result) == 1
        assert result[0]["text"] == "테스트"
        mock_client.files.delete.assert_called_once()

    def test_empty_response_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        video = tmp_path / "v.mp4"
        video.write_bytes(b"x" * 100)

        mock_uploaded = MagicMock()
        mock_uploaded.state.name = "ACTIVE"
        mock_uploaded.name = "files/test"

        mock_response = MagicMock()
        mock_response.text = ""

        mock_client = MagicMock()
        mock_client.files.upload.return_value = mock_uploaded
        mock_client.models.generate_content.return_value = mock_response

        with patch("google.genai.Client", return_value=mock_client):
            with pytest.raises(GeminiTranscribeError, match="빈 응답"):
                gemini_transcribe_video(video)
