"""Gemini TTS generator — converts ShortsScript to voice MP3 via Google AI Studio.

Phase 1 MVP: Single API call strategy (to respect 5 RPM free tier limit),
character-ratio timing distribution across scenes.

Why single-call: Gemini TTS free tier is limited to 5 requests per minute. A
10-scene video would need 2 minutes of waiting with per-scene calls. Instead
we combine all scenes into one request and approximate per-scene timings by
character count, matching the proportion of spoken audio.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR
from src.video.outro_template import OUTRO_VOICE_TEXT

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Leda"
# Gemini TTS returns raw PCM: 24kHz, 16-bit, mono (no WAV header).
SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2


class GeminiTTSError(Exception):
    """Raised when Gemini TTS generation fails."""


def compute_scene_timings(
    scenes,
    total_duration_ms: int,
    outro_duration_ms: int = 0,
) -> list[dict]:
    """Distribute total audio duration across scenes by voice_text character count.

    The outro (if any) is allocated ``outro_duration_ms`` and gets scene_id=-1.
    The remaining ``total_duration_ms - outro_duration_ms`` is split proportionally
    among scenes with non-empty voice_text.
    """
    char_counts = [
        (s.id, len((s.voice_text or "").strip()))
        for s in scenes
    ]
    total_chars = sum(c for _, c in char_counts)
    if total_chars == 0:
        return []

    main_duration_ms = max(0, total_duration_ms - outro_duration_ms)
    timings: list[dict] = []
    cursor_ms = 0
    for sid, chars in char_counts:
        if chars == 0:
            continue
        duration_ms = round(main_duration_ms * chars / total_chars)
        timings.append({
            "scene_id": sid,
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + duration_ms,
        })
        cursor_ms += duration_ms

    if outro_duration_ms > 0:
        timings.append({
            "scene_id": -1,
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + outro_duration_ms,
        })

    return timings


def _pcm_duration_ms(pcm_bytes: bytes) -> int:
    """Milliseconds for mono 16-bit PCM at SAMPLE_RATE."""
    bytes_per_ms = SAMPLE_RATE * BYTES_PER_SAMPLE // 1000  # 48
    return len(pcm_bytes) // bytes_per_ms


def _pcm_to_mp3(pcm_bytes: bytes, output_path: Path) -> None:
    """Convert raw PCM (24kHz/16bit/mono) to MP3 via ffmpeg stdin pipe."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-f", "s16le",
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            "-i", "pipe:0",
            "-y",
            "-loglevel", "error",
            str(output_path),
        ],
        input=pcm_bytes,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise GeminiTTSError(
            f"ffmpeg PCM→MP3 변환 실패: {result.stderr.decode(errors='replace')[:300]}"
        )


def _call_gemini_tts(
    text: str,
    voice_name: str,
    api_key: str,
    style_prompt: str | None = None,
    temperature: float | None = None,
    max_retries: int = 4,
) -> bytes:
    """Call Gemini TTS API and return raw PCM bytes.

    Args:
        text: Body text to be spoken.
        voice_name: Prebuilt voice name (e.g., "Leda", "Charon").
        api_key: Google AI Studio API key.
        style_prompt: Optional natural-language style instruction prepended to
            ``text``. Example: "Read in a British RP newscaster voice at a rapid
            pace, with neutral political tone:". Gemini TTS follows the
            instruction when the speech is generated.
        temperature: Optional sampling temperature in [0, 2]. Lower values
            produce more consistent delivery (e.g., 0.5 for newscaster tone).
            ``None`` lets the API pick its default.
        max_retries: Retry budget for transient empty-content responses
            (FinishReason.OTHER, content=None) and 500 INTERNAL errors. The
            same prompt is occasionally rejected by Gemini's response filter
            on long Korean political text + style_prompt combos, even though
            it succeeds on retry. lock-in (Charon + style_prompt + temp 0.5)
            is preserved — only retry behavior is added (2026-06-08).
    """
    import time

    client = genai.Client(api_key=api_key)

    contents = f"{style_prompt} {text}" if style_prompt else text

    config_kwargs: dict = {
        "response_modalities": ["AUDIO"],
        "speech_config": types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name,
                ),
            ),
        ),
    }
    if temperature is not None:
        config_kwargs["temperature"] = temperature

    last_finish = None
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            cand = response.candidates[0]
            if cand.content and cand.content.parts:
                part = cand.content.parts[0]
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
            last_finish = cand.finish_reason
            logger.warning(
                "Gemini TTS 빈 응답 (attempt %d/%d, finish_reason=%s) — 재시도",
                attempt, max_retries, last_finish,
            )
        except Exception as e:
            # 500 INTERNAL or transient HTTPX issues — retry.
            msg = str(e)
            if "500" in msg or "INTERNAL" in msg or "UNAVAILABLE" in msg or "503" in msg:
                last_exc = e
                logger.warning(
                    "Gemini TTS 일시 오류 (attempt %d/%d): %s — 재시도",
                    attempt, max_retries, msg[:200],
                )
            else:
                # 400/permanent errors — propagate immediately.
                raise
        # Exponential backoff: 1s, 2s, 4s, 8s
        if attempt < max_retries:
            time.sleep(2 ** (attempt - 1))

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(
        f"Gemini TTS {max_retries}회 모두 빈 응답 (last finish_reason={last_finish})"
    )


def _safe_filename(title: str) -> str:
    safe = "".join(c for c in title[:30] if c.isalnum() or c in " _-")
    return safe.strip().replace(" ", "_") or "untitled"


def generate_voice_with_timing_gemini(
    script: ShortsScript,
    output_dir: Path | None = None,
    voice_name: str = DEFAULT_VOICE,
    api_key: str | None = None,
    include_outro: bool = True,
    style_prompt: str | None = None,
    temperature: float | None = None,
) -> tuple[Path, list[dict]]:
    """Generate voice MP3 from a ShortsScript using Gemini TTS.

    Returns (audio_path, scene_timings) matching edge_tts_generator's format:
        [{"scene_id": int, "start_ms": int, "end_ms": int}, ...]
    Outro (if present) gets scene_id = -1.

    Quota-resilient (2026-05-14): when Gemini returns 429 RESOURCE_EXHAUSTED,
    automatically fall back to:
        1. Content-hash cache (data/tts_cache/{hash}.mp3) if same text+voice
           +style_prompt+temperature was synthesized before.
        2. Title-based fallback in data/audio/ — best-effort, picks the most
           recent matching mp3+timing.json pair.
    Successful API calls always populate the cache for future fallback.
    """
    from src.tts import tts_cache  # local import — avoids any module-cycle risk

    key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise GeminiTTSError(
            "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. "
            "https://aistudio.google.com/app/apikey 에서 발급 후 "
            "export GEMINI_API_KEY='...' 로 설정하세요."
        )

    parts: list[str] = []
    for scene in script.scenes:
        text = (scene.voice_text or "").strip()
        if text:
            parts.append(text)
    if not parts:
        raise GeminiTTSError("스크립트에 음성 텍스트가 없습니다")

    main_text = " ".join(parts)
    full_text = f"{main_text} {OUTRO_VOICE_TEXT}" if include_outro else main_text

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = _safe_filename(script.metadata.title)
    output_path = target_dir / f"{timestamp}_{safe_title}.mp3"

    cache_key = tts_cache.compute_cache_key(
        text=full_text,
        voice_name=voice_name,
        style_prompt=style_prompt,
        temperature=temperature,
    )

    logger.info(
        "Gemini TTS 호출: voice=%s, 씬=%d개, 텍스트=%d자, cache_key=%s",
        voice_name, len(parts), len(full_text), cache_key,
    )

    try:
        pcm_bytes = _call_gemini_tts(
            full_text,
            voice_name,
            key,
            style_prompt=style_prompt,
            temperature=temperature,
        )
    except Exception as e:
        # ── Quota fallback path ──────────────────────────────────────
        if tts_cache.is_quota_error(e):
            logger.warning(
                "Gemini TTS quota 초과 감지 — 캐시 폴백 시도 (key=%s)", cache_key,
            )
            cached = tts_cache.lookup_cached(cache_key)
            if cached is None:
                cached = tts_cache.lookup_by_title_fallback(script.metadata.title)
            if cached is not None:
                cached_audio, cached_timings = cached
                logger.info(
                    "✅ TTS 캐시 폴백 성공: %s (%d 씬 timing 재사용)",
                    cached_audio.name, len(cached_timings),
                )
                return cached_audio, cached_timings
            raise GeminiTTSError(
                "Gemini TTS API 한도(quota)가 초과되었고 재사용 가능한 캐시도 없습니다. "
                "잠시 후 다시 시도하거나 동일 텍스트로 이전에 생성한 TTS가 "
                f"data/tts_cache/ 또는 data/audio/ 에 있는지 확인하세요. (원인: {e})"
            ) from e
        raise GeminiTTSError(f"Gemini TTS API 호출 실패: {e}") from e

    if not pcm_bytes:
        raise GeminiTTSError("Gemini API가 빈 오디오를 반환했습니다")

    total_ms = _pcm_duration_ms(pcm_bytes)
    _pcm_to_mp3(pcm_bytes, output_path)

    outro_ms = 0
    if include_outro:
        outro_chars = len(OUTRO_VOICE_TEXT)
        total_chars = len(main_text) + outro_chars
        outro_ms = round(total_ms * outro_chars / total_chars) if total_chars else 0

    timings = compute_scene_timings(
        script.scenes,
        total_duration_ms=total_ms,
        outro_duration_ms=outro_ms,
    )

    timing_path = output_path.with_suffix(".timing.json")
    timing_path.write_text(
        json.dumps(timings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 자동 캐시 저장 — 다음 quota 초과 시 폴백 가능
    try:
        tts_cache.save_to_cache(key=cache_key, audio_path=output_path, timings=timings)
    except Exception as cache_err:
        # 캐시 저장 실패는 치명적이지 않음 (TTS 자체는 성공)
        logger.warning("TTS 캐시 저장 실패 (무시): %s", cache_err)

    logger.info(
        "Gemini TTS 완료: %s (%.1fs)", output_path.name, total_ms / 1000,
    )
    return output_path, timings
