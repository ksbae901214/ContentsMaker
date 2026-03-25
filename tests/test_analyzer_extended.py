"""Extended tests for Claude analyzer — _ensure_line_breaks and integration."""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.analyzer.claude_analyzer import (
    analyze, _ensure_line_breaks, _apply_voice_config, _call_claude,
    AnalyzerError,
)
from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig,
)
from src.scraper.models import BlindPost


class TestEnsureLineBreaks:
    def test_short_text_unchanged(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="title",
                      text="짧은 텍스트", voice_text="짧은 텍스트"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        assert result.scenes[0].text == "짧은 텍스트"

    def test_already_has_linebreaks_unchanged(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="title",
                      text="이미 줄바꿈이\n있는 텍스트입니다", voice_text="t"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        assert "\n" in result.scenes[0].text

    def test_long_text_gets_breaks(self):
        long_text = "회사에서 3년 동안 일했는데 월급이 200만원도 안 돼서 너무 화가 납니다"
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="angry", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="body",
                      text=long_text, voice_text=long_text),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        assert "\n" in result.scenes[0].text
        lines = result.scenes[0].text.split("\n")
        for line in lines:
            assert len(line) <= 20  # roughly 15 chars boundary

    def test_voice_text_preserved(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="body",
                      text="아주 긴 텍스트가 여기에 들어가서 줄바꿈이 필요합니다",
                      voice_text="원래 음성 텍스트는 그대로"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        assert result.scenes[0].voice_text == "원래 음성 텍스트는 그대로"

    def test_multiple_scenes(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="title", text="짧은", voice_text="t"),
                Scene(id=2, timestamp=5, duration=8, type="body",
                      text="이것은 줄바꿈이 필요한 아주 긴 텍스트입니다 정말로",
                      voice_text="t"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        assert len(result.scenes) == 2
        assert result.scenes[0].text == "짧은"
        assert "\n" in result.scenes[1].text


class TestCallClaude:
    @patch("src.analyzer.claude_analyzer.subprocess.run")
    def test_success(self, mock_run, sample_script_dict):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(sample_script_dict),
            stderr="",
        )
        result = _call_claude("test prompt")
        assert "metadata" in result or "테스트" in result

    @patch("src.analyzer.claude_analyzer.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_claude_raises(self, _):
        with pytest.raises(AnalyzerError, match="설치되지 않았습니다"):
            _call_claude("test prompt")

    @patch("src.analyzer.claude_analyzer.subprocess.run")
    def test_nonzero_exit_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error", stdout="")
        with pytest.raises(AnalyzerError, match="실행 실패"):
            _call_claude("test prompt")


class TestAnalyzeIntegration:
    @patch("src.analyzer.claude_analyzer._call_claude")
    def test_full_pipeline(self, mock_claude, sample_post, sample_script_dict, tmp_data_dir):
        mock_claude.return_value = json.dumps(sample_script_dict)
        result = analyze(sample_post, output_dir=tmp_data_dir / "scripts")
        assert isinstance(result, ShortsScript)
        assert result.metadata.title == "테스트 제목"
        # Voice config should be applied
        assert result.audio.voice == "ko-KR-SunHiNeural"
        # Script should be saved
        scripts = list((tmp_data_dir / "scripts").glob("*.json"))
        assert len(scripts) == 1

    @patch("src.analyzer.claude_analyzer._call_claude")
    def test_saved_script_is_loadable(self, mock_claude, sample_post, sample_script_dict, tmp_data_dir):
        mock_claude.return_value = json.dumps(sample_script_dict)
        result = analyze(sample_post, output_dir=tmp_data_dir / "scripts")
        scripts = list((tmp_data_dir / "scripts").glob("*.json"))
        loaded = ShortsScript.load(scripts[0])
        assert loaded.metadata.title == result.metadata.title
