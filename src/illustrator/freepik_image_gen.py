"""Freepik AI image generator via browser automation.

Automates https://www.freepik.com/pikaso/ai-image-generator using Playwright,
generating scene-by-scene images in a single browser session. Requires a
one-time manual login (run `python3 -m src.main freepik_login`).

Premium+ unlimited image models (2026-04-08):
  - Google Nano Banana Pro (1K/2K)  ⭐ default
  - GPT Image 1.5 (high quality)
  - Flux.2 Max
  - Google Nano Banana 2 / base, Seedream 5 Lite, Recraft V4, Grok, Flux.2 Pro

The generator picks the model once per session, selects 9:16 aspect ratio,
then iterates through all scene prompts — clearing and re-typing for each.
On model failure, it falls back to the next model in `model_priority`.

Compare with `src/illustrator/image_generator.py` which uses the paid
OpenAI GPT Image API ($0.005/image). This module costs $0/image under
the Premium+ fixed monthly subscription.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import httpx

from src.config.settings import (
    FREEPIK_HEADLESS,
    FREEPIK_IMAGE_MODEL_PRIORITY,
    FREEPIK_IMAGE_URL,
    FREEPIK_PROFILE_DIR,
    PROJECT_ROOT,
)
from src.illustrator.freepik_image_selectors import (
    IMAGE_MODEL_DATA_CY,
    IMAGE_SELECTORS,
)

logger = logging.getLogger(__name__)

DATA_IMAGES_DIR = PROJECT_ROOT / "data" / "images"


class FreepikImageError(Exception):
    """Raised when Freepik image browser automation fails."""


class FreepikImageGenerator:
    """Browser-automation image generator for freepik.com/pikaso.

    Usage:
        gen = FreepikImageGenerator()
        results = await gen.generate_scene_images(
            prompts=[
                {"scene_id": 1, "prompt": "..."},
                {"scene_id": 2, "prompt": "..."},
            ],
            output_dir=Path("data/images"),
        )

    All images within one call share the same browser session + model selection
    + 9:16 aspect ratio, which is much faster than launching Playwright per image.
    """

    def __init__(
        self,
        headless: bool | None = None,
        model_priority: list[str] | None = None,
    ) -> None:
        self.profile_dir = FREEPIK_PROFILE_DIR
        self.headless = FREEPIK_HEADLESS if headless is None else headless
        self.model_priority = list(model_priority or FREEPIK_IMAGE_MODEL_PRIORITY)

    # ─────────────── main entry point ───────────────

    async def generate_scene_images(
        self,
        prompts: list[dict],
        output_dir: Path | None = None,
        aspect_ratio: str = "9:16",
        max_wait_per_image: float = 600.0,  # 10분 — Nano Banana Pro는 보통 30~120s, 여유
        allow_paid: bool = False,
    ) -> list[dict]:
        """Generate one image per prompt.

        Args:
            prompts: List of {"scene_id": int, "prompt": str}.
            output_dir: Where to write PNG files. Defaults to data/images/.
            aspect_ratio: "9:16" for vertical shorts (default) or "1:1" etc.
            max_wait_per_image: Max seconds to wait for one image to render.

        Returns:
            List of {"scene_id": int, "image_path": str, "prompt": str}.
        """
        if not prompts:
            return []

        if not self.profile_dir.exists():
            raise FreepikImageError(
                "Freepik 로그인 세션이 없습니다. "
                "터미널에서 `python3 -m src.main freepik_login`을 먼저 실행해주세요."
            )

        target_dir = output_dir or DATA_IMAGES_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

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

                # Select model (try priority list, fall back on failure)
                selected_model = await self._select_model_with_fallback(page)
                logger.info("이미지 모델 선택됨: %s", selected_model)

                # Select 9:16 aspect ratio once
                await self._select_aspect_ratio(page, aspect_ratio)

                # Generate each prompt sequentially
                results = []
                for i, prompt_data in enumerate(prompts):
                    scene_id = prompt_data["scene_id"]
                    prompt = prompt_data["prompt"]
                    logger.info(
                        "이미지 %d/%d (씬 %d): %s",
                        i + 1, len(prompts), scene_id, prompt[:60],
                    )
                    try:
                        image_path = await self._generate_one(
                            page=page,
                            prompt=prompt,
                            scene_id=scene_id,
                            output_dir=target_dir,
                            max_wait=max_wait_per_image,
                            allow_paid=allow_paid,
                        )
                        results.append({
                            "scene_id": scene_id,
                            "image_path": str(image_path),
                            "prompt": prompt,
                        })
                    except FreepikImageError as exc:
                        logger.warning(
                            "씬 %d 이미지 생성 실패 (스킵): %s", scene_id, exc
                        )

                if not results:
                    raise FreepikImageError("모든 씬 이미지 생성에 실패했습니다")

                logger.info(
                    "이미지 생성 완료: %d/%d장 (Premium+ 무제한, 변동비 $0)",
                    len(results), len(prompts),
                )
                return results
            except PWTimeout as exc:
                raise FreepikImageError(
                    f"Freepik 페이지 작업 시간 초과: {exc}"
                ) from exc
            finally:
                await ctx.close()

    # ─────────────── helpers ───────────────

    async def _goto_generator(self, page) -> None:
        logger.info("Freepik Image 접속: %s", FREEPIK_IMAGE_URL)
        await page.goto(FREEPIK_IMAGE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

    async def _select_model_with_fallback(self, page) -> str:
        """Try each model in priority order, return the one successfully selected."""
        errors: list[str] = []
        for model_name in self.model_priority:
            try:
                await self._select_model(page, model_name)
                return model_name
            except FreepikImageError as exc:
                errors.append(f"{model_name}: {exc}")
                logger.warning("❌ %s 선택 실패: %s", model_name, exc)
                # Reload to reset modal state
                try:
                    await page.goto(
                        FREEPIK_IMAGE_URL, wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(3000)
                except Exception:
                    pass
        raise FreepikImageError(
            "모든 이미지 모델 선택 실패: " + "; ".join(errors)
        )

    async def _select_model(self, page, model_name: str) -> None:
        slug = IMAGE_MODEL_DATA_CY.get(model_name)
        if not slug:
            raise FreepikImageError(
                f"알 수 없는 이미지 모델: {model_name!r}. "
                f"freepik_image_selectors.py IMAGE_MODEL_DATA_CY 참조"
            )

        logger.info("이미지 모델 선택: %s (%s)", model_name, slug)

        trigger_sel = IMAGE_SELECTORS["model_selector_trigger"]
        try:
            await page.click(trigger_sel, timeout=5000)
            await page.wait_for_timeout(1500)
        except Exception as exc:
            raise FreepikImageError(f"모델 트리거 클릭 실패: {exc}") from exc

        # Click "All models" to open full modal
        all_btn_sel = IMAGE_SELECTORS["all_models_button"]
        all_btn = await page.query_selector(all_btn_sel)
        if all_btn:
            await all_btn.click()
            await page.wait_for_timeout(2500)

        # Click target model
        target = await page.query_selector(f'[data-cy="{slug}"]')
        if not target:
            raise FreepikImageError(
                f"모델 '{model_name}' ({slug}) 을 모달에서 찾을 수 없습니다"
            )
        try:
            await target.click(timeout=10000)
        except Exception as exc:
            raise FreepikImageError(
                f"모델 '{model_name}' 클릭 실패: {exc}"
            ) from exc
        await page.wait_for_timeout(1500)

        # Close modal
        backdrop_sel = IMAGE_SELECTORS["model_modal_backdrop"]
        for _ in range(10):
            backdrop = await page.query_selector(backdrop_sel)
            if not backdrop:
                break
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
        await page.wait_for_timeout(800)

    async def _select_aspect_ratio(self, page, aspect_ratio: str) -> None:
        trigger_sel = IMAGE_SELECTORS["aspect_ratio_trigger"]
        ar_btn = await page.query_selector(trigger_sel)
        if not ar_btn:
            logger.warning("aspect_ratio_trigger 미발견, 기본값 유지")
            return

        current = (await ar_btn.inner_text()).strip()
        if aspect_ratio in current:
            logger.info("%s 이미 선택됨", aspect_ratio)
            return

        try:
            await ar_btn.click()
            await page.wait_for_timeout(1500)

            # Find the option in dropdown
            option_sel = IMAGE_SELECTORS["aspect_9_16_option"]
            if aspect_ratio == "9:16" and option_sel:
                await page.click(option_sel, timeout=5000)
            else:
                # Generic text match
                await page.click(f"button:has-text('{aspect_ratio}')", timeout=5000)
            await page.wait_for_timeout(800)
            logger.info("%s aspect ratio 선택", aspect_ratio)
        except Exception as exc:
            logger.warning("%s 선택 실패 (기본값 유지): %s", aspect_ratio, exc)

    async def _check_generate_cost(self, page) -> int:
        """Parse Generate button text → credit cost (0 = free, >0 = credits).

        Pikaso image generator conventions:
            "Generate"             → 0 (free)
            "Generate\\nUnlimited"  → 0 (explicit free indicator)
            "Generate\\n75"         → 75 credits (paid)
            "Upgrade\\n..."         → no credits (plan locked)

        Polls until the button becomes enabled (cost calculation done) so
        the text we read is the final state, not the transient "calculating"
        placeholder.
        """
        # Poll until the button becomes enabled.
        # NOTE: HTML `disabled` attribute returns "" (empty string) when set.
        gen_btn = None
        enabled = False
        for _ in range(60):
            gen_btn = await page.query_selector(IMAGE_SELECTORS["generate_button"])
            if gen_btn:
                disabled = await gen_btn.get_attribute("disabled")
                aria_disabled = await gen_btn.get_attribute("aria-disabled")
                if disabled is None and aria_disabled != "true":
                    enabled = True
                    break
            await page.wait_for_timeout(250)
        if not gen_btn:
            raise FreepikImageError("Generate 버튼을 찾을 수 없습니다.")
        if not enabled:
            raise FreepikImageError(
                "Generate 버튼이 활성화되지 않습니다 (15초 대기 후에도 disabled 상태)"
            )

        text = (await gen_btn.inner_text()).strip()
        if "upgrade" in text.lower():
            raise FreepikImageError("Generate 버튼이 'Upgrade'로 바뀜")

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) <= 1:
            return 0
        cost_line = lines[1].lower()
        if cost_line == "unlimited" or cost_line == "무제한":
            return 0
        try:
            if cost_line.endswith("k"):
                return int(float(cost_line[:-1]) * 1000)
            return int(float(cost_line))
        except (ValueError, TypeError):
            logger.warning("Generate 버튼 텍스트 파싱 실패: %r", text)
            return -1

    async def _generate_one(
        self,
        page,
        prompt: str,
        scene_id: int,
        output_dir: Path,
        max_wait: float,
        allow_paid: bool = False,
    ) -> Path:
        """Generate and download a single image for one prompt.

        If allow_paid=False (default) and the Generate button shows a non-zero
        credit cost, raises FreepikImageError BEFORE clicking Generate.
        """
        # Snapshot existing image URLs
        existing_urls = await self._get_image_urls(page)

        # Clear prompt (Ctrl/Cmd+A → Delete)
        prompt_el = await page.query_selector(IMAGE_SELECTORS["prompt_input"])
        if not prompt_el:
            raise FreepikImageError("프롬프트 입력창 미발견")
        await prompt_el.click()
        await page.wait_for_timeout(200)
        await page.keyboard.press("Meta+A")
        await page.wait_for_timeout(100)
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(300)
        await prompt_el.type(prompt)
        await page.wait_for_timeout(500)

        # ─── Cost guard — abort BEFORE clicking Generate if non-zero ───
        await page.wait_for_timeout(1500)  # let UI settle
        cost = await self._check_generate_cost(page)
        logger.info("이미지 Generate 비용: %d (allow_paid=%s)", cost, allow_paid)
        if cost != 0 and not allow_paid:
            raise FreepikImageError(
                f"이 이미지 생성은 {cost} 크레딧을 차감합니다. "
                f"무제한 모드를 사용하려면 모델/설정을 변경하세요. "
                f"(allow_paid=True로 강제 진행 가능)"
            )

        # Click Generate via page.click — Playwright auto-waits for enabled state.
        await page.click(IMAGE_SELECTORS["generate_button"], timeout=15000)
        await page.wait_for_timeout(2000)

        # Post-click sanity check
        gen_btn = await page.query_selector(IMAGE_SELECTORS["generate_button"])
        if gen_btn:
            text = (await gen_btn.inner_text()).strip().lower()
            if "upgrade" in text:
                raise FreepikImageError(
                    "Freepik 크레딧이 부족합니다 — Generate 클릭 후 Upgrade로 전환됨"
                )

        # Poll for new image
        new_url = await self._wait_for_new_image(
            page, existing_urls, max_wait
        )

        # Download
        return await self._download_image(new_url, output_dir, scene_id)

    async def _get_image_urls(self, page) -> set[str]:
        """Return all CDN image URLs (excluding avatar/thumbnails)."""
        imgs = await page.query_selector_all("img")
        urls: set[str] = set()
        for img in imgs:
            src = await img.get_attribute("src")
            if src and "cdnpk" in src and src.startswith("http"):
                urls.add(src)
        return urls

    async def _wait_for_new_image(
        self, page, existing_urls: set[str], max_wait: float
    ) -> str:
        elapsed = 0.0
        check_interval = 5.0
        while elapsed < max_wait:
            current = await self._get_image_urls(page)
            new = current - existing_urls
            # Prefer PNG rendered images (not thumbnails)
            render_pngs = [u for u in new if "render.png" in u or u.endswith(".png")]
            if render_pngs:
                chosen = render_pngs[0]
                logger.info("이미지 생성 완료 (%.0fs): %s", elapsed, chosen[:100])
                return chosen
            if new:
                chosen = next(iter(new))
                logger.info("이미지 생성 완료 (%.0fs, non-png): %s", elapsed, chosen[:100])
                return chosen
            await asyncio.sleep(check_interval)
            elapsed += check_interval

        raise FreepikImageError(f"이미지 생성 시간 초과 ({max_wait:.0f}초)")

    async def _download_image(
        self, image_url: str, output_dir: Path, scene_id: int
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_scene_{scene_id:02d}.png"
        out_path = output_dir / filename

        logger.info("CDN 이미지 다운로드: %s → %s", image_url[:100], out_path.name)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)

        logger.info("  저장: %s (%.1f KB)", out_path.name, out_path.stat().st_size / 1024)
        return out_path
