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
        # Wan 2.2 480p + start image = Unlimited (confirmed 2026-04-09)
        assert gen.model_priority[0] == "Wan 2.2"

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
        btn.get_attribute = AsyncMock(return_value=None)  # not disabled
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
        # _select_model now uses page.evaluate for JS click on the model item.
        # Returns True if model_selectable=True, False otherwise.
        page.evaluate = AsyncMock(return_value=model_selectable)

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


class TestCheckGenerateCost:
    """_check_generate_cost should parse Generate button text accurately."""

    def _make_page(self, button_text: str):
        gen_btn = MagicMock()
        gen_btn.inner_text = AsyncMock(return_value=button_text)
        gen_btn.get_attribute = AsyncMock(return_value=None)  # not disabled
        page = MagicMock()
        page.query_selector = AsyncMock(return_value=gen_btn)
        page.wait_for_timeout = AsyncMock()
        return page

    def test_bare_generate_is_free(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate")
        assert asyncio.run(gen._check_generate_cost(page)) == 0

    def test_unlimited_label_is_free(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate\nUnlimited")
        assert asyncio.run(gen._check_generate_cost(page)) == 0

    def test_korean_unlimited_is_free(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate\n무제한")
        assert asyncio.run(gen._check_generate_cost(page)) == 0

    def test_numeric_cost_is_paid(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate\n160")
        assert asyncio.run(gen._check_generate_cost(page)) == 160

    def test_high_cost_veo(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate\n2080")
        assert asyncio.run(gen._check_generate_cost(page)) == 2080

    def test_k_suffix_thousand_credits(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate\n1.2K")
        assert asyncio.run(gen._check_generate_cost(page)) == 1200

    def test_upgrade_button_raises(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Upgrade")
        with pytest.raises(FreepikError, match="Upgrade"):
            asyncio.run(gen._check_generate_cost(page))

    def test_unparseable_returns_negative(self):
        gen = FreepikBrowserGenerator()
        page = self._make_page("Generate\nProcessing")
        assert asyncio.run(gen._check_generate_cost(page)) == -1


class TestSubmitPromptCostGuard:
    """_submit_prompt should refuse to click Generate when cost > 0 and allow_paid=False."""

    def _make_mock_page_with_cost(self, cost_text: str):
        prompt_el = MagicMock()
        prompt_el.click = AsyncMock()
        prompt_el.type = AsyncMock()

        ar_btn = MagicMock()
        ar_btn.inner_text = AsyncMock(return_value="9:16")
        ar_btn.click = AsyncMock()

        gen_btn = MagicMock()
        gen_btn.inner_text = AsyncMock(return_value=cost_text)
        gen_btn.get_attribute = AsyncMock(return_value=None)  # not disabled
        gen_btn.click = AsyncMock()

        async def query_selector(selector):
            if "contenteditable" in selector or "image-prompt" in selector:
                return prompt_el
            if "aspect-ratio" in selector:
                return ar_btn
            if "generate-button" in selector:
                return gen_btn
            return None

        page = MagicMock()
        page.query_selector = AsyncMock(side_effect=query_selector)
        page.click = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        return page, gen_btn

    def test_aborts_when_paid_and_not_allowed(self):
        gen = FreepikBrowserGenerator()
        page, gen_btn = self._make_mock_page_with_cost("Generate\n160")
        with pytest.raises(FreepikError, match="160 크레딧"):
            asyncio.run(
                gen._submit_prompt(page, "test", 5.0, "720p", allow_paid=False)
            )
        assert not gen_btn.click.called

    def test_proceeds_when_paid_and_allowed(self):
        gen = FreepikBrowserGenerator()
        page, gen_btn = self._make_mock_page_with_cost("Generate\n160")
        asyncio.run(
            gen._submit_prompt(page, "test", 5.0, "720p", allow_paid=True)
        )
        # Now uses page.click() instead of element.click()
        page.click.assert_any_call(
            "[data-cy='generate-button']", timeout=15000
        )

    def test_proceeds_when_free(self):
        gen = FreepikBrowserGenerator()
        page, gen_btn = self._make_mock_page_with_cost("Generate")
        asyncio.run(
            gen._submit_prompt(page, "test", 5.0, "720p", allow_paid=False)
        )
        page.click.assert_any_call(
            "[data-cy='generate-button']", timeout=15000
        )


class TestUploadStartImage:
    """_upload_start_image should set_input_files on the first image input."""

    def test_missing_source_file_raises(self, tmp_path):
        gen = FreepikBrowserGenerator()
        page = MagicMock()
        with pytest.raises(FreepikError, match="Source image not found"):
            asyncio.run(
                gen._upload_start_image(page, str(tmp_path / "nonexistent.png"))
            )

    def test_no_file_inputs_raises(self, tmp_path):
        gen = FreepikBrowserGenerator()
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        page = MagicMock()
        page.wait_for_timeout = AsyncMock()
        page.query_selector_all = AsyncMock(return_value=[])  # no inputs
        page.query_selector = AsyncMock(return_value=None)

        with pytest.raises(FreepikError, match="이미지 업로드 input"):
            asyncio.run(gen._upload_start_image(page, str(img)))

    def test_calls_set_input_files_on_first_input(self, tmp_path):
        gen = FreepikBrowserGenerator()
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        input_el = MagicMock()
        input_el.set_input_files = AsyncMock()

        start_frame_el = MagicMock()
        preview_img = MagicMock()
        start_frame_el.query_selector = AsyncMock(return_value=preview_img)

        page = MagicMock()
        page.wait_for_timeout = AsyncMock()
        page.query_selector_all = AsyncMock(return_value=[input_el])

        async def qs(sel):
            if "video-start-frame" in sel:
                return start_frame_el
            return None

        page.query_selector = AsyncMock(side_effect=qs)

        asyncio.run(gen._upload_start_image(page, str(img)))

        input_el.set_input_files.assert_called_once_with(str(img))


class TestSelectModel:
    """_select_model should fail cleanly for unknown models."""

    def test_unknown_model_raises(self):
        gen = FreepikBrowserGenerator()
        page = MagicMock()  # not called
        with pytest.raises(FreepikError, match="알 수 없는 모델"):
            asyncio.run(gen._select_model(page, "NonExistentModel 99"))

    def test_known_model_uses_data_cy(self):
        """_select_model should look up the slug in MODEL_DATA_CY and call
        page.evaluate with the JS click for [data-cy='ai-model-item-<slug>']."""
        from src.video_gen.freepik_selectors import MODEL_DATA_CY

        gen = FreepikBrowserGenerator()

        all_models_btn = MagicMock()
        all_models_btn.click = AsyncMock()

        async def query_selector(selector):
            if "All models" in selector:
                return all_models_btn
            if "backdrop-blur-lg" in selector:
                return None
            return None

        recorded_evaluate_args = []

        async def fake_evaluate(js, arg=None):
            recorded_evaluate_args.append((js, arg))
            return True

        page = MagicMock()
        page.click = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.query_selector = AsyncMock(side_effect=query_selector)
        page.evaluate = AsyncMock(side_effect=fake_evaluate)

        asyncio.run(gen._select_model(page, "Kling 2.5"))

        # Verify page.evaluate was called with the right slug
        expected_slug = MODEL_DATA_CY["Kling 2.5"]
        assert any(expected_slug == arg for _, arg in recorded_evaluate_args), (
            f"Expected slug {expected_slug} in evaluate args, got {recorded_evaluate_args}"
        )


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
