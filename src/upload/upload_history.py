"""업로드 이력 JSON 기록 (Feature 026).

data/upload_history.json에 플랫폼별 업로드 성공/실패를 append한다.
어떤 영상이 언제 어디에 올라갔는지 추적하고, 실패 원인을 남긴다.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.config.settings import DATA_DIR

logger = logging.getLogger(__name__)

HISTORY_PATH = DATA_DIR / "upload_history.json"


def record_upload(
    *,
    platform: str,
    video_path: Path,
    title: str,
    status: str,
    result: str | None = None,
    error: str | None = None,
    history_path: Path | None = None,
) -> dict:
    """업로드 결과 1건을 이력 파일에 append하고 기록된 entry를 반환한다.

    이력 기록 실패가 업로드 자체를 실패시키면 안 되므로, 호출자는
    이 함수를 best-effort로 취급해도 된다 (I/O 오류는 로그 후 전파).

    Args:
        platform: "youtube" | "tiktok"
        status: "success" | "failed"
        result: 성공 시 video URL 또는 publish_id
        error: 실패 시 원인 메시지
        history_path: 기본 data/upload_history.json 오버라이드 (테스트용)
    """
    path = history_path if history_path is not None else HISTORY_PATH

    entries: list[dict] = []
    if path.exists():
        try:
            loaded = json.loads(path.read_text())
            if isinstance(loaded, list):
                entries = loaded
            else:
                logger.warning("이력 파일 형식 이상 — 새로 시작: %s", path)
        except json.JSONDecodeError as exc:
            logger.warning("이력 파일 파싱 실패 — 새로 시작: %s (%s)", path, exc)

    entry = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "platform": platform,
        "video_path": str(video_path),
        "title": title,
        "status": status,
        "result": result,
        "error": error,
    }
    entries = [*entries, entry]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    return entry
