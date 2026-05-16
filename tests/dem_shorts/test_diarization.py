"""T042: Diarization JSON 스키마 · 세그먼트 병합 테스트."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dem_shorts.diarization import DiarizationTurn, load_diarization


class TestDiarizationTurn:
    def test_to_dict(self):
        t = DiarizationTurn(start_sec=0.0, end_sec=5.2, speaker_cluster="SPEAKER_00")
        assert t.to_dict() == {
            "start": 0.0,
            "end": 5.2,
            "speaker_cluster": "SPEAKER_00",
        }


class TestLoadDiarization:
    def test_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        sdir = tmp_path / "segments"
        sdir.mkdir()
        monkeypatch.setattr(
            "src.dem_shorts.diarization.segments_path", lambda vid: sdir / f"{vid}.json"
        )

        payload = {
            "video_id": "abc",
            "model": "pyannote/speaker-diarization-3.1",
            "speakers": [
                {"start": 0.0, "end": 3.0, "speaker_cluster": "SPEAKER_00"},
                {"start": 3.0, "end": 8.0, "speaker_cluster": "SPEAKER_01"},
            ],
        }
        (sdir / "abc.json").write_text(json.dumps(payload), encoding="utf-8")

        turns = load_diarization("abc")
        assert len(turns) == 2
        assert turns[1].speaker_cluster == "SPEAKER_01"

    def test_missing_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        from src.dem_shorts.diarization import DiarizationError

        sdir = tmp_path / "segments"
        sdir.mkdir()
        monkeypatch.setattr(
            "src.dem_shorts.diarization.segments_path", lambda vid: sdir / f"{vid}.json"
        )

        with pytest.raises(DiarizationError):
            load_diarization("missing")
