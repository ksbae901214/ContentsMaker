"""ShortsScript data models for video generation pipeline.

Defines the schema for script.json — the bridge between Analyzer and Video modules.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Literal


EmotionType = Literal["funny", "touching", "angry", "relatable"]
SceneType = Literal["title", "body", "comment"]
Emphasis = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Scene:
    """A single scene in the shorts video."""
    id: int
    timestamp: float
    duration: float
    type: str  # SceneType
    text: str
    voice_text: str
    emphasis: str = "medium"  # Emphasis

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Scene:
        return cls(
            id=data["id"],
            timestamp=float(data["timestamp"]),
            duration=float(data["duration"]),
            type=data["type"],
            text=data["text"],
            voice_text=data.get("voice_text", data.get("voiceText", data["text"])),
            emphasis=data.get("emphasis", "medium"),
        )


@dataclass(frozen=True)
class Metadata:
    """Script metadata."""
    title: str
    emotion_type: str  # EmotionType
    duration: float
    source_url: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "emotion_type": self.emotion_type,
            "duration": self.duration,
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Metadata:
        return cls(
            title=data["title"],
            emotion_type=data.get("emotion_type", data.get("emotionType", "relatable")),
            duration=float(data.get("duration", 45)),
            source_url=data.get("source_url", data.get("sourceUrl", "")),
        )


@dataclass(frozen=True)
class AudioConfig:
    """TTS audio configuration."""
    tts_script: str
    voice: str = "ko-KR-SunHiNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"

    def to_dict(self) -> dict:
        return {
            "tts_script": self.tts_script,
            "voice": self.voice,
            "rate": self.rate,
            "pitch": self.pitch,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AudioConfig:
        return cls(
            tts_script=data.get("tts_script", data.get("ttsScript", "")),
            voice=data.get("voice", "ko-KR-SunHiNeural"),
            rate=data.get("rate", "+0%"),
            pitch=data.get("pitch", "+0Hz"),
        )


@dataclass(frozen=True)
class BackgroundConfig:
    """Video background configuration."""
    type: str = "gradient"
    colors: tuple[str, ...] = ("#4169E1", "#1E90FF", "#87CEEB")

    def to_dict(self) -> dict:
        return {"type": self.type, "colors": list(self.colors)}

    @classmethod
    def from_dict(cls, data: dict) -> BackgroundConfig:
        return cls(
            type=data.get("type", "gradient"),
            colors=tuple(data.get("colors", ["#4169E1", "#1E90FF", "#87CEEB"])),
        )


@dataclass(frozen=True)
class ShortsScript:
    """Complete script for shorts video generation."""
    metadata: Metadata
    scenes: tuple[Scene, ...]
    audio: AudioConfig
    background: BackgroundConfig = field(default_factory=lambda: BackgroundConfig())

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "scenes": [s.to_dict() for s in self.scenes],
            "audio": self.audio.to_dict(),
            "background": self.background.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> ShortsScript:
        return cls(
            metadata=Metadata.from_dict(data["metadata"]),
            scenes=tuple(Scene.from_dict(s) for s in data.get("scenes", [])),
            audio=AudioConfig.from_dict(data.get("audio", {})),
            background=BackgroundConfig.from_dict(data.get("background", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ShortsScript:
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load(cls, file_path) -> ShortsScript:
        from pathlib import Path
        text = Path(file_path).read_text(encoding="utf-8")
        return cls.from_json(text)

    def save(self, file_path) -> None:
        from pathlib import Path
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
