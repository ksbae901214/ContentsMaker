"""Tests for FreepikImageGenerator."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.illustrator.freepik_image_gen import (
    FreepikImageError,
    FreepikImageGenerator,
)


class TestModelPriority:
    def test_default_matches_settings(self):
        from src.config.settings import FREEPIK_IMAGE_MODEL_PRIORITY

        gen = FreepikImageGenerator()
        assert gen.model_priority == list(FREEPIK_IMAGE_MODEL_PRIORITY)
        assert gen.model_priority[0] == "Google Nano Banana Pro"

    def test_custom_priority(self):
        gen = FreepikImageGenerator(model_priority=["GPT Image 1.5"])
        assert gen.model_priority == ["GPT Image 1.5"]

    def test_priority_is_copied(self):
        original = ["Google Nano Banana Pro"]
        gen = FreepikImageGenerator(model_priority=original)
        gen.model_priority.append("Extra")
        assert "Extra" not in original


class TestPreconditions:
    def test_missing_profile_raises(self, tmp_path):
        gen = FreepikImageGenerator()
        gen.profile_dir = tmp_path / "nonexistent"
        with pytest.raises(FreepikImageError, match="freepik_login"):
            asyncio.run(
                gen.generate_scene_images(
                    prompts=[{"scene_id": 1, "prompt": "test"}],
                    output_dir=tmp_path,
                )
            )

    def test_empty_prompts_returns_empty(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()
        gen = FreepikImageGenerator()
        gen.profile_dir = profile
        result = asyncio.run(
            gen.generate_scene_images(prompts=[], output_dir=tmp_path)
        )
        assert result == []


class TestSelectModel:
    def test_unknown_model_raises(self):
        gen = FreepikImageGenerator()
        page = MagicMock()
        with pytest.raises(FreepikImageError, match="알 수 없는"):
            asyncio.run(gen._select_model(page, "NonExistent Model"))

    def test_known_model_uses_data_cy(self):
        from src.illustrator.freepik_image_selectors import IMAGE_MODEL_DATA_CY

        gen = FreepikImageGenerator()
        recorded = []
        target = MagicMock()
        target.click = AsyncMock()
        all_btn = MagicMock()
        all_btn.click = AsyncMock()

        async def query_selector(selector):
            recorded.append(selector)
            if "show-all-button" in selector:
                return all_btn
            if "ai-model-item-" in selector:
                return target
            if "backdrop-blur-lg" in selector:
                return None
            return None

        page = MagicMock()
        page.click = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.query_selector = AsyncMock(side_effect=query_selector)

        asyncio.run(gen._select_model(page, "Google Nano Banana Pro"))

        slug = IMAGE_MODEL_DATA_CY["Google Nano Banana Pro"]
        assert any(slug in s for s in recorded), (
            f"Expected {slug} in queries, got {recorded}"
        )
        assert target.click.called


class TestGenerateSceneImagesFlow:
    """End-to-end flow with fully mocked Playwright + httpx."""

    def _make_mock_page(
        self,
        num_scenes: int = 2,
        upgrade_after_click: bool = False,
        model_selectable: bool = True,
    ):
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.add_init_script = AsyncMock()
        page.click = AsyncMock()
        page.reload = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()

        # Mock elements
        prompt_el = MagicMock()
        prompt_el.click = AsyncMock()
        prompt_el.type = AsyncMock()

        ar_btn = MagicMock()
        ar_btn.inner_text = AsyncMock(return_value="9:16")
        ar_btn.click = AsyncMock()

        gen_btn = MagicMock()
        gen_btn.inner_text = AsyncMock(
            return_value="Upgrade" if upgrade_after_click else "Generate"
        )
        gen_btn.click = AsyncMock()

        all_models_btn = MagicMock()
        all_models_btn.click = AsyncMock()

        model_item = MagicMock() if model_selectable else None
        if model_item:
            model_item.click = AsyncMock()

        async def query_selector(selector):
            if "image-prompt-input" in selector or "contenteditable" in selector:
                return prompt_el
            if "aspect-ratio" in selector:
                return ar_btn
            if "generate-button" in selector:
                return gen_btn
            if "show-all-button" in selector:
                return all_models_btn
            if "ai-model-item-" in selector:
                return model_item
            if "backdrop-blur-lg" in selector:
                return None
            return None

        page.query_selector = AsyncMock(side_effect=query_selector)

        # Simulate image URL polling: after 1 poll, return a new render.png
        call_state = {"polls": 0, "scene_idx": 0}

        async def query_selector_all(selector):
            if "img" not in selector:
                return []
            call_state["polls"] += 1
            # For first pass (existing_urls snapshot), return empty
            # For subsequent polls, return a new scene-specific URL
            scene_num = call_state["scene_idx"] + 1
            if call_state["polls"] <= 1 + call_state["scene_idx"] * 3:
                return []
            call_state["scene_idx"] += 1
            img = MagicMock()
            img.get_attribute = AsyncMock(
                return_value=f"https://pikaso.cdnpk.net/render{scene_num}.png?token=abc"
            )
            return [img]

        page.query_selector_all = AsyncMock(side_effect=query_selector_all)
        return page

    def _patch_playwright(self, page):
        ctx = MagicMock()
        ctx.pages = [page]
        ctx.close = AsyncMock()
        chromium = MagicMock()
        chromium.launch_persistent_context = AsyncMock(return_value=ctx)
        p = MagicMock()
        p.chromium = chromium
        playwright_ctx = MagicMock()
        playwright_ctx.__aenter__ = AsyncMock(return_value=p)
        playwright_ctx.__aexit__ = AsyncMock(return_value=None)
        return playwright_ctx

    def test_success_2_scenes(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = FreepikImageGenerator()
        gen.profile_dir = profile

        page = self._make_mock_page(num_scenes=2)
        playwright_ctx = self._patch_playwright(page)

        async def fake_sleep(_):
            pass

        # Mock httpx download
        class _FakeResp:
            content = b"fake png bytes"
            def raise_for_status(self): pass

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=_FakeResp())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("playwright.async_api.async_playwright", return_value=playwright_ctx):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch(
                    "src.illustrator.freepik_image_gen.httpx.AsyncClient",
                    return_value=mock_client,
                ):
                    results = asyncio.run(
                        gen.generate_scene_images(
                            prompts=[
                                {"scene_id": 1, "prompt": "A sunny beach"},
                                {"scene_id": 2, "prompt": "A cat playing"},
                            ],
                            output_dir=tmp_path,
                        )
                    )

        assert len(results) == 2
        assert results[0]["scene_id"] == 1
        assert results[1]["scene_id"] == 2
        assert results[0]["prompt"] == "A sunny beach"
        # Files actually written
        for r in results:
            assert Path(r["image_path"]).exists()
            assert Path(r["image_path"]).read_bytes() == b"fake png bytes"

    def test_all_models_fail_upgrade(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = FreepikImageGenerator(
            model_priority=["Google Nano Banana Pro", "GPT Image 1.5"]
        )
        gen.profile_dir = profile

        page = self._make_mock_page(upgrade_after_click=True)
        playwright_ctx = self._patch_playwright(page)

        async def fake_sleep(_):
            pass

        with patch("playwright.async_api.async_playwright", return_value=playwright_ctx):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with pytest.raises(
                    FreepikImageError, match="(모든 씬|Upgrade|크레딧|실패)"
                ):
                    asyncio.run(
                        gen.generate_scene_images(
                            prompts=[{"scene_id": 1, "prompt": "test"}],
                            output_dir=tmp_path,
                        )
                    )


class TestImageSelectorsValid:
    def test_required_keys_present(self):
        from src.illustrator.freepik_image_selectors import IMAGE_SELECTORS

        required = {
            "prompt_input",
            "generate_button",
            "model_selector_trigger",
            "all_models_button",
            "aspect_ratio_trigger",
        }
        assert required.issubset(IMAGE_SELECTORS.keys())

    def test_unlimited_models_in_map(self):
        from src.illustrator.freepik_image_selectors import IMAGE_MODEL_DATA_CY

        # All three default priority models must exist
        for model in ["Google Nano Banana Pro", "GPT Image 1.5", "Flux.2 Max"]:
            assert model in IMAGE_MODEL_DATA_CY, (
                f"{model} missing — add to IMAGE_MODEL_DATA_CY"
            )
        assert (
            IMAGE_MODEL_DATA_CY["Google Nano Banana Pro"]
            == "ai-model-item-imagen-nano-banana-2"
        )


class TestImageGeneratorBranch:
    """image_generator.generate_scene_images should route to freepik backend."""

    def test_provider_freepik_calls_freepik(self, tmp_path):
        from src.illustrator import image_generator
        from src.analyzer.script_models import ShortsScript

        # Build a minimal ShortsScript using from_dict
        script = ShortsScript.from_dict({
            "metadata": {
                "title": "test",
                "emotion_type": "funny",
                "duration": 30,
                "source_type": "topic",
            },
            "scenes": [
                {
                    "id": 1, "timestamp": 0, "duration": 5, "type": "title",
                    "text": "t", "voice_text": "t", "emphasis": False,
                },
            ],
            "audio_config": {
                "tts_script": "hi", "voice": "ko-KR-SunHiNeural",
                "rate": "+0%", "pitch": "+0Hz",
            },
            "background_config": {"type": "gradient", "colors": ["#fff", "#000"]},
        })

        called = {"freepik": False}

        def fake_freepik(**kwargs):
            called["freepik"] = True
            return [{"scene_id": 1, "image_path": "fake.png", "prompt": "x"}]

        with patch.object(image_generator, "_generate_via_freepik", fake_freepik):
            result = image_generator.generate_scene_images(
                script=script,
                output_dir=tmp_path,
                provider="freepik",
            )

        assert called["freepik"]
        assert len(result) == 1
