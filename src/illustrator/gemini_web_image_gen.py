"""Imagen 4 이미지 생성 (Phase 2A) — gemini.google.com 웹앱 자동화.

2026-05-19 라이브 페이지 탐색 기반 구현:
  1. ESC 2회로 첫 방문 모달 닫기
  2. "🖼️ 이미지 만들기" 도구 버튼 클릭 (한 번이면 세션 유지)
  3. 프롬프트 입력 + 전송
  4. 응답 영역의 ``button.image-button img`` blob URL 감지
  5. 해당 element를 Playwright screenshot으로 PNG 저장 (blob URL은 httpx 불가)

폴백 체인:
  1. gemini (이 모듈)
  2. gpt (OpenAI GPT Image)
  3. 빈 결과 → 그라데이션 배경
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.config.settings import (
    GEMINI_HEADLESS,
    GEMINI_PROFILE_DIR,
    GEMINI_WEB_URL,
    PROJECT_ROOT,
)
from src.illustrator.gemini_web_selectors import (
    GEM_LABS_SELECTORS,
    GEMINI_SELECTORS,
    IMAGE_ASPECT_HINT,
    IMAGE_GENERATION_TIMEOUT_SEC,
    IMAGE_POLL_INTERVAL_SEC,
    IMAGE_PROMPT_PREFIX,
    MODAL_DISMISS_COUNT,
)

logger = logging.getLogger(__name__)

DATA_IMAGES_DIR = PROJECT_ROOT / "data" / "images"


class GeminiWebImageError(Exception):
    """Imagen 4 웹앱 자동화 실패."""


class GeminiWebImageGenerator:
    """gemini.google.com 기반 이미지 생성기 (세션 재사용).

    Usage:
        # 일반 모드 (메인 채팅, 풀 스타일 프롬프트)
        async with GeminiWebImageGenerator() as gen:
            results = await gen.generate_scene_images(
                prompts=[{"scene_id": 1, "prompt": "..."}, ...],
            )

        # Gem 모드 (등록된 Gem으로 이동, 씬 내용만 전송)
        async with GeminiWebImageGenerator(gem_key="webtoon") as gen:
            results = await gen.generate_scene_images(
                prompts=[{"scene_id": 1, "prompt": "야근하는 직장인 사무실"}, ...],
            )
    """

    def __init__(self, *, headless: bool | None = None, gem_key: str | None = None) -> None:
        self.headless = GEMINI_HEADLESS if headless is None else headless
        self.gem_key = gem_key
        self._page = None
        self._context = None
        self._playwright = None
        self._image_tool_activated = False
        # Gem Labs 모드에서 사용하는 opal._app 프레임
        self._opal_frame = None
        # 응답 시 이미 존재하던 이미지 개수 (새 응답 감지용)
        self._image_count_baseline = 0

    async def __aenter__(self) -> "GeminiWebImageGenerator":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        if self._page is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise GeminiWebImageError(
                "playwright 미설치: pip install playwright && playwright install chromium"
            ) from e

        if not GEMINI_PROFILE_DIR.exists():
            raise GeminiWebImageError(
                f"Gemini 세션 없음 ({GEMINI_PROFILE_DIR}). "
                "터미널에서 'python3 -m src.main gemini_login' 먼저 실행하세요."
            )

        self._playwright = await async_playwright().start()
        # 2026-05-19: Google 자동화 차단 회피 — 시스템 Chrome + AutomationControlled OFF
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(GEMINI_PROFILE_DIR),
            channel="chrome",
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._page = (
            self._context.pages[0] if self._context.pages else await self._context.new_page()
        )
        await self._page.goto(GEMINI_WEB_URL)
        await self._page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)

        if await self._page.locator(GEMINI_SELECTORS["login_required_marker"]).count() > 0:
            raise GeminiWebImageError("로그인 세션 만료 — gemini_login 재실행 필요.")

        # 첫 방문 모달 해제 (ESC 키)
        for _ in range(MODAL_DISMISS_COUNT):
            await self._page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

        # Gem Labs 모드: gem_id로 직접 이동 → opal_frame 반환
        if self.gem_key:
            from src.illustrator.gem_navigator import get_gem_config, navigate_to_gem, GemNavigationError
            try:
                gem_cfg = get_gem_config("image", self.gem_key)
                self._opal_frame = await navigate_to_gem(self._page, gem_cfg)
            except GemNavigationError as e:
                logger.warning("Gem 탐색 실패, 메인 채팅으로 폴백: %s", e)
                self.gem_key = None  # 폴백: 풀 프롬프트 모드
                self._opal_frame = None

    async def _activate_image_tool(self) -> None:
        """이미지 도구 버튼 1회 클릭 (세션 동안 유지).

        Gem Labs 모드에서는 이미지 도구가 Gem 워크플로에 내장되므로 건너뜀.
        """
        if self._image_tool_activated or self._opal_frame is not None:
            return
        try:
            btn = self._page.locator(GEMINI_SELECTORS["image_tool_button"]).first
            if await btn.count() == 0:
                raise GeminiWebImageError(
                    "이미지 만들기 버튼을 찾지 못했습니다 (UI 변경 가능성)"
                )
            await btn.click(timeout=10000)
            await asyncio.sleep(2)
            self._image_tool_activated = True
        except Exception as e:
            raise GeminiWebImageError(f"이미지 도구 활성화 실패: {e}") from e

    async def close(self) -> None:
        try:
            if self._context:
                await self._context.close()
        finally:
            if self._playwright:
                await self._playwright.stop()
            self._page = None
            self._context = None
            self._playwright = None
            self._image_tool_activated = False

    async def generate_one(self, *, scene_id: int, prompt: str) -> dict:
        """단일 프롬프트로 이미지 1장 생성 → 로컬 PNG 저장."""
        if self._page is None:
            await self._ensure_session()
        await self._activate_image_tool()

        # 응답 베이스라인: 현재 큰 이미지 개수
        self._image_count_baseline = await self._page.evaluate(
            "() => document.querySelectorAll("
            "'model-response button.image-button img').length"
        )

        # Gem 모드: 씬 내용만 전송 (Gem 지침이 스타일 담당)
        # 일반 모드: 풀 스타일 프롬프트 조합
        if self._opal_frame is not None:
            truncated = prompt if len(prompt) <= 400 else prompt[:400] + "..."
            full_prompt = f"{truncated} (9:16 세로)"
        else:
            truncated = prompt if len(prompt) <= 800 else prompt[:800] + "..."
            full_prompt = f"{IMAGE_PROMPT_PREFIX}{truncated}{IMAGE_ASPECT_HINT}"

        if self._opal_frame is not None:
            return await self._generate_one_gem_mode(scene_id, full_prompt, prompt)

        chat = self._page.locator(GEMINI_SELECTORS["chat_input"]).first
        send_btn = self._page.locator(GEMINI_SELECTORS["send_button"]).first
        # 이전 씬 응답 완료 대기 (송신 버튼이 다시 보일 때까지)
        try:
            await send_btn.wait_for(state="visible", timeout=60000)
        except Exception:
            pass

        await chat.click()
        # type 대신 evaluate로 직접 내용 설정 + input 이벤트 발생 (빠름)
        await chat.evaluate(
            """(el, text) => {
                el.innerText = text;
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }""",
            full_prompt,
        )
        await asyncio.sleep(0.8)  # input 이벤트 후 송신 버튼 활성화 대기
        await send_btn.click(timeout=15000)

        # 새 이미지 출현 polling
        elapsed = 0.0
        while elapsed < IMAGE_GENERATION_TIMEOUT_SEC:
            await asyncio.sleep(IMAGE_POLL_INTERVAL_SEC)
            elapsed += IMAGE_POLL_INTERVAL_SEC
            current = await self._page.evaluate(
                "() => document.querySelectorAll("
                "'model-response button.image-button img').length"
            )
            if current > self._image_count_baseline:
                # 새로 생긴 마지막 이미지 element 캡처
                return await self._capture_last_image(scene_id, prompt)

        raise GeminiWebImageError(
            f"씬 {scene_id} 이미지 생성 타임아웃 ({IMAGE_GENERATION_TIMEOUT_SEC:.0f}s)"
        )

    async def _generate_one_gem_mode(
        self, scene_id: int, full_prompt: str, original_prompt: str
    ) -> dict:
        """Gem Labs(Opal) 채팅 인터페이스로 이미지 1장 생성."""
        frame = self._opal_frame
        chat = frame.locator(GEM_LABS_SELECTORS["gem_chat_input"]).first
        send_btn = frame.locator(GEM_LABS_SELECTORS["gem_send_button"]).first

        # 송신 버튼 활성화 대기
        try:
            await send_btn.wait_for(state="visible", timeout=60000)
        except Exception:
            pass

        # 현재 이미지 개수 베이스라인
        baseline = await frame.locator(GEM_LABS_SELECTORS["image_in_opal"]).count()

        await chat.click()
        await chat.fill(full_prompt)
        await asyncio.sleep(0.5)
        await send_btn.click(timeout=15000)

        # 새 이미지 출현 polling
        elapsed = 0.0
        while elapsed < IMAGE_GENERATION_TIMEOUT_SEC:
            await asyncio.sleep(IMAGE_POLL_INTERVAL_SEC)
            elapsed += IMAGE_POLL_INTERVAL_SEC
            current = await frame.locator(GEM_LABS_SELECTORS["image_in_opal"]).count()
            if current > baseline:
                return await self._capture_last_image_gem(scene_id, original_prompt)

        raise GeminiWebImageError(
            f"씬 {scene_id} Gem 이미지 생성 타임아웃 ({IMAGE_GENERATION_TIMEOUT_SEC:.0f}s)"
        )

    async def _capture_last_image_gem(self, scene_id: int, prompt: str) -> dict:
        """Gem Labs 응답에서 마지막 이미지 element를 PNG로 저장."""
        DATA_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = DATA_IMAGES_DIR / f"gemini_{ts}_scene{scene_id:02d}.png"

        img_locator = self._opal_frame.locator(GEM_LABS_SELECTORS["image_in_opal"]).last
        await asyncio.sleep(2)
        await img_locator.screenshot(path=str(out_path))

        return {
            "scene_id": scene_id,
            "image_path": str(out_path),
            "prompt": prompt,
        }

    async def _capture_last_image(self, scene_id: int, prompt: str) -> dict:
        """가장 최근 생성 이미지 element를 screenshot으로 PNG 저장.

        blob: URL은 httpx로 다운로드 불가하므로 element.screenshot 사용.
        """
        DATA_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = DATA_IMAGES_DIR / f"gemini_{ts}_scene{scene_id:02d}.png"

        img_locator = self._page.locator(GEMINI_SELECTORS["image_in_response"]).last
        # 안정화 대기 (이미지 로드 완료)
        await asyncio.sleep(2)
        await img_locator.screenshot(path=str(out_path))

        return {
            "scene_id": scene_id,
            "image_path": str(out_path),
            "prompt": prompt,
        }

    async def generate_scene_images(
        self,
        *,
        prompts: list[dict],
    ) -> list[dict]:
        """N개 씬 프롬프트 일괄 처리. 단일 세션 재사용."""
        await self._ensure_session()
        results: list[dict] = []
        for item in prompts:
            sid = item["scene_id"]
            try:
                results.append(
                    await self.generate_one(scene_id=sid, prompt=item["prompt"])
                )
            except GeminiWebImageError as e:
                logger.warning("씬 %d 실패: %s", sid, e)
        return results


def generate_scene_images_sync(
    prompts: list[dict],
    gem_key: str | None = None,
) -> list[dict]:
    """동기 wrapper.

    Args:
        prompts: [{"scene_id": int, "prompt": str}, ...]
        gem_key: 등록된 Gem 키 (e.g. "webtoon"). None이면 메인 채팅 사용.
    """
    async def _run() -> list[dict]:
        async with GeminiWebImageGenerator(gem_key=gem_key) as gen:
            return await gen.generate_scene_images(prompts=prompts)

    return asyncio.run(_run())
