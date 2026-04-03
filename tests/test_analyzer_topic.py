"""Tests for analyze_topic in Claude Analyzer (T008).

TDD RED phase: these tests define the expected behavior of
analyze_topic before implementation exists.
"""
import json
from pathlib import Path

import pytest

from src.analyzer.claude_analyzer import analyze_topic
from src.analyzer.script_models import ShortsScript
from src.scraper.topic_input import TopicInput


MOCK_TOPIC_RESPONSE = json.dumps({
    "metadata": {
        "title": "과자의 배신",
        "emotion_type": "funny",
        "duration": 40,
        "source_type": "topic",
    },
    "scenes": [
        {
            "id": 1,
            "timestamp": 0,
            "duration": 5,
            "type": "title",
            "text": "과자의 배신",
            "voice_text": "과자의 배신",
            "emphasis": "high",
            "highlight_words": ["배신"],
        },
        {
            "id": 2,
            "timestamp": 5,
            "duration": 30,
            "type": "body",
            "text": "어릴 때 먹던\n과자들이",
            "voice_text": "어릴 때 먹던 과자들이, 지금은 완전히 달라졌어요...",
            "emphasis": "medium",
            "highlight_words": ["과자"],
        },
    ],
    "audio": {
        "tts_script": "과자의 배신. 어릴 때 먹던 과자들이...",
        "voice": "",
        "rate": "",
        "pitch": "",
    },
    "background": {
        "type": "gradient",
        "colors": [],
    },
}, ensure_ascii=False)


class TestAnalyzeTopic:
    def test_analyze_topic_returns_script(self, mocker, tmp_path):
        mocker.patch(
            "src.analyzer.claude_analyzer._call_claude",
            return_value=MOCK_TOPIC_RESPONSE,
        )
        topic_input = TopicInput(topic="과자의 배신 이야기", style="narration")
        script, path = analyze_topic(topic_input, output_dir=tmp_path)

        assert isinstance(script, ShortsScript)
        assert isinstance(path, Path)
        assert script.metadata.source_type == "topic"

    def test_analyze_topic_applies_voice_config(self, mocker, tmp_path):
        mocker.patch(
            "src.analyzer.claude_analyzer._call_claude",
            return_value=MOCK_TOPIC_RESPONSE,
        )
        topic_input = TopicInput(topic="과자의 배신 이야기", style="narration")
        script, _ = analyze_topic(topic_input, output_dir=tmp_path)

        assert script.audio.voice != ""
        assert len(script.background.colors) > 0

    def test_analyze_topic_saves_file(self, mocker, tmp_path):
        mocker.patch(
            "src.analyzer.claude_analyzer._call_claude",
            return_value=MOCK_TOPIC_RESPONSE,
        )
        topic_input = TopicInput(topic="과자의 배신 이야기", style="narration")
        _, path = analyze_topic(topic_input, output_dir=tmp_path)

        assert path.exists()
        assert path.suffix == ".json"

        saved_data = json.loads(path.read_text(encoding="utf-8"))
        assert saved_data["metadata"]["title"] == "과자의 배신"
