"""ChatGPT(Plus) 웹 이미지 생성 — chatgpt.com 브라우저 자동화 (045 정보쇼츠 V1.0).

흐름:
  1. 영구 프로필로 시스템 Chrome 실행 → 새 채팅
  2. 한 편의 일러스트를 **같은 대화 안에서** 순서대로 요청 — 화풍·주인공이 이어진다
  3. 응답 완료('중지' 버튼 사라짐) + 생성 이미지 개수 증가를 기다린 뒤
     마지막 이미지 원본(blob, 1254×1254)을 페이지 안에서 꺼내 저장 (실패 시 스크린샷)
  4. 장 사이 20초 간격 — 사람 사용 속도에 맞춘다

실패한 장은 결과에서 빠진다. 호출자(`render_info_v1 images`)가 그 장의 프롬프트를
출력해 수동으로 만들어 넣게 한다.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path

from src.config.settings import CHATGPT_HEADLESS, CHATGPT_PROFILE_DIR, CHATGPT_WEB_URL
from src.illustrator.chatgpt_web_selectors import (
    CHATGPT_SELECTORS as SEL,
    IMAGE_GENERATION_TIMEOUT_SEC,
    IMAGE_POLL_INTERVAL_SEC,
    PACING_BETWEEN_IMAGES_SEC,
    SETTLE_AFTER_DONE_SEC,
)

logger = logging.getLogger(__name__)

# 생성 이미지 src 는 blob: URL 이라 페이지 컨텍스트에서만 읽힌다 → base64 로 꺼낸다
_READ_BLOB_JS = """async (img) => {
    const buf = await (await fetch(img.src)).arrayBuffer();
    let bin = "";
    const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i += 0x8000) {
        bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    }
    return btoa(bin);
}"""


class ChatGPTWebImageError(Exception):
    """chatgpt.com 이미지 자동화 실패."""


class ChatGPTWebImageGenerator:
    """세션 1개로 여러 장을 같은 대화에서 생성한다."""

    def __init__(self, *, headless: bool | None = None) -> None:
        self.headless = CHATGPT_HEADLESS if headless is None else headless
        self._playwright = None
        self._context = None
        self._page = None

    async def __aenter__(self) -> "ChatGPTWebImageGenerator":
        await self._open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def _open(self) -> None:
        if not CHATGPT_PROFILE_DIR.exists():
            raise ChatGPTWebImageError(
                f"ChatGPT 세션 없음 ({CHATGPT_PROFILE_DIR}) — "
                "'python3 -m src.main chatgpt_login' 을 먼저 실행하세요."
            )
        from playwright.async_api import async_playwright

        from src.illustrator.chatgpt_web_login import launch_context
        self._playwright = await async_playwright().start()
        self._context = await launch_context(self._playwright, headless=self.headless)
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        await self._page.goto(CHATGPT_WEB_URL)
        await self._page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)
        await self._page.locator(SEL["chat_input"]).first.wait_for(state="visible", timeout=30000)
        if await self._page.locator(SEL["logged_in_marker"]).count() == 0:
            raise ChatGPTWebImageError("로그인 세션 만료 — chatgpt_login 재실행 필요")

    async def _image_count(self) -> int:
        return await self._page.locator(SEL["generated_image"]).count()

    async def _is_busy(self) -> bool:
        return await self._page.locator(SEL["stop_button"]).count() > 0

    async def _send(self, prompt: str) -> None:
        box = self._page.locator(SEL["chat_input"]).first
        await box.click()
        await self._page.keyboard.insert_text(prompt)
        await asyncio.sleep(0.8)
        await self._page.keyboard.press("Enter")

    async def _wait_new_image(self, baseline: int) -> None:
        elapsed = 0.0
        while elapsed < IMAGE_GENERATION_TIMEOUT_SEC:
            await asyncio.sleep(IMAGE_POLL_INTERVAL_SEC)
            elapsed += IMAGE_POLL_INTERVAL_SEC
            if not await self._is_busy() and await self._image_count() > baseline:
                await asyncio.sleep(SETTLE_AFTER_DONE_SEC)
                return
        raise ChatGPTWebImageError(f"이미지 생성 타임아웃 ({IMAGE_GENERATION_TIMEOUT_SEC:.0f}초)")

    async def _save_last_image(self, out: Path) -> Path:
        img = self._page.locator(SEL["generated_image"]).last
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = await img.evaluate(_READ_BLOB_JS)
            out.write_bytes(base64.b64decode(data))
            return out
        except Exception as exc:  # blob 해제 등 — 해상도는 낮지만 화면 캡처로 대체
            logger.warning("원본 추출 실패(%s) — 스크린샷으로 대체", exc)
        await img.screenshot(path=str(out))
        return out

    async def generate_one(self, prompt: str, out: Path) -> Path:
        baseline = await self._image_count()
        await self._send(prompt)
        try:
            await self._wait_new_image(baseline)
        except ChatGPTWebImageError as exc:
            reply = await self._diagnose(out)
            raise ChatGPTWebImageError(f"{exc} — ChatGPT 마지막 답변: {reply}") from exc
        return await self._save_last_image(out)

    async def _diagnose(self, out: Path) -> str:
        """실패 시 화면 캡처 + 마지막 답변 글 — 거절·한도 메시지인지 사람이 보고 판단한다."""
        shot = out.parent.parent / "_verify" / f"chatgpt_fail_{out.stem}.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        try:
            await self._page.screenshot(path=str(shot))
            texts = await self._page.locator(SEL["assistant_message"]).all_inner_texts()
        except Exception as exc:  # 진단 실패가 원래 오류를 가리지 않게
            return f"(진단 실패: {exc})"
        last = " ".join((texts[-1] if texts else "(없음)").split())[:200]
        return f"{last} [화면: {shot}]"

    async def generate_many(self, jobs: list[dict]) -> list[dict]:
        """jobs: [{"key", "prompt", "out"}] → 성공한 것만 [{"key", "path"}]."""
        results: list[dict] = []
        for i, job in enumerate(jobs):
            if i:
                await asyncio.sleep(PACING_BETWEEN_IMAGES_SEC)
            try:
                path = await self.generate_one(job["prompt"], Path(job["out"]))
                results.append({"key": job["key"], "path": path})
                print(f"  🖼️ [{job['key']}] {path}", flush=True)
            except Exception as exc:  # 한 장 실패가 나머지를 막지 않게
                logger.warning("[%s] 생성 실패: %s", job["key"], exc)
                print(f"  ❌ [{job['key']}] {exc}", flush=True)
        return results


def generate_images_sync(jobs: list[dict]) -> list[dict]:
    """동기 래퍼. 세션 자체가 안 열리면(미로그인 등) 빈 결과 — 전 장 수동 폴백."""
    async def _run() -> list[dict]:
        async with ChatGPTWebImageGenerator() as gen:
            return await gen.generate_many(jobs)

    try:
        return asyncio.run(_run())
    except ChatGPTWebImageError as exc:
        print(f"❌ {exc}", flush=True)
        return []
