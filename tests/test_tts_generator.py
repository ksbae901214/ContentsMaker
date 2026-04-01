"""Tests for TTS generator — generate_voice with mocked edge-tts."""
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from src.tts.edge_tts_generator import generate_voice, TTSError
from src.analyzer.script_models import ShortsScript, Metadata, AudioConfig, Scene


def _make_script(tts_text="테스트 음성 텍스트", voice="ko-KR-SunHiNeural"):
    return ShortsScript(
        metadata=Metadata(title="테스트", emotion_type="funny", duration=30),
        scenes=(
            Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다"),
        ),
        audio=AudioConfig(tts_script=tts_text, voice=voice, rate="+20%", pitch="+0Hz"),
    )


class TestGenerateVoice:
    @patch("src.tts.edge_tts_generator._generate_async")
    def test_success(self, mock_async, tmp_data_dir):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"fake mp3 content")

        mock_async.side_effect = fake_gen
        script = _make_script()
        result = generate_voice(script, output_dir=tmp_data_dir / "audio")
        assert result.exists()
        assert result.suffix == ".mp3"
        assert result.stat().st_size > 0

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_empty_output_raises(self, mock_async, tmp_data_dir):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"")

        mock_async.side_effect = fake_gen
        script = _make_script()
        with pytest.raises(TTSError, match="생성되지 않았습니다"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_exception_wrapped(self, mock_async, tmp_data_dir):
        async def fail(*a, **k):
            raise RuntimeError("edge-tts broken")

        mock_async.side_effect = fail
        script = _make_script()
        with pytest.raises(TTSError, match="TTS 생성 실패"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    def test_empty_tts_text_raises(self, tmp_data_dir):
        script = _make_script(tts_text="")
        with pytest.raises(TTSError, match="비어있습니다"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    def test_whitespace_tts_text_raises(self, tmp_data_dir):
        script = _make_script(tts_text="   \n  ")
        with pytest.raises(TTSError, match="비어있습니다"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_output_dir_created(self, mock_async, tmp_path):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"mp3")

        mock_async.side_effect = fake_gen
        script = _make_script()
        new_dir = tmp_path / "new" / "audio"
        assert not new_dir.exists()
        result = generate_voice(script, output_dir=new_dir)
        assert new_dir.exists()
        assert result.exists()

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_filename_contains_title(self, mock_async, tmp_data_dir):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"mp3")

        mock_async.side_effect = fake_gen
        script = _make_script()
        result = generate_voice(script, output_dir=tmp_data_dir / "audio")
        assert "mp3" in result.name
