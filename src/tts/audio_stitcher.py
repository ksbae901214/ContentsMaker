"""Audio stitcher for political commentary cross-edit mode.

Merges original clip audio segments (for "clip" scenes) and TTS commentary
audio (for "commentary"/"title" scenes) into a single continuous MP3 file.

The merged audio is consumed by Remotion as a single <Audio> track, so no
Remotion changes are needed.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.tts.edge_tts_generator import (
    _concat_mp3,
    _generate_async,
    _get_mp3_duration_ms,
)

logger = logging.getLogger(__name__)


class StitchError(Exception):
    """Raised when audio stitching fails."""


def _extract_audio_segment(
    audio_path: Path, start: float, end: float, output: Path
) -> Path:
    """Extract a segment from an MP3 file using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_path),
        "-ss", str(start),
        "-to", str(end),
        "-c", "copy",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise StitchError(f"오디오 세그먼트 추출 실패: {result.stderr[:200]}")
    return output


def stitch_political_audio(
    script: ShortsScript,
    clip_audio_path: Path,
    voice: str = "ko-KR-InJoonNeural",
    rate: str = "+10%",
    pitch: str = "+0Hz",
    output_dir: Path | None = None,
) -> tuple[Path, list[dict]]:
    """Stitch audio for cross-edit political commentary.

    For each scene:
      - "clip" scenes: extract the matching segment from clip_audio_path
      - "title"/"commentary" scenes: generate TTS via edge-tts

    Returns:
        (merged_audio_path, scene_timings)
        scene_timings: [{"scene_id": int, "start_ms": int, "end_ms": int}, ...]
    """
    from src.config.settings import DATA_AUDIO_DIR

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    segments: list[Path] = []
    timings: list[dict] = []
    cursor_ms = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        for scene in script.scenes:
            seg_path = tmp_dir / f"seg_{scene.id:02d}.mp3"

            if scene.type == "clip" and scene.clip_start is not None and scene.clip_end is not None:
                # Extract original audio segment
                _extract_audio_segment(
                    clip_audio_path, scene.clip_start, scene.clip_end, seg_path
                )
            elif scene.voice_text:
                # Generate TTS for commentary/title scenes
                asyncio.run(_generate_async(
                    text=scene.voice_text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    output_path=seg_path,
                ))
            else:
                # Scene with no audio (e.g., empty voice_text) — create silence
                _create_silence(scene.duration, seg_path)

            if not seg_path.exists() or seg_path.stat().st_size == 0:
                _create_silence(scene.duration, seg_path)

            dur_ms = _get_mp3_duration_ms(seg_path)
            if dur_ms == 0:
                dur_ms = int(scene.duration * 1000)

            timings.append({
                "scene_id": scene.id,
                "start_ms": cursor_ms,
                "end_ms": cursor_ms + dur_ms,
            })
            segments.append(seg_path)
            cursor_ms += dur_ms

            logger.info(
                "씬 %d (%s): %dms", scene.id, scene.type, dur_ms
            )

        # Concatenate all segments
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = target_dir / f"{timestamp}_political_stitched.mp3"
        _concat_mp3(segments, output_path)

    total_s = cursor_ms / 1000
    logger.info("오디오 스티칭 완료: %d씬, %.1fs", len(segments), total_s)
    return output_path, timings


def _create_silence(duration_s: float, output: Path) -> None:
    """Create a silent MP3 file of the given duration using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration_s),
        "-c:a", "libmp3lame",
        "-ab", "48k",
        str(output),
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=10)
