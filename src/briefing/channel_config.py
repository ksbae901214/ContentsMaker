"""모니터링 대상 YouTube 정치 채널 목록 로더.

채널 ID는 `data/briefing_channels.json`에서 로드. 사용자가 직접 편집.

채널 ID 추출 방법:
    1. 채널 페이지 열기 (예: https://youtube.com/@MBCRadio)
    2. View source → og:url 또는 channelId 검색
    3. UC로 시작하는 24자 문자열이 channel_id

균형 권장: 보수/진보/중립 채널을 함께 등록해 한쪽 편향 방지.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.config.settings import DATA_DIR

logger = logging.getLogger(__name__)

CHANNELS_CONFIG_PATH = DATA_DIR / "briefing_channels.json"

# Default 채널 목록 — 사용자가 처음 실행 시 자동 생성됨.
# 빈 리스트로 시작 (정치 채널 선택은 사용자 가치 판단이라 임의 default 위험).
_DEFAULT_CONFIG = {
    "version": 1,
    "description": (
        "매일 브리핑 모니터링 채널 목록. channel_id는 UC로 시작하는 24자. "
        "균형 권장: 보수/진보/중립 채널을 함께 등록."
    ),
    "channels": [
        # 예시 항목 (실제 사용 전 사용자가 추가/수정)
        # {"channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx", "name": "MBC 라디오 시사", "category": "neutral"},
        # {"channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx", "name": "뉴스핌TV", "category": "neutral"},
    ],
}


def load_channels() -> list[dict]:
    """채널 목록 로드. 파일 없으면 default 생성 후 안내.

    Returns:
        list of {"channel_id": str, "name": str, "category": str}.
        category: "conservative" | "progressive" | "neutral"
    """
    if not CHANNELS_CONFIG_PATH.exists():
        CHANNELS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHANNELS_CONFIG_PATH.write_text(
            json.dumps(_DEFAULT_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.warning(
            "%s 가 비어 있습니다. 모니터링할 YouTube 채널을 추가하세요.",
            CHANNELS_CONFIG_PATH,
        )
        return []

    try:
        data = json.loads(CHANNELS_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{CHANNELS_CONFIG_PATH} JSON 파싱 실패: {e}") from e

    channels = data.get("channels", [])
    # validate
    valid: list[dict] = []
    for c in channels:
        cid = c.get("channel_id", "").strip()
        if not cid:
            continue
        if not (cid.startswith("UC") and len(cid) == 24):
            logger.warning("잘못된 channel_id 형식 (UC + 22자 필요): %r", cid)
            continue
        valid.append({
            "channel_id": cid,
            "name": c.get("name", cid),
            "category": c.get("category", "neutral"),
        })
    return valid


def save_channels(channels: list[dict]) -> None:
    """채널 목록 저장 (UI에서 편집 시 호출)."""
    CHANNELS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "description": _DEFAULT_CONFIG["description"],
        "channels": channels,
    }
    CHANNELS_CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
