"""chatgpt.com 1회 수동 로그인 — 정보쇼츠 일러스트 자동화용 세션 저장 (045).

사용법:
  python3 -m src.main chatgpt_login

브라우저가 열리면 ChatGPT Plus 계정으로 직접 로그인한다(10분 안). 로그인이
감지되면 브라우저가 저절로 닫힌다. 세션은 ``CHATGPT_PROFILE_DIR`` 에 저장되어
``ChatGPTWebImageGenerator`` 가 재사용한다.
"""
from __future__ import annotations

import asyncio

from src.config.settings import CHATGPT_PROFILE_DIR, CHATGPT_WEB_URL

LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]
LOGIN_TIMEOUT_SEC = 600


async def launch_context(playwright, *, headless: bool):
    """시스템 Chrome + 영구 프로필 — 번들 Chromium 은 Cloudflare 에 막힌다."""
    CHATGPT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return await playwright.chromium.launch_persistent_context(
        user_data_dir=str(CHATGPT_PROFILE_DIR),
        channel="chrome",
        headless=headless,
        viewport={"width": 1280, "height": 900},
        args=LAUNCH_ARGS,
    )


async def _interactive_login_async() -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright 미설치: pip install playwright")
        return 1

    print(f"📁 세션 저장 위치: {CHATGPT_PROFILE_DIR}")
    print("👉 브라우저에서 ChatGPT 계정으로 로그인하세요 (10분 안).")
    print("   로그인이 감지되면 브라우저가 저절로 닫힙니다.\n")
    async with async_playwright() as p:
        context = await launch_context(p, headless=False)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(CHATGPT_WEB_URL)
        try:
            logged_in = await _wait_logged_in(page)
        finally:
            await context.close()
    if not logged_in:
        print(f"\n❌ {LOGIN_TIMEOUT_SEC // 60}분 안에 로그인이 확인되지 않았습니다. 다시 실행하세요.")
        return 1
    print("\n✅ 세션 저장 완료. 이제 `render_info_v1.py <config> images` 가 재사용합니다.")
    return 0


async def _wait_logged_in(page) -> bool:
    """Enter 입력 대신 로그인 상태를 감지한다 — 비대화형 실행에서도 동작하도록.

    로그아웃 상태 홈에도 입력창이 있으므로 '프로필 메뉴가 보이는가'로 판정한다.
    """
    from src.illustrator.chatgpt_web_selectors import CHATGPT_SELECTORS as SEL
    for _ in range(LOGIN_TIMEOUT_SEC // 2):
        await asyncio.sleep(2)
        try:
            on_chat = "chatgpt.com" in page.url and "auth" not in page.url
            has_input = await page.locator(SEL["chat_input"]).count() > 0
            logged_in = await page.locator(SEL["logged_in_marker"]).count() > 0
        except Exception:  # 로그인 리다이렉트 중 페이지 교체
            continue
        if on_chat and has_input and logged_in:
            await asyncio.sleep(3)  # 쿠키 기록 여유
            return True
    return False


def run_interactive_login() -> int:
    return asyncio.run(_interactive_login_async())
