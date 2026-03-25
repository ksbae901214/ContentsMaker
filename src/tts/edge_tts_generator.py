"""Edge-TTS generator — converts ShortsScript to voice MP3.

Uses Microsoft Edge's free TTS engine via edge-tts library.
Generates per-scene audio segments and concatenates them for
precise scene-to-audio timing synchronization.
"""
from __future__ import annotations

import asyncio
import json
import logging
import struct
from datetime import datetime
from pathlib import Path

import edge_tts

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR

logger = logging.getLogger(__name__)

OUTRO_TEXT = "구독과 좋아요를 눌러주시면 더 많은 영상을 볼 수 있습니다."


class TTSError(Exception):
    """Raised when TTS generation fails."""


def generate_voice(script: ShortsScript, output_dir: Path | None = None) -> Path:
    """Generate voice MP3 from a ShortsScript (legacy simple mode).

    Returns path to the generated MP3 file.
    """
    tts_text = script.audio.tts_script
    if not tts_text or not tts_text.strip():
        raise TTSError("TTS 스크립트가 비어있습니다")

    voice = script.audio.voice
    rate = script.audio.rate
    pitch = script.audio.pitch

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = _safe_filename(script.metadata.title)
    output_path = target_dir / f"{timestamp}_{safe_title}.mp3"

    try:
        asyncio.run(_generate_async(tts_text, voice, rate, pitch, output_path))
    except Exception as e:
        raise TTSError(f"TTS 생성 실패: {e}") from e

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TTSError(f"TTS 파일이 생성되지 않았습니다: {output_path}")

    logger.info("TTS 저장 완료: %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)
    return output_path


def generate_voice_with_timing(
    script: ShortsScript,
    output_dir: Path | None = None,
) -> tuple[Path, list[dict]]:
    """Generate per-scene TTS audio and concatenate with precise timing.

    Strategy: generate each scene's voice_text as a separate MP3,
    measure its duration, then concatenate all segments into one file.
    This gives exact start/end timing per scene.

    Returns (audio_path, scene_timings) where scene_timings is:
    [{"scene_id": int, "start_ms": int, "end_ms": int}, ...]
    """
    voice = script.audio.voice
    rate = script.audio.rate
    pitch = script.audio.pitch

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = _safe_filename(script.metadata.title)

    # Generate per-scene audio segments
    scene_segments: list[dict] = []
    temp_files: list[Path] = []

    for scene in script.scenes:
        text = scene.voice_text.strip()
        if not text:
            continue

        seg_path = target_dir / f"{timestamp}_seg_{scene.id:02d}.mp3"
        temp_files.append(seg_path)

        try:
            asyncio.run(_generate_async(text, voice, rate, pitch, seg_path))
        except Exception as e:
            logger.warning("씬 %d TTS 실패: %s", scene.id, e)
            continue

        if not seg_path.exists() or seg_path.stat().st_size == 0:
            logger.warning("씬 %d TTS 빈 파일", scene.id)
            continue

        dur_ms = _get_mp3_duration_ms(seg_path)
        scene_segments.append({
            "scene_id": scene.id,
            "path": seg_path,
            "duration_ms": dur_ms,
        })
        logger.info("  씬 %d: %.1fs (%s)", scene.id, dur_ms / 1000, text[:30])

    # Generate outro segment
    outro_path = target_dir / f"{timestamp}_seg_outro.mp3"
    temp_files.append(outro_path)
    try:
        asyncio.run(_generate_async(OUTRO_TEXT, voice, rate, pitch, outro_path))
        outro_dur_ms = _get_mp3_duration_ms(outro_path) if outro_path.exists() else 0
    except Exception:
        outro_dur_ms = 0

    # Concatenate all segments into one MP3
    output_path = target_dir / f"{timestamp}_{safe_title}.mp3"
    _concat_mp3(
        [s["path"] for s in scene_segments] + ([outro_path] if outro_dur_ms > 0 else []),
        output_path,
    )

    # Build timing map
    timings: list[dict] = []
    cursor_ms = 0
    for seg in scene_segments:
        timings.append({
            "scene_id": seg["scene_id"],
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + seg["duration_ms"],
        })
        cursor_ms += seg["duration_ms"]

    if outro_dur_ms > 0:
        timings.append({
            "scene_id": -1,
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + outro_dur_ms,
        })

    # Save timing
    timing_path = output_path.with_suffix(".timing.json")
    timing_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2))

    # Cleanup temp segments
    for f in temp_files:
        if f.exists():
            f.unlink()

    total_dur = timings[-1]["end_ms"] / 1000 if timings else 0
    logger.info("TTS 완료: %d씬 + 아웃트로, 총 %.1fs", len(scene_segments), total_dur)

    return output_path, timings


def _get_mp3_duration_ms(path: Path) -> int:
    """Get MP3 duration in milliseconds from MPEG frame header.

    Correctly handles both MPEG1 and MPEG2/2.5 bitrate tables.
    edge-tts outputs MPEG2 Layer3 at 24kHz/48kbps.
    """
    # Bitrate tables: [index] → kbps
    MPEG1_L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    MPEG2_L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]

    try:
        file_size = path.stat().st_size
        if file_size < 100:
            return 0

        with open(path, "rb") as f:
            data = f.read(8192)

        for i in range(len(data) - 4):
            if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
                header = struct.unpack(">I", data[i : i + 4])[0]
                version_bits = (header >> 19) & 0x3  # 11=MPEG1, 10=MPEG2, 00=MPEG2.5
                bitrate_idx = (header >> 12) & 0xF

                if 0 < bitrate_idx < 15:
                    if version_bits == 3:  # MPEG1
                        bitrate_kbps = MPEG1_L3[bitrate_idx]
                    else:  # MPEG2 or MPEG2.5
                        bitrate_kbps = MPEG2_L3[bitrate_idx]

                    if bitrate_kbps > 0:
                        return int((file_size * 8 * 1000) / (bitrate_kbps * 1000))

        return 0
    except Exception:
        return 0


def _concat_mp3(paths: list[Path], output: Path) -> None:
    """Concatenate MP3 files by raw byte concatenation."""
    with open(output, "wb") as out:
        for p in paths:
            if p.exists():
                out.write(p.read_bytes())


def _safe_filename(title: str) -> str:
    safe = "".join(c for c in title[:30] if c.isalnum() or c in " _-")
    return safe.strip().replace(" ", "_") or "untitled"


async def _generate_async(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
) -> None:
    """Async edge-tts generation."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(str(output_path))
