"""Remotion video renderer — generates MP4 from ShortsScript + audio + images.

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
SPEED_FACTOR = 1.2  # 1.2x playback speed (TTS + video)


class RenderError(Exception):
    """Raised when video rendering fails."""


def render_video(
    script: ShortsScript,
    audio_path: Path | None = None,
    scene_images: list[dict] | None = None,
    output_dir: Path | None = None,
    use_bgm: bool = True,
) -> Path:
    """Render a ShortsScript into an MP4 video.

    Args:
        script: The ShortsScript to render
        audio_path: Path to voice MP3 file
        scene_images: List of {scene_id, image_path} dicts for manga backgrounds
        output_dir: Output directory (defaults to data/outputs/)
        use_bgm: Whether to include background music
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

    scaled_duration = script.metadata.duration / SPEED_FACTOR
    outro_seconds = 4  # Subscribe/like/bell outro
    duration_frames = int((scaled_duration + outro_seconds) * FPS)

    # Copy assets to Remotion public dir for staticFile() access
    public_dir = PROJECT_ROOT / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    temp_files: list[Path] = []

    # Audio
    audio_filename = ""
    if audio_path and audio_path.exists():
        audio_filename = f"audio_{timestamp}.mp3"
        shutil.copy2(audio_path, public_dir / audio_filename)
        temp_files.append(public_dir / audio_filename)

    # Scene images
    scene_image_props = []
    if scene_images:
        for img_data in scene_images:
            src_path = Path(img_data["image_path"])
            if src_path.exists():
                img_filename = f"img_{timestamp}_scene_{img_data['scene_id']:02d}.png"
                shutil.copy2(src_path, public_dir / img_filename)
                temp_files.append(public_dir / img_filename)
                scene_image_props.append({
                    "sceneId": img_data["scene_id"],
                    "imageFile": img_filename,
                })

    # BGM
    bgm_filename = ""
    if use_bgm:
        from src.tts.voice_config import get_bgm_file
        emotion = script.metadata.emotion_type
        bgm_src = PROJECT_ROOT / "data" / "bgm" / get_bgm_file(emotion)
        if bgm_src.exists():
            bgm_filename = f"bgm_{timestamp}.mp3"
            shutil.copy2(bgm_src, public_dir / bgm_filename)
            temp_files.append(public_dir / bgm_filename)
            logger.info("BGM 적용: %s (%s)", bgm_src.name, emotion)
        else:
            logger.warning("BGM 파일 없음: %s — BGM 없이 진행", bgm_src)

    script_dict = _convert_to_camel_case(script.to_dict())
    # Scale scene timings for 1.2x speed
    script_dict["metadata"]["duration"] = scaled_duration
    for scene in script_dict["scenes"]:
        scene["timestamp"] = scene["timestamp"] / SPEED_FACTOR
        scene["duration"] = scene["duration"] / SPEED_FACTOR

    props = {
        "scriptData": script_dict,
        "audioFile": audio_filename,
        "sceneImages": scene_image_props,
        "bgmFile": bgm_filename,
    }

    props_path = target_dir / f"{timestamp}_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    img_count = len(scene_image_props)
    logger.info(
        "렌더링 시작: %s (%d프레임, %.1f초 @%.1fx, 이미지 %d장)",
        output_filename, duration_frames, scaled_duration, SPEED_FACTOR, img_count,
    )

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
        raise RenderError("렌더링 시간 초과 (5분).")
    finally:
        if props_path.exists():
            props_path.unlink()
        for f in temp_files:
            if f.exists():
                f.unlink()

    if result.returncode != 0:
        error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
        raise RenderError(f"Remotion 렌더링 실패 (exit {result.returncode}):\n{error_msg}")

    if not output_path.exists():
        raise RenderError(f"렌더링 완료되었으나 출력 파일이 없습니다: {output_path}")

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("렌더링 완료: %s (%.1f MB)", output_path, file_size_mb)

    return output_path


def _convert_to_camel_case(data):
    """Convert snake_case keys to camelCase for Remotion props."""
    if isinstance(data, dict):
        return {_snake_to_camel(k): _convert_to_camel_case(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_to_camel_case(item) for item in data]
    return data


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
