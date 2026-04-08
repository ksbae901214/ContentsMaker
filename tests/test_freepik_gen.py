"""Tests for FreepikBrowserGenerator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.video_gen.base import VideoResult
from src.video_gen.freepik_gen import FreepikBrowserGenerator, FreepikError


class TestEstimateCost:
    """estimate_cost returns 0.0 on Premium+ unlimited models."""

    def test_returns_zero_on_unlimited(self):
        """Premium+ unlimited models have $0 per-clip variable cost."""
        gen = FreepikBrowserGenerator()
        assert gen.estimate_cost() == 0.0

    def test_constant_regardless_of_duration(self):
        """Unlimited = same $0 regardless of duration."""
        gen = FreepikBrowserGenerator()
        assert gen.estimate_cost(duration=5.0) == gen.estimate_cost(duration=10.0) == 0.0

    def test_returns_float(self):
        gen = FreepikBrowserGenerator()
        assert isinstance(gen.estimate_cost(), float)


class TestModelPriority:
    """model_priority should default to settings but be overridable."""

    def test_default_matches_settings(self):
        from src.config.settings import FREEPIK_VIDEO_MODEL_PRIORITY

        gen = FreepikBrowserGenerator()
        assert gen.model_priority == list(FREEPIK_VIDEO_MODEL_PRIORITY)
        # Premium+ unlimited models first
        assert gen.model_priority[0] == "Kling 2.5"

    def test_custom_priority(self):
        gen = FreepikBrowserGenerator(model_priority=["Kling 2.5"])
        assert gen.model_priority == ["Kling 2.5"]

    def test_priority_is_copied(self):
        """Caller's list should not be mutated if model_priority changes."""
        original = ["Kling 2.5", "Wan 2.2"]
        gen = FreepikBrowserGenerator(model_priority=original)
        gen.model_priority.append("Extra")
        assert "Extra" not in original


class TestStubbedAbstractMethods:
    """generate / get_status / download must raise NotImplementedError."""

    def test_generate_raises(self):
        gen = FreepikBrowserGenerator()
        with pytest.raises(NotImplementedError, match="generate_and_wait"):
            asyncio.run(gen.generate(prompt="test"))

    def test_get_status_raises(self):
        gen = FreepikBrowserGenerator()
        with pytest.raises(NotImplementedError):
            asyncio.run(gen.get_status("any-id"))

    def test_download_raises(self):
        gen = FreepikBrowserGenerator()
        with pytest.raises(NotImplementedError):
            asyncio.run(gen.download("any-id", "out.mp4"))


class TestGenerateAndWaitPreconditions:
    """Pre-flight checks before launching the browser."""

    def test_missing_output_path_raises(self):
        gen = FreepikBrowserGenerator()
        with pytest.raises(FreepikError, match="output_path"):
            asyncio.run(gen.generate_and_wait(prompt="test", output_path=None))

    def test_missing_profile_raises(self, tmp_path):
        gen = FreepikBrowserGenerator()
        gen.profile_dir = tmp_path / "nonexistent_profile"
        with pytest.raises(FreepikError, match="freepik_login"):
            asyncio.run(
                gen.generate_and_wait(
                    prompt="test", output_path=str(tmp_path / "out.mp4")
                )
            )


class TestGenerateAndWaitFlow:
    """End-to-end flow with fully mocked Playwright."""

    def _make_prompt_el(self):
        el = MagicMock()
        el.click = AsyncMock()
        el.type = AsyncMock()
        return el

    def _make_ar_btn(self, current_ratio="9:16"):
        btn = MagicMock()
        btn.inner_text = AsyncMock(return_value=current_ratio)
        btn.click = AsyncMock()
        return btn

    def _make_gen_btn(self, after_click_text="Generate"):
        btn = MagicMock()
        btn.inner_text = AsyncMock(return_value=after_click_text)
        btn.click = AsyncMock()
        return btn

    def _make_model_item_el(self):
        """Mock for an ai-model-item-* button in the All models modal."""
        el = MagicMock()
        el.click = AsyncMock()
        return el

    def _make_all_models_btn(self):
        btn = MagicMock()
        btn.click = AsyncMock()
        return btn

    def _make_mock_page(
        self,
        new_video_after_polls=2,
        upgrade_after_click=False,
        model_selectable=True,
    ):
        """Build a mock page that simulates the Freepik video generator DOM.

        model_selectable=False simulates Kling 2.5 not appearing in the modal
        → _select_model raises FreepikError → fallback chain kicks in.
        """
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.add_init_script = AsyncMock()
        page.click = AsyncMock()  # for page.click(trigger_sel) in _select_model
        page.reload = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.wait_for_selector = AsyncMock(return_value=MagicMock())

        prompt_el = self._make_prompt_el()
        ar_btn = self._make_ar_btn(current_ratio="9:16")
        gen_btn = self._make_gen_btn(
            after_click_text="Upgrade" if upgrade_after_click else "Generate"
        )
        all_models_btn = self._make_all_models_btn()
        model_item = self._make_model_item_el() if model_selectable else None

        async def query_selector(selector):
            if "contenteditable" in selector:
                return prompt_el
            if "aspect-ratio" in selector:
                return ar_btn
            if "generate-button" in selector:
                return gen_btn
            if "All models" in selector:
                return all_models_btn
            if selector.startswith("[data-cy=\"ai-model-item-"):
                return model_item
            if "backdrop-blur-lg" in selector:
                # Modal always closed in mock
                return None
            return None

        page.query_selector = AsyncMock(side_effect=query_selector)

        call_state = {"poll_count": 0}
        NEW_VIDEO_URL = "https://cdn.freepik.com/videos/test_new.mp4"

        async def query_selector_all(selector):
            if "video" not in selector:
                return []
            call_state["poll_count"] += 1
            if call_state["poll_count"] <= new_video_after_polls:
                return []
            el = MagicMock()
            el.get_attribute = AsyncMock(return_value=NEW_VIDEO_URL)
            return [el]

        page.query_selector_all = AsyncMock(side_effect=query_selector_all)
        page.is_visible = AsyncMock(return_value=False)
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

    def test_success_flow(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = FreepikBrowserGenerator()
        gen.profile_dir = profile

        page = self._make_mock_page(new_video_after_polls=2)
        playwright_ctx = self._patch_playwright(page)

        async def fake_sleep(_):
            pass

        fake_video_bytes = b"fake freepik mp4 data"

        class _FakeStream:
            status_code = 200
            def raise_for_status(self): pass
            async def aiter_bytes(self, chunk_size=65536):
                yield fake_video_bytes
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        mock_httpx = MagicMock()
        mock_httpx.stream = MagicMock(return_value=_FakeStream())
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=None)

        with patch("playwright.async_api.async_playwright", return_value=playwright_ctx):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("src.video_gen.freepik_gen.httpx.AsyncClient", return_value=mock_httpx):
                    result = asyncio.run(
                        gen.generate_and_wait(
                            prompt="A sunny beach at sunset",
                            duration=5.0,
                            output_path=str(tmp_path / "out.mp4"),
                        )
                    )

        assert isinstance(result, VideoResult)
        assert result.path == str(tmp_path / "out.mp4")
        assert result.duration_ms == 5000
        assert result.prompt == "A sunny beach at sunset"
        assert result.cost_usd == 0.0  # Premium+ unlimited

    def test_fallback_chain_all_fail_raises(self, tmp_path):
        """When every model in priority list returns 'Upgrade',
        the final error should mention all attempted models."""
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = FreepikBrowserGenerator(
            model_priority=["Kling 2.5", "MiniMax Hailuo 2.3 Fast", "Wan 2.2"]
        )
        gen.profile_dir = profile

        page = self._make_mock_page(upgrade_after_click=True)
        playwright_ctx = self._patch_playwright(page)

        async def fake_sleep(_):
            pass

        with patch("playwright.async_api.async_playwright", return_value=playwright_ctx):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with pytest.raises(FreepikError, match="모든 모델"):
                    asyncio.run(
                        gen.generate_and_wait(
                            prompt="test",
                            output_path=str(tmp_path / "out.mp4"),
                        )
                    )


class TestSelectModel:
    """_select_model should fail cleanly for unknown models."""

    def test_unknown_model_raises(self):
        gen = FreepikBrowserGenerator()
        page = MagicMock()  # not called
        with pytest.raises(FreepikError, match="알 수 없는 모델"):
            asyncio.run(gen._select_model(page, "NonExistentModel 99"))

    def test_known_model_uses_data_cy(self):
        """_select_model should look up the slug in MODEL_DATA_CY and click
        the corresponding [data-cy='ai-model-item-<slug>'] element."""
        from src.video_gen.freepik_selectors import MODEL_DATA_CY

        gen = FreepikBrowserGenerator()

        # Build a minimal mock page that records what data-cy was queried
        recorded_selectors = []
        model_item = MagicMock()
        model_item.click = AsyncMock()
        all_models_btn = MagicMock()
        all_models_btn.click = AsyncMock()

        async def query_selector(selector):
            recorded_selectors.append(selector)
            if "All models" in selector:
                return all_models_btn
            if "ai-model-item-" in selector:
                return model_item
            if "backdrop-blur-lg" in selector:
                return None
            return None

        page = MagicMock()
        page.click = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.query_selector = AsyncMock(side_effect=query_selector)

        asyncio.run(gen._select_model(page, "Kling 2.5"))

        # Verify the correct data-cy was queried
        expected_slug = MODEL_DATA_CY["Kling 2.5"]
        assert any(expected_slug in s for s in recorded_selectors), (
            f"Expected [data-cy='{expected_slug}'] in queries, got {recorded_selectors}"
        )
        # Model item was clicked
        assert model_item.click.called


class TestSelectorsValid:
    """Selectors module should be importable and have required keys."""

    def test_required_keys_present(self):
        from src.video_gen.freepik_selectors import SELECTORS

        required = {
            "prompt_input",
            "generate_button",
            "no_credits_marker",
            "model_dropdown_trigger",
            "all_models_button",
        }
        assert required.issubset(SELECTORS.keys())

    def test_video_url_format(self):
        from src.video_gen.freepik_selectors import FREEPIK_VIDEO_URL

        assert FREEPIK_VIDEO_URL.startswith("https://www.freepik.com/")
        assert "pikaso" in FREEPIK_VIDEO_URL

    def test_model_data_cy_has_unlimited_models(self):
        from src.video_gen.freepik_selectors import MODEL_DATA_CY

        # The three Premium+ unlimited models must be present
        for model in ["Kling 2.5", "MiniMax Hailuo 2.3 Fast", "Wan 2.2"]:
            assert model in MODEL_DATA_CY, f"{model} missing from MODEL_DATA_CY"
        assert MODEL_DATA_CY["Kling 2.5"] == "ai-model-item-kling-25"


class TestFactoryRegistration:
    """factory.create_generator should return FreepikBrowserGenerator."""

    def test_freepik_provider(self):
        from src.video_gen.factory import create_generator

        gen = create_generator("freepik")
        assert isinstance(gen, FreepikBrowserGenerator)
