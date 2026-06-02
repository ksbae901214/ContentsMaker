"""Gemini Gem Labs 탐색 유틸리티.

gems_config.json의 gem_id로 https://gemini.google.com/gem-labs/{id} 에
직접 이동해 "Start" 버튼을 클릭한 뒤 Opal 채팅 인터페이스를 반환한다.
이름 기반 탐색 불필요 — gem_id만 업데이트하면 동작한다.

사용 흐름:
  1. python3 -m src.main gems list  → 등록된 Gem 목록 확인
  2. GeminiWebImageGenerator(gem_key="webtoon")  → 자동으로 Webtoonify Gem 진입
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # playwright Frame type is not importable at module load time

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "gems_config.json"
_PROMPTS_DIR = Path(__file__).parent.parent / "config" / "gem_prompts"

GEM_LABS_BASE_URL = "https://gemini.google.com/gem-labs"
# 레거시 호환 — 기존 코드에서 GEMS_LIST_URL을 import할 경우 대비
GEMS_LIST_URL = "https://gemini.google.com/gems/view"


class GemNotFoundError(Exception):
    """gems_config.json에 등록되지 않은 키."""


class GemNavigationError(Exception):
    """Gem 페이지 탐색·클릭 실패."""


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def get_gem_config(kind: str, gem_key: str) -> dict:
    """gems_config.json에서 Gem 설정 반환.

    Args:
        kind: "image" | "video"
        gem_key: e.g. "webtoon", "news", "drama"

    Raises:
        GemNotFoundError: 해당 키 미등록
    """
    config = _load_config()
    gems = config.get(kind, {})
    if gem_key not in gems:
        available = list(gems.keys())
        raise GemNotFoundError(
            f"Gem '{gem_key}' ({kind}) 미등록. "
            f"사용 가능: {available}. "
            f"gems_config.json에서 등록하거나 이름을 확인하세요."
        )
    return gems[gem_key]


def list_gems() -> dict[str, list[dict]]:
    """등록된 모든 Gem 목록 반환."""
    config = _load_config()
    return {
        kind: [{"key": k, **v} for k, v in config.get(kind, {}).items()]
        for kind in ("image", "video")
    }


def get_system_prompt_text(prompt_file: str) -> str:
    """Gem 지침 텍스트 반환 (Gem 생성 시 붙여넣기용)."""
    path = _PROMPTS_DIR / prompt_file
    if not path.exists():
        return f"(지침 파일 없음: {path})"
    return path.read_text(encoding="utf-8")


async def navigate_to_gem(page, gem_cfg: dict):
    """Gem Labs 앱으로 이동 후 채팅 인터페이스를 활성화한다.

    Args:
        page: Playwright Page 객체
        gem_cfg: get_gem_config()가 반환한 Gem 설정 dict
                 (gem_id, gem_name, description, prompt_file 포함)

    Returns:
        opal_app_frame: "Type or upload your response." 입력창이 있는 Playwright Frame

    Raises:
        GemNavigationError: gem_id 미설정 또는 탐색 실패
    """
    gem_id = gem_cfg.get("gem_id")
    if not gem_id:
        raise GemNavigationError(
            f"gems_config.json의 '{gem_cfg.get('gem_name')}' 항목에 gem_id가 없습니다."
        )

    gem_url = f"{GEM_LABS_BASE_URL}/{gem_id}"
    gem_name = gem_cfg.get("gem_name", gem_id)

    try:
        await page.goto(gem_url)
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(8)  # Opal iframe 로드 대기

        # opal._app 프레임 탐색
        opal_frame = _find_opal_frame(page)
        if opal_frame is None:
            raise GemNavigationError(
                f"Gem '{gem_name}' — opal._app 프레임 미발견. "
                "gemini_login 재실행 또는 gem_id를 확인하세요."
            )

        # "Got it" 안내 팝업 닫기
        got_it = opal_frame.locator("button:has-text('Got it')")
        if await got_it.count() > 0 and await got_it.first.is_visible():
            await got_it.first.click()
            await asyncio.sleep(1)

        # "Start" 버튼 클릭 → 채팅 인터페이스 활성화
        start_btn = opal_frame.locator("button:has-text('Start')")
        if await start_btn.count() > 0 and await start_btn.first.is_visible():
            await start_btn.first.click()
            await asyncio.sleep(3)

        # 채팅 입력창 출현 확인
        chat_input = opal_frame.locator("textarea[placeholder*='Type or upload']")
        for _ in range(10):
            if await chat_input.count() > 0 and await chat_input.first.is_visible():
                break
            await asyncio.sleep(1)
        else:
            raise GemNavigationError(
                f"Gem '{gem_name}' — 채팅 입력창 미출현 (Start 후 타임아웃)."
            )

        logger.info("Gem Labs '%s' 채팅 진입 완료 (id=%s)", gem_name, gem_id)
        return opal_frame

    except GemNavigationError:
        raise
    except Exception as e:
        raise GemNavigationError(f"Gem '{gem_name}' 탐색 실패: {e}") from e


def _find_opal_frame(page):
    """page.frames에서 opal._app 프레임을 반환. 없으면 None."""
    for frame in page.frames:
        if "opal.google/_app" in frame.url:
            return frame
    return None
