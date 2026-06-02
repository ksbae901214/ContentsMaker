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


class TestSceneHookField:
    """QW-01: 첫 씬을 hook 으로 표시하기 위한 Scene.hook 필드."""

    def test_default_hook_is_false(self):
        """기본값은 False — 기존 코드 회귀 방지."""
        s = Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다")
        assert s.hook is False

    def test_create_with_hook_true(self):
        s = Scene(id=1, timestamp=0, duration=2, type="title",
                  text="후킹", voice_text="후킹 음성", hook=True)
        assert s.hook is True

    def test_hook_true_roundtrip(self):
        """hook=True 인 Scene은 to_dict/from_dict 라운드트립에서 보존."""
        original = Scene(id=1, timestamp=0, duration=2, type="title",
                         text="후킹", voice_text="짧게", hook=True)
        restored = Scene.from_dict(original.to_dict())
        assert restored.hook is True
        assert restored == original

    def test_hook_false_omitted_from_dict(self):
        """hook=False 면 to_dict 결과에 키가 없어야 한다 (기존 JSON 호환)."""
        s = Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다", hook=False)
        d = s.to_dict()
        assert "hook" not in d, (
            "hook=False는 키 생략 — 기존 JSON 파일과 호환"
        )

    def test_hook_true_appears_in_dict(self):
        s = Scene(id=1, timestamp=0, duration=2, type="title",
                  text="후킹", voice_text="짧게", hook=True)
        d = s.to_dict()
        assert d.get("hook") is True

    def test_legacy_json_without_hook_loads_as_false(self):
        """기존 JSON(hook 키 없음)은 hook=False 로 로드되어야 한다."""
        data = {
            "id": 1, "timestamp": 0, "duration": 5, "type": "title",
            "text": "제목", "voice_text": "제목입니다",
        }
        s = Scene.from_dict(data)
        assert s.hook is False


class TestSceneSubtitleGroup:
    """Phase 3 (2026-05-20): subtitle_group_id / subtitle_group_first 필드."""

    def test_defaults(self):
        """Default: group_id=None, group_first=True (독립 씬, 항상 fade-in)."""
        s = Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다")
        assert s.subtitle_group_id is None
        assert s.subtitle_group_first is True

    def test_group_roundtrip(self):
        """그룹 필드 to_dict/from_dict 보존."""
        original = Scene(id=1, timestamp=0, duration=2, type="body",
                         text="첫줄", voice_text="첫줄",
                         subtitle_group_id=5, subtitle_group_first=True)
        restored = Scene.from_dict(original.to_dict())
        assert restored.subtitle_group_id == 5
        assert restored.subtitle_group_first is True
        assert restored == original

    def test_group_continuation_roundtrip(self):
        """group_first=False (연속 씬) 라운드트립."""
        original = Scene(id=2, timestamp=2, duration=2, type="body",
                         text="둘째줄", voice_text="둘째줄",
                         subtitle_group_id=5, subtitle_group_first=False)
        restored = Scene.from_dict(original.to_dict())
        assert restored.subtitle_group_id == 5
        assert restored.subtitle_group_first is False

    def test_defaults_omitted_from_dict(self):
        """기본값(group_id=None, group_first=True)은 직렬화 시 생략 (V1·V2 JSON 호환)."""
        s = Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다")
        d = s.to_dict()
        assert "subtitle_group_id" not in d
        assert "subtitle_group_first" not in d

    def test_legacy_json_loads_with_defaults(self):
        """그룹 필드 없는 V1·V2 JSON → default (None / True) 로드."""
        data = {
            "id": 1, "timestamp": 0, "duration": 5, "type": "title",
            "text": "제목", "voice_text": "제목입니다",
            "subtitle_color": "yellow", "subtitle_emphasis": True,  # V2 필드만 있음
        }
        s = Scene.from_dict(data)
        assert s.subtitle_group_id is None
        assert s.subtitle_group_first is True
        # V2 필드도 그대로 로드
        assert s.subtitle_color == "yellow"
        assert s.subtitle_emphasis is True

    def test_camel_case_keys(self):
        """camelCase 키(subtitleGroupId / subtitleGroupFirst)도 인식."""
        data = {
            "id": 3, "timestamp": 0, "duration": 1, "type": "body",
            "text": "x", "voice_text": "x",
            "subtitleGroupId": 7, "subtitleGroupFirst": False,
        }
        s = Scene.from_dict(data)
        assert s.subtitle_group_id == 7
        assert s.subtitle_group_first is False


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

    def test_source_type_default_blind(self):
        """source_type 없는 기존 데이터 → 기본값 'blind' (역호환)"""
        m = Metadata.from_dict({"title": "t", "emotion_type": "funny", "duration": 30})
        assert m.source_type == "blind"

    def test_source_type_topic(self):
        """source_type='topic' 라운드트립"""
        m = Metadata(title="과자", emotion_type="funny", duration=40, source_type="topic")
        d = m.to_dict()
        assert d["source_type"] == "topic"
        restored = Metadata.from_dict(d)
        assert restored.source_type == "topic"

    def test_source_type_camel_case(self):
        """camelCase sourceType 지원"""
        m = Metadata.from_dict({"title": "t", "sourceType": "topic"})
        assert m.source_type == "topic"

    def test_source_type_in_script_roundtrip(self):
        """ShortsScript 전체 라운드트립에서 source_type 보존"""
        script = ShortsScript(
            metadata=Metadata(title="토픽", emotion_type="relatable", duration=45, source_type="topic"),
            scenes=(Scene(id=1, timestamp=0, duration=5, type="title", text="t", voice_text="t"),),
            audio=AudioConfig(tts_script="t"),
        )
        json_str = script.to_json()
        restored = ShortsScript.from_json(json_str)
        assert restored.metadata.source_type == "topic"


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
