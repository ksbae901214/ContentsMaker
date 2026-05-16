"""T041: Whisper STT 래퍼 구조 · JSON 스키마 검증 (의존성은 mocking)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dem_shorts.stt import TranscriptSegment, load_transcript


class TestTranscriptSegment:
    def test_to_dict(self):
        s = TranscriptSegment(start_sec=0.0, end_sec=3.2, text="안녕하세요")
        assert s.to_dict() == {"start": 0.0, "end": 3.2, "text": "안녕하세요"}


class TestLoadTranscript:
    def test_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Redirect transcripts dir to tmp
        tdir = tmp_path / "transcripts"
        tdir.mkdir()
        monkeypatch.setattr("src.dem_shorts.stt.transcript_path", lambda vid: tdir / f"{vid}.json")

        payload = {
            "video_id": "abc",
            "language": "ko",
            "model": "large-v3",
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "첫 문장"},
                {"start": 3.0, "end": 6.5, "text": "두 번째 문장"},
            ],
        }
        (tdir / "abc.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        segments = load_transcript("abc")
        assert len(segments) == 2
        assert segments[0].text == "첫 문장"
        assert segments[1].end_sec == 6.5

    def test_missing_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        from src.dem_shorts.stt import STTError

        tdir = tmp_path / "transcripts"
        tdir.mkdir()
        monkeypatch.setattr("src.dem_shorts.stt.transcript_path", lambda vid: tdir / f"{vid}.json")

        with pytest.raises(STTError):
            load_transcript("missing")
