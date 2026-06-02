"""Tests for DeevidGenerator (browser automation video generator).

The browser is fully mocked — no real network calls or chromium launches.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.video_gen.base import VideoResult
from src.video_gen.deevid_gen import (
    DeevidError,
    DeevidGenerator,
)


class TestEstimateCost:
    """deevid.ai is free within the 20-credit allotment → cost is always 0."""

    def test_default(self):
        gen = DeevidGenerator()
        assert gen.estimate_cost() == 0.0

    def test_5s_720p(self):
        gen = DeevidGenerator()
        assert gen.estimate_cost(duration=5.0, resolution="720p") == 0.0

    def test_10s_1080p(self):
        gen = DeevidGenerator()
        assert gen.estimate_cost(duration=10.0, resolution="1080p") == 0.0


class TestStubbedAbstractMethods:
    """generate / get_status / download must raise NotImplementedError.

    Browser-automation generators only support the all-in-one
    generate_and_wait() flow because the browser session can't be split
    across separate calls.
    """

    def test_generate_raises(self):
        gen = DeevidGenerator()
        with pytest.raises(NotImplementedError, match="generate_and_wait"):
            asyncio.run(gen.generate(prompt="test"))

    def test_get_status_raises(self):
        gen = DeevidGenerator()
        with pytest.raises(NotImplementedError):
            asyncio.run(gen.get_status("any-id"))

    def test_download_raises(self):
        gen = DeevidGenerator()
        with pytest.raises(NotImplementedError):
            asyncio.run(gen.download("any-id", "out.mp4"))


class TestGenerateAndWaitPreconditions:
    """Pre-flight validations before launching playwright."""

    def test_missing_output_path_raises(self):
        gen = DeevidGenerator()
        with pytest.raises(DeevidError, match="output_path"):
            asyncio.run(gen.generate_and_wait(prompt="test", output_path=None))

    def test_missing_profile_raises(self, tmp_path):
        gen = DeevidGenerator()
        gen.profile_dir = tmp_path / "nonexistent_profile"
        with pytest.raises(DeevidError, match="로그인 세션이 없습니다"):
            asyncio.run(
                gen.generate_and_wait(prompt="test", output_path=str(tmp_path / "out.mp4"))
            )


class TestGenerateAndWaitFlow:
    """End-to-end flow with fully mocked playwright."""

    def _make_mock_page(
        self,
        new_video_after_polls=2,
        no_credits=False,
    ):
        """Build a mock page that simulates the deevid.ai DOM.

        The page starts with zero video elements; after `new_video_after_polls`
        calls to query_selector_all, a new CDN URL appears to simulate completion.
        """
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        page.add_init_script = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.wait_for_selector = AsyncMock(return_value=MagicMock())

        # Simulate video elements appearing after generation
        call_state = {"poll_count": 0}
        NEW_VIDEO_URL = "https://cdn2.deevid.ai/user-video/v2_test_new.mp4"

        async def query_selector_all(selector):
            if "video" not in selector:
                return []
            call_state["poll_count"] += 1
            if call_state["poll_count"] <= new_video_after_polls:
                return []  # no new video yet
            # Return a mock element with the new video URL
            el = MagicMock()
            el.get_attribute = AsyncMock(return_value=NEW_VIDEO_URL)
            return [el]

        page.query_selector_all = AsyncMock(side_effect=query_selector_all)

        async def is_visible(sel):
            if no_credits and "credits" in sel:
                return True
            return False

        page.is_visible = AsyncMock(side_effect=is_visible)

        return page

    def _patch_playwright(self, page):
        """Mock playwright.async_api.async_playwright() chain."""
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

    def test_success_flow(self, tmp_path, monkeypatch):
        # Pretend the profile dir exists
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = DeevidGenerator()
        gen.profile_dir = profile

        page = self._make_mock_page(new_video_after_polls=2)
        playwright_ctx = self._patch_playwright(page)

        # Stub asyncio.sleep to make polling instant
        async def fake_sleep(_):
            pass

        # Mock httpx download
        fake_video_bytes = b"fake mp4 data"

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
                with patch("src.video_gen.deevid_gen.httpx.AsyncClient", return_value=mock_httpx):
                    result = asyncio.run(
                        gen.generate_and_wait(
                            prompt="A cat walking",
                            duration=5.0,
                            output_path=str(tmp_path / "out.mp4"),
                        )
                    )

        assert isinstance(result, VideoResult)
        assert result.path == str(tmp_path / "out.mp4")
        assert result.cost_usd == 0.0
        assert result.duration_ms == 5000
        assert result.prompt == "A cat walking"
        page.fill.assert_called()

    def test_no_credits_raises(self, tmp_path):
        profile = tmp_path / "profile"
        profile.mkdir()

        gen = DeevidGenerator()
        gen.profile_dir = profile

        page = self._make_mock_page(no_credits=True)
        playwright_ctx = self._patch_playwright(page)

        async def fake_sleep(_):
            pass

        with patch("playwright.async_api.async_playwright", return_value=playwright_ctx):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with pytest.raises(DeevidError, match="크레딧"):
                    asyncio.run(
                        gen.generate_and_wait(
                            prompt="test",
                            output_path=str(tmp_path / "out.mp4"),
                        )
                    )


class TestSelectorsValid:
    """Selectors module should be importable and have the required keys."""

    def test_required_keys_present(self):
        from src.video_gen.deevid_selectors import SELECTORS

        required = {
            "prompt_input",
            "create_button",
            "download_button",
            "no_credits_marker",
        }
        assert required.issubset(SELECTORS.keys())

    def test_text_to_video_url(self):
        from src.video_gen.deevid_selectors import TEXT_TO_VIDEO_URL

        assert TEXT_TO_VIDEO_URL.startswith("https://deevid.ai/")
