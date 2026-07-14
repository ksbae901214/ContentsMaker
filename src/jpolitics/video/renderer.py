"""모먼트 직캠 렌더러 — Remotion V3 CLI를 호출해 MP4를 생성합니다.

격리 원칙: V1/V2 파일(src/video/renderer.py) 0 수정. 독립 실행.
"""
from __future__ import annotations

import json
import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.config.settings import PROJECT_ROOT
from src.jpolitics.models.clip import CaptionCue, ClipResult

logger = logging.getLogger(__name__)

REMOTION_V3_DIR = PROJECT_ROOT / "src" / "video" / "remotion_v3"
FPS = 30


class RenderError(Exception):
    """렌더링 실패 시 발생."""


def _duration_in_frames(duration_sec: float) -> int:
    """클립 길이(초) → Remotion durationInFrames (올림)."""
    return math.ceil(duration_sec * FPS)


def _build_props(
    clip_result: ClipResult,
    captions: list[CaptionCue],
    *,
    channel: str,
    source_date: str,
    clip_filename: str,
) -> dict:
    """렌더 props dict 생성 (camelCase, Remotion 전달용)."""
    moment = clip_result.moment_dict
    hook_question = str(moment.get("hook_question", moment.get("hookQuestion", "")))
    keywords = list(moment.get("keywords") or [])

    return {
        "clipFileName": clip_filename,
        "hookQuestion": hook_question,
        "hookKeywords": keywords,
        "captions": [
            {
                "startSec": c.start_sec,
                "endSec": c.end_sec,
                "text": c.text,
            }
            for c in captions
        ],
        "sourceLabel": f"출처: {channel} ({source_date})",
        "durationSec": clip_result.duration_sec,
    }


def render_moment_short(
    clip_result: ClipResult,
    captions: list[CaptionCue],
    *,
    channel: str,
    source_date: str,
    output_path: Path,
) -> Path:
    """모먼트 클립을 Remotion V3으로 렌더링해 MP4를 생성합니다.

    Args:
        clip_result: Phase 2 클리퍼가 생성한 ClipResult.
        captions: 클립 기준 상대 시간의 CaptionCue 목록.
        channel: 출처 채널명 (예: "YTN").
        source_date: 출처 날짜 "YYYY.MM.DD" 형식 (예: "2016.12.15").
        output_path: 최종 MP4 저장 경로.

    Returns:
        output_path (렌더 완료 후).

    Raises:
        RenderError: npx 미설치 또는 Remotion 렌더 실패 시.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    public_dir = REMOTION_V3_DIR / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    # 클립 파일을 public/ 에 복사
    src_clip = Path(clip_result.clip_path)
    clip_filename = src_clip.name
    dest_clip = public_dir / clip_filename
    shutil.copy2(src_clip, dest_clip)
    logger.info("클립 복사: %s → %s", src_clip.name, dest_clip)

    props = _build_props(
        clip_result, captions, channel=channel, source_date=source_date,
        clip_filename=clip_filename,
    )
    duration_frames = _duration_in_frames(clip_result.duration_sec)
    logger.info(
        "렌더 시작: %s (%d프레임, %.1f초)",
        output_path.name, duration_frames, clip_result.duration_sec,
    )

    npx_path = shutil.which("npx")
    if not npx_path:
        raise RenderError(
            "npx를 찾을 수 없습니다. Node.js가 설치되어 있는지 확인하세요."
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as props_file:
        json.dump(props, props_file, ensure_ascii=False)
        props_path = Path(props_file.name)

    try:
        cmd = [
            npx_path, "remotion", "render",
            "src/index.ts",
            "MomentShorts",
            str(output_path),
            "--props", str(props_path),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(REMOTION_V3_DIR),
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError("렌더링 시간 초과 (600초).") from exc
    finally:
        if props_path.exists():
            props_path.unlink()
        # public/ 에서 클립 파일 정리
        if dest_clip.exists():
            dest_clip.unlink()
            logger.info("클립 정리 완료: %s", dest_clip.name)

    if result.returncode != 0:
        error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
        raise RenderError(
            f"Remotion 렌더링 실패 (exit {result.returncode}):\n{error_msg}"
        )

    if not output_path.exists():
        raise RenderError(
            f"렌더링 완료되었으나 출력 파일이 없습니다: {output_path}"
        )

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("렌더링 완료: %s (%.1f MB)", output_path.name, file_size_mb)
    return output_path
