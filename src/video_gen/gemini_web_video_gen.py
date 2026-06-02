"""Veo 3 영상 생성 (Phase 2B) — gemini.google.com 웹앱 자동화.

Freepik Premium+ 구독 해지 후 영상 모드를 Pro 구독에 포함된 Veo 3로
대체. 8초 720p 클립 + 네이티브 오디오 지원.

폴백 체인 (factory에서 사용):
  1) gemini (이 모듈)
  2) deevid (Playwright, Veo 3.1 무료 20 credits)
  3) seedance (API, ~$0.05/씬)

⚠️ Phase 2B 초안 — 실제 Veo 3 트리거 문법과 selector는 gemini_login 후 UI에서
   확인 필요. 현재는 deevid_gen 패턴 차용한 골격만 구현.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
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
    MODAL_DISMISS_COUNT,
    VIDEO_ASPECT_HINT,
    VIDEO_GENERATION_TIMEOUT_SEC,
    VIDEO_POLL_INTERVAL_SEC,
    VIDEO_PROMPT_PREFIX,
)
from src.video_gen.base import (
    VideoGenerationError,
    VideoGeneratorBase,
    VideoResult,
    VideoStatus,
)

logger = logging.getLogger(__name__)

DATA_VIDEOS_DIR = PROJECT_ROOT / "data" / "videos"


class GeminiWebVideoGenerator(VideoGeneratorBase):
    """Veo 3 영상 생성기 (Pro 구독 웹앱 활용).

    Veo 3 무료 한도(예상): 일 ~10편. 구독자별 정확한 한도는 UI에 표시되는
    "Generation credits" 영역에서 확인.
    """

    def __init__(self, *, headless: bool | None = None, gem_key: str | None = None) -> None:
        self.headless = GEMINI_HEADLESS if headless is None else headless
        self.gem_key = gem_key
        # task_id → {prompt, started_at, status, output_path?}
        self._tasks: dict[str, dict] = {}
        self._page = None
        self._context = None
        self._playwright = None
        # Gem Labs 모드에서 사용하는 opal._app 프레임
        self._opal_frame = None

    # ---- VideoGeneratorBase 구현 ----

    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
    ) -> str:
        """Veo 3 호출 - 비동기 시작 시뮬레이션 후 task_id 반환.

        Gemini 웹앱은 polling API가 없으므로 generate_and_wait 한 번에 처리.
        task_id는 내부 추적용 UUID.
        """
        task_id = uuid.uuid4().hex[:12]
        self._tasks[task_id] = {
            "prompt": prompt,
            "started_at": datetime.utcnow(),
            "status": "pending",
            "result": None,
            "error": None,
        }
        return task_id

    async def get_status(self, task_id: str) -> VideoStatus:
        info = self._tasks.get(task_id)
        if not info:
            return VideoStatus(task_id=task_id, status="failed",
                               progress=0.0, error="unknown task_id")
        return VideoStatus(
            task_id=task_id,
            status=info["status"],
            progress=0.5 if info["status"] == "processing" else (
                1.0 if info["status"] == "completed" else 0.0
            ),
            error=info["error"],
            result=info["result"],
        )

    async def download(self, task_id: str, output_path: str) -> VideoResult:
        info = self._tasks.get(task_id)
        if not info or info["status"] != "completed":
            raise VideoGenerationError(f"task_id={task_id} 완료 안 됨")
        return info["result"]

    def estimate_cost(self, duration: float = 5.0, resolution: str = "720p") -> float:
        """Pro 구독 한도 내 변동비 $0."""
        return 0.0

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
        """단일 prompt → 완성 영상까지 한 번에. Gemini 웹앱 특성에 맞춰 override."""
        await self._ensure_session()
        task_id = await self.generate(prompt, duration, resolution, source_image)
        self._tasks[task_id]["status"] = "processing"

        # Gem 모드: 씬 내용만 전송 (Gem 지침이 스타일 담당)
        # 일반 모드: 풀 모션 프롬프트
        if self._opal_frame is not None:
            scene_hint = prompt if len(prompt) <= 400 else prompt[:400] + "..."
            full_prompt = f"{scene_hint} (9:16 세로, 약 8초)"
        else:
            full_prompt = f"{VIDEO_PROMPT_PREFIX}{prompt}{VIDEO_ASPECT_HINT}"
        try:
            if self._opal_frame is not None:
                chat = self._opal_frame.locator(GEM_LABS_SELECTORS["gem_chat_input"]).first
                send = self._opal_frame.locator(GEM_LABS_SELECTORS["gem_send_button"]).first
                video_locator = self._opal_frame.locator(GEM_LABS_SELECTORS["video_in_opal"]).last
            else:
                chat = self._page.locator(GEMINI_SELECTORS["chat_input"]).first
                send = self._page.locator(GEMINI_SELECTORS["send_button"]).first
                video_locator = self._page.locator(GEMINI_SELECTORS["video_in_response"]).last

            await chat.click()
            await chat.fill(full_prompt)
            await send.click()
            elapsed = 0.0
            timeout = min(max_wait, VIDEO_GENERATION_TIMEOUT_SEC)
            while elapsed < timeout:
                if await video_locator.count() > 0:
                    src = await video_locator.get_attribute("src")
                    if src:
                        out = output_path or self._default_output_path(task_id)
                        result = await self._download_video(src, out, prompt, resolution)
                        self._tasks[task_id]["status"] = "completed"
                        self._tasks[task_id]["result"] = result
                        return result
                await asyncio.sleep(VIDEO_POLL_INTERVAL_SEC)
                elapsed += VIDEO_POLL_INTERVAL_SEC

            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = f"timeout {timeout:.0f}s"
            raise VideoGenerationError(f"Veo 3 영상 생성 타임아웃 ({timeout:.0f}s)")
        except Exception as e:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = str(e)
            if isinstance(e, VideoGenerationError):
                raise
            raise VideoGenerationError(f"Veo 3 자동화 실패: {e}") from e

    # ---- Browser session ----

    async def _ensure_session(self) -> None:
        if self._page is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise VideoGenerationError(
                "playwright 미설치 — pip install playwright && playwright install chromium"
            ) from e

        if not GEMINI_PROFILE_DIR.exists():
            raise VideoGenerationError(
                f"Gemini 세션 없음 ({GEMINI_PROFILE_DIR}). "
                "'python3 -m src.main gemini_login' 먼저 실행하세요."
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
            raise VideoGenerationError("Gemini 로그인 만료 — gemini_login 재실행 필요.")

        # 첫 방문 모달 해제 (ESC 키)
        for _ in range(MODAL_DISMISS_COUNT):
            await self._page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

        # Gem Labs 모드: gem_id로 직접 이동 → opal_frame 반환
        if self.gem_key:
            from src.illustrator.gem_navigator import get_gem_config, navigate_to_gem, GemNavigationError
            try:
                gem_cfg = get_gem_config("video", self.gem_key)
                self._opal_frame = await navigate_to_gem(self._page, gem_cfg)
            except GemNavigationError as e:
                logger.warning("Gem 탐색 실패, 메인 채팅으로 폴백: %s", e)
                self.gem_key = None
                self._opal_frame = None

        # "동영상 만들기" 도구 활성화 (세션 동안 유지)
        try:
            btn = self._page.locator(GEMINI_SELECTORS["video_tool_button"]).first
            if await btn.count() > 0:
                await btn.click(timeout=10000)
                await asyncio.sleep(2)
                logger.info("Veo 3 도구 활성화 완료")
        except Exception as e:
            logger.warning("Veo 3 도구 버튼 미발견 (계속): %s", e)

    async def _download_video(
        self, url: str, output_path: str, prompt: str, resolution: str
    ) -> VideoResult:
        """브라우저 컨텍스트의 인증된 fetch로 영상 다운로드.

        Gemini 영상 URL은 Google auth 쿠키가 필요하며 contribution.usercontent.google.com
        으로 리다이렉트되므로, 브라우저 안에서 fetch → base64로 받아 디코딩한다.
        """
        import base64

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # blob: URL은 직접 fetch 가능 (브라우저 내부 참조)
        # https: URL은 인증 쿠키 자동 첨부 (page.evaluate가 브라우저 컨텍스트에서 동작)
        b64 = await self._page.evaluate(
            """async (videoUrl) => {
                const resp = await fetch(videoUrl, { credentials: 'include' });
                if (!resp.ok) throw new Error('fetch failed: ' + resp.status);
                const buf = await resp.arrayBuffer();
                const bytes = new Uint8Array(buf);
                let binary = '';
                const chunkSize = 0x8000;
                for (let i = 0; i < bytes.length; i += chunkSize) {
                    binary += String.fromCharCode.apply(null,
                        bytes.subarray(i, i + chunkSize));
                }
                return btoa(binary);
            }""",
            url,
        )
        out.write_bytes(base64.b64decode(b64))

        return VideoResult(
            path=str(out),
            duration_ms=8000,  # Veo 3 기본 8초
            resolution=resolution,
            cost_usd=0.0,
            source_image=None,
            prompt=prompt,
        )

    def _default_output_path(self, task_id: str) -> str:
        DATA_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(DATA_VIDEOS_DIR / f"veo3_{ts}_{task_id}.mp4")

    async def close(self) -> None:
        try:
            if self._context:
                await self._context.close()
        finally:
            if self._playwright:
                await self._playwright.stop()
