"""TopicInput model for free-topic video generation.

Frozen dataclass for user-submitted topics (not Blind posts).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))

VALID_STYLES = ("narration", "skit", "review")


class TopicInputError(Exception):
    """Raised when topic input validation fails."""


@dataclass(frozen=True)
class TopicInput:
    """A free-topic input for Shorts video generation."""
    topic: str
    style: str = "narration"
    tone: str = ""
    details: str = ""
    created_at: str = ""

    def __post_init__(self):
        if len(self.topic) < 5:
            raise TopicInputError(
                f"주제는 최소 5자 이상이어야 합니다 (현재 {len(self.topic)}자)"
            )
        if self.style not in VALID_STYLES:
            raise TopicInputError(
                f"유효하지 않은 스타일: '{self.style}'. "
                f"사용 가능: {', '.join(VALID_STYLES)}"
            )
        if not self.created_at:
            object.__setattr__(
                self, "created_at", datetime.now(KST).isoformat()
            )

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "style": self.style,
            "tone": self.tone,
            "details": self.details,
            "created_at": self.created_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> TopicInput:
        return cls(
            topic=data["topic"],
            style=data.get("style", "narration"),
            tone=data.get("tone", ""),
            details=data.get("details", ""),
            created_at=data.get("created_at", ""),
        )


def save_topic(
    topic_input: TopicInput,
    output_dir: Path | None = None,
) -> Path:
    """Save a TopicInput to a JSON file.

    Returns the file path.
    """
    from src.config.settings import DATA_RAW_DIR

    target_dir = output_dir or DATA_RAW_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(
        c for c in topic_input.topic[:30] if c.isalnum() or c in " _-"
    )
    safe_topic = safe_topic.strip().replace(" ", "_") or "topic"
    filename = f"{timestamp}_{safe_topic}.json"
    file_path = target_dir / filename

    file_path.write_text(topic_input.to_json(), encoding="utf-8")
    return file_path
