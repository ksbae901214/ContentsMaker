"""Tests for gem_navigator — Gemini Gems 탐색 유틸리티."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.illustrator.gem_navigator import (
    GemNotFoundError,
    get_gem_config,
    get_system_prompt_text,
    list_gems,
)

# ─── fixtures ────────────────────────────────────────────────────────────────

_FAKE_CONFIG = {
    "image": {
        "webtoon": {
            "gem_name": "나노바나나-웹툰",
            "description": "웹툰 스타일",
            "prompt_file": "image_webtoon.txt",
        }
    },
    "video": {
        "news": {
            "gem_name": "Veo3-뉴스",
            "description": "뉴스 앵커",
            "prompt_file": "video_news.txt",
        },
        "drama": {
            "gem_name": "Veo3-드라마",
            "description": "드라마 감성",
            "prompt_file": "video_drama.txt",
        },
    },
}


def _patch_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "gems_config.json"
    cfg.write_text(json.dumps(_FAKE_CONFIG), encoding="utf-8")
    return cfg


# ─── get_gem_config ───────────────────────────────────────────────────────────


def test_get_gem_config_image_webtoon(tmp_path):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        cfg = get_gem_config("image", "webtoon")
    assert cfg["gem_name"] == "나노바나나-웹툰"
    assert cfg["prompt_file"] == "image_webtoon.txt"


def test_get_gem_config_video_news(tmp_path):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        cfg = get_gem_config("video", "news")
    assert cfg["gem_name"] == "Veo3-뉴스"


def test_get_gem_config_missing_key_raises(tmp_path):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        with pytest.raises(GemNotFoundError, match="unknown"):
            get_gem_config("image", "unknown")


def test_get_gem_config_missing_kind_raises(tmp_path):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        with pytest.raises(GemNotFoundError):
            get_gem_config("audio", "webtoon")


# ─── list_gems ────────────────────────────────────────────────────────────────


def test_list_gems_returns_both_kinds(tmp_path):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        gems = list_gems()
    assert "image" in gems
    assert "video" in gems
    assert len(gems["image"]) == 1
    assert len(gems["video"]) == 2


def test_list_gems_includes_key_field(tmp_path):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        gems = list_gems()
    keys = [g["key"] for g in gems["image"]]
    assert "webtoon" in keys


# ─── get_system_prompt_text ───────────────────────────────────────────────────


def test_get_system_prompt_text_returns_content(tmp_path):
    prompts_dir = tmp_path / "gem_prompts"
    prompts_dir.mkdir()
    (prompts_dir / "image_webtoon.txt").write_text("웹툰 지침", encoding="utf-8")

    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_PROMPTS_DIR", prompts_dir):
        text = get_system_prompt_text("image_webtoon.txt")
    assert "웹툰" in text


def test_get_system_prompt_text_missing_returns_placeholder(tmp_path):
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_PROMPTS_DIR", tmp_path):
        text = get_system_prompt_text("nonexistent.txt")
    assert "없음" in text or "지침 파일" in text


# ─── GeminiWebImageGenerator gem_key 연동 ────────────────────────────────────


def test_image_generator_stores_gem_key():
    from src.illustrator.gemini_web_image_gen import GeminiWebImageGenerator
    gen = GeminiWebImageGenerator(gem_key="webtoon")
    assert gen.gem_key == "webtoon"


def test_image_generator_default_gem_key_is_none():
    from src.illustrator.gemini_web_image_gen import GeminiWebImageGenerator
    gen = GeminiWebImageGenerator()
    assert gen.gem_key is None


# ─── GeminiWebVideoGenerator gem_key 연동 ────────────────────────────────────


def test_video_generator_stores_gem_key():
    from src.video_gen.gemini_web_video_gen import GeminiWebVideoGenerator
    gen = GeminiWebVideoGenerator(gem_key="news")
    assert gen.gem_key == "news"


def test_factory_passes_gem_key_to_gemini():
    from src.video_gen.factory import create_generator
    gen = create_generator(provider="gemini", gem_key="drama")
    assert gen.gem_key == "drama"


# ─── CLI gems list ────────────────────────────────────────────────────────────


def test_cli_gems_list_runs(tmp_path, capsys):
    cfg_path = _patch_config(tmp_path)
    import src.illustrator.gem_navigator as nav
    with patch.object(nav, "_CONFIG_PATH", cfg_path):
        import src.main as m_mod
        import argparse
        args = argparse.Namespace(command="gems", gems_action="list")
        m_mod._cmd_gems(args)

    out = capsys.readouterr().out
    assert "webtoon" in out
    assert "news" in out


def test_cli_gems_show_prompt(tmp_path, capsys):
    cfg_path = _patch_config(tmp_path)
    prompts_dir = tmp_path / "gem_prompts"
    prompts_dir.mkdir()
    (prompts_dir / "image_webtoon.txt").write_text("웹툰 지침 내용", encoding="utf-8")

    import src.illustrator.gem_navigator as nav
    import src.main as m_mod
    import argparse

    with patch.object(nav, "_CONFIG_PATH", cfg_path), \
         patch.object(nav, "_PROMPTS_DIR", prompts_dir):
        args = argparse.Namespace(command="gems", gems_action="show-prompt", key="webtoon", kind="image")
        ret = m_mod._cmd_gems(args)

    assert ret == 0
    out = capsys.readouterr().out
    assert "웹툰 지침 내용" in out
