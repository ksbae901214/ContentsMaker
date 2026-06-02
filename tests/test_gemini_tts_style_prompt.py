"""Tests for Gemini TTS style_prompt + temperature parameter passing.

Spec mapping: T004 / Feature 009 — Charon voice, British RP newscaster style,
temperature 0.5.

All Gemini API calls are mocked — no real network.
"""
from __future__ import annotations

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


def _mk_script() -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title="test",
            emotion_type="angry",
            duration=10.0,
            source_url="",
            source_type="political_pro",
        ),
        scenes=(
            Scene(id=0, timestamp=0, duration=5.0, type="title",
                  text="hook", voice_text="hook line", emphasis=True, highlight_words=()),
            Scene(id=1, timestamp=5.0, duration=5.0, type="body",
                  text="body", voice_text="body line", emphasis=False, highlight_words=()),
        ),
        audio=AudioConfig(tts_script="hook line body line"),
        background=BackgroundConfig(type="gradient", colors=()),
    )


def _mock_genai_response(pcm_bytes: bytes = b"\x00\x01" * 48000):
    mock_part = MagicMock()
    mock_part.inline_data.data = pcm_bytes
    mock_content = MagicMock()
    mock_content.parts = [mock_part]
    mock_candidate = MagicMock()
    mock_candidate.content = mock_content
    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    return mock_response


def test_call_gemini_tts_threads_charon_voice_and_temperature():
    from src.tts.gemini_tts_generator import _call_gemini_tts

    with patch("src.tts.gemini_tts_generator.genai.Client") as mock_client_cls:
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response()
        mock_client_cls.return_value = client

        _call_gemini_tts(
            text="hello",
            voice_name="Charon",
            api_key="fake",
            style_prompt="Read in a British RP newscaster voice at a rapid pace:",
            temperature=0.5,
        )

        assert client.models.generate_content.called
        call_kwargs = client.models.generate_content.call_args.kwargs
        # text prefix carries style_prompt
        contents = call_kwargs["contents"]
        assert "British RP newscaster" in contents
        assert "hello" in contents
        # GenerateContentConfig should carry temperature
        cfg = call_kwargs["config"]
        # Two possible introspection paths — attribute or dict
        temp_seen = getattr(cfg, "temperature", None)
        assert temp_seen == 0.5, f"temperature not threaded: {temp_seen}"


def test_call_gemini_tts_omits_prefix_when_style_prompt_none():
    from src.tts.gemini_tts_generator import _call_gemini_tts

    with patch("src.tts.gemini_tts_generator.genai.Client") as mock_client_cls:
        client = MagicMock()
        client.models.generate_content.return_value = _mock_genai_response()
        mock_client_cls.return_value = client

        _call_gemini_tts(
            text="naked-text",
            voice_name="Leda",
            api_key="fake",
            style_prompt=None,
            temperature=None,
        )

        contents = client.models.generate_content.call_args.kwargs["contents"]
        # exact equality — no prefix
        assert contents == "naked-text"


def test_generate_voice_with_timing_gemini_threads_charon_args(tmp_path: Path, monkeypatch):
    """End-to-end on the public generator: ensure parameters flow through."""
    import src.tts.gemini_tts_generator as mod

    captured: dict = {}

    def fake_call(text, voice_name, api_key, *, style_prompt=None, temperature=None):
        captured["text"] = text
        captured["voice_name"] = voice_name
        captured["style_prompt"] = style_prompt
        captured["temperature"] = temperature
        # 1 second of mono PCM at 24kHz, 16-bit = 48_000 bytes
        return b"\x00\x01" * 24_000

    monkeypatch.setattr(mod, "_call_gemini_tts", fake_call)
    monkeypatch.setattr(mod, "_pcm_to_mp3", lambda pcm, path: path.write_bytes(b"FAKE_MP3"))

    script = _mk_script()
    audio_path, timings = mod.generate_voice_with_timing_gemini(
        script,
        output_dir=tmp_path,
        voice_name="Charon",
        api_key="fake",
        style_prompt="Read in a British RP newscaster voice at a rapid pace:",
        temperature=0.5,
        include_outro=False,
    )

    assert captured["voice_name"] == "Charon"
    assert captured["temperature"] == 0.5
    assert captured["style_prompt"] == "Read in a British RP newscaster voice at a rapid pace:"
    assert audio_path.exists()
    assert len(timings) >= 1
