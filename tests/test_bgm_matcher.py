"""QW-07: 후킹 씬 빌드업 BGM 자동 매칭.

hook 씬(첫 1.5~2.5초)에 인트로 빌드업 BGM을 깔아 시각·청각 임팩트
일치. emotion에 따라 트랙을 회전.

자산: public/bgm/intro_buildup_*.mp3 (사전 수집됨, LICENSES.md 참조)
출처: docs/dem-shorts/political-youtube-style-plan.md §1.2, §4.1, §8.2 QW-07.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.video.bgm_matcher import (
    INTRO_BGM_TRACKS,
    PUBLIC_BGM_DIR,
    find_hook_scene,
    intro_bgm_for_emotion,
)


def _make_script(*scenes: Scene, emotion: str = "angry") -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(title="t", emotion_type=emotion, duration=30.0),
        scenes=scenes,
        audio=AudioConfig(tts_script="t"),
    )


class TestAssetsPresent:
    """자산이 public/bgm/ 에 사전 수집되어 있어야 한다."""

    def test_intro_bgm_dir_exists(self):
        assert PUBLIC_BGM_DIR.exists(), f"BGM dir 누락: {PUBLIC_BGM_DIR}"

    def test_at_least_one_intro_track_present(self):
        assert len(INTRO_BGM_TRACKS) >= 1
        # 적어도 하나는 실제 파일로 존재
        present = [t for t in INTRO_BGM_TRACKS if (PUBLIC_BGM_DIR / t).exists()]
        assert len(present) >= 1, (
            f"INTRO_BGM_TRACKS {INTRO_BGM_TRACKS} 중 실제 파일 0개"
        )

    def test_licenses_documented(self):
        licenses = PUBLIC_BGM_DIR / "LICENSES.md"
        assert licenses.exists(), "public/bgm/LICENSES.md 필요"


class TestIntroBgmForEmotion:
    def test_returns_track_for_known_emotion(self):
        track = intro_bgm_for_emotion("angry")
        assert track in INTRO_BGM_TRACKS
        assert track.endswith(".mp3")

    def test_returns_track_for_each_emotion(self):
        for emo in ("funny", "touching", "angry", "relatable"):
            track = intro_bgm_for_emotion(emo)
            assert track in INTRO_BGM_TRACKS

    def test_unknown_emotion_falls_back_to_first(self):
        """미지의 emotion은 첫 트랙으로 폴백 (깨지지 않음)."""
        track = intro_bgm_for_emotion("nonexistent_xyz")
        assert track in INTRO_BGM_TRACKS


class TestFindHookScene:
    def test_returns_first_hook_scene(self):
        s = _make_script(
            Scene(id=1, timestamp=0, duration=2, type="title",
                  text="후킹", voice_text="훅", hook=True),
            Scene(id=2, timestamp=2, duration=4, type="body",
                  text="본문", voice_text="본문"),
        )
        hook = find_hook_scene(s)
        assert hook is not None
        assert hook.id == 1

    def test_returns_none_when_no_hook(self):
        s = _make_script(
            Scene(id=1, timestamp=0, duration=4, type="title",
                  text="제목", voice_text="제목"),
            Scene(id=2, timestamp=4, duration=4, type="body",
                  text="본문", voice_text="본문"),
        )
        assert find_hook_scene(s) is None

    def test_hook_scene_at_non_first_position(self):
        """드물지만 hook=True가 첫 씬이 아닐 수도 있음 — 첫 hook 씬 반환."""
        s = _make_script(
            Scene(id=1, timestamp=0, duration=2, type="title",
                  text="t", voice_text="t"),
            Scene(id=2, timestamp=2, duration=2, type="body",
                  text="t", voice_text="t", hook=True),
        )
        hook = find_hook_scene(s)
        assert hook is not None
        assert hook.id == 2
