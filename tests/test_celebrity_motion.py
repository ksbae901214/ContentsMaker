"""Tests for celebrity motion prompt builder (Phase 9-4)."""
from __future__ import annotations

from src.analyzer.script_models import Scene
from src.video_gen.celebrity_motion import (
    CELEBRITY_IDENTITY_GUARD,
    GENTLE_PORTRAIT_CAMERA,
    STATIC_PORTRAIT_CAMERA,
    build_celebrity_motion_prompt,
)
from src.video_gen.motion_prompt_builder import MOTION_GUARD


def _scene(type_: str = "body", emphasis: str = "medium", motion_prompt=None) -> Scene:
    return Scene(
        id=1,
        timestamp=0.0,
        duration=4.0,
        type=type_,
        text="테스트",
        voice_text="테스트 음성",
        emphasis=emphasis,
        motion_prompt=motion_prompt,
    )


class TestBuildCelebrityMotionPrompt:
    def test_title_scene_uses_static_camera(self):
        prompt = build_celebrity_motion_prompt(_scene(type_="title"), "손흥민")
        assert STATIC_PORTRAIT_CAMERA in prompt
        assert GENTLE_PORTRAIT_CAMERA not in prompt

    def test_body_scene_uses_gentle_camera(self):
        prompt = build_celebrity_motion_prompt(_scene(type_="body"), "손흥민")
        assert GENTLE_PORTRAIT_CAMERA in prompt
        assert STATIC_PORTRAIT_CAMERA not in prompt

    def test_comment_scene_uses_gentle_camera(self):
        prompt = build_celebrity_motion_prompt(_scene(type_="comment"), "손흥민")
        assert GENTLE_PORTRAIT_CAMERA in prompt

    def test_includes_identity_guard(self):
        prompt = build_celebrity_motion_prompt(_scene(), "손흥민")
        assert CELEBRITY_IDENTITY_GUARD in prompt

    def test_includes_universal_motion_guard(self):
        prompt = build_celebrity_motion_prompt(_scene(), "손흥민")
        assert MOTION_GUARD in prompt

    def test_includes_person_name(self):
        prompt = build_celebrity_motion_prompt(_scene(), "손흥민")
        assert "손흥민" in prompt

    def test_missing_name_omitted_gracefully(self):
        prompt = build_celebrity_motion_prompt(_scene(), "")
        # Should still produce a valid prompt without the subject hint
        assert CELEBRITY_IDENTITY_GUARD in prompt
        assert "The subject is ." not in prompt

    def test_user_motion_prompt_override_honored(self):
        custom = "custom camera move"
        scene = _scene(motion_prompt=custom)
        assert build_celebrity_motion_prompt(scene, "손흥민") == custom

    def test_identity_guard_contains_key_rules(self):
        """Identity guard must forbid face morphing, age changes, lip-sync."""
        assert "facial identity" in CELEBRITY_IDENTITY_GUARD
        assert "morph" in CELEBRITY_IDENTITY_GUARD.lower()
        assert "lip sync" in CELEBRITY_IDENTITY_GUARD.lower()
        assert "no new people" in CELEBRITY_IDENTITY_GUARD.lower()

    def test_gentle_camera_small_zoom_only(self):
        """Must limit zoom to ~5% and forbid rotation/pan."""
        assert "5%" in GENTLE_PORTRAIT_CAMERA or "subtle" in GENTLE_PORTRAIT_CAMERA.lower()
        assert "rotation" in GENTLE_PORTRAIT_CAMERA.lower()
        assert "pan" in GENTLE_PORTRAIT_CAMERA.lower()
