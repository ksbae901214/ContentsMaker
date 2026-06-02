"""PoliticalInput model for political commentary video generation.

Frozen dataclass for YouTube-sourced political commentary content.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))

YOUTUBE_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/live/)"
)


class PoliticalInputError(Exception):
    """Raised when political input validation fails."""


@dataclass(frozen=True)
class PoliticalInput:
    """Input for political commentary Shorts generation."""
    youtube_url: str
    clip_start: float = 0.0
    clip_end: float = 0.0      # 0 = auto (first 60s)
    tone: str = ""              # e.g. "날카롭게", "객관적으로"
    details: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not YOUTUBE_PATTERN.search(self.youtube_url):
            raise PoliticalInputError(
                "유효한 YouTube URL이 아닙니다."
            )
        if self.clip_end > 0 and self.clip_end <= self.clip_start:
            raise PoliticalInputError(
                f"clip_end({self.clip_end})는 clip_start({self.clip_start})보다 커야 합니다."
            )
        if self.clip_end > 0 and (self.clip_end - self.clip_start) > 120:
            raise PoliticalInputError(
                "클립 길이는 최대 120초까지 지원됩니다."
            )
        if not self.created_at:
            object.__setattr__(
                self, "created_at", datetime.now(KST).isoformat()
            )

    def to_dict(self) -> dict:
        return {
            "youtube_url": self.youtube_url,
            "clip_start": self.clip_start,
            "clip_end": self.clip_end,
            "tone": self.tone,
            "details": self.details,
            "created_at": self.created_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> PoliticalInput:
        return cls(
            youtube_url=data["youtube_url"],
            clip_start=float(data.get("clip_start", 0)),
            clip_end=float(data.get("clip_end", 0)),
            tone=data.get("tone", ""),
            details=data.get("details", ""),
            created_at=data.get("created_at", ""),
        )


def save_political(
    political_input: PoliticalInput,
    output_dir: Path | None = None,
) -> Path:
    """Save a PoliticalInput to a JSON file. Returns the file path."""
    from src.config.settings import DATA_RAW_DIR

    target_dir = output_dir or DATA_RAW_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_political.json"
    file_path = target_dir / filename

    file_path.write_text(political_input.to_json(), encoding="utf-8")
    return file_path
