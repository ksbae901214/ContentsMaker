"""gemini.google.com 1회 수동 로그인 — 영상/이미지 자동화용 세션 저장.

사용법:
  python3 -m src.main gemini_login

브라우저가 열리면 직접 Google 계정으로 로그인 후 메인 채팅 화면이 보이면
터미널에 엔터 입력. 이후 ``GEMINI_PROFILE_DIR`` 에 세션이 저장되어
``GeminiWebImageGenerator`` / ``GeminiWebVideoGenerator`` 가 재사용한다.
"""
from __future__ import annotations

import asyncio
import logging

from src.config.settings import GEMINI_PROFILE_DIR, GEMINI_WEB_URL

logger = logging.getLogger(__name__)


async def _interactive_login_async() -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(
            "❌ playwright 미설치. 다음을 실행하세요:\n"
            "   pip install playwright && playwright install chromium"
        )
        return 1

    GEMINI_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 세션 저장 위치: {GEMINI_PROFILE_DIR}")
    print(f"🌐 열릴 페이지: {GEMINI_WEB_URL}")
    print("👉 브라우저에서 Google 계정으로 로그인 후 메인 채팅 화면이 보이면")
    print("   터미널로 돌아와 Enter 키를 누르세요.\n")

    async with async_playwright() as p:
        # 2026-05-19: Google 자동화 차단 회피 — 번들 chromium 대신 시스템 Chrome 사용
        # + AutomationControlled 플래그 비활성화. macOS에 Chrome 설치 전제.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(GEMINI_PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(GEMINI_WEB_URL)
        try:
            input("✅ 로그인 완료 후 Enter (브라우저 닫힘): ")
        finally:
            await context.close()

    print("\n✅ 세션 저장 완료. 이제 만화/영상 모드에서 자동 로그인 됩니다.")
    return 0


def run_interactive_login() -> int:
    return asyncio.run(_interactive_login_async())
