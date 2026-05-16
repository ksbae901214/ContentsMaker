"""Tests for TTS content-hash cache + quota-fallback path.

When Gemini TTS quota (429 RESOURCE_EXHAUSTED) is exhausted, the system should
automatically reuse a previously cached TTS audio for the same content
(same script text + voice + style_prompt + temperature).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)


def _mk_script(title: str = "test", voice_text: str = "테스트 문장") -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title=title, emotion_type="angry", duration=10.0,
            source_url="", source_type="political_pro",
        ),
        scenes=(
            Scene(id=0, timestamp=0, duration=5.0, type="title",
                  text=voice_text, voice_text=voice_text,
                  emphasis=True, highlight_words=()),
        ),
        audio=AudioConfig(tts_script=voice_text),
        background=BackgroundConfig(type="gradient", colors=()),
    )


# ─────────────────────────── Cache key + roundtrip ───────────────────────────


def test_cache_key_is_deterministic():
    from src.tts.tts_cache import compute_cache_key
    k1 = compute_cache_key(text="안녕", voice_name="Charon", style_prompt="x", temperature=0.5)
    k2 = compute_cache_key(text="안녕", voice_name="Charon", style_prompt="x", temperature=0.5)
    assert k1 == k2
    assert len(k1) >= 8


def test_cache_key_differs_on_content_change():
    from src.tts.tts_cache import compute_cache_key
    k1 = compute_cache_key(text="A", voice_name="Charon", style_prompt="", temperature=0.5)
    k2 = compute_cache_key(text="B", voice_name="Charon", style_prompt="", temperature=0.5)
    k3 = compute_cache_key(text="A", voice_name="Leda", style_prompt="", temperature=0.5)
    k4 = compute_cache_key(text="A", voice_name="Charon", style_prompt="x", temperature=0.5)
    k5 = compute_cache_key(text="A", voice_name="Charon", style_prompt="", temperature=1.0)
    assert len({k1, k2, k3, k4, k5}) == 5  # all different


def test_save_and_lookup_cache(tmp_path, monkeypatch):
    from src.tts import tts_cache
    monkeypatch.setattr(tts_cache, "_cache_root", lambda: tmp_path / "tts_cache")
    key = "abc123def456"
    audio_src = tmp_path / "src.mp3"
    audio_src.write_bytes(b"FAKE_MP3_BYTES")
    timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 5000}]
    tts_cache.save_to_cache(key=key, audio_path=audio_src, timings=timings)

    found = tts_cache.lookup_cached(key)
    assert found is not None
    cached_path, cached_timings = found
    assert cached_path.exists()
    assert cached_path.read_bytes() == b"FAKE_MP3_BYTES"
    assert cached_timings == timings


def test_lookup_cached_returns_none_when_missing(tmp_path, monkeypatch):
    from src.tts import tts_cache
    monkeypatch.setattr(tts_cache, "_cache_root", lambda: tmp_path / "tts_cache")
    assert tts_cache.lookup_cached("nonexistent_key") is None


# ─────────────────────────── Title-based fallback ───────────────────────────


def test_lookup_by_title_fallback_finds_recent_match(tmp_path, monkeypatch):
    from src.tts import tts_cache
    fake_audio_dir = tmp_path / "audio"
    fake_audio_dir.mkdir()
    monkeypatch.setattr(tts_cache, "_audio_root", lambda: fake_audio_dir)

    # Create 2 candidates; we should pick the most recent matching one
    older = fake_audio_dir / "20260513_120000_test_title.mp3"
    older.write_bytes(b"OLDER")
    older_t = older.with_suffix(".timing.json")
    older_t.write_text(json.dumps([{"scene_id": 0, "start_ms": 0, "end_ms": 1000}]))

    newer = fake_audio_dir / "20260514_120000_test_title.mp3"
    newer.write_bytes(b"NEWER")
    newer_t = newer.with_suffix(".timing.json")
    newer_t.write_text(json.dumps([{"scene_id": 0, "start_ms": 0, "end_ms": 2000}]))

    # Bump newer's mtime to be unambiguously after older
    import os
    os.utime(older, (1715000000, 1715000000))
    os.utime(older_t, (1715000000, 1715000000))
    os.utime(newer, (1715990000, 1715990000))
    os.utime(newer_t, (1715990000, 1715990000))

    found = tts_cache.lookup_by_title_fallback("test title")
    assert found is not None
    audio_path, timings = found
    assert audio_path.read_bytes() == b"NEWER"
    assert timings[0]["end_ms"] == 2000


def test_lookup_by_title_fallback_returns_none_when_no_match(tmp_path, monkeypatch):
    from src.tts import tts_cache
    fake_audio_dir = tmp_path / "audio"
    fake_audio_dir.mkdir()
    monkeypatch.setattr(tts_cache, "_audio_root", lambda: fake_audio_dir)
    assert tts_cache.lookup_by_title_fallback("nonexistent slug") is None


# ─────────────────────────── Quota error → cache fallback ───────────────────


def test_gemini_quota_error_falls_back_to_cache(tmp_path, monkeypatch):
    """Simulate 429 RESOURCE_EXHAUSTED → cache should be returned."""
    from src.tts import tts_cache
    from src.tts import gemini_tts_generator as gen

    # Direct cache root override
    monkeypatch.setattr(tts_cache, "_cache_root", lambda: tmp_path / "cache")
    monkeypatch.setattr(tts_cache, "_audio_root", lambda: tmp_path / "audio")

    script = _mk_script(title="test_quota", voice_text="할당량 초과 테스트")

    # Pre-populate cache with the EXACT key the function will compute
    key = tts_cache.compute_cache_key(
        text="할당량 초과 테스트",
        voice_name="Charon",
        style_prompt="news:",
        temperature=0.5,
    )
    cached_audio = tmp_path / "pre_cached.mp3"
    cached_audio.write_bytes(b"CACHED_FALLBACK_BYTES")
    cached_timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 4000}]
    tts_cache.save_to_cache(key=key, audio_path=cached_audio, timings=cached_timings)

    # Simulate Gemini API quota error (429)
    quota_error = Exception(
        "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED'}}"
    )
    monkeypatch.setattr(gen, "_call_gemini_tts", MagicMock(side_effect=quota_error))

    # Should NOT raise — falls back to cached audio
    audio_path, timings = gen.generate_voice_with_timing_gemini(
        script,
        output_dir=tmp_path / "audio",
        voice_name="Charon",
        api_key="fake",
        style_prompt="news:",
        temperature=0.5,
        include_outro=False,
    )

    assert audio_path.exists()
    assert audio_path.read_bytes() == b"CACHED_FALLBACK_BYTES"
    assert timings == cached_timings


def test_gemini_quota_error_with_no_cache_raises(monkeypatch, tmp_path):
    """Quota error + no cached audio → still raises a clear error."""
    from src.tts import tts_cache
    from src.tts import gemini_tts_generator as gen

    monkeypatch.setattr(tts_cache, "_cache_root", lambda: tmp_path / "cache_empty")
    monkeypatch.setattr(tts_cache, "_audio_root", lambda: tmp_path / "audio_empty")

    script = _mk_script(title="no_cache", voice_text="캐시 없음")
    quota_error = Exception(
        "429 RESOURCE_EXHAUSTED quota exceeded"
    )
    monkeypatch.setattr(gen, "_call_gemini_tts", MagicMock(side_effect=quota_error))

    with pytest.raises(gen.GeminiTTSError) as exc:
        gen.generate_voice_with_timing_gemini(
            script,
            output_dir=tmp_path / "audio_empty",
            voice_name="Charon",
            api_key="fake",
            include_outro=False,
        )
    # The error should mention quota OR cache absence so user knows what happened
    msg = str(exc.value).lower()
    assert ("quota" in msg or "한도" in str(exc.value) or "cache" in msg or "캐시" in str(exc.value))


def test_successful_call_saves_to_cache(tmp_path, monkeypatch):
    """Successful Gemini call should write to cache for future fallback."""
    from src.tts import tts_cache
    from src.tts import gemini_tts_generator as gen

    monkeypatch.setattr(tts_cache, "_cache_root", lambda: tmp_path / "cache")
    monkeypatch.setattr(tts_cache, "_audio_root", lambda: tmp_path / "audio")

    script = _mk_script(title="save_test", voice_text="성공 테스트")
    fake_pcm = b"\x00\x01" * 24_000  # 1s mono PCM at 24kHz
    monkeypatch.setattr(gen, "_call_gemini_tts", MagicMock(return_value=fake_pcm))
    # Skip ffmpeg by patching _pcm_to_mp3
    monkeypatch.setattr(gen, "_pcm_to_mp3", lambda pcm, path: path.write_bytes(b"FAKE_MP3"))

    audio_path, timings = gen.generate_voice_with_timing_gemini(
        script,
        output_dir=tmp_path / "audio",
        voice_name="Charon",
        api_key="fake",
        style_prompt="x:",
        temperature=0.5,
        include_outro=False,
    )

    # The cache should now contain this content
    key = tts_cache.compute_cache_key(
        text="성공 테스트",
        voice_name="Charon",
        style_prompt="x:",
        temperature=0.5,
    )
    found = tts_cache.lookup_cached(key)
    assert found is not None, "successful call should populate cache"
    cached_path, cached_timings = found
    assert cached_path.exists()
    assert cached_timings == timings
