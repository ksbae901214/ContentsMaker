"""Tests for PoliticalInput model."""
import json
import pytest
from pathlib import Path

from src.scraper.political_input import (
    PoliticalInput,
    PoliticalInputError,
    save_political,
)


class TestCreatePoliticalInput:
    def test_valid_creation(self):
        pi = PoliticalInput(youtube_url="https://youtube.com/watch?v=abc123")
        assert pi.youtube_url == "https://youtube.com/watch?v=abc123"
        assert pi.clip_start == 0.0
        assert pi.clip_end == 0.0
        assert pi.created_at  # auto-set

    def test_with_clip_range(self):
        pi = PoliticalInput(
            youtube_url="https://youtu.be/abc123",
            clip_start=30.0,
            clip_end=90.0,
            tone="날카롭게",
            details="의원의 발언에 집중",
        )
        assert pi.clip_start == 30.0
        assert pi.clip_end == 90.0
        assert pi.tone == "날카롭게"

    def test_frozen(self):
        pi = PoliticalInput(youtube_url="https://youtube.com/watch?v=abc")
        with pytest.raises(AttributeError):
            pi.tone = "changed"


class TestValidation:
    def test_invalid_url(self):
        with pytest.raises(PoliticalInputError, match="YouTube URL"):
            PoliticalInput(youtube_url="https://example.com/not-youtube")

    def test_clip_end_before_start(self):
        with pytest.raises(PoliticalInputError, match="clip_end"):
            PoliticalInput(
                youtube_url="https://youtube.com/watch?v=abc",
                clip_start=60,
                clip_end=30,
            )

    def test_clip_too_long(self):
        with pytest.raises(PoliticalInputError, match="120초"):
            PoliticalInput(
                youtube_url="https://youtube.com/watch?v=abc",
                clip_start=0,
                clip_end=150,
            )

    def test_youtube_shorts_url(self):
        pi = PoliticalInput(youtube_url="https://youtube.com/shorts/abc123")
        assert pi.youtube_url.endswith("abc123")

    def test_youtube_live_url(self):
        pi = PoliticalInput(youtube_url="https://youtube.com/live/abc123")
        assert pi.youtube_url.endswith("abc123")


class TestSerialization:
    def test_roundtrip(self):
        pi = PoliticalInput(
            youtube_url="https://youtube.com/watch?v=abc",
            clip_start=10,
            clip_end=50,
            tone="객관적",
        )
        d = pi.to_dict()
        pi2 = PoliticalInput.from_dict(d)
        assert pi2.youtube_url == pi.youtube_url
        assert pi2.clip_start == pi.clip_start
        assert pi2.clip_end == pi.clip_end
        assert pi2.tone == pi.tone

    def test_to_json(self):
        pi = PoliticalInput(youtube_url="https://youtube.com/watch?v=abc")
        parsed = json.loads(pi.to_json())
        assert parsed["youtube_url"] == pi.youtube_url
        assert "created_at" in parsed


class TestSavePolitical:
    def test_save(self, tmp_path):
        pi = PoliticalInput(youtube_url="https://youtube.com/watch?v=test")
        path = save_political(pi, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".json"
        data = json.loads(path.read_text())
        assert data["youtube_url"] == pi.youtube_url
