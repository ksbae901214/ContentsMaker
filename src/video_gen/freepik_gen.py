"""Freepik AI video generator via browser automation.

Automates https://www.freepik.com/ai/video-generator using Playwright.
Requires a one-time manual login (run `python3 -m src.main freepik_login`).

Think of this as a remote-control intern: the intern opens freepik.com in a
browser with your saved session, types your prompt, selects 9:16 aspect ratio,
clicks Generate, waits for the video to render, and downloads it.

Subscription requirements:
  - freepik.com Essential ($9.99/month) or higher
  - Each 9-second video costs ~2,600 AI credits
  - Essential plan gives 8,000 credits/month (~3 clips/month)
  - Premium+ ($24.50/month) gives 45,000 credits/month (~17 clips/month)

Cloudflare notice:
  Freepik uses Cloudflare protection. Automation is attempted using the
  user's real Chrome browser (channel="chrome") which is harder to detect.
  If blocked, run freepik_login in headed mode and complete any CAPTCHA manually.

This generator overrides `generate_and_wait()` because the browser session
must stay alive across the full prompt → wait → download flow.
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
    FREEPIK_VIDEO_URL,
)
from src.video_gen.base import (
    VideoGenerationError,
    VideoGeneratorBase,
    VideoResult,
    VideoStatus,
)
from src.video_gen.freepik_selectors import FREEPIK_VIDEO_URL as VIDEO_URL, SELECTORS

logger = logging.getLogger(__name__)


class FreepikError(VideoGenerationError):
    """Raised when Freepik browser automation fails."""


class FreepikBrowserGenerator(VideoGeneratorBase):
    """Browser-automation video generator for freepik.com."""

    def __init__(self, headless: bool | None = None) -> None:
        self.profile_dir = FREEPIK_PROFILE_DIR
        self.headless = FREEPIK_HEADLESS if headless is None else headless

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
        """Approximate cost based on Essential plan ($9.99/8000 credits, ~2600/clip)."""
        # $9.99 / 8000 credits * 2600 credits per 9s clip ≈ $0.032 per clip
        # Scale linearly by duration (9s = base)
        cost_per_9s = 9.99 / 8000 * 2600
        return round(cost_per_9s * (duration / 9.0), 4)

    # ─────────────── main flow ───────────────

    async def generate_and_wait(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
        output_path: str | None = None,
        poll_interval: float = 10.0,
        max_wait: float = 600.0,
    ) -> VideoResult:
        """Generate one video clip via Freepik and download it.

        Opens a Playwright browser with the persistent profile, navigates to
        freepik.com/ai/video-generator, submits the prompt, waits for the video
        to render, and downloads it to `output_path`.
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
                existing_urls = await self._get_video_urls(page)
                await self._submit_prompt(page, prompt, duration, resolution)
                video_url = await self._wait_for_new_video(page, existing_urls, max_wait)
                return await self._download_video(
                    video_url, output_path, prompt, duration, resolution
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

    async def _submit_prompt(
        self, page, prompt: str, duration: float, resolution: str
    ) -> None:
        """Fill in the prompt, select 9:16, and click Generate."""
        logger.info("프롬프트 입력: %s", prompt[:60])

        await page.fill(SELECTORS["prompt_input"], prompt)
        await page.wait_for_timeout(500)

        # Try to select 9:16 aspect ratio
        trigger = SELECTORS.get("aspect_ratio_trigger")
        aspect_opt = SELECTORS.get("aspect_9_16_option")
        if trigger and aspect_opt:
            try:
                await page.click(trigger, timeout=5000)
                await page.wait_for_timeout(500)
                await page.click(aspect_opt, timeout=5000)
                await page.wait_for_timeout(500)
                await page.keyboard.press("Escape")
                logger.info("9:16 aspect ratio 선택")
            except Exception as e:
                logger.warning("9:16 선택 스킵 (기본 비율로 진행): %s", e)

        # Click Generate
        await page.click(SELECTORS["generate_button"])
        logger.info("생성 요청 전송")

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

        logger.info("영상 다운로드 완료: %s", out)
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
