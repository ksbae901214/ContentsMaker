"""T046: pyannote.audio 화자 분리 (FR-013).

Research: research.md R-03 (pyannote.audio 3.1 free w/ HuggingFace token).

출력 JSON 포맷:
  {
    "video_id": "abc",
    "speakers": [
      {"start": 0.0, "end": 3.2, "speaker_cluster": "SPEAKER_00"},
      ...
    ]
  }
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.dem_shorts.config import DIARIZATION_MODEL, HUGGINGFACE_TOKEN
from src.dem_shorts.utils.paths import segments_path

logger = logging.getLogger(__name__)


class DiarizationError(Exception):
    """화자 분리 실패."""


@dataclass(frozen=True)
class DiarizationTurn:
    start_sec: float
    end_sec: float
    speaker_cluster: str  # e.g., "SPEAKER_00"

    def to_dict(self) -> dict:
        return {
            "start": self.start_sec,
            "end": self.end_sec,
            "speaker_cluster": self.speaker_cluster,
        }


def diarize_video(
    audio_or_video_path: Path,
    *,
    video_id: str,
    model_name: str = DIARIZATION_MODEL,
) -> Path:
    """영상/오디오에 대해 화자 분리 수행 후 JSON 저장.

    Returns: segments/{video_id}.json 경로.

    Raises: DiarizationError
    """
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise DiarizationError(
            "pyannote.audio not installed. "
            "Run: pip install -r requirements-dem-shorts.txt"
        ) from exc

    if not HUGGINGFACE_TOKEN:
        raise DiarizationError(
            "HUGGINGFACE_TOKEN not configured; required for pyannote model download"
        )
    if not audio_or_video_path.exists():
        raise DiarizationError(f"input not found: {audio_or_video_path}")

    logger.info("Diarization 시작: %s", audio_or_video_path.name)
    pipeline = Pipeline.from_pretrained(model_name, token=HUGGINGFACE_TOKEN)
    result = pipeline(str(audio_or_video_path))

    annotation = getattr(result, "speaker_diarization", result)

    turns: list[DiarizationTurn] = []
    for segment, _, speaker in annotation.itertracks(yield_label=True):
        turns.append(
            DiarizationTurn(
                start_sec=float(segment.start),
                end_sec=float(segment.end),
                speaker_cluster=str(speaker),
            )
        )

    out_path = segments_path(video_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video_id": video_id,
        "model": model_name,
        "speakers": [t.to_dict() for t in turns],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Diarization 완료: %s (turns=%d)", out_path, len(turns))
    return out_path


def load_diarization(video_id: str) -> list[DiarizationTurn]:
    """저장된 diarization JSON 로드."""
    path = segments_path(video_id)
    if not path.exists():
        raise DiarizationError(f"diarization not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        DiarizationTurn(
            start_sec=float(t["start"]),
            end_sec=float(t["end"]),
            speaker_cluster=str(t["speaker_cluster"]),
        )
        for t in data.get("speakers", [])
    ]
