"""gemini.google.com 텍스트 채팅 자동화 — Gemini API 한도 폴백용.

API Free Tier (gemini-2.5-flash 일 20건) 소진 시 자동 폴백 백엔드.
사용자가 Gemini Pro 구독자면 웹앱은 사실상 무제한.

trade-off:
    - 장점: API 한도 무관, gemini-2.5-pro 사용 (Flash보다 강력)
    - 단점: 호출당 30~60초 (API 1~5초 대비)
    - 단점: UI 변경 시 selector 갱신 필요

사용법:
    text = chat("프롬프트")   # JSON mode면 응답 텍스트에서 JSON 추출 필요
    text = chat("프롬프트", json_mode=True)   # 자동으로 JSON 블록 추출

전제: `python3 -m src.main gemini_login` 1회 완료.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re

from src.config.settings import GEMINI_PROFILE_DIR, GEMINI_WEB_URL
from src.illustrator.gemini_web_selectors import (
    GEMINI_SELECTORS,
    MODAL_DISMISS_COUNT,
)

logger = logging.getLogger(__name__)


class GeminiWebChatError(Exception):
    """Gemini 웹 채팅 자동화 실패."""


DEFAULT_TIMEOUT_SEC = 180.0
RESPONSE_STABLE_POLLS = 3  # 응답 텍스트 변화 멈춤 횟수 (×poll_interval = 안정 판단)
RESPONSE_POLL_INTERVAL = 2.0  # 초


async def chat_async(
    prompt: str,
    *,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    headless: bool | None = None,
) -> str:
    """Gemini 웹앱에 prompt를 보내고 응답 텍스트 반환.

    Args:
        prompt: 사용자 입력 텍스트.
        timeout_sec: 응답 등장 + 안정화 총 대기 시간.
        headless: True면 백그라운드. **default True** — 자동화가 사용자 작업 화면에 침입하지
                  않도록 강제. 디버깅 시에만 `GEMINI_HEADLESS=0` 환경변수 또는 명시적 False.
                  (2026-05-21: daily-briefing 자동 폴백 시 사용자 Chrome 작업과 시야 충돌 → headless 강제)

    Returns:
        응답 텍스트 (rich-text는 무시, 텍스트만).

    Raises:
        GeminiWebChatError: 로그인 필요, selector 못 찾음, 타임아웃.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise GeminiWebChatError(
            "playwright 미설치. pip install playwright && playwright install chromium"
        ) from e

    if headless is None:
        # 2026-05-21: default True — 사용자 작업 화면 침입 방지. 명시적 GEMINI_HEADLESS=0 시만 헤드.
        headless = os.environ.get("GEMINI_HEADLESS", "1") != "0"

    if not GEMINI_PROFILE_DIR.exists() or not any(GEMINI_PROFILE_DIR.iterdir()):
        raise GeminiWebChatError(
            "Gemini 웹 세션이 없습니다. 다음을 실행하세요:\n"
            "   python3 -m src.main gemini_login"
        )

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(GEMINI_PROFILE_DIR),
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(GEMINI_WEB_URL, wait_until="domcontentloaded")
            # ESC로 첫 방문 모달 닫기
            for _ in range(MODAL_DISMISS_COUNT):
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)

            # 로그인 확인
            if await page.locator(GEMINI_SELECTORS["login_required_marker"]).count() > 0:
                raise GeminiWebChatError(
                    "로그인 세션 만료. python3 -m src.main gemini_login 재실행."
                )

            # 채팅 입력 ready 대기
            input_box = page.locator(GEMINI_SELECTORS["chat_input"]).first
            await input_box.wait_for(state="visible", timeout=30000)

            # 입력 (Quill editor — fill 대신 click + keyboard.type 사용해야 안정적)
            await input_box.click()
            await page.keyboard.type(prompt, delay=5)
            await asyncio.sleep(0.5)

            # 전송 — send_button 활성화 대기 후 클릭
            send_btn = page.locator(GEMINI_SELECTORS["send_button"]).first
            await send_btn.wait_for(state="visible", timeout=10000)
            # disabled 상태일 수 있으니 polling
            for _ in range(20):
                if await send_btn.is_enabled():
                    break
                await asyncio.sleep(0.2)
            await send_btn.click()
            logger.info("Gemini 웹: 프롬프트 전송 (%d자)", len(prompt))

            # 응답 컨테이너 등장 대기
            response_loc = page.locator(GEMINI_SELECTORS["response_container"]).last
            await response_loc.wait_for(state="visible", timeout=int(timeout_sec * 1000))

            # 응답 안정화 (텍스트 변화 멈춤 = 생성 완료)
            prev_text = ""
            stable_count = 0
            elapsed = 0.0
            while elapsed < timeout_sec:
                await asyncio.sleep(RESPONSE_POLL_INTERVAL)
                elapsed += RESPONSE_POLL_INTERVAL
                try:
                    text = (await response_loc.inner_text()).strip()
                except Exception:
                    text = ""
                if text and text == prev_text:
                    stable_count += 1
                    if stable_count >= RESPONSE_STABLE_POLLS:
                        break
                else:
                    stable_count = 0
                    prev_text = text

            if not prev_text:
                raise GeminiWebChatError(
                    f"응답 텍스트 비어 있음 (타임아웃 {timeout_sec}s)"
                )

            logger.info("Gemini 웹: 응답 수신 (%d자, %.1fs)", len(prev_text), elapsed)
            return prev_text
        finally:
            await context.close()


def chat(
    prompt: str,
    *,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    headless: bool | None = None,
    json_mode: bool = False,
) -> str:
    """Sync wrapper. json_mode=True면 응답에서 JSON 블록만 추출."""
    text = asyncio.run(chat_async(prompt, timeout_sec=timeout_sec, headless=headless))
    if json_mode:
        return extract_json_block(text)
    return text


def extract_json_block(text: str) -> str:
    """응답 텍스트에서 첫 JSON 객체 추출.

    우선순위:
        1. ```json ... ``` 코드 펜스
        2. ``` ... ``` (json 명시 안 됨)
        3. 첫 `{` ~ 매칭 `}` (balanced)
        4. 원본 텍스트 (이미 JSON이라고 가정)
    """
    # 1. ```json ... ```
    m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 2. ``` ... ```
    m = re.search(r"```\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 3. balanced { ... } 추출
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1].strip()
    # 4. 그냥 반환
    return text.strip()
