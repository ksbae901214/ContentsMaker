"""Tests for political commentary prompt template."""
import pytest

from src.analyzer.prompt_template import build_political_prompt


class TestBuildPoliticalPrompt:
    def test_basic_output(self):
        transcript = [
            {"start": 0.0, "end": 3.5, "text": "존경하는 국민 여러분"},
            {"start": 3.5, "end": 7.0, "text": "경제 위기를 극복해야 합니다"},
        ]
        result = build_political_prompt(
            youtube_url="https://youtube.com/watch?v=test",
            transcript=transcript,
            clip_start=0,
            clip_end=60,
        )
        assert "youtube.com/watch?v=test" in result
        assert "존경하는 국민 여러분" in result
        assert "0.0s-3.5s" in result

    def test_includes_cross_edit_rules(self):
        result = build_political_prompt(
            youtube_url="https://youtube.com/watch?v=test",
            transcript=[],
            clip_start=0,
            clip_end=60,
        )
        assert "교차 편집" in result
        assert "clip" in result
        assert "commentary" in result
        assert "voice_text" in result

    def test_empty_transcript(self):
        result = build_political_prompt(
            youtube_url="https://youtube.com/watch?v=test",
            transcript=[],
            clip_start=0,
            clip_end=60,
        )
        assert "자막 없음" in result

    def test_tone_and_details(self):
        result = build_political_prompt(
            youtube_url="https://youtube.com/watch?v=test",
            transcript=[{"start": 0, "end": 3, "text": "test"}],
            clip_start=10,
            clip_end=50,
            tone="날카롭게",
            details="경제 정책에 집중",
        )
        assert "날카롭게" in result
        assert "경제 정책에 집중" in result
        assert "10" in result
        assert "50" in result

    def test_source_type_political(self):
        result = build_political_prompt(
            youtube_url="https://youtube.com/watch?v=test",
            transcript=[],
            clip_start=0,
            clip_end=60,
        )
        assert '"source_type": "political"' in result

    def test_clip_scene_voice_text_empty(self):
        result = build_political_prompt(
            youtube_url="https://youtube.com/watch?v=test",
            transcript=[],
            clip_start=0,
            clip_end=60,
        )
        # Clip scenes should have empty voice_text
        assert '"voice_text": ""' in result
