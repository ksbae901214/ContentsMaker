"""Edge-TTS generator — converts ShortsScript to voice MP3.

Uses Microsoft Edge's free TTS engine via edge-tts library.
Constitution Principle I: Zero-Cost Pipeline ($0).
Constitution Principle V: Emotion-Driven voice selection.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import edge_tts

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR
from src.tts.voice_config import get_voice_config

logger = logging.getLogger(__name__)


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
