"""T045: Whisper 로컬 STT 래퍼 (FR-012).

Research: research.md R-02 (openai-whisper large-v3, $0 로컬).

heavy lifting은 openai-whisper 라이브러리에 위임. 본 모듈은:
- 입력 오디오 파일 경로 → transcripts JSON 출력
- 모델 lazy-load
- 한국어 강제
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.dem_shorts.config import WHISPER_MODEL
from src.dem_shorts.utils.paths import transcript_path

logger = logging.getLogger(__name__)


class STTError(Exception):
    """STT 처리 실패."""


@dataclass(frozen=True)
class TranscriptSegment:
    start_sec: float
    end_sec: float
    text: str

    def to_dict(self) -> dict:
        return {"start": self.start_sec, "end": self.end_sec, "text": self.text}


def transcribe_video(
    video_path: Path,
    *,
    video_id: str,
    model_name: str = WHISPER_MODEL,
    language: str = "ko",
    device: str | None = None,
) -> Path:
    """Whisper 로 영상의 오디오를 전사하고 JSON 파일 저장.

    Returns:
        저장된 transcript JSON 경로.

    Raises:
        STTError
    """
    try:
        import whisper  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise STTError(
            "openai-whisper not installed. "
            "Run: pip install -r requirements-dem-shorts.txt"
        ) from exc

    if not video_path.exists():
        raise STTError(f"video file not found: {video_path}")

    logger.info("Whisper STT 시작: %s (model=%s)", video_path.name, model_name)
    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(str(video_path), language=language, verbose=False)

    segments = [
        TranscriptSegment(
            start_sec=float(s["start"]),
            end_sec=float(s["end"]),
            text=s["text"].strip(),
        )
        for s in result.get("segments", [])
    ]

    out_path = transcript_path(video_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video_id": video_id,
        "language": language,
        "model": model_name,
        "segments": [s.to_dict() for s in segments],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Whisper STT 완료: %s (segments=%d)", out_path, len(segments))
    return out_path


def load_transcript(video_id: str) -> list[TranscriptSegment]:
    """저장된 transcript JSON을 로드."""
    path = transcript_path(video_id)
    if not path.exists():
        raise STTError(f"transcript not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        TranscriptSegment(
            start_sec=float(s["start"]),
            end_sec=float(s["end"]),
            text=s["text"],
        )
        for s in data.get("segments", [])
    ]
