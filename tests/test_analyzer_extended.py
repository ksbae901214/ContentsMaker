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

    def test_voice_text_preserved_when_no_split(self):
        """28자 이하 단일 씬은 voice_text 원본 보존 (분할 없음)."""
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="body",
                      text="22자 이하 짧은 텍스트 한 줄",
                      voice_text="원래 음성 텍스트는 그대로"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        # 단일 씬 — voice_text 원본 보존
        assert len(result.scenes) == 1
        assert result.scenes[0].voice_text == "원래 음성 텍스트는 그대로"

    def test_voice_text_per_segment_when_split(self):
        """42자 초과 씬은 자식들로 분할되고 각 자식이 자기 voice_text로 합성됨 (그룹 TTS)."""
        long_text = "회사에서 3년 동안 일했는데 월급이 200만원도 안 돼서 너무 화가 납니다 정말 억울합니다"
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="angry", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=6, type="body",
                      text=long_text, voice_text=long_text),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        result = _ensure_line_breaks(script)
        # 분할 — 2개 이상 자식
        assert len(result.scenes) >= 2
        # 모든 자식이 같은 group_id (TTS 1회 합성용)
        gids = {s.subtitle_group_id for s in result.scenes}
        assert len(gids) == 1 and None not in gids
        # 첫 자식만 group_first=True
        assert result.scenes[0].subtitle_group_first is True
        for s in result.scenes[1:]:
            assert s.subtitle_group_first is False
        # 각 자식의 voice_text가 자기 자막 텍스트
        for s in result.scenes:
            assert s.voice_text == s.text.replace("\n", " ").strip()

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
        # --output-format json → Claude CLI wraps response in type/subtype/result
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "type": "result",
                "subtype": "success",
                "result": json.dumps(sample_script_dict),
            }),
            stderr="",
        )
        result = _call_claude("test prompt")
        assert "metadata" in result or "테스트" in result

    @patch("src.analyzer.claude_analyzer.subprocess.run")
    def test_plain_json_response_accepted(self, mock_run, sample_script_dict):
        """Plain JSON (without Claude CLI wrapper) is accepted as-is for backward compat."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(sample_script_dict),
            stderr="",
        )
        result = _call_claude("test prompt")
        assert "metadata" in result

    @patch("src.analyzer.claude_analyzer.subprocess.run")
    @patch("src.analyzer.claude_analyzer.time.sleep")
    def test_error_during_execution_retries_with_backoff(self, mock_sleep, mock_run):
        """error_during_execution triggers retry with exponential backoff."""
        error_response = MagicMock(
            returncode=0,
            stdout='{"type":"result","subtype":"error_during_execution","result":""}',
            stderr="",
        )
        success_response = MagicMock(
            returncode=0,
            stdout='{"type":"result","subtype":"success","result":"{}"}',
            stderr="",
        )
        mock_run.side_effect = [error_response, error_response, success_response]
        result = _call_claude("test", max_attempts=5)
        assert result == "{}"
        assert mock_run.call_count == 3
        # Exponential backoff: 1s then 2s
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 2.0

    @patch("src.analyzer.claude_analyzer.subprocess.run")
    def test_max_attempts_default_at_least_8(self, mock_run):
        """Default max_attempts must be >= 8 for robustness."""
        import inspect
        sig = inspect.signature(_call_claude)
        default = sig.parameters["max_attempts"].default
        assert default >= 8

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
        script, file_path = analyze(sample_post, output_dir=tmp_data_dir / "scripts")
        assert isinstance(script, ShortsScript)
        assert script.metadata.title == "테스트 제목"
        # Voice config should be applied
        assert script.audio.voice == "ko-KR-SunHiNeural"
        # Script should be saved
        scripts = list((tmp_data_dir / "scripts").glob("*.json"))
        assert len(scripts) == 1

    @patch("src.analyzer.claude_analyzer._call_claude")
    def test_saved_script_is_loadable(self, mock_claude, sample_post, sample_script_dict, tmp_data_dir):
        mock_claude.return_value = json.dumps(sample_script_dict)
        script, file_path = analyze(sample_post, output_dir=tmp_data_dir / "scripts")
        scripts = list((tmp_data_dir / "scripts").glob("*.json"))
        loaded = ShortsScript.load(scripts[0])
        assert loaded.metadata.title == script.metadata.title
