"""Tests for FreepikBrowserGenerator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.video_gen.base import VideoResult
from src.video_gen.freepik_gen import FreepikBrowserGenerator, FreepikError


class TestEstimateCost:
    """estimate_cost should scale with duration."""

    def test_default(self):
        gen = FreepikBrowserGenerator()
        cost = gen.estimate_cost()
        assert cost > 0.0

    def test_scales_with_duration(self):
        gen = FreepikBrowserGenerator()
        cost_5s = gen.estimate_cost(duration=5.0)
        cost_10s = gen.estimate_cost(duration=10.0)
        assert cost_10s == pytest.approx(cost_5s * 2, rel=0.01)

    def test_returns_float(self):
        gen = FreepikBrowserGenerator()
        assert isinstance(gen.estimate_cost(), float)


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
        """Mock for the contenteditable prompt input element."""
        el = MagicMock()
        el.click = AsyncMock()
        el.type = AsyncMock()
        return el

    def _make_ar_btn(self, current_ratio="9:16"):
        """Mock for the aspect ratio button (shows current selection)."""
        btn = MagicMock()
        btn.inner_text = AsyncMock(return_value=current_ratio)
        btn.click = AsyncMock()
        return btn

    def _make_gen_btn(self, after_click_text="Generate"):
        """Mock for the generate button.

        after_click_text simulates the button text after click:
        - "Generate": normal state → generation proceeds
        - "Upgrade": credits exhausted → FreepikError raised
        """
        btn = MagicMock()
        btn.inner_text = AsyncMock(return_value=after_click_text)
        btn.click = AsyncMock()
        return btn

    def _make_mock_page(self, new_video_after_polls=2, upgrade_after_click=False):
        """Build a mock page that simulates the Freepik video generator DOM."""
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.add_init_script = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.wait_for_selector = AsyncMock(return_value=MagicMock())

        prompt_el = self._make_prompt_el()
        ar_btn = self._make_ar_btn(current_ratio="9:16")  # already 9:16 — no re-selection
        gen_btn = self._make_gen_btn(
            after_click_text="Upgrade" if upgrade_after_click else "Generate"
        )

        async def query_selector(selector):
            if "contenteditable" in selector:
                return prompt_el
            if "aspect-ratio" in selector:
                return ar_btn
            if "generate-button" in selector:
                return gen_btn
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

        async def is_visible(sel):
            return False

        page.is_visible = AsyncMock(side_effect=is_visible)
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
        assert result.cost_usd > 0.0

    def test_no_credits_raises(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = FreepikBrowserGenerator()
        gen.profile_dir = profile

        page = self._make_mock_page(upgrade_after_click=True)
        playwright_ctx = self._patch_playwright(page)

        async def fake_sleep(_):
            pass

        with patch("playwright.async_api.async_playwright", return_value=playwright_ctx):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with pytest.raises(FreepikError, match="크레딧"):
                    asyncio.run(
                        gen.generate_and_wait(
                            prompt="test",
                            output_path=str(tmp_path / "out.mp4"),
                        )
                    )


class TestSelectorsValid:
    """Selectors module should be importable and have required keys."""

    def test_required_keys_present(self):
        from src.video_gen.freepik_selectors import SELECTORS

        required = {"prompt_input", "generate_button", "no_credits_marker"}
        assert required.issubset(SELECTORS.keys())

    def test_video_url_format(self):
        from src.video_gen.freepik_selectors import FREEPIK_VIDEO_URL

        assert FREEPIK_VIDEO_URL.startswith("https://www.freepik.com/")
        assert "pikaso" in FREEPIK_VIDEO_URL


class TestFactoryRegistration:
    """factory.create_generator should return FreepikBrowserGenerator."""

    def test_freepik_provider(self):
        from src.video_gen.factory import create_generator

        gen = create_generator("freepik")
        assert isinstance(gen, FreepikBrowserGenerator)
