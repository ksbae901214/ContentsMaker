"""Tests for edge-tts generator module."""
import pytest
from src.tts.voice_config import (
    get_voice_config, get_gradient, get_bgm_file, get_highlight_color,
    VOICE_CONFIG, GRADIENT_THEMES, BGM_FILES, HIGHLIGHT_COLORS, DEFAULT_EMOTION,
)
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
        assert config["voice"] == "ko-KR-SunHiNeural"
        assert config["rate"] == "+20%"

    def test_touching_voice(self):
        config = get_voice_config("touching")
        assert config["voice"] == "ko-KR-SunHiNeural"
        assert config["rate"] == "+20%"

    def test_angry_voice(self):
        config = get_voice_config("angry")
        assert config["voice"] == "ko-KR-SunHiNeural"

    def test_relatable_voice(self):
        config = get_voice_config("relatable")
        assert config["voice"] == "ko-KR-SunHiNeural"

    def test_unknown_defaults_to_relatable(self):
        config = get_voice_config("unknown_emotion")
        assert config == VOICE_CONFIG["relatable"]

    def test_all_emotions_have_gradient(self):
        for emotion in ["funny", "touching", "angry", "relatable"]:
            colors = get_gradient(emotion)
            assert len(colors) == 3
            assert all(c.startswith("#") for c in colors)

    def test_gradients_differ_per_emotion(self):
        gradients = {tuple(get_gradient(e)) for e in GRADIENT_THEMES}
        assert len(gradients) == 4  # each emotion has distinct gradient


class TestBGMConfig:
    def test_all_emotions_have_bgm(self):
        for emotion in ["funny", "touching", "angry", "relatable"]:
            bgm = get_bgm_file(emotion)
            assert bgm.endswith(".mp3")

    def test_unknown_emotion_defaults(self):
        bgm = get_bgm_file("unknown")
        assert bgm == BGM_FILES[DEFAULT_EMOTION]

    def test_each_emotion_has_unique_bgm(self):
        files = {get_bgm_file(e) for e in BGM_FILES}
        assert len(files) == 4


class TestHighlightColors:
    def test_all_emotions_have_color(self):
        for emotion in ["funny", "touching", "angry", "relatable"]:
            color = get_highlight_color(emotion)
            assert color.startswith("#")

    def test_unknown_emotion_defaults(self):
        color = get_highlight_color("unknown")
        assert color == HIGHLIGHT_COLORS[DEFAULT_EMOTION]


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
