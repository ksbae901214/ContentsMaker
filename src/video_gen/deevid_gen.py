"""deevid.ai browser automation video generator.

Generates AI video clips by automating the deevid.ai web UI via Playwright.
Unlike API-based generators, this requires:
  1. A one-time manual Google login (run `python3 -m src.main deevid_login`)
  2. A persistent browser profile stored at DEEVID_PROFILE_DIR

Think of this as a remote-control intern: the intern opens deevid.ai in a
browser, types your prompt, clicks Create, waits for the video to render,
and downloads the file. They use the same browser profile every time so
they don't need to log in again.

Free tier limits:
  - 20 credits one-time on signup (~4-10 videos)
  - 720p resolution max
  - Watermark on output
  - Personal use only

This generator overrides `generate_and_wait()` directly because the browser
session must stay alive across the full prompt → wait → download flow. The
abstract `generate()`, `get_status()`, `download()` methods are stubbed.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx

from src.config.settings import (
    DEEVID_HEADLESS,
    DEEVID_PROFILE_DIR,
    DEEVID_URL,
)
from src.video_gen.base import (
    VideoGenerationError,
    VideoGeneratorBase,
    VideoResult,
    VideoStatus,
)
from src.video_gen.deevid_selectors import SELECTORS, TEXT_TO_VIDEO_URL

logger = logging.getLogger(__name__)


class DeevidError(VideoGenerationError):
    """Raised when deevid.ai automation fails."""


class DeevidGenerator(VideoGeneratorBase):
    """Browser-automation video generator for deevid.ai (Veo 3.1)."""

    def __init__(self, headless: bool | None = None) -> None:
        self.profile_dir = DEEVID_PROFILE_DIR
        self.url = DEEVID_URL
        self.headless = DEEVID_HEADLESS if headless is None else headless

    # ─────────────── stubbed abstract methods ───────────────

    async def generate(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "DeevidGenerator does not split generation into separate calls. "
            "Use generate_and_wait() instead — the browser session is per-call."
        )

    async def get_status(self, *args, **kwargs) -> VideoStatus:
        raise NotImplementedError("Use generate_and_wait().")

    async def download(self, *args, **kwargs) -> VideoResult:
        raise NotImplementedError("Use generate_and_wait().")

    def estimate_cost(self, duration: float = 5.0, resolution: str = "720p") -> float:
        """deevid.ai is free (within the 20-credit allotment)."""
        return 0.0

    # ─────────────── main flow ───────────────

    async def generate_and_wait(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
        output_path: str | None = None,
        poll_interval: float = 5.0,
        max_wait: float = 600.0,
    ) -> VideoResult:
        """Generate one video clip via deevid.ai and download it.

        Opens a Playwright browser with the persistent profile, navigates to
        deevid.ai, submits the prompt, waits for the video to render, and
        downloads it to `output_path`. The browser is closed afterward.
        """
        if not output_path:
            raise DeevidError("output_path is required for DeevidGenerator")

        if not self.profile_dir.exists():
            raise DeevidError(
                "deevid.ai 로그인 세션이 없습니다. "
                "터미널에서 `python3 -m src.main deevid_login`을 먼저 실행해주세요."
            )

        # Lazy import — playwright is heavy and only needed when this runs
        from playwright.async_api import async_playwright, TimeoutError as PWTimeout

        _ctx_kwargs: dict = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            accept_downloads=True,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        async with async_playwright() as p:
            # Use system Chrome when available (matches the profile created by deevid_login)
            try:
                ctx = await p.chromium.launch_persistent_context(channel="chrome", **_ctx_kwargs)
            except Exception:
                ctx = await p.chromium.launch_persistent_context(**_ctx_kwargs)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            try:
                await self._goto_home(page)
                if not await self._is_logged_in(page):
                    raise DeevidError(
                        "deevid.ai 로그인 세션이 만료되었습니다. "
                        "`python3 -m src.main deevid_login`을 다시 실행해주세요."
                    )
                existing_urls = await self._get_video_urls(page)
                await self._submit_prompt(page, prompt, duration, resolution)
                video_url = await self._wait_for_new_video(page, existing_urls, max_wait)
                return await self._download_video(
                    video_url, output_path, prompt, duration, resolution
                )
            except PWTimeout as exc:
                raise DeevidError(
                    f"deevid.ai 페이지 작업 시간 초과: {exc}"
                ) from exc
            finally:
                await ctx.close()

    # ─────────────── helpers ───────────────

    async def _goto_home(self, page) -> None:
        """Navigate to the text-to-video page (the actual generator)."""
        logger.info("deevid.ai 접속: %s", TEXT_TO_VIDEO_URL)
        await page.goto(TEXT_TO_VIDEO_URL, wait_until="domcontentloaded")
        # Give SPA frameworks a moment to hydrate
        await page.wait_for_timeout(3000)

    async def _is_logged_in(self, page) -> bool:
        """Heuristic login detection.

        Tries multiple signals: avatar, profile menu, or absence of a "Sign in"
        button. Customize via `SELECTORS["logged_in_marker"]` if the site changes.
        """
        marker = SELECTORS.get("logged_in_marker")
        if marker:
            try:
                await page.wait_for_selector(marker, timeout=5000, state="visible")
                return True
            except Exception:
                pass

        # Fallback: check for absence of login button
        login_btn = SELECTORS.get("login_button")
        if login_btn:
            try:
                visible = await page.is_visible(login_btn)
                return not visible
            except Exception:
                pass

        # If we can't determine, assume logged in (the user has a session dir)
        return True

    async def _submit_prompt(
        self, page, prompt: str, duration: float, resolution: str
    ) -> None:
        logger.info("프롬프트 입력: %s", prompt[:60])

        # Type prompt
        await page.fill(SELECTORS["prompt_input"], prompt)
        await page.wait_for_timeout(500)

        # Try to switch to 9:16 aspect ratio (for YouTube Shorts)
        # The format selector opens a dialog with aspect/duration/resolution options
        format_sel = SELECTORS.get("format_selector")
        aspect_opt = SELECTORS.get("aspect_9_16_option")
        if format_sel and aspect_opt:
            try:
                await page.click(format_sel, timeout=5000)
                await page.wait_for_timeout(500)
                await page.click(aspect_opt, timeout=5000)
                await page.wait_for_timeout(500)
                # Close dialog by clicking outside (if still open)
                await page.keyboard.press("Escape")
                logger.info("9:16 aspect ratio 선택")
            except Exception as e:
                logger.warning("9:16 선택 스킵 (16:9로 진행): %s", e)

        # Model selection — default "Master V2.0" already maps to Veo 3.1 tier
        # Skip unless model_veo_31_option is set (for explicit override)
        if SELECTORS.get("model_selector") and SELECTORS.get("model_veo_31_option"):
            try:
                await page.click(SELECTORS["model_selector"], timeout=5000)
                await page.click(SELECTORS["model_veo_31_option"], timeout=5000)
            except Exception as e:
                logger.warning("모델 선택 스킵: %s", e)

        # Click Create
        await page.click(SELECTORS["create_button"])
        logger.info("생성 요청 전송")

    async def _get_video_urls(self, page) -> set[str]:
        """Return all CDN video URLs currently on the page."""
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
        """Wait until a new video CDN URL appears; return it."""
        no_credits = SELECTORS.get("no_credits_marker")
        elapsed = 0.0
        check_interval = 5.0

        while elapsed < max_wait:
            # Check for credit exhaustion
            if no_credits:
                try:
                    if await page.is_visible(no_credits):
                        raise DeevidError(
                            "deevid.ai 무료 크레딧이 모두 소진되었습니다. "
                            "유료 플랜으로 업그레이드하거나 새 계정이 필요합니다."
                        )
                except DeevidError:
                    raise
                except Exception:
                    pass

            current_urls = await self._get_video_urls(page)
            new_urls = current_urls - existing_urls
            if new_urls:
                # Prefer non-watermarked URL if available; otherwise take any new one
                mp4_urls = [u for u in new_urls if u.endswith(".mp4")]
                chosen = mp4_urls[-1] if mp4_urls else next(iter(new_urls))
                logger.info("영상 생성 완료 (%.0fs): %s", elapsed, chosen)
                return chosen

            await asyncio.sleep(check_interval)
            elapsed += check_interval
            logger.info("생성 대기 중... (%.0fs/%.0fs)", elapsed, max_wait)

        raise DeevidError(
            f"deevid.ai 영상 생성 시간 초과 ({max_wait:.0f}초)"
        )

    async def _download_video(
        self, video_url: str, output_path: str, prompt: str, duration: float, resolution: str
    ) -> VideoResult:
        """Download video from CDN URL directly (no button click needed)."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        logger.info("CDN 다운로드: %s → %s", video_url, out)
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("GET", video_url) as resp:
                resp.raise_for_status()
                with out.open("wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        f.write(chunk)

        logger.info("영상 다운로드 완료: %s", out)

        return VideoResult(
            path=str(out),
            duration_ms=int(duration * 1000),
            resolution=resolution,
            cost_usd=0.0,
            source_image=None,
            prompt=prompt,
        )


# ─────────────── one-time login helper ───────────────


async def interactive_login() -> None:
    """Open a headed browser, let the user log in to deevid.ai, then save profile.

    Called by `python3 -m src.main deevid_login`.
    """
    from playwright.async_api import async_playwright

    DEEVID_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🌐 deevid.ai 브라우저를 엽니다...")
    print(f"   프로필 위치: {DEEVID_PROFILE_DIR}")

    # Anti-detection flags: hide webdriver/automation signals from Google OAuth
    _launch_kwargs: dict = dict(
        user_data_dir=str(DEEVID_PROFILE_DIR),
        headless=False,
        accept_downloads=True,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )

    async with async_playwright() as p:
        # Prefer the user's real Chrome (less detectable) if available
        try:
            ctx = await p.chromium.launch_persistent_context(
                channel="chrome", **_launch_kwargs
            )
            print("   (실제 Chrome 브라우저 사용)")
        except Exception:
            ctx = await p.chromium.launch_persistent_context(**_launch_kwargs)
            print("   (Playwright Chromium 사용)")

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        # Mask webdriver flag via JS
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        await page.goto(DEEVID_URL, wait_until="domcontentloaded")

        print()
        print("👉 브라우저 창에서 deevid.ai에 로그인해주세요 (Google OAuth 권장).")
        print("   로그인이 완료되면 이 터미널로 돌아와서 Enter를 누르세요.")
        print()

        # Block on stdin (sync input is fine — we're not in a tight loop)
        try:
            input("로그인 완료 후 Enter ➜ ")
        except KeyboardInterrupt:
            print("\n취소됨.")
            await ctx.close()
            sys.exit(1)

        # Verify by checking the URL or looking for some logged-in marker
        current_url = page.url
        print(f"✅ 세션 저장됨. 현재 URL: {current_url}")
        await ctx.close()

    print()
    print(f"세션 디렉토리: {DEEVID_PROFILE_DIR}")
    print("이제 영상 생성에서 deevid 제공업체를 사용할 수 있습니다.")


def run_interactive_login() -> int:
    """Sync entry point for the deevid_login CLI command."""
    try:
        asyncio.run(interactive_login())
        return 0
    except Exception as e:
        print(f"\n❌ 로그인 실패: {e}", file=sys.stderr)
        return 1
