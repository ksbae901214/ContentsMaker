"""Freepik AI video generator via browser automation.

Automates https://www.freepik.com/pikaso/ai-video-generator using Playwright.
Requires a one-time manual login (run `python3 -m src.main freepik_login`).

Think of this as a remote-control intern: the intern opens freepik.com in a
browser with your saved session, picks the desired model, types your prompt,
selects 9:16 aspect ratio, clicks Generate, waits for the video to render,
and downloads it.

Premium+ unlimited models (2026-04-08):
  - Kling 2.5            — 720p-1080p, 5-10s, top quality
  - MiniMax Hailuo 2.3 Fast — 768p-1080p, 6-10s, fallback
  - Wan 2.2              — 480p-720p, 5-10s, fallback

The generator tries each model in FREEPIK_VIDEO_MODEL_PRIORITY order,
falling back to the next model on failure. This gives robust "infinite"
generation as long as at least one unlimited model works.

Cloudflare notice:
  Freepik uses Cloudflare protection. Automation uses the user's real Chrome
  (channel="chrome") which is harder to detect. If blocked, run freepik_login
  again and complete any CAPTCHA manually.

This generator overrides `generate_and_wait()` because the browser session
must stay alive across the full select-model → prompt → wait → download flow.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx

from src.config.settings import (
    FREEPIK_HEADLESS,
    FREEPIK_PROFILE_DIR,
    FREEPIK_VIDEO_MODEL_PRIORITY,
    FREEPIK_VIDEO_URL,
)
from src.video_gen.base import (
    VideoGenerationError,
    VideoGeneratorBase,
    VideoResult,
    VideoStatus,
)
from src.video_gen.freepik_selectors import (
    FREEPIK_VIDEO_URL as VIDEO_URL,
    MODEL_DATA_CY,
    SELECTORS,
    UNLIMITED_RESOLUTION_MAP,
)

logger = logging.getLogger(__name__)


class FreepikError(VideoGenerationError):
    """Raised when Freepik browser automation fails."""


class FreepikBrowserGenerator(VideoGeneratorBase):
    """Browser-automation video generator for freepik.com."""

    def __init__(
        self,
        headless: bool | None = None,
        model_priority: list[str] | None = None,
    ) -> None:
        self.profile_dir = FREEPIK_PROFILE_DIR
        self.headless = FREEPIK_HEADLESS if headless is None else headless
        self.model_priority = list(model_priority or FREEPIK_VIDEO_MODEL_PRIORITY)

    # ─────────────── stubbed abstract methods ───────────────

    async def generate(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "FreepikBrowserGenerator does not support separate generate() calls. "
            "Use generate_and_wait() — the browser session is per-call."
        )

    async def get_status(self, *args, **kwargs) -> VideoStatus:
        raise NotImplementedError("Use generate_and_wait().")

    async def download(self, *args, **kwargs) -> VideoResult:
        raise NotImplementedError("Use generate_and_wait().")

    def estimate_cost(self, duration: float = 5.0, resolution: str = "720p") -> float:
        """On Premium+ unlimited models (Kling 2.5 / MiniMax / Wan 2.2),
        per-clip variable cost is $0. The monthly $34 subscription is a fixed
        cost and is not attributed to individual clips here.
        """
        return 0.0

    # ─────────────── main flow ───────────────

    async def generate_and_wait(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
        output_path: str | None = None,
        poll_interval: float = 10.0,
        max_wait: float = 1200.0,  # 20분 — Kling 2.5는 보통 60~120s, 여유롭게
        allow_paid: bool = False,
    ) -> VideoResult:
        """Generate one video clip via Freepik and download it.

        IMPORTANT — Premium+ Unlimited rules (verified 2026-04-08):
            Kling 2.5 / Wan 2.2 / MiniMax Hailuo 2.3 (Fast) all REQUIRE a
            Start image upload. They do NOT support pure text-to-video.
            With Start image at the model's unlimited resolution
            (Kling 2.5 720p / Wan 2.2 480p / MiniMax 768p), the Generate
            button shows "Generate\\nUnlimited" = $0 cost.

            Calling without source_image will leave the button disabled
            and raise FreepikError. Pass source_image to enable generation.

        Cost guard (allow_paid=False default):
            Aborts BEFORE clicking Generate if the button text shows a
            non-zero credit cost. Free states are bare "Generate" or
            "Generate\\nUnlimited". Any "Generate\\n<number>" raises.

        Opens a Playwright browser with the persistent profile, navigates to
        Freepik Pikaso, iterates through `self.model_priority`, and returns
        the first successful result. Each model attempt reuses the same
        browser session (much faster than restarting per model).
        """
        if not output_path:
            raise FreepikError("output_path is required for FreepikBrowserGenerator")

        if not self.profile_dir.exists():
            raise FreepikError(
                "Freepik 로그인 세션이 없습니다. "
                "터미널에서 `python3 -m src.main freepik_login`을 먼저 실행해주세요."
            )

        from playwright.async_api import async_playwright, TimeoutError as PWTimeout

        _ctx_kwargs: dict = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        async with async_playwright() as p:
            # Prefer real Chrome — less detectable by Cloudflare
            try:
                ctx = await p.chromium.launch_persistent_context(
                    channel="chrome", **_ctx_kwargs
                )
                logger.info("실제 Chrome 브라우저 사용")
            except Exception:
                ctx = await p.chromium.launch_persistent_context(**_ctx_kwargs)
                logger.info("Playwright Chromium 사용")

            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            try:
                await self._goto_generator(page)
                if not await self._is_logged_in(page):
                    raise FreepikError(
                        "Freepik 로그인 세션이 만료되었습니다. "
                        "`python3 -m src.main freepik_login`을 다시 실행해주세요."
                    )

                # Try each model in priority order, falling back on failure
                errors: list[str] = []
                for model_name in self.model_priority:
                    try:
                        logger.info("모델 시도: %s", model_name)
                        await self._select_model(page, model_name)
                        # Force the resolution to the unlimited tier for this model
                        # (Kling 2.5 → 720p, Wan 2.2 → 480p, etc.).
                        # Without this, the UI keeps the previous resolution and
                        # the Generate button stays disabled with "Switch to
                        # Unlimited mode" warning OR shows credit cost.
                        target_res = UNLIMITED_RESOLUTION_MAP.get(model_name)
                        if target_res:
                            await self._select_resolution(page, target_res)
                        # Upload source image (if provided) AFTER model selection
                        # so that Kling 2.5 activates its Start/End frame mode.
                        # NOTE: source_image triggers paid mode (~160 credits)
                        # even on Premium+. Cost guard below catches this.
                        if source_image:
                            await self._upload_start_image(page, source_image)
                        existing_urls = await self._get_video_urls(page)
                        await self._submit_prompt(
                            page, prompt, duration, resolution,
                            allow_paid=allow_paid,
                        )
                        video_url = await self._wait_for_new_video(
                            page, existing_urls, max_wait
                        )
                        logger.info("✅ %s로 영상 생성 성공", model_name)
                        return await self._download_video(
                            video_url, output_path, prompt, duration, resolution,
                            model_name=model_name,
                        )
                    except FreepikError as exc:
                        errors.append(f"{model_name}: {exc}")
                        logger.warning(
                            "❌ %s 실패, 다음 모델로 재시도: %s", model_name, exc
                        )
                        # Reset the page for the next attempt
                        try:
                            await self._reset_page(page)
                        except Exception as reset_exc:
                            logger.warning("페이지 초기화 실패: %s", reset_exc)
                            # Hard reload as fallback
                            try:
                                await page.goto(
                                    VIDEO_URL, wait_until="domcontentloaded"
                                )
                                await page.wait_for_timeout(3000)
                            except Exception:
                                pass

                raise FreepikError(
                    "모든 모델에서 영상 생성 실패: " + "; ".join(errors)
                )
            except PWTimeout as exc:
                raise FreepikError(
                    f"Freepik 페이지 작업 시간 초과: {exc}"
                ) from exc
            finally:
                await ctx.close()

    # ─────────────── helpers ───────────────

    async def _goto_generator(self, page) -> None:
        """Navigate to the Freepik AI video generator page."""
        logger.info("Freepik 접속: %s", VIDEO_URL)
        await page.goto(VIDEO_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

    async def _is_logged_in(self, page) -> bool:
        """Detect login state via logged_in_marker or absence of login button."""
        marker = SELECTORS.get("logged_in_marker")
        if marker:
            try:
                await page.wait_for_selector(marker, timeout=5000, state="visible")
                return True
            except Exception:
                pass

        login_btn = SELECTORS.get("login_button")
        if login_btn:
            try:
                visible = await page.is_visible(login_btn)
                return not visible
            except Exception:
                pass

        return True  # assume logged in if profile dir exists

    async def _select_model(self, page, model_name: str) -> None:
        """Open the model dropdown → click 'All models' → pick the target model.

        Uses the stable `data-cy="ai-model-item-<slug>"` attributes. The slug
        is resolved from `MODEL_DATA_CY[model_name]`.

        Raises FreepikError if the model is not in the map or not clickable.
        """
        slug = MODEL_DATA_CY.get(model_name)
        if not slug:
            raise FreepikError(
                f"알 수 없는 모델: {model_name!r}. "
                f"src/video_gen/freepik_selectors.py MODEL_DATA_CY 참조"
            )

        logger.info("모델 선택: %s (%s)", model_name, slug)

        # 1. Open the current model button to reveal dropdown
        trigger_sel = SELECTORS.get("model_dropdown_trigger")
        if not trigger_sel:
            raise FreepikError("model_dropdown_trigger 셀렉터 없음")
        try:
            await page.click(trigger_sel, timeout=5000)
            await page.wait_for_timeout(1500)
        except Exception as exc:
            raise FreepikError(f"모델 드롭다운 열기 실패: {exc}") from exc

        # 2. Click "All models" to open the full modal
        all_btn = await page.query_selector(SELECTORS["all_models_button"])
        if all_btn:
            await all_btn.click()
            await page.wait_for_timeout(2500)

        # 3. Click the target model by its stable data-cy.
        # IMPORTANT: Use a JS click via page.evaluate. The Pikaso modal
        # has overlay elements that intercept Playwright pointer events,
        # making regular .click() silently no-op (verified 2026-04-08).
        result = await page.evaluate(
            """(slug) => {
                const btn = document.querySelector(`[data-cy="${slug}"]`);
                if (!btn) return false;
                btn.click();
                return true;
            }""",
            slug,
        )
        if not result:
            raise FreepikError(
                f"모델 '{model_name}' ({slug}) 을 모달에서 찾을 수 없습니다"
            )
        await page.wait_for_timeout(1500)

        # 4. Close the modal (Escape) and wait for backdrop to disappear
        backdrop_sel = SELECTORS.get("model_modal_backdrop")
        for _ in range(10):
            backdrop = (
                await page.query_selector(backdrop_sel) if backdrop_sel else None
            )
            if not backdrop:
                break
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
        await page.wait_for_timeout(800)
        logger.info("모델 선택 완료: %s", model_name)

    async def _select_resolution(self, page, target_resolution: str) -> None:
        """Pick a specific resolution from the [data-cy='video-resolution-option']
        popover. The button text shows the currently selected resolution
        (e.g. "720", "480"). Clicking opens a popover with `popover-option`
        items labeled like "720p", "480p", "768p".

        target_resolution is the desired label without the 'p' (e.g. "720")
        OR with it ("720p"). We try both forms.

        If the resolution selector is missing OR the target option is not
        available for the current model, logs a warning and continues.
        """
        trigger_sel = SELECTORS.get("resolution_trigger")
        if not trigger_sel:
            return

        trigger = await page.query_selector(trigger_sel)
        if not trigger:
            logger.info("해상도 셀렉터 미발견 — 기본값 유지")
            return

        # Normalize: ensure both forms ("720" and "720p")
        target_p = target_resolution if target_resolution.endswith("p") else f"{target_resolution}p"
        target_no_p = target_resolution.rstrip("p")

        current = (await trigger.inner_text()).strip()
        if current == target_no_p or current == target_p:
            logger.info("해상도 이미 %s 선택됨", target_p)
            return

        logger.info("해상도 변경: %s → %s", current, target_p)
        try:
            await trigger.click()
            await page.wait_for_timeout(1500)

            # Find the popover option with matching text
            options = await page.query_selector_all('[data-cy="popover-option"]')
            chosen = None
            for opt in options:
                txt = (await opt.inner_text()).strip()
                if txt == target_p or txt == target_no_p:
                    chosen = opt
                    break

            if chosen:
                await chosen.click()
                await page.wait_for_timeout(800)
                logger.info("✅ 해상도 %s 선택", target_p)
            else:
                logger.warning(
                    "해상도 옵션 %s 미발견 (popover에 없음) — Escape로 닫음",
                    target_p,
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
        except Exception as exc:
            logger.warning("해상도 선택 실패 (%s): %s", target_p, exc)
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    async def _upload_start_image(self, page, source_image: str) -> None:
        """Upload a source image to the Start frame input (image-to-video).

        Requires that a model supporting Start frame (e.g. Kling 2.5) was
        already selected. Uses Playwright's `set_input_files()` directly on
        the first image file input — this bypasses the visible click flow
        and doesn't require the "Start image" button to be activated first.

        On success the UI shows a thumbnail preview of the uploaded image
        inside `[data-cy="video-start-frame-input"]`.
        """
        from pathlib import Path as _Path

        src_path = _Path(source_image)
        if not src_path.exists():
            raise FreepikError(f"Source image not found: {source_image}")

        logger.info("Start image 업로드: %s", src_path.name)

        inputs = await page.query_selector_all(SELECTORS["image_file_inputs"])
        if not inputs:
            raise FreepikError(
                "이미지 업로드 input 미발견. Start image 지원 모델인지 확인하세요"
                " (예: Kling 2.5)"
            )

        try:
            # The first image/* input is the Start frame upload.
            await inputs[0].set_input_files(str(src_path))
        except Exception as exc:
            raise FreepikError(
                f"Start image 업로드 실패: {exc}"
            ) from exc

        # Wait for upload → preview to appear
        await page.wait_for_timeout(4000)

        # Verify preview appeared inside the start-frame container
        start_el = await page.query_selector(SELECTORS["start_image_trigger"])
        if start_el:
            preview = await start_el.query_selector("img")
            if preview:
                logger.info("✅ Start image 업로드 & 프리뷰 확인됨")
            else:
                logger.warning("Start image 업로드 후 프리뷰 <img> 미발견 (진행 계속)")

    async def _reset_page(self, page) -> None:
        """Clear the prompt input and any modal overlay — for fallback retries."""
        # Close any open modal first
        backdrop_sel = SELECTORS.get("model_modal_backdrop")
        for _ in range(5):
            backdrop = (
                await page.query_selector(backdrop_sel) if backdrop_sel else None
            )
            if not backdrop:
                break
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)

        # Clear the contenteditable prompt
        ce = await page.query_selector(SELECTORS["prompt_input"])
        if ce:
            await ce.click()
            await page.wait_for_timeout(200)
            # Select all + delete
            await page.keyboard.press("Meta+A")  # macOS
            await page.wait_for_timeout(100)
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(300)

    async def _check_generate_cost(self, page) -> int:
        """Parse the Generate button text and return the credit cost.

        Pikaso Generate button conventions (verified 2026-04-08):
            "Generate"             → 0 credits (truly free, video gen)
            "Generate\\nUnlimited"  → 0 credits (truly free, image gen)
            "Generate\\n160"        → 160 credits (paid, e.g. image-to-video)
            "Generate\\n2080"       → 2080 credits (paid, e.g. Veo 3.1)
            "Upgrade\\n..."         → button changed to upgrade CTA (no credits)

        IMPORTANT: Pikaso disables the Generate button briefly while
        calculating cost (after model/prompt change). We poll until enabled
        before reading the text — otherwise we'd see stale "Generate" text
        and falsely report 0 credits.

        Returns:
            int: 0 if free, otherwise the credit cost.

        Raises:
            FreepikError: if the button is missing or shows "Upgrade".
        """
        # Poll until the button becomes enabled (cost calculation done).
        # NOTE: HTML `disabled` attribute returns "" (empty string) when set,
        # NOT None — so we must explicitly check for is None to detect absence.
        gen_btn = None
        enabled = False
        for _ in range(60):  # up to ~15 seconds
            gen_btn = await page.query_selector(SELECTORS["generate_button"])
            if gen_btn:
                disabled = await gen_btn.get_attribute("disabled")
                aria_disabled = await gen_btn.get_attribute("aria-disabled")
                # disabled is None only when the attribute is absent.
                # disabled = "" means <button disabled> (still disabled).
                if disabled is None and aria_disabled != "true":
                    enabled = True
                    break
            await page.wait_for_timeout(250)
        if not gen_btn:
            raise FreepikError("Generate 버튼을 찾을 수 없습니다.")
        if not enabled:
            # Diagnose why
            panel = await page.query_selector("[data-cy='video-generator-panel']")
            panel_text = (await panel.inner_text()).strip() if panel else "(panel 미발견)"
            raise FreepikError(
                f"Generate 버튼이 활성화되지 않습니다. 패널 상태:\n{panel_text}"
            )

        text = (await gen_btn.inner_text()).strip()
        if "upgrade" in text.lower():
            raise FreepikError(
                "Generate 버튼이 'Upgrade'로 바뀜 — 크레딧 부족 또는 플랜 제약"
            )

        # Find the second line (after "Generate")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) <= 1:
            return 0  # bare "Generate" — free
        cost_line = lines[1].lower()
        if cost_line == "unlimited" or cost_line == "무제한":
            return 0  # explicit free indicator (image gen)
        # Otherwise expect a numeric cost (e.g. "160", "2080", "1.2K")
        try:
            # Strip K/k suffix and convert
            if cost_line.endswith("k"):
                return int(float(cost_line[:-1]) * 1000)
            return int(float(cost_line))
        except (ValueError, TypeError):
            # Unrecognized format — be conservative and treat as paid
            logger.warning("Generate 버튼 텍스트 파싱 실패: %r — paid로 간주", text)
            return -1  # sentinel: unparseable, treat as paid

    async def _submit_prompt(
        self,
        page,
        prompt: str,
        duration: float,
        resolution: str,
        allow_paid: bool = False,
    ) -> None:
        """Fill in the prompt, ensure 9:16, then click Generate (with cost guard).

        Assumes the desired model has already been selected via _select_model.

        If allow_paid=False (default) and the Generate button shows a non-zero
        credit cost, raises FreepikError BEFORE clicking — no credits are spent.
        """
        logger.info("프롬프트 입력: %s", prompt[:60])

        # Prompt input is a contenteditable div — must click then type
        prompt_el = await page.query_selector(SELECTORS["prompt_input"])
        if not prompt_el:
            raise FreepikError("프롬프트 입력창을 찾을 수 없습니다.")
        await prompt_el.click()
        await page.wait_for_timeout(300)
        await prompt_el.type(prompt)
        await page.wait_for_timeout(500)

        # Try to select 9:16 aspect ratio if not already selected
        trigger = SELECTORS.get("aspect_ratio_trigger")
        aspect_opt = SELECTORS.get("aspect_9_16_option")
        if trigger and aspect_opt:
            try:
                ar_btn = await page.query_selector(trigger)
                if ar_btn:
                    current_text = (await ar_btn.inner_text()).strip()
                    if "9:16" not in current_text:
                        await ar_btn.click()
                        await page.wait_for_timeout(1000)
                        await page.click(aspect_opt, timeout=5000)
                        await page.wait_for_timeout(500)
                        logger.info("9:16 aspect ratio 선택")
                    else:
                        logger.info("9:16 이미 선택됨")
            except Exception as e:
                logger.warning("9:16 선택 스킵 (기본 비율로 진행): %s", e)

        # ─── Cost guard — check BEFORE clicking Generate ───
        await page.wait_for_timeout(1500)  # let UI settle so button text updates
        cost = await self._check_generate_cost(page)
        logger.info("Generate 비용: %d 크레딧 (allow_paid=%s)", cost, allow_paid)
        if cost != 0 and not allow_paid:
            raise FreepikError(
                f"이 설정은 {cost} 크레딧을 차감합니다. 무제한 플랜에서만 사용하려면 "
                f"image-to-video(source_image)를 제거하거나 다른 모델로 폴백하세요. "
                f"강제로 진행하려면 allow_paid=True를 전달하세요."
            )

        # Click Generate via page.click — Playwright auto-waits for enabled state.
        # This avoids stale ElementHandle issues from the cost check above.
        await page.click(SELECTORS["generate_button"], timeout=15000)
        await page.wait_for_timeout(2000)

        # Post-click sanity check — ensure button didn't flip to Upgrade
        gen_btn = await page.query_selector(SELECTORS["generate_button"])
        if gen_btn:
            btn_text = (await gen_btn.inner_text()).strip().lower()
            if "upgrade" in btn_text:
                raise FreepikError(
                    "Freepik 크레딧이 부족합니다 — Generate 클릭 후 Upgrade로 전환됨"
                )
        logger.info("생성 요청 전송 (비용: %d 크레딧)", cost)

    async def _get_video_urls(self, page) -> set[str]:
        """Return all CDN video URLs currently rendered on the page."""
        els = await page.query_selector_all("video[src]")
        urls: set[str] = set()
        for el in els:
            src = await el.get_attribute("src")
            if src and src.startswith("http"):
                urls.add(src)
        return urls

    async def _wait_for_new_video(
        self, page, existing_urls: set[str], max_wait: float
    ) -> str:
        """Poll until a new video CDN URL appears; return it."""
        no_credits = SELECTORS.get("no_credits_marker")
        elapsed = 0.0
        check_interval = 10.0

        while elapsed < max_wait:
            if no_credits:
                try:
                    if await page.is_visible(no_credits):
                        raise FreepikError(
                            "Freepik AI 크레딧이 부족합니다. "
                            "구독 플랜의 월 크레딧 한도를 확인하세요."
                        )
                except FreepikError:
                    raise
                except Exception:
                    pass

            current_urls = await self._get_video_urls(page)
            new_urls = current_urls - existing_urls
            if new_urls:
                mp4_urls = [u for u in new_urls if ".mp4" in u]
                chosen = mp4_urls[-1] if mp4_urls else next(iter(new_urls))
                logger.info("영상 생성 완료 (%.0fs): %s", elapsed, chosen)
                return chosen

            await asyncio.sleep(check_interval)
            elapsed += check_interval
            logger.info("생성 대기 중... (%.0fs/%.0fs)", elapsed, max_wait)

        raise FreepikError(f"Freepik 영상 생성 시간 초과 ({max_wait:.0f}초)")

    async def _download_video(
        self,
        video_url: str,
        output_path: str,
        prompt: str,
        duration: float,
        resolution: str,
        model_name: str | None = None,
    ) -> VideoResult:
        """Stream-download from CDN URL to disk."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        logger.info("CDN 다운로드: %s → %s", video_url, out)
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("GET", video_url) as resp:
                resp.raise_for_status()
                with out.open("wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        f.write(chunk)

        logger.info(
            "영상 다운로드 완료: %s (모델: %s)", out, model_name or "unknown"
        )
        return VideoResult(
            path=str(out),
            duration_ms=int(duration * 1000),
            resolution=resolution,
            cost_usd=self.estimate_cost(duration, resolution),
            source_image=None,
            prompt=prompt,
        )


# ─────────────── one-time login helper ───────────────


async def interactive_login() -> None:
    """Open a headed browser for one-time manual Freepik login.

    Called by `python3 -m src.main freepik_login`.
    Saves the browser profile to FREEPIK_PROFILE_DIR so subsequent runs
    can reuse the session without logging in again.

    Tip: Use email/password login (not Google OAuth) — it's more stable
    for automated browser sessions and avoids Google's bot-detection.
    """
    from playwright.async_api import async_playwright

    FREEPIK_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print("🌐 Freepik 브라우저를 엽니다...")
    print(f"   프로필 위치: {FREEPIK_PROFILE_DIR}")

    _launch_kwargs: dict = dict(
        user_data_dir=str(FREEPIK_PROFILE_DIR),
        headless=False,
        accept_downloads=True,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )

    async with async_playwright() as p:
        try:
            ctx = await p.chromium.launch_persistent_context(
                channel="chrome", **_launch_kwargs
            )
            print("   (실제 Chrome 브라우저 사용)")
        except Exception:
            ctx = await p.chromium.launch_persistent_context(**_launch_kwargs)
            print("   (Playwright Chromium 사용)")

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        await page.goto("https://www.freepik.com/log-in", wait_until="domcontentloaded")

        print()
        print("👉 브라우저 창에서 Freepik에 로그인해주세요.")
        print("   권장: 이메일/비밀번호 로그인 (Google OAuth보다 안정적)")
        print("   로그인 완료 후 AI 영상 생성 페이지까지 이동해주세요.")
        print(f"   URL: {VIDEO_URL}")
        print()

        try:
            input("로그인 완료 후 Enter ➜ ")
        except KeyboardInterrupt:
            print("\n취소됨.")
            await ctx.close()
            sys.exit(1)

        current_url = page.url
        print(f"✅ 세션 저장됨. 현재 URL: {current_url}")
        await ctx.close()

    print()
    print(f"세션 디렉토리: {FREEPIK_PROFILE_DIR}")
    print("이제 영상 생성에서 freepik 제공업체를 사용할 수 있습니다.")


def run_interactive_login() -> int:
    """Sync entry point for the freepik_login CLI command."""
    try:
        asyncio.run(interactive_login())
        return 0
    except Exception as e:
        print(f"\n❌ 로그인 실패: {e}", file=sys.stderr)
        return 1
