"""Content-hash TTS cache + title-based fallback.

Use case: Google AI Studio Gemini TTS has a free-tier quota (10 reqs/day for
``gemini-2.5-flash-tts``). When that quota is exhausted, the political_pro
pipeline falls back to a previously-saved audio file rather than failing the
whole render.

Two lookup strategies:
    1. **Hash-based** (preferred): ``compute_cache_key()`` over text + voice
       + style_prompt + temperature → exact-match lookup in
       ``data/tts_cache/{key}.mp3``.
    2. **Title-based fallback** (best-effort): when hash misses (e.g. cache was
       cleared or the audio is older than this cache scheme), search
       ``data/audio/`` for the most recent file whose stem contains the script
       title slug.
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


# Indirection to enable test-time monkey-patching of cache + audio roots.
def _cache_root() -> Path:
    from src.config.settings import DATA_DIR
    return DATA_DIR / "tts_cache"


def _audio_root() -> Path:
    from src.config.settings import DATA_AUDIO_DIR
    return DATA_AUDIO_DIR


def compute_cache_key(
    *,
    text: str,
    voice_name: str,
    style_prompt: str | None = None,
    temperature: float | None = None,
) -> str:
    """Stable 16-char hex key for the (text, voice, style, temp) tuple.

    The cache key is deliberately content-only (no timestamps) so the same
    script text + voice + style produces the same key on repeat runs.
    """
    payload = json.dumps(
        {
            "text": text or "",
            "voice": voice_name or "",
            "style": style_prompt or "",
            "temp": temperature if temperature is not None else "",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _paths_for_key(key: str) -> tuple[Path, Path]:
    root = _cache_root()
    return root / f"{key}.mp3", root / f"{key}.timing.json"


def lookup_cached(key: str) -> tuple[Path, list[dict]] | None:
    """Return ``(audio_path, timings)`` if both files exist for this key."""
    mp3, timing = _paths_for_key(key)
    if not (mp3.exists() and timing.exists()):
        return None
    try:
        timings = json.loads(timing.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("TTS cache timing JSON parse failed (%s): %s", key, e)
        return None
    return mp3, timings


def save_to_cache(*, key: str, audio_path: Path, timings: list[dict]) -> Path:
    """Copy ``audio_path`` and serialize ``timings`` into the cache.

    Returns the cached audio path (so callers can verify or re-use).
    """
    root = _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    target_mp3, target_timing = _paths_for_key(key)
    if audio_path.resolve() != target_mp3.resolve():
        shutil.copy2(audio_path, target_mp3)
    target_timing.write_text(
        json.dumps(timings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("TTS 캐시 저장: %s (%d bytes)", target_mp3.name, target_mp3.stat().st_size)
    return target_mp3


def _safe_slug(s: str) -> str:
    """Mirror the slug logic used by the Gemini generator filename builder."""
    cleaned = "".join(c for c in (s or "")[:30] if c.isalnum() or c in " _-가-힣")
    return cleaned.strip().replace(" ", "_")


def lookup_by_title_fallback(script_title: str) -> tuple[Path, list[dict]] | None:
    """Best-effort: most recent ``data/audio/*{slug}*.mp3`` with a sibling
    ``.timing.json`` file.

    Used when the exact-hash cache misses but we still want to avoid a hard
    failure (e.g. text edited slightly between runs but voice still cached).
    """
    audio_dir = _audio_root()
    if not audio_dir.exists():
        return None
    slug = _safe_slug(script_title)
    if not slug:
        return None
    candidates = sorted(
        audio_dir.glob(f"*{slug}*.mp3"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for mp3 in candidates:
        timing = mp3.with_suffix(".timing.json")
        if not timing.exists():
            # Some older recordings stored timing alongside as `<base>.timing.json`
            timing = mp3.parent / f"{mp3.stem}.timing.json"
        if timing.exists():
            try:
                timings = json.loads(timing.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            logger.info("TTS title-fallback hit: %s", mp3.name)
            return mp3, timings
    return None


def is_quota_error(exc: BaseException) -> bool:
    """Heuristic: detect Google AI 429 RESOURCE_EXHAUSTED responses."""
    msg = str(exc) or ""
    if not msg:
        return False
    needles = (
        "429",
        "RESOURCE_EXHAUSTED",
        "quota",
        "Quota exceeded",
        "rate limit",
    )
    lower = msg.lower()
    return any(n.lower() in lower for n in needles)


__all__ = [
    "compute_cache_key",
    "lookup_cached",
    "save_to_cache",
    "lookup_by_title_fallback",
    "is_quota_error",
]
