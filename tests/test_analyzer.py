"""Tests for Claude Analyzer module."""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.analyzer.claude_analyzer import _parse_response, _apply_voice_config, AnalyzerError
from src.analyzer.prompt_template import build_prompt
from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)


class TestBuildPrompt:
    def test_basic_prompt(self):
        prompt = build_prompt(
            title="테스트 제목",
            author="회사 · 닉네임",
            body="본문 내용입니다",
            comments=[{"text": "댓글", "likes": 5, "author": "작성자"}],
        )
        assert "테스트 제목" in prompt
        assert "본문 내용입니다" in prompt
        assert "댓글" in prompt

    def test_no_comments(self):
        prompt = build_prompt("제목", "작성자", "본문", [])
        assert "(댓글 없음)" in prompt

    def test_personal_info_instruction(self):
        prompt = build_prompt("제목", "작성자", "본문", [])
        assert "개인정보 제거" in prompt or "마스킹" in prompt


class TestParseResponse:
    def _make_valid_json(self) -> str:
        return json.dumps({
            "metadata": {"title": "테스트", "emotion_type": "funny", "duration": 45},
            "scenes": [
                {"id": 1, "timestamp": 0, "duration": 5, "type": "title",
                 "text": "제목", "voice_text": "제목입니다"},
            ],
            "audio": {"tts_script": "제목입니다", "voice": "", "rate": "", "pitch": ""},
            "background": {"type": "gradient", "colors": []},
        }, ensure_ascii=False)

    def test_direct_json(self):
        script = _parse_response(self._make_valid_json())
        assert script.metadata.title == "테스트"

    def test_json_in_code_block(self):
        raw = f"Here is the result:\n```json\n{self._make_valid_json()}\n```\nDone."
        script = _parse_response(raw)
        assert script.metadata.title == "테스트"

    def test_json_in_text(self):
        raw = f"Analysis complete. {self._make_valid_json()} End of response."
        script = _parse_response(raw)
        assert script.metadata.title == "테스트"

    def test_claude_output_wrapper(self):
        wrapped = json.dumps({"result": self._make_valid_json()})
        script = _parse_response(wrapped)
        assert script.metadata.title == "테스트"

    def test_invalid_json(self):
        with pytest.raises(AnalyzerError, match="파싱할 수 없습니다"):
            _parse_response("This is not JSON at all")

    def test_empty_response(self):
        with pytest.raises(AnalyzerError):
            _parse_response("")


class TestApplyVoiceConfig:
    def test_funny(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=45),
            scenes=(),
            audio=AudioConfig(tts_script="text"),
        )
        result = _apply_voice_config(script)
        assert result.audio.voice == "ko-KR-SunHiNeural"
        assert result.audio.rate == "+25%"
        assert result.background.colors == ("#FF6B6B", "#FFA500", "#FFD93D")

    def test_touching(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="touching", duration=45),
            scenes=(),
            audio=AudioConfig(tts_script="text"),
        )
        result = _apply_voice_config(script)
        assert result.audio.voice == "ko-KR-SunHiNeural"
        assert result.audio.rate == "+10%"
        assert result.background.colors == ("#6A5ACD", "#9370DB", "#DDA0DD")

    def test_unknown_emotion_defaults_to_relatable(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="unknown", duration=45),
            scenes=(),
            audio=AudioConfig(tts_script="text"),
        )
        result = _apply_voice_config(script)
        assert result.audio.voice == "ko-KR-SunHiNeural"
        assert result.audio.rate == "+20%"
