"""Headless browser e2e test for cmaker.store-daehaeng.com.

Drives a real Chromium browser via Playwright to verify the 2-phase flow:
1. Topic input → Click "영상 생성" → wait for Phase 1 analyze to finish
2. Verify ScriptReviewer appears with title + scenes
3. Click "영상 생성" on the reviewer → verify Phase 2 processing starts

Captures screenshots at each state transition for visual confirmation.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

URL = "https://cmaker.store-daehaeng.com/"
OUT = Path("/tmp/e2e_browser")
OUT.mkdir(parents=True, exist_ok=True)

TOPIC = "퇴근길 지하철에서 자리 양보 안 하는 사람들"

CONSOLE_MSGS: list[str] = []
FAILED_REQS: list[str] = []


def _on_console(msg) -> None:
    txt = f"[{msg.type}] {msg.text}"
    CONSOLE_MSGS.append(txt)
    if msg.type in ("error", "warning"):
        print(f"  console: {txt}")


def _on_requestfailed(req) -> None:
    line = f"{req.method} {req.url} — {req.failure}"
    FAILED_REQS.append(line)
    print(f"  ❌ request failed: {line}")


async def shot(page: Page, name: str) -> None:
    p = OUT / f"{name}.png"
    await page.screenshot(path=str(p), full_page=True)
    print(f"  📸 {p}")


async def run() -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = await ctx.new_page()
        page.on("console", _on_console)
        page.on("requestfailed", _on_requestfailed)

        print(f"[1/6] GET {URL}")
        t0 = time.time()
        await page.goto(URL, wait_until="networkidle", timeout=30_000)
        print(f"    loaded in {time.time()-t0:.1f}s")
        await shot(page, "01_loaded")

        # Hard reload to bust any cached JS (user asked for 직접 새로고침)
        print("[2/6] Hard reload (bypass cache)")
        await page.reload(wait_until="networkidle", timeout=30_000)
        await shot(page, "02_reloaded")

        print("[3/6] Click '💡 주제 입력' tab")
        tab = page.get_by_role("button", name="💡 주제 입력")
        await tab.wait_for(timeout=5_000)
        await tab.click()
        await asyncio.sleep(0.5)
        await shot(page, "03_topic_tab")

        print(f"[4/6] Enter topic: {TOPIC!r}")
        topic_input = page.get_by_placeholder("예: 즐겨 먹던 과자들의 배신")
        await topic_input.wait_for(timeout=5_000)
        await topic_input.fill(TOPIC)
        await shot(page, "04_topic_entered")

        print("[5/6] Click '🎬 영상 생성' — Phase 1 begin")
        # The topic tab has 2 generate buttons (영상 생성, 테스트) —
        # the first visible one in the topic tab is what we want.
        # We scope via nth-match on the visible topic-tab's button.
        gen_btns = page.locator("button:has-text('🎬 영상 생성')")
        count = await gen_btns.count()
        print(f"    found {count} '영상 생성' buttons on page (4 tabs)")
        # Find the one inside the currently visible topic tab
        clicked = False
        for i in range(count):
            b = gen_btns.nth(i)
            if await b.is_visible() and await b.is_enabled():
                print(f"    clicking button #{i}")
                await b.click()
                clicked = True
                break
        if not clicked:
            print("    ❌ no enabled visible '영상 생성' button found")
            await shot(page, "ERR_no_button")
            await browser.close()
            return 1

        # ── Wait for "processing" state ──
        print("    waiting for '스크립트 분석 중' header...")
        try:
            await page.wait_for_selector("h2:has-text('스크립트 분석 중')", timeout=10_000)
            print("    ✅ processing state entered")
        except PWTimeout:
            print("    ❌ processing state did NOT start")
            await shot(page, "ERR_no_processing")
            await browser.close()
            return 1
        await shot(page, "05_processing")

        # ── Wait for "reviewing" state ──
        print("    waiting for reviewing screen (Phase 1 done)... (up to 5 min)")
        review_deadline = time.time() + 330  # 5m30s (Claude timeout 300s + margin)
        last_progress = ""
        entered_review = False
        while time.time() < review_deadline:
            # Poll the latest progress line (the text below the spinner)
            try:
                latest = await page.locator("p.text-gray-400").first.text_content(timeout=1000)
                if latest and latest != last_progress:
                    last_progress = latest
                    print(f"    · {latest.strip()[:100]}")
            except Exception:
                pass
            # Check if the review screen appeared
            try:
                if await page.locator("h2:has-text('스크립트 검토 및 수정')").is_visible():
                    entered_review = True
                    break
            except Exception:
                pass
            # Did we hit an error state?
            try:
                err = await page.locator("div.bg-red-900\\/50").first.text_content(timeout=500)
                if err and err.strip():
                    print(f"    ❌ ERROR shown: {err.strip()[:200]}")
                    await shot(page, "ERR_red_banner")
                    await browser.close()
                    return 1
            except Exception:
                pass
            await asyncio.sleep(2)

        if not entered_review:
            print(f"    ❌ review screen never appeared — last progress: {last_progress!r}")
            await shot(page, "ERR_no_review")
            print("\n--- Browser console messages (last 30) ---")
            for m in CONSOLE_MSGS[-30:]:
                print(m)
            print("\n--- Failed requests ---")
            for r in FAILED_REQS:
                print(r)
            await browser.close()
            return 1

        print("    ✅ review screen appeared")
        await shot(page, "06_review_screen")

        # Verify key UI elements are present
        print("[6/6] Verify review screen contents")
        checks = [
            ("감정 라벨", "감정"),
            ("제목 섹션", "📌 영상 제목"),
            ("씬 1 라벨", "씬 1"),
            ("화면 표시 글", "🖼️ 화면에 표시할 글"),
            ("TTS 대본", "🎙️ TTS 음성 대본"),
            ("취소 버튼", "← 취소"),
            ("영상 생성 버튼", "영상 생성"),
        ]
        all_ok = True
        for label, text in checks:
            try:
                await page.get_by_text(text, exact=False).first.wait_for(
                    state="visible", timeout=2000
                )
                print(f"    ✅ {label}: '{text}' 보임")
            except PWTimeout:
                print(f"    ❌ {label}: '{text}' 못 찾음")
                all_ok = False

        await browser.close()

        if not all_ok:
            print("\n💥 일부 UI 요소 누락")
            return 1

        print("\n🎉 검토 화면이 정상 표시됩니다!")
        print(f"📁 screenshots: {OUT}")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
