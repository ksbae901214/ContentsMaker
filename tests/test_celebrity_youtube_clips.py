"""Tests for celebrity YouTube clip helpers (Phase 9 YouTube source).

TDD RED phase: tests written before implementation.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_scene(
    id: int,
    *,
    clip_query: str | None = None,
    image_query: str | None = None,
    duration: float = 4.0,
) -> Scene:
    return Scene(
        id=id,
        timestamp=float(id * 4),
        duration=duration,
        type="body",
        text="text",
        voice_text="voice",
        clip_query=clip_query,
        image_query=image_query,
    )


def _make_script(scenes: tuple) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title="테스트",
            emotion_type="relatable",
            duration=30.0,
            source_url="https://namu.wiki/w/손흥민",
            source_type="celebrity",
        ),
        scenes=scenes,
        audio=AudioConfig(tts_script="..."),
        background=BackgroundConfig(),
    )


# ── _build_celebrity_clip_keywords ───────────────────────────────────────────


class TestBuildCelebrityClipKeywords:
    def test_uses_clip_query_when_present(self):
        """clip_query takes priority over image_query and name."""
        from src.main import _build_celebrity_clip_keywords

        scene = _make_scene(1, clip_query="손흥민 골 장면", image_query="다른 키워드")
        script = _make_script((scene,))
        kws = _build_celebrity_clip_keywords("손흥민", script)
        assert kws == ["손흥민 골 장면"]

    def test_falls_back_to_name_plus_image_query(self):
        """No clip_query → name + image_query combined."""
        from src.main import _build_celebrity_clip_keywords

        scene = _make_scene(1, clip_query=None, image_query="골 장면")
        script = _make_script((scene,))
        kws = _build_celebrity_clip_keywords("손흥민", script)
        assert kws == ["손흥민 골 장면"]

    def test_falls_back_to_name_only(self):
        """No clip_query, no image_query → name only."""
        from src.main import _build_celebrity_clip_keywords

        scene = _make_scene(1, clip_query=None, image_query=None)
        script = _make_script((scene,))
        kws = _build_celebrity_clip_keywords("손흥민", script)
        assert kws == ["손흥민"]

    def test_all_fallbacks_in_one_script(self):
        """Mixed scenes: clip_query / image_query fallback / name-only fallback."""
        from src.main import _build_celebrity_clip_keywords

        s1 = _make_scene(1, clip_query="손흥민 챔피언스리그")
        s2 = _make_scene(2, clip_query=None, image_query="토트넘")
        s3 = _make_scene(3, clip_query=None, image_query=None)
        script = _make_script((s1, s2, s3))
        kws = _build_celebrity_clip_keywords("손흥민", script)
        assert kws[0] == "손흥민 챔피언스리그"
        assert kws[1] == "손흥민 토트넘"
        assert kws[2] == "손흥민"


# ── _run_celebrity_youtube_clips ──────────────────────────────────────────────


class TestRunCelebrityYoutubeClips:
    def test_maps_scene_ids(self, tmp_path):
        """Each returned dict has scene_id matching the corresponding scene."""
        from src.main import _run_celebrity_youtube_clips

        s1 = _make_scene(1)
        s2 = _make_scene(2)
        script = _make_script((s1, s2))

        fake_clip1 = tmp_path / "s00.mp4"
        fake_clip2 = tmp_path / "s01.mp4"
        fake_clip1.write_bytes(b"mp4")
        fake_clip2.write_bytes(b"mp4")

        with patch("src.scraper.youtube_news_searcher.build_scene_clips", return_value=[fake_clip1, fake_clip2]):
            result = _run_celebrity_youtube_clips("손흥민", script)

        assert result is not None
        assert len(result) == 2
        assert result[0]["scene_id"] == 1
        assert result[1]["scene_id"] == 2
        assert result[0]["video_path"] == str(fake_clip1)

    def test_skips_none_clips(self, tmp_path):
        """None clips (failed downloads) are excluded from result."""
        from src.main import _run_celebrity_youtube_clips

        s1 = _make_scene(1)
        s2 = _make_scene(2)
        script = _make_script((s1, s2))

        fake_clip1 = tmp_path / "s00.mp4"
        fake_clip1.write_bytes(b"mp4")

        with patch("src.scraper.youtube_news_searcher.build_scene_clips", return_value=[fake_clip1, None]):
            result = _run_celebrity_youtube_clips("손흥민", script)

        assert result is not None
        assert len(result) == 1
        assert result[0]["scene_id"] == 1

    def test_uses_timing_for_duration(self, tmp_path):
        """scene_timings override scene.duration when computing clip lengths."""
        from src.main import _run_celebrity_youtube_clips

        s1 = _make_scene(1, duration=4.0)  # original duration
        script = _make_script((s1,))

        fake_clip = tmp_path / "s00.mp4"
        fake_clip.write_bytes(b"mp4")

        # TTS timing says 6.5 s — should override the 4.0 scene.duration
        scene_timings = [{"scene_id": 1, "start_ms": 0, "end_ms": 6500}]

        captured_durations: list = []

        def fake_build_scene_clips(durations, *, keywords, out_dir, crop_mode="crop"):
            captured_durations.extend(durations)
            return [fake_clip]

        with patch("src.scraper.youtube_news_searcher.build_scene_clips", side_effect=fake_build_scene_clips):
            _run_celebrity_youtube_clips("손흥민", script, scene_timings=scene_timings)

        assert abs(captured_durations[0] - 6.5) < 0.01

    def test_all_failed_returns_none(self, tmp_path):
        """If all clips are None, returns None."""
        from src.main import _run_celebrity_youtube_clips

        s1 = _make_scene(1)
        script = _make_script((s1,))

        with patch("src.scraper.youtube_news_searcher.build_scene_clips", return_value=[None]):
            result = _run_celebrity_youtube_clips("손흥민", script)

        assert result is None

    def test_exception_returns_none(self, tmp_path):
        """If build_scene_clips raises, returns None gracefully."""
        from src.main import _run_celebrity_youtube_clips

        s1 = _make_scene(1)
        script = _make_script((s1,))

        with patch("src.scraper.youtube_news_searcher.build_scene_clips", side_effect=RuntimeError("network error")):
            result = _run_celebrity_youtube_clips("손흥민", script)

        assert result is None
