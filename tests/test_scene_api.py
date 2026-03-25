"""Tests for scene editing API logic (script file read/write)."""
import json
import pytest
from pathlib import Path

from src.analyzer.script_models import ShortsScript, Metadata, Scene, AudioConfig


class TestScriptFileEdit:
    """Test the core logic used by /api/scene/script — JSON read/modify/write."""

    def _create_script_file(self, tmp_data_dir) -> Path:
        script = ShortsScript(
            metadata=Metadata(title="테스트", emotion_type="funny", duration=45),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="title",
                      text="원래 제목", voice_text="원래 제목입니다"),
                Scene(id=2, timestamp=5, duration=8, type="body",
                      text="원래 본문", voice_text="원래 본문입니다"),
            ),
            audio=AudioConfig(tts_script="원래 제목입니다 원래 본문입니다"),
        )
        path = tmp_data_dir / "scripts" / "test_script.json"
        script.save(path)
        return path

    def test_modify_scene_text(self, tmp_data_dir):
        path = self._create_script_file(tmp_data_dir)
        raw = json.loads(path.read_text())

        # Simulate what the API does
        updated_scenes = []
        for s in raw["scenes"]:
            if s["id"] == 1:
                updated_scenes.append({**s, "text": "수정된 제목", "voice_text": "수정된 제목입니다"})
            else:
                updated_scenes.append(s)

        tts = " ".join(s["voice_text"] for s in updated_scenes)
        updated = {**raw, "scenes": updated_scenes, "audio": {**raw["audio"], "tts_script": tts}}
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2))

        # Verify
        loaded = ShortsScript.load(path)
        assert loaded.scenes[0].text == "수정된 제목"
        assert loaded.scenes[0].voice_text == "수정된 제목입니다"
        assert loaded.scenes[1].text == "원래 본문"  # unchanged
        assert "수정된 제목입니다" in loaded.audio.tts_script

    def test_roundtrip_preserves_all_fields(self, tmp_data_dir):
        path = self._create_script_file(tmp_data_dir)
        original = ShortsScript.load(path)
        original.save(path)
        reloaded = ShortsScript.load(path)

        assert reloaded.metadata.title == original.metadata.title
        assert reloaded.metadata.emotion_type == original.metadata.emotion_type
        assert len(reloaded.scenes) == len(original.scenes)
        for a, b in zip(reloaded.scenes, original.scenes):
            assert a.id == b.id
            assert a.text == b.text
            assert a.voice_text == b.voice_text

    def test_modify_nonexistent_scene_no_change(self, tmp_data_dir):
        path = self._create_script_file(tmp_data_dir)
        raw = json.loads(path.read_text())

        updated_scenes = []
        for s in raw["scenes"]:
            if s["id"] == 999:  # doesn't exist
                updated_scenes.append({**s, "text": "should not appear"})
            else:
                updated_scenes.append(s)

        assert len(updated_scenes) == 2
        assert updated_scenes[0]["text"] == "원래 제목"


class TestSceneImageReplacement:
    """Test image path update logic used by scene editing."""

    def test_replace_existing_image(self):
        images = [
            {"scene_id": 1, "image_path": "/old/1.png", "prompt": "old"},
            {"scene_id": 2, "image_path": "/old/2.png", "prompt": "old"},
        ]
        new_image = {"scene_id": 1, "image_path": "/new/1.png", "prompt": "new prompt"}
        updated = [img for img in images if img["scene_id"] != 1]
        updated.append(new_image)

        assert len(updated) == 2
        scene1 = next(img for img in updated if img["scene_id"] == 1)
        assert scene1["image_path"] == "/new/1.png"
        assert scene1["prompt"] == "new prompt"

    def test_add_image_for_new_scene(self):
        images = [
            {"scene_id": 1, "image_path": "/old/1.png", "prompt": "old"},
        ]
        new_image = {"scene_id": 3, "image_path": "/new/3.png", "prompt": "new"}
        updated = [img for img in images if img["scene_id"] != 3]
        updated.append(new_image)

        assert len(updated) == 2
