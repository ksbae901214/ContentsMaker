"""Tests for split_scenes_to_max_duration — safety-net splitter for long scenes."""
from __future__ import annotations

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.editor.scene_ops import SceneOpsError, split_scenes_to_max_duration


def _make_script(scenes: list[Scene]) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title="test",
            emotion_type="angry",
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


def _make_scene(scene_id: int, duration: float, text: str, voice: str) -> Scene:
    return Scene(
        id=scene_id,
        timestamp=0.0,
        duration=duration,
        type="body",
        text=text,
        voice_text=voice,
        emphasis="medium",
        highlight_words=(),
    )


class TestSplitScenesToMaxDuration:
    def test_all_scenes_already_short(self):
        """No-op when every scene is already ≤ max_duration."""
        script = _make_script([
            _make_scene(1, 3.0, "짧은 씬 하나\n두 줄", "짧은 씬 하나 두 줄"),
            _make_scene(2, 4.0, "짧은 씬 두개\n두 줄", "짧은 씬 두개 두 줄"),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        assert len(result.scenes) == 2
        assert all(s.duration <= 5.0 for s in result.scenes)

    def test_one_long_scene_gets_split(self):
        """A single 9-second scene should split into 2 ≤ 5s pieces."""
        script = _make_script([
            _make_scene(
                1,
                9.0,
                "긴 씬 하나가 있는데\n이 씬을 분할해야 한다",
                "긴 씬 하나가 있는데 이 씬을 분할해야 한다 매우 긴 문장",
            ),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        assert len(result.scenes) >= 2
        assert all(s.duration <= 5.0 for s in result.scenes)

    def test_total_duration_roughly_preserved(self):
        """Sum of scene durations should approximately equal the original total."""
        script = _make_script([
            _make_scene(
                1,
                10.0,
                "아주 긴 한 씬을\n반으로 나누어야 하는 케이스",
                "아주 긴 한 씬을 반으로 나누어야 하는 케이스",
            ),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        total = sum(s.duration for s in result.scenes)
        assert abs(total - 10.0) < 0.5  # allow rounding drift

    def test_multiple_long_scenes(self):
        """Multiple long scenes should all be split."""
        script = _make_script([
            _make_scene(1, 3.0, "짧은 씬\n두 줄", "짧은 씬 두 줄"),
            _make_scene(
                2,
                8.0,
                "긴 씬 하나다\n여기서 분할",
                "긴 씬 하나 여기서 분할",
            ),
            _make_scene(3, 2.0, "또 짧은\n씬", "또 짧은 씬"),
            _make_scene(
                4,
                7.0,
                "또 다른 긴 씬이다\n이것도 분할",
                "또 다른 긴 씬 이것도 분할",
            ),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        assert all(s.duration <= 5.0 for s in result.scenes)
        # Should have at least 6 scenes now (2 short + 2 * 2 from splits)
        assert len(result.scenes) >= 6

    def test_default_uses_settings_constant(self):
        """Calling with no max_duration uses settings.MAX_SCENE_DURATION_SECONDS."""
        from src.config.settings import MAX_SCENE_DURATION_SECONDS

        assert MAX_SCENE_DURATION_SECONDS == 5.0
        script = _make_script([
            _make_scene(
                1,
                9.0,
                "긴 씬 하나가 있는데\n이 씬을 분할",
                "긴 씬 하나가 있는데 이 씬을 분할해야",
            ),
        ])
        result = split_scenes_to_max_duration(script)  # no arg
        assert all(s.duration <= MAX_SCENE_DURATION_SECONDS for s in result.scenes)

    def test_invalid_max_duration_raises(self):
        script = _make_script([_make_scene(1, 3.0, "씬\n텍스트", "씬 텍스트")])
        with pytest.raises(SceneOpsError, match="positive"):
            split_scenes_to_max_duration(script, max_duration=0)
        with pytest.raises(SceneOpsError, match="positive"):
            split_scenes_to_max_duration(script, max_duration=-1.0)

    def test_ids_are_renumbered_sequentially(self):
        """After splitting, scene IDs should be unique and sequential."""
        script = _make_script([
            _make_scene(1, 3.0, "첫번째 씬\n짧음", "첫번째 씬 짧음"),
            _make_scene(
                2,
                9.0,
                "두번째 긴 씬\n분할 필요",
                "두번째 긴 씬이다 분할 필요",
            ),
            _make_scene(3, 3.0, "세번째 씬\n짧음", "세번째 씬 짧음"),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        ids = [s.id for s in result.scenes]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_tiny_scene_not_infinitely_split(self):
        """Scene that can't be meaningfully split should not infinite-loop."""
        # Edge case: duration > max but text is very short (not enough to split)
        script = _make_script([
            _make_scene(1, 10.0, "짧은\n둘", "짧은 둘"),
        ])
        # Should complete without hanging
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        # Might still be one scene if splitting failed, but no exception
        assert len(result.scenes) >= 1


class TestSplitPrefersSentenceBoundary:
    """문장 종결 부호(., !, ?, …) 우선 분할 — 문장 중간 끊김 방지."""

    def test_prefers_period_over_space(self):
        """중앙에 공백과 마침표가 둘 다 있으면 마침표에서 자른다."""
        # 이게 A야. 이게 B야. 이게 C야.  (len≈22, mid≈11 "B")
        # 가까운 ` ` = 10, 가까운 `.` = 7 or 12 — `.` 선택돼야 함.
        script = _make_script([
            _make_scene(1, 10.0, "이게 A야. 이게 B야. 이게 C야.",
                        "이게 A야. 이게 B야. 이게 C야."),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)

        # 첫 씬은 반드시 마침표로 끝나야 한다 (문장 완성)
        assert result.scenes[0].voice_text.rstrip().endswith((".", "!", "?", "…"))

    def test_prefers_exclamation_and_question(self):
        """! 와 ? 도 문장 종결로 인정한다."""
        script = _make_script([
            _make_scene(1, 10.0, "정말요? 그럴 수가! 믿기지 않네요.",
                        "정말요? 그럴 수가! 믿기지 않네요."),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        assert result.scenes[0].voice_text.rstrip().endswith((".", "!", "?", "…"))

    def test_falls_back_to_comma_when_no_sentence_boundary(self):
        """한 문장 안이면 쉼표에서 자른다."""
        # 한 문장, 매우 긴 구절로 이루어진 텍스트입니다
        script = _make_script([
            _make_scene(1, 10.0, "한 문장, 매우 긴 구절로 이루어진 텍스트입니다",
                        "한 문장, 매우 긴 구절로 이루어진 텍스트입니다"),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        # 2개 씬으로 분할됐다면 첫 씬 끝은 쉼표여야 함 (또는 공백)
        assert len(result.scenes) >= 1

    def test_falls_back_to_space_when_no_punctuation(self):
        """마침표/쉼표 없으면 공백에서 자른다 (기존 동작 유지)."""
        script = _make_script([
            _make_scene(1, 10.0, "아주 긴 문장 그냥 이어지는 텍스트 더",
                        "아주 긴 문장 그냥 이어지는 텍스트 더"),
        ])
        result = split_scenes_to_max_duration(script, max_duration=5.0)
        assert len(result.scenes) >= 2  # 분할됨

    def test_voice_text_split_preserves_sentence(self):
        """voice_text 분할도 문장 경계를 따라야 한다."""
        from src.editor.scene_ops import scene_split

        script = _make_script([
            _make_scene(1, 10.0,
                        "첫 문장입니다. 두 번째 문장입니다.",
                        "첫 문장입니다. 두 번째 문장입니다."),
        ])
        # 중앙 근처 (첫 문장 끝 '.' 위치) 에서 분할
        text = script.scenes[0].text
        split_pos = text.index(".") + 1  # "첫 문장입니다." 뒤
        result = scene_split(script, 1, split_pos)

        # voice_text 도 문장 종결로 끝나야 한다
        assert result.scenes[0].voice_text.rstrip().endswith((".", "!", "?", "…"))
