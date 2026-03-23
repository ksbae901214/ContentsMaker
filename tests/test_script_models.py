"""Tests for ShortsScript data models."""
import json
import pytest
from src.analyzer.script_models import (
    Scene, Metadata, AudioConfig, BackgroundConfig, ShortsScript,
)


def _make_script() -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(title="테스트", emotion_type="funny", duration=45.0),
        scenes=(
            Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다"),
            Scene(id=2, timestamp=5, duration=35, type="body",
                  text="본문", voice_text="본문 내용입니다", emphasis="high"),
            Scene(id=3, timestamp=40, duration=5, type="comment",
                  text="ㅋㅋ", voice_text="ㅋㅋ"),
        ),
        audio=AudioConfig(
            tts_script="제목입니다. 본문 내용입니다. ㅋㅋ",
            voice="ko-KR-BongJinNeural",
            rate="+15%",
            pitch="+5Hz",
        ),
    )


class TestScene:
    def test_create(self):
        s = Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다")
        assert s.type == "title"
        assert s.emphasis == "medium"

    def test_frozen(self):
        s = Scene(id=1, timestamp=0, duration=5, type="title",
                  text="a", voice_text="a")
        with pytest.raises(AttributeError):
            s.text = "mutated"

    def test_roundtrip(self):
        original = Scene(id=1, timestamp=3.5, duration=10, type="body",
                         text="본문", voice_text="본문 TTS", emphasis="high")
        restored = Scene.from_dict(original.to_dict())
        assert restored == original


class TestMetadata:
    def test_create(self):
        m = Metadata(title="테스트", emotion_type="funny", duration=45)
        assert m.emotion_type == "funny"

    def test_from_dict_camel_case(self):
        m = Metadata.from_dict({"title": "t", "emotionType": "angry", "duration": 30})
        assert m.emotion_type == "angry"

    def test_defaults(self):
        m = Metadata.from_dict({"title": "t"})
        assert m.emotion_type == "relatable"
        assert m.duration == 45


class TestAudioConfig:
    def test_from_dict_camel_case(self):
        a = AudioConfig.from_dict({"ttsScript": "hello", "voice": "ko-KR-SunHiNeural"})
        assert a.tts_script == "hello"

    def test_defaults(self):
        a = AudioConfig.from_dict({})
        assert a.voice == "ko-KR-SunHiNeural"
        assert a.rate == "+0%"


class TestShortsScript:
    def test_create(self):
        script = _make_script()
        assert len(script.scenes) == 3
        assert script.metadata.emotion_type == "funny"

    def test_frozen(self):
        script = _make_script()
        with pytest.raises(AttributeError):
            script.metadata = None

    def test_to_json_korean(self):
        script = _make_script()
        json_str = script.to_json()
        assert "테스트" in json_str
        assert "본문" in json_str

    def test_roundtrip(self):
        original = _make_script()
        json_str = original.to_json()
        restored = ShortsScript.from_json(json_str)
        assert restored.metadata.title == original.metadata.title
        assert len(restored.scenes) == len(original.scenes)
        assert restored.audio.voice == original.audio.voice

    def test_save_and_load(self, tmp_path):
        script = _make_script()
        path = tmp_path / "test_script.json"
        script.save(path)
        loaded = ShortsScript.load(path)
        assert loaded.metadata.title == "테스트"
        assert len(loaded.scenes) == 3

    def test_background_defaults(self):
        script = _make_script()
        assert script.background.type == "gradient"
        assert len(script.background.colors) == 3
