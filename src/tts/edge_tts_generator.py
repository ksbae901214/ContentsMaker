"""Edge-TTS generator — converts ShortsScript to voice MP3.

Uses Microsoft Edge's free TTS engine via edge-tts library.
Constitution Principle I: Zero-Cost Pipeline ($0).
Constitution Principle V: Emotion-Driven voice selection.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import edge_tts

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR
from src.tts.voice_config import get_voice_config

logger = logging.getLogger(__name__)

OUTRO_TEXT = "구독과 좋아요를 눌러주시면 더 많은 영상을 볼 수 있습니다."


class TTSError(Exception):
    """Raised when TTS generation fails."""


def generate_voice(script: ShortsScript, output_dir: Path | None = None) -> Path:
    """Generate voice MP3 from a ShortsScript.

    Synchronous wrapper around async edge-tts.
    Returns path to the generated MP3 file.
    """
    tts_text = script.audio.tts_script
    if not tts_text or not tts_text.strip():
        raise TTSError("TTS 스크립트가 비어있습니다")

    voice = script.audio.voice
    rate = script.audio.rate
    pitch = script.audio.pitch

    logger.info("TTS 생성 시작: voice=%s, rate=%s, pitch=%s", voice, rate, pitch)
    logger.info("TTS 텍스트 (%d자): %s...", len(tts_text), tts_text[:50])

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(
        c for c in script.metadata.title[:30] if c.isalnum() or c in " _-"
    )
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    filename = f"{timestamp}_{safe_title}.mp3"
    output_path = target_dir / filename

    try:
        asyncio.run(_generate_async(tts_text, voice, rate, pitch, output_path))
    except Exception as e:
        raise TTSError(f"TTS 생성 실패: {e}") from e

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TTSError(f"TTS 파일이 생성되지 않았습니다: {output_path}")

    file_size_kb = output_path.stat().st_size / 1024
    logger.info("TTS 저장 완료: %s (%.1f KB)", output_path, file_size_kb)

    return output_path


def generate_voice_with_timing(
    script: ShortsScript,
    output_dir: Path | None = None,
) -> tuple[Path, list[dict]]:
    """Generate voice MP3 and extract per-scene timing via WordBoundary events.

    Returns (audio_path, scene_timings) where scene_timings is:
    [{"scene_id": int, "start_ms": int, "end_ms": int}, ...]
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
    safe_title = "".join(
        c for c in script.metadata.title[:30] if c.isalnum() or c in " _-"
    )
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    filename = f"{timestamp}_{safe_title}.mp3"
    output_path = target_dir / filename

    # Build per-scene text segments with markers
    scene_texts = []
    for scene in script.scenes:
        scene_texts.append({
            "scene_id": scene.id,
            "voice_text": scene.voice_text,
            "char_start": 0,
            "char_end": 0,
        })

    # Calculate character offsets in the full TTS text
    # TTS text = all voice_texts joined with space
    full_text = ""
    for st in scene_texts:
        if full_text:
            full_text += " "
        st["char_start"] = len(full_text)
        full_text += st["voice_text"]
        st["char_end"] = len(full_text)

    # Add outro text
    outro_char_start = len(full_text) + 1
    full_text_with_outro = full_text + " " + OUTRO_TEXT

    logger.info("TTS 생성 (타이밍 추출): %d자 + 아웃트로", len(full_text))

    try:
        word_boundaries = asyncio.run(
            _generate_with_boundaries(full_text_with_outro, voice, rate, pitch, output_path)
        )
    except Exception as e:
        raise TTSError(f"TTS 생성 실패: {e}") from e

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TTSError(f"TTS 파일이 생성되지 않았습니다: {output_path}")

    # Map word boundaries to scenes
    scene_timings = _map_boundaries_to_scenes(word_boundaries, scene_texts, outro_char_start)

    timing_path = output_path.with_suffix(".timing.json")
    timing_path.write_text(json.dumps(scene_timings, ensure_ascii=False, indent=2))
    logger.info("타이밍 저장: %s (%d씬)", timing_path, len(scene_timings))

    return output_path, scene_timings


def generate_outro_voice(
    voice: str = "ko-KR-SunHiNeural",
    rate: str = "+20%",
    pitch: str = "+0Hz",
    output_dir: Path | None = None,
) -> Path:
    """Generate outro TTS: '구독과 좋아요를 눌러주시면...'"""
    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = target_dir / f"{timestamp}_outro.mp3"

    try:
        asyncio.run(_generate_async(OUTRO_TEXT, voice, rate, pitch, output_path))
    except Exception as e:
        raise TTSError(f"아웃트로 TTS 생성 실패: {e}") from e

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TTSError("아웃트로 TTS 파일이 생성되지 않았습니다")

    logger.info("아웃트로 TTS 저장: %s", output_path)
    return output_path


def _map_boundaries_to_scenes(
    boundaries: list[dict],
    scene_texts: list[dict],
    outro_char_start: int,
) -> list[dict]:
    """Map WordBoundary events to scene timing ranges."""
    timings = []

    for st in scene_texts:
        scene_start_ms = None
        scene_end_ms = None

        for wb in boundaries:
            offset = wb["offset"]
            # Check if this word falls within the scene's character range
            if st["char_start"] <= offset < st["char_end"]:
                if scene_start_ms is None:
                    scene_start_ms = wb["time_ms"]
                scene_end_ms = wb["time_ms"] + wb["duration_ms"]

        if scene_start_ms is not None:
            timings.append({
                "scene_id": st["scene_id"],
                "start_ms": scene_start_ms,
                "end_ms": scene_end_ms,
            })

    # Outro timing
    outro_start_ms = None
    outro_end_ms = None
    for wb in boundaries:
        if wb["offset"] >= outro_char_start:
            if outro_start_ms is None:
                outro_start_ms = wb["time_ms"]
            outro_end_ms = wb["time_ms"] + wb["duration_ms"]

    if outro_start_ms is not None:
        timings.append({
            "scene_id": -1,  # special: outro
            "start_ms": outro_start_ms,
            "end_ms": outro_end_ms,
        })

    return timings


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


async def _generate_with_boundaries(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
) -> list[dict]:
    """Generate TTS and collect WordBoundary events for timing sync."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )

    boundaries: list[dict] = []

    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "offset": chunk["offset"],
                    "duration_ms": chunk["duration"] // 10000,  # 100ns units → ms
                    "time_ms": int(chunk["offset_in_ticks"] // 10000) if "offset_in_ticks" in chunk else 0,
                    "text": chunk.get("text", ""),
                })

    # If offset_in_ticks wasn't available, estimate from audio offset
    if boundaries and boundaries[0]["time_ms"] == 0 and len(boundaries) > 1:
        # Use cumulative duration as fallback
        cumulative = 0
        for wb in boundaries:
            wb["time_ms"] = cumulative
            cumulative += max(wb["duration_ms"], 100)

    return boundaries
