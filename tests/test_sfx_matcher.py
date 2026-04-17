"""Tests for QW-04 — auto-assigned cut transition SFX (whoosh / impact / chime).

Why: 정치 유튜브 표준 패턴 §4.2 — 컷마다 효과음. ContentsMaker는 Scene.sfx
인프라가 이미 있지만 항상 비어있어서 사용자가 수동 지정해야 했음. sfx_matcher 가
씬 type / emphasis 를 보고 SFX를 자동 할당해 모든 영상에 즉시 효과를 적용한다.
"""
import pytest

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, SfxConfig,
)
from src.video.sfx_matcher import (
    auto_assign_sfx,
    IMPACT_SOUND,
    DING_SOUND,
    WHOOSH_SOUNDS,
)


def _scene(
    id: int,
    type: str = "body",
    emphasis: str = "medium",
    sfx: tuple = (),
) -> Scene:
    return Scene(
        id=id, timestamp=float(id), duration=3.0, type=type,
        text=f"scene {id}", voice_text=f"scene {id}",
        emphasis=emphasis, sfx=sfx,
    )


def _script(scenes: tuple[Scene, ...]) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(title="t", emotion_type="relatable", duration=30.0),
        scenes=scenes,
        audio=AudioConfig(tts_script="t"),
    )


class TestSfxMatcherConstants:
    def test_whoosh_sounds_is_tuple(self):
        assert isinstance(WHOOSH_SOUNDS, tuple)
        assert len(WHOOSH_SOUNDS) >= 2  # 최소 2종 회전 필요

    def test_whoosh_sounds_use_qw04_prefix(self):
        for name in WHOOSH_SOUNDS:
            assert "qw04" in name and "whoosh" in name

    def test_impact_and_ding_are_qw04(self):
        assert "qw04" in IMPACT_SOUND and "impact" in IMPACT_SOUND
        assert "qw04" in DING_SOUND


class TestAutoAssignSfx:
    def test_returns_shorts_script(self):
        out = auto_assign_sfx(_script((_scene(1, type="title"),)))
        assert isinstance(out, ShortsScript)

    def test_empty_scenes_returns_empty(self):
        out = auto_assign_sfx(_script(()))
        assert out.scenes == ()

    def test_title_scene_gets_impact(self):
        out = auto_assign_sfx(_script((_scene(1, type="title"),)))
        assert len(out.scenes[0].sfx) >= 1
        assert out.scenes[0].sfx[0].name == IMPACT_SOUND

    def test_body_scene_gets_whoosh(self):
        s1 = _scene(1, type="title")
        s2 = _scene(2, type="body", emphasis="medium")
        out = auto_assign_sfx(_script((s1, s2)))
        assert "whoosh" in out.scenes[1].sfx[0].name

    def test_high_emphasis_gets_impact(self):
        s1 = _scene(1, type="title")
        s2 = _scene(2, type="body", emphasis="high")
        out = auto_assign_sfx(_script((s1, s2)))
        assert out.scenes[1].sfx[0].name == IMPACT_SOUND

    def test_existing_sfx_preserved(self):
        custom = SfxConfig(name="custom_sound", category="emphasis", offset_ms=100, volume=0.5)
        s1 = _scene(1, type="body", sfx=(custom,))
        out = auto_assign_sfx(_script((s1,)))
        # User sfx wins — auto matcher must not overwrite
        assert out.scenes[0].sfx == (custom,)

    def test_whoosh_rotates_across_scenes(self):
        scenes = tuple(_scene(i, type="body", emphasis="medium") for i in range(1, 5))
        out = auto_assign_sfx(_script(scenes))
        names = [s.sfx[0].name for s in out.scenes]
        # 4개 씬에 최소 2개 이상의 다른 whoosh 가 사용됨 (단조로움 방지)
        assert len(set(names)) >= 2

    def test_offset_ms_zero_for_cut_transition(self):
        s1 = _scene(1, type="title")
        s2 = _scene(2, type="body", emphasis="medium")
        out = auto_assign_sfx(_script((s1, s2)))
        # Whoosh fires right at scene start (cut transition)
        assert out.scenes[1].sfx[0].offset_ms == 0

    def test_volume_within_safe_range(self):
        s1 = _scene(1, type="title")
        s2 = _scene(2, type="body", emphasis="medium")
        out = auto_assign_sfx(_script((s1, s2)))
        for scene in out.scenes:
            for sfx in scene.sfx:
                # -10 ~ -15 dB 권장 (§4.1) → 약 0.1~0.3 사이
                assert 0.05 <= sfx.volume <= 0.4

    def test_immutability_original_script_unchanged(self):
        s1 = _scene(1, type="title")
        original_scenes = (s1,)
        script = _script(original_scenes)
        out = auto_assign_sfx(script)
        # Original scene must still have empty sfx
        assert script.scenes[0].sfx == ()
        # New script returned, original untouched
        assert out is not script
        assert out.scenes[0].sfx != ()

    def test_metadata_audio_background_preserved(self):
        s1 = _scene(1, type="title")
        script = _script((s1,))
        out = auto_assign_sfx(script)
        assert out.metadata == script.metadata
        assert out.audio == script.audio
        assert out.background == script.background

    def test_high_emphasis_overrides_index_zero_rule(self):
        # Non-title first scene with high emphasis still gets impact
        s1 = _scene(1, type="body", emphasis="high")
        out = auto_assign_sfx(_script((s1,)))
        assert out.scenes[0].sfx[0].name == IMPACT_SOUND
