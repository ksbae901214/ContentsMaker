"""Remotion video renderer — generates MP4 from ShortsScript + audio.

Calls Remotion CLI via subprocess to render the final video.
Constitution Principle III: Text-First Video.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

DATA_OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"
REMOTION_DIR = PROJECT_ROOT / "src" / "video" / "remotion"
FPS = 30


class RenderError(Exception):
    """Raised when video rendering fails."""


def render_video(
    script: ShortsScript,
    audio_path: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Render a ShortsScript into an MP4 video.

    1. Write props JSON (script data + audio path)
    2. Call Remotion CLI to render
    3. Return path to generated MP4
    """
    target_dir = output_dir or DATA_OUTPUTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(
        c for c in script.metadata.title[:30] if c.isalnum() or c in " _-"
    )
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    output_filename = f"{timestamp}_{safe_title}.mp4"
    output_path = target_dir / output_filename

    duration_frames = int(script.metadata.duration * FPS)

    # Copy audio to Remotion public dir for staticFile() access
    public_dir = PROJECT_ROOT / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    audio_filename = ""
    if audio_path and audio_path.exists():
        audio_filename = f"audio_{timestamp}.mp3"
        shutil.copy2(audio_path, public_dir / audio_filename)

    props = {
        "scriptData": _convert_to_camel_case(script.to_dict()),
        "audioFile": audio_filename,
    }

    props_path = target_dir / f"{timestamp}_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    logger.info("렌더링 시작: %s (%d프레임, %d초)", output_filename, duration_frames, script.metadata.duration)

    # Check npx availability
    npx_path = shutil.which("npx")
    if not npx_path:
        raise RenderError("npx를 찾을 수 없습니다. Node.js가 설치되어 있는지 확인하세요.")

    cmd = [
        npx_path, "remotion", "render",
        str(REMOTION_DIR / "src" / "index.ts"),
        "BlindShorts",
        str(output_path),
        "--props", str(props_path),
        "--frames", f"0-{duration_frames - 1}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        raise RenderError("렌더링 시간 초과 (5분). 영상 길이를 줄여보세요.")
    finally:
        if props_path.exists():
            props_path.unlink()
        if audio_filename:
            audio_public = public_dir / audio_filename
            if audio_public.exists():
                audio_public.unlink()

    if result.returncode != 0:
        error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
        raise RenderError(f"Remotion 렌더링 실패 (exit {result.returncode}):\n{error_msg}")

    if not output_path.exists():
        raise RenderError(f"렌더링 완료되었으나 출력 파일이 없습니다: {output_path}")

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("렌더링 완료: %s (%.1f MB)", output_path, file_size_mb)

    return output_path


def _convert_to_camel_case(data: dict) -> dict:
    """Convert snake_case keys to camelCase for Remotion props."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            camel_key = _snake_to_camel(key)
            result[camel_key] = _convert_to_camel_case(value)
        return result
    if isinstance(data, list):
        return [_convert_to_camel_case(item) for item in data]
    return data


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
