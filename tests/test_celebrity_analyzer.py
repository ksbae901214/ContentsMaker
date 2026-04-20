"""Tests for analyze_celebrity (Phase 9-3).

Claude subprocess is mocked so tests run offline.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.analyzer.celebrity_analyzer import analyze_celebrity
from src.scraper.celebrity_models import CelebrityInfo


VALID_CLAUDE_RESPONSE = json.dumps({
    "metadata": {
        "title": "손흥민",
        "emotion_type": "touching",
        "duration": 35,
        "source_url": "",           # intentionally empty — analyzer must override
        "source_type": "blind",      # intentionally wrong — analyzer must override
    },
    "scenes": [
        {
            "id": 1, "timestamp": 0, "duration": 4, "type": "title",
            "text": "손흥민\n한국 축구의 자존심",
            "voice_text": "손흥민, 한국 축구의 자존심이죠.",
            "emphasis": "high", "highlight_words": ["손흥민"],
        },
        {
            "id": 2, "timestamp": 4, "duration": 4, "type": "body",
            "text": "토트넘에서\n뛰고 있습니다",
            "voice_text": "토트넘 홋스퍼에서 뛰고 있습니다.",
            "emphasis": "medium", "highlight_words": ["토트넘"],
        },
        {
            "id": 3, "timestamp": 8, "duration": 4, "type": "comment",
            "text": "출처: 나무위키",
            "voice_text": "출처는 나무위키.",
            "emphasis": "low", "highlight_words": ["나무위키"],
        },
    ],
    "audio": {"tts_script": "...", "voice": "", "rate": "", "pitch": ""},
    "background": {"type": "gradient", "colors": []},
})


def _sample_info() -> CelebrityInfo:
    return CelebrityInfo(
        name="손흥민",
        summary="대한민국의 축구 선수",
        profession="축구 선수",
        career_highlights=("토트넘 이적",),
        source_url="https://namu.wiki/w/손흥민",
    )


class TestAnalyzeCelebrity:
    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_returns_script_and_path(self, mock_claude, tmp_path):
        mock_claude.return_value = VALID_CLAUDE_RESPONSE
        script, path = analyze_celebrity(_sample_info(), output_dir=tmp_path)

        assert script.metadata.title == "손흥민"
        assert path.exists()
        assert path.parent == tmp_path
        assert "celebrity" in path.name

    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_forces_source_type_celebrity(self, mock_claude, tmp_path):
        """Analyzer must override source_type regardless of Claude output."""
        mock_claude.return_value = VALID_CLAUDE_RESPONSE
        script, _ = analyze_celebrity(_sample_info(), output_dir=tmp_path)
        assert script.metadata.source_type == "celebrity"

    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_forces_source_url_to_namuwiki(self, mock_claude, tmp_path):
        mock_claude.return_value = VALID_CLAUDE_RESPONSE
        script, _ = analyze_celebrity(_sample_info(), output_dir=tmp_path)
        assert script.metadata.source_url == "https://namu.wiki/w/손흥민"

    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_applies_voice_config(self, mock_claude, tmp_path):
        mock_claude.return_value = VALID_CLAUDE_RESPONSE
        script, _ = analyze_celebrity(_sample_info(), output_dir=tmp_path)
        # Voice config applied: voice/rate/pitch should be non-empty
        assert script.audio.voice
        assert script.audio.rate

    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_saves_file_with_celebrity_prefix(self, mock_claude, tmp_path):
        mock_claude.return_value = VALID_CLAUDE_RESPONSE
        _, path = analyze_celebrity(_sample_info(), output_dir=tmp_path)
        assert path.name.endswith(".json")
        assert "celebrity" in path.name
        assert "손흥민" in path.name

    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_scenes_preserved(self, mock_claude, tmp_path):
        mock_claude.return_value = VALID_CLAUDE_RESPONSE
        script, _ = analyze_celebrity(_sample_info(), output_dir=tmp_path)
        assert len(script.scenes) == 3
        assert script.scenes[0].type == "title"
        assert script.scenes[-1].type == "comment"

    @patch("src.analyzer.celebrity_analyzer._call_claude")
    def test_invalid_claude_response_raises(self, mock_claude, tmp_path):
        from src.analyzer.claude_analyzer import AnalyzerError

        mock_claude.return_value = "not valid json at all"
        with pytest.raises(AnalyzerError):
            analyze_celebrity(_sample_info(), output_dir=tmp_path)
