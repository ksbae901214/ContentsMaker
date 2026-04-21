"""Tests for CLI cmd_celebrity (Phase 9-5).

All external dependencies (namuwiki, naver, claude, freepik, renderer, tts)
are mocked. Verifies orchestration, not component internals.
"""
from __future__ import annotations

import argparse
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
from src.main import build_parser, cmd_celebrity
from src.scraper.celebrity_models import CelebrityInfo


def _ns(**kwargs) -> argparse.Namespace:
    base = {
        "name": "손흥민",
        "no_video": True,   # default in tests: skip Freepik
        "no_images": True,  # default in tests: skip Naver
        "no_bgm": True,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def _sample_script() -> ShortsScript:
    scenes = (
        Scene(
            id=1, timestamp=0.0, duration=4.0, type="title",
            text="손흥민", voice_text="손흥민입니다.", emphasis="high",
        ),
        Scene(
            id=2, timestamp=4.0, duration=4.0, type="body",
            text="토트넘", voice_text="토트넘에서 뛰고 있습니다.", emphasis="medium",
        ),
        Scene(
            id=3, timestamp=8.0, duration=4.0, type="comment",
            text="출처: 나무위키", voice_text="출처는 나무위키.", emphasis="low",
        ),
    )
    return ShortsScript(
        metadata=Metadata(
            title="손흥민",
            emotion_type="relatable",
            duration=12.0,
            source_url="https://namu.wiki/w/손흥민",
            source_type="celebrity",
        ),
        scenes=scenes,
        audio=AudioConfig(tts_script="..."),
        background=BackgroundConfig(type="gradient", colors=("#4169E1",)),
    )


def _sample_info() -> CelebrityInfo:
    return CelebrityInfo(
        name="손흥민",
        summary="대한민국의 축구 선수",
        source_url="https://namu.wiki/w/손흥민",
        career_highlights=("토트넘 이적",),
    )


@pytest.fixture
def base_mocks(tmp_path):
    """Install mocks for the full happy-path dependency chain."""
    mock_output = tmp_path / "out.mp4"
    mock_output.write_bytes(b"fake-mp4")

    with patch("src.scraper.namuwiki_scraper.NamuwikiScraper") as scraper_cls, \
         patch("src.analyzer.celebrity_analyzer.analyze_celebrity") as analyze, \
         patch("src.main._run_tts") as tts, \
         patch("src.video.renderer.render_video") as render:

        scraper = MagicMock()
        scraper.fetch_person.return_value = _sample_info()
        scraper_cls.return_value = scraper

        analyze.return_value = (_sample_script(), tmp_path / "script.json")
        tts.return_value = (0, tmp_path / "voice.mp3", [])
        render.return_value = mock_output

        yield {
            "scraper_cls": scraper_cls,
            "scraper": scraper,
            "analyze": analyze,
            "tts": tts,
            "render": render,
            "mock_output": mock_output,
        }


class TestCmdCelebrity:
    def test_empty_name_returns_1(self):
        assert cmd_celebrity(_ns(name="")) == 1
        assert cmd_celebrity(_ns(name="   ")) == 1

    def test_happy_path_returns_0(self, base_mocks):
        result = cmd_celebrity(_ns())
        assert result == 0

    def test_happy_path_calls_namuwiki(self, base_mocks):
        cmd_celebrity(_ns())
        base_mocks["scraper"].fetch_person.assert_called_once_with("손흥민", qualifier=None)

    def test_happy_path_calls_analyzer(self, base_mocks):
        cmd_celebrity(_ns())
        args, _kwargs = base_mocks["analyze"].call_args
        assert args[0].name == "손흥민"

    def test_happy_path_calls_renderer(self, base_mocks):
        cmd_celebrity(_ns())
        base_mocks["render"].assert_called_once()
        call_kwargs = base_mocks["render"].call_args.kwargs
        assert call_kwargs.get("use_bgm") is False  # no_bgm=True in fixture

    def test_no_images_does_not_call_naver(self, base_mocks):
        with patch("src.illustrator.naver_image_search.NaverImageSearcher") as naver:
            cmd_celebrity(_ns(no_images=True))
            naver.assert_not_called()

    def test_with_images_calls_naver(self, base_mocks, tmp_path):
        saved = tuple(tmp_path / f"p{i}.jpg" for i in range(3))
        for p in saved:
            p.write_bytes(b"x")

        with patch("src.illustrator.naver_image_search.NaverImageSearcher") as naver_cls:
            naver = MagicMock()
            naver.search.return_value = ()
            naver.download.return_value = saved
            naver_cls.return_value = naver

            cmd_celebrity(_ns(no_images=False, no_video=True))
            naver_cls.assert_called_once()
            naver.search.assert_called_once()
            naver.download.assert_called_once()

    def test_no_video_skips_freepik(self, base_mocks):
        """Even with images, --no-video must not create the Freepik generator."""
        saved = (Path("/tmp/p.jpg"),)

        with patch("src.illustrator.naver_image_search.NaverImageSearcher") as naver_cls, \
             patch("src.video_gen.factory.create_generator") as create_gen:
            naver = MagicMock()
            naver.search.return_value = ()
            naver.download.return_value = saved
            naver_cls.return_value = naver

            cmd_celebrity(_ns(no_images=False, no_video=True))
            create_gen.assert_not_called()

    def test_namuwiki_error_returns_1(self, tmp_path):
        from src.scraper.namuwiki_scraper import NamuwikiScraperError

        with patch("src.scraper.namuwiki_scraper.NamuwikiScraper") as scraper_cls:
            scraper = MagicMock()
            scraper.fetch_person.side_effect = NamuwikiScraperError("404")
            scraper_cls.return_value = scraper

            assert cmd_celebrity(_ns()) == 1

    def test_analyzer_error_returns_1(self, base_mocks):
        from src.analyzer.claude_analyzer import AnalyzerError

        base_mocks["analyze"].side_effect = AnalyzerError("claude failed")
        assert cmd_celebrity(_ns()) == 1


class TestArgparse:
    def test_celebrity_subcommand_registered(self):
        parser = build_parser()
        args = parser.parse_args(["celebrity", "손흥민"])
        assert args.command == "celebrity"
        assert args.name == "손흥민"

    def test_celebrity_flags_default_false(self):
        parser = build_parser()
        args = parser.parse_args(["celebrity", "세종"])
        assert args.no_video is False
        assert args.no_images is False
        assert args.no_bgm is False

    def test_celebrity_flags_set_true(self):
        parser = build_parser()
        args = parser.parse_args([
            "celebrity", "세종",
            "--no-video", "--no-images", "--no-bgm",
        ])
        assert args.no_video is True
        assert args.no_images is True
        assert args.no_bgm is True

    def test_celebrity_requires_name(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["celebrity"])


class TestCommandsDict:
    def test_celebrity_dispatched(self):
        from src.main import main

        with patch("src.main.cmd_celebrity") as mock_cmd, \
             patch("sys.argv", ["contentsmaker", "celebrity", "손흥민"]):
            mock_cmd.return_value = 0
            assert main() == 0
            mock_cmd.assert_called_once()
