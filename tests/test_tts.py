"""Tests for edge-tts generator module."""
import pytest
from src.tts.voice_config import get_voice_config, get_gradient, VOICE_CONFIG
from src.tts.edge_tts_generator import TTSError
from src.analyzer.script_models import (
    ShortsScript, Metadata, AudioConfig, Scene,
)


class TestVoiceConfig:
    def test_all_emotions_have_config(self):
        for emotion in ["funny", "touching", "angry", "relatable"]:
            config = get_voice_config(emotion)
            assert "voice" in config
            assert "rate" in config
            assert "pitch" in config

    def test_funny_voice(self):
        config = get_voice_config("funny")
        assert config["voice"] == "ko-KR-HyunsuNeural"
        assert "+" in config["rate"]

    def test_touching_voice(self):
        config = get_voice_config("touching")
        assert config["voice"] == "ko-KR-SunHiNeural"
        assert "-" in config["rate"]

    def test_unknown_defaults_to_relatable(self):
        config = get_voice_config("unknown_emotion")
        assert config == VOICE_CONFIG["relatable"]

    def test_all_emotions_have_gradient(self):
        for emotion in ["funny", "touching", "angry", "relatable"]:
            colors = get_gradient(emotion)
            assert len(colors) == 3
            assert all(c.startswith("#") for c in colors)

    def test_different_voices_per_emotion(self):
        voices = {get_voice_config(e)["voice"] for e in VOICE_CONFIG}
        assert len(voices) >= 3  # at least 3 distinct voices


class TestTTSErrorHandling:
    def test_empty_script_raises(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(),
            audio=AudioConfig(tts_script="", voice="ko-KR-SunHiNeural"),
        )
        from src.tts.edge_tts_generator import generate_voice
        with pytest.raises(TTSError, match="비어있습니다"):
            generate_voice(script)

    def test_whitespace_script_raises(self):
        script = ShortsScript(
            metadata=Metadata(title="t", emotion_type="funny", duration=30),
            scenes=(),
            audio=AudioConfig(tts_script="   ", voice="ko-KR-SunHiNeural"),
        )
        from src.tts.edge_tts_generator import generate_voice
        with pytest.raises(TTSError, match="비어있습니다"):
            generate_voice(script)
