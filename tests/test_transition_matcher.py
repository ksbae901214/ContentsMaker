"""QW-06: punch-zoom 트랜지션 자동 매칭.

emphasis="high" + hook 씬 → 자동 punch-zoom 트랜지션.
사용자 수동 지정 transition은 보존.

출처: docs/dem-shorts/political-youtube-style-plan.md §3.3, §8.2 QW-06.
"""
from __future__ import annotations

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    Metadata,
    Scene,
    ShortsScript,
    TransitionConfig,
)


# Module-under-test — created in GREEN phase
from src.video.transition_matcher import (
    PUNCH_ZOOM_DURATION_SECONDS,
    auto_assign_transitions,
)


def _make_script(*scenes: Scene) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(title="t", emotion_type="angry", duration=30.0),
        scenes=scenes,
        audio=AudioConfig(tts_script="t"),
    )


class TestAutoAssignTransitions:
    def test_high_emphasis_gets_punch_zoom(self):
        s = _make_script(
            Scene(id=1, timestamp=0, duration=2, type="title",
                  text="후킹", voice_text="훅", emphasis="medium", hook=True),
            Scene(id=2, timestamp=2, duration=4, type="body",
                  text="핵심", voice_text="핵심 발언", emphasis="high"),
        )
        result = auto_assign_transitions(s)
        assert result.scenes[1].transition is not None
        assert result.scenes[1].transition.type == "punch-zoom"

    def test_hook_scene_gets_punch_zoom(self):
        s = _make_script(
            Scene(id=1, timestamp=0, duration=2, type="title",
                  text="후킹", voice_text="훅", emphasis="medium", hook=True),
        )
        result = auto_assign_transitions(s)
        assert result.scenes[0].transition is not None
        assert result.scenes[0].transition.type == "punch-zoom"

    def test_medium_emphasis_keeps_default_or_no_transition(self):
        """emphasis=medium 일반 씬은 자동 punch-zoom 안 받음."""
        s = _make_script(
            Scene(id=1, timestamp=0, duration=4, type="body",
                  text="중간", voice_text="중간 발언", emphasis="medium"),
        )
        result = auto_assign_transitions(s)
        # 기존 None 이면 None 유지 (또는 fade 같은 기본값) — punch-zoom 아니어야
        if result.scenes[0].transition is not None:
            assert result.scenes[0].transition.type != "punch-zoom"

    def test_low_emphasis_no_punch_zoom(self):
        s = _make_script(
            Scene(id=1, timestamp=0, duration=4, type="comment",
                  text="댓글", voice_text="댓글", emphasis="low"),
        )
        result = auto_assign_transitions(s)
        if result.scenes[0].transition is not None:
            assert result.scenes[0].transition.type != "punch-zoom"

    def test_user_transition_preserved(self):
        """사용자가 명시적으로 다른 transition 지정 시 덮어쓰지 않음."""
        s = _make_script(
            Scene(id=1, timestamp=0, duration=4, type="body",
                  text="강조", voice_text="강조", emphasis="high",
                  transition=TransitionConfig(type="slide-left", duration=0.5)),
        )
        result = auto_assign_transitions(s)
        assert result.scenes[0].transition is not None
        assert result.scenes[0].transition.type == "slide-left"

    def test_returns_new_script_immutable(self):
        """frozen dataclass — 원본 ShortsScript 불변."""
        original = _make_script(
            Scene(id=1, timestamp=0, duration=4, type="body",
                  text="강조", voice_text="강조", emphasis="high"),
        )
        result = auto_assign_transitions(original)
        assert original.scenes[0].transition is None
        assert result is not original

    def test_punch_zoom_duration_short(self):
        """QW-06 기본값: 0.2초 = 6 frames at 30fps."""
        s = _make_script(
            Scene(id=1, timestamp=0, duration=4, type="body",
                  text="강조", voice_text="강조", emphasis="high"),
        )
        result = auto_assign_transitions(s)
        assert result.scenes[0].transition.duration == PUNCH_ZOOM_DURATION_SECONDS
        assert PUNCH_ZOOM_DURATION_SECONDS == pytest.approx(0.2, abs=0.01)


class TestTransitionTypeIncludesPunchZoom:
    """script_models.TransitionType에 'punch-zoom' 이 포함되어야 한다."""

    def test_punch_zoom_is_valid_transition_type(self):
        # Just verify TransitionConfig accepts it (no validation error)
        tc = TransitionConfig(type="punch-zoom", duration=0.2)
        assert tc.type == "punch-zoom"
        assert tc.to_dict()["type"] == "punch-zoom"

    def test_punch_zoom_roundtrip(self):
        original = TransitionConfig(type="punch-zoom", duration=0.2)
        restored = TransitionConfig.from_dict(original.to_dict())
        assert restored.type == "punch-zoom"
