"""Tests for scene_delete — immutable scene removal operation."""
from __future__ import annotations

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.editor.scene_ops import SceneOpsError, scene_delete


def _make_script(scenes: list[Scene]) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title="test",
            emotion_type="funny",
            duration=sum(s.duration for s in scenes),
            source_type="blind",
        ),
        scenes=tuple(scenes),
        audio=AudioConfig(
            tts_script=" ".join(s.voice_text for s in scenes),
            voice="ko-KR-SunHiNeural",
            rate="+20%",
            pitch="+0Hz",
        ),
        background=BackgroundConfig(type="gradient", colors=("#000", "#fff")),
    )


def _make_scene(scene_id: int, timestamp: float, duration: float, text: str, voice: str) -> Scene:
    return Scene(
        id=scene_id,
        timestamp=timestamp,
        duration=duration,
        type="body",
        text=text,
        voice_text=voice,
        emphasis="medium",
        highlight_words=(),
    )


class TestSceneDelete:
    def test_delete_middle_scene_renumbers(self):
        """Deleting scene 2 of 3 renumbers remaining scenes to 1, 2."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "씬A 텍스트", "씬A"),
            _make_scene(2, 3.0, 4.0, "씬B 텍스트", "씬B"),
            _make_scene(3, 7.0, 5.0, "씬C 텍스트", "씬C"),
        ]
        result = scene_delete(_make_script(scenes), scene_id=2)

        assert len(result.scenes) == 2
        assert result.scenes[0].id == 1
        assert result.scenes[0].text == "씬A 텍스트"
        assert result.scenes[1].id == 2
        assert result.scenes[1].text == "씬C 텍스트"

    def test_delete_recalculates_timestamps(self):
        """After deletion, timestamps are contiguous."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "씬A 텍스트", "씬A"),
            _make_scene(2, 3.0, 4.0, "씬B 텍스트", "씬B"),
            _make_scene(3, 7.0, 5.0, "씬C 텍스트", "씬C"),
        ]
        result = scene_delete(_make_script(scenes), scene_id=2)

        assert result.scenes[0].timestamp == 0.0
        assert result.scenes[1].timestamp == 3.0  # directly after scene 1

    def test_delete_updates_tts_script(self):
        """TTS script excludes the deleted scene's voice_text."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "씬A 텍스트", "씬A 음성"),
            _make_scene(2, 3.0, 4.0, "씬B 텍스트", "씬B 음성"),
            _make_scene(3, 7.0, 5.0, "씬C 텍스트", "씬C 음성"),
        ]
        result = scene_delete(_make_script(scenes), scene_id=2)

        assert "씬B 음성" not in result.audio.tts_script
        assert "씬A 음성" in result.audio.tts_script
        assert "씬C 음성" in result.audio.tts_script

    def test_delete_first_scene(self):
        """Deleting the first scene works correctly."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "첫째 텍스트", "첫째"),
            _make_scene(2, 3.0, 4.0, "둘째 텍스트", "둘째"),
        ]
        result = scene_delete(_make_script(scenes), scene_id=1)

        assert len(result.scenes) == 1
        assert result.scenes[0].id == 1
        assert result.scenes[0].text == "둘째 텍스트"
        assert result.scenes[0].timestamp == 0.0

    def test_delete_last_scene(self):
        """Deleting the last scene works correctly."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "첫째 텍스트", "첫째"),
            _make_scene(2, 3.0, 4.0, "둘째 텍스트", "둘째"),
        ]
        result = scene_delete(_make_script(scenes), scene_id=2)

        assert len(result.scenes) == 1
        assert result.scenes[0].id == 1
        assert result.scenes[0].text == "첫째 텍스트"

    def test_delete_only_scene_raises(self):
        """Deleting the only scene raises SceneOpsError."""
        scenes = [_make_scene(1, 0.0, 5.0, "유일한 씬", "유일한 씬입니다")]
        with pytest.raises(SceneOpsError, match="마지막 씬"):
            scene_delete(_make_script(scenes), scene_id=1)

    def test_delete_nonexistent_scene_raises(self):
        """Deleting a scene with a nonexistent ID raises SceneOpsError."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "씬A 텍스트", "씬A"),
            _make_scene(2, 3.0, 4.0, "씬B 텍스트", "씬B"),
        ]
        with pytest.raises(SceneOpsError, match="찾을 수 없습니다"):
            scene_delete(_make_script(scenes), scene_id=99)

    def test_delete_does_not_mutate_original(self):
        """scene_delete is immutable — original script is unchanged."""
        scenes = [
            _make_scene(1, 0.0, 3.0, "씬A 텍스트", "씬A"),
            _make_scene(2, 3.0, 4.0, "씬B 텍스트", "씬B"),
        ]
        original = _make_script(scenes)
        scene_delete(original, scene_id=1)

        assert len(original.scenes) == 2
