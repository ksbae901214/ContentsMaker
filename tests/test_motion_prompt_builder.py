"""Unit tests for the shared motion prompt builder."""
from __future__ import annotations

import pytest

from src.analyzer.script_models import Scene
from src.video_gen.motion_prompt_builder import (
    DYNAMIC_CAMERA,
    MOTION_GUARD,
    STATIC_CAMERA,
    build_motion_prompt,
)


def _make_scene(**overrides) -> Scene:
    base = {
        "id": 1,
        "timestamp": 0.0,
        "duration": 5.0,
        "type": "body",
        "text": "테스트 텍스트",
        "voice_text": "테스트 보이스 텍스트입니다.",
        "emphasis": "medium",
    }
    base.update(overrides)
    return Scene(**base)


class TestUserOverride:
    def test_returns_user_motion_prompt_verbatim(self) -> None:
        """If the scene editor set a motion_prompt, it must win."""
        custom = "Hand-written custom camera movement for this one scene."
        scene = _make_scene(motion_prompt=custom, emphasis="high", type="body")
        assert build_motion_prompt(scene) == custom

    def test_ignores_heuristic_when_override_present(self) -> None:
        """Override must bypass the static/dynamic heuristic entirely."""
        scene = _make_scene(motion_prompt="override")
        result = build_motion_prompt(scene)
        assert STATIC_CAMERA not in result
        assert DYNAMIC_CAMERA not in result
        assert MOTION_GUARD not in result


class TestStaticCameraHeuristic:
    def test_high_emphasis_body_scene_uses_static(self) -> None:
        scene = _make_scene(emphasis="high", type="body")
        result = build_motion_prompt(scene)
        assert STATIC_CAMERA in result
        assert DYNAMIC_CAMERA not in result

    def test_medium_emphasis_body_scene_uses_dynamic(self) -> None:
        scene = _make_scene(emphasis="medium", type="body")
        result = build_motion_prompt(scene)
        assert DYNAMIC_CAMERA in result
        assert STATIC_CAMERA not in result

    def test_high_emphasis_title_scene_uses_dynamic(self) -> None:
        """Title scenes get the intro push-in even at high emphasis."""
        scene = _make_scene(emphasis="high", type="title")
        result = build_motion_prompt(scene)
        assert DYNAMIC_CAMERA in result
        assert STATIC_CAMERA not in result

    def test_high_emphasis_comment_scene_uses_dynamic(self) -> None:
        scene = _make_scene(emphasis="high", type="comment")
        result = build_motion_prompt(scene)
        assert DYNAMIC_CAMERA in result


class TestUniversalGuard:
    @pytest.mark.parametrize("emphasis", ["low", "medium", "high"])
    @pytest.mark.parametrize("scene_type", ["title", "body", "comment"])
    def test_motion_guard_always_applied(self, emphasis, scene_type) -> None:
        """Every generated prompt must include the MOTION_GUARD."""
        scene = _make_scene(emphasis=emphasis, type=scene_type)
        result = build_motion_prompt(scene)
        assert MOTION_GUARD in result

    def test_guard_blocks_ghost_characters(self) -> None:
        """The guard itself must explicitly name the ghost-character failure."""
        assert "Do NOT introduce" in MOTION_GUARD
        assert "ghostly" in MOTION_GUARD.lower()
        assert "new characters" in MOTION_GUARD

    def test_guard_protects_anatomy(self) -> None:
        assert "exactly two hands" in MOTION_GUARD
        assert "extra limbs" in MOTION_GUARD.lower()


class TestVoiceHint:
    def test_short_voice_hint_appended(self) -> None:
        scene = _make_scene(voice_text="정말 슬픈 장면이에요")
        result = build_motion_prompt(scene)
        assert "정말 슬픈 장면이에요" in result

    def test_voice_hint_truncated_to_80_chars(self) -> None:
        long_text = "가" * 200
        scene = _make_scene(voice_text=long_text)
        result = build_motion_prompt(scene)
        # The hint portion should not exceed 80 chars
        assert ("가" * 80) in result
        assert ("가" * 81) not in result

    def test_falls_back_to_text_when_voice_empty(self) -> None:
        scene = _make_scene(voice_text="", text="폴백 텍스트")
        result = build_motion_prompt(scene)
        assert "폴백 텍스트" in result
