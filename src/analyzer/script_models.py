"""ShortsScript data models for video generation pipeline.

Defines the schema for script.json — the bridge between Analyzer and Video modules.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Literal


EmotionType = Literal["funny", "touching", "angry", "relatable"]
SceneType = Literal["title", "body", "comment", "clip", "commentary"]
Emphasis = Literal["high", "medium", "low"]
VisualType = Literal["image", "video", "none"]
TransitionType = Literal[
    "fade", "slide-left", "slide-up", "zoom", "dissolve", "wipe", "punch-zoom",
]


@dataclass(frozen=True)
class SubtitleStyle:
    """Customizable subtitle appearance for a scene."""
    font_family: str = "Noto Sans KR"
    font_size: int = 55
    font_weight: str = "bold"
    color: str = "#FFFFFF"
    shadow: str = "3px 3px 8px rgba(0,0,0,0.7)"
    position_y: float = 0.6
    bg_color: str | None = None
    bg_opacity: float = 0.0

    def to_dict(self) -> dict:
        return {
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "color": self.color,
            "shadow": self.shadow,
            "position_y": self.position_y,
            "bg_color": self.bg_color,
            "bg_opacity": self.bg_opacity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SubtitleStyle:
        return cls(
            font_family=data.get("font_family", "Noto Sans KR"),
            font_size=int(data.get("font_size", 55)),
            font_weight=data.get("font_weight", "bold"),
            color=data.get("color", "#FFFFFF"),
            shadow=data.get("shadow", "3px 3px 8px rgba(0,0,0,0.7)"),
            position_y=float(data.get("position_y", 0.6)),
            bg_color=data.get("bg_color"),
            bg_opacity=float(data.get("bg_opacity", 0.0)),
        )


@dataclass(frozen=True)
class TransitionConfig:
    """Scene transition effect configuration."""
    type: str = "fade"  # TransitionType
    duration: float = 0.5

    def to_dict(self) -> dict:
        return {"type": self.type, "duration": self.duration}

    @classmethod
    def from_dict(cls, data: dict) -> TransitionConfig:
        return cls(
            type=data.get("type", "fade"),
            duration=max(0.3, min(1.0, float(data.get("duration", 0.5)))),
        )


@dataclass(frozen=True)
class SfxConfig:
    """Sound effect configuration for a scene."""
    name: str
    category: str  # surprise, laugh, touching, emphasis
    offset_ms: int = 0
    volume: float = 0.2

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "offset_ms": self.offset_ms,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SfxConfig:
        return cls(
            name=data["name"],
            category=data.get("category", "emphasis"),
            offset_ms=int(data.get("offset_ms", 0)),
            volume=max(0.0, min(1.0, float(data.get("volume", 0.2)))),
        )


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
    highlight_words: tuple[str, ...] = ()
    visual_type: str = "image"  # VisualType
    motion_prompt: str | None = None
    subtitle_style: SubtitleStyle | None = None
    transition: TransitionConfig | None = None
    sfx: tuple[SfxConfig, ...] = ()
    clip_start: float | None = None   # seconds into source clip (political mode)
    clip_end: float | None = None     # seconds into source clip (political mode)
    # QW-01: 첫 1.5~2.5초 후킹 씬 표시. True면 렌더 단계에서 1.4x 폰트 +
    # 중앙 정렬 + 펀치 줌 적용. 기본 False (호환).
    hook: bool = False

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "timestamp": self.timestamp,
            "duration": self.duration,
            "type": self.type,
            "text": self.text,
            "voice_text": self.voice_text,
            "emphasis": self.emphasis,
            "highlight_words": list(self.highlight_words),
        }
        if self.visual_type != "image":
            d["visual_type"] = self.visual_type
        if self.motion_prompt is not None:
            d["motion_prompt"] = self.motion_prompt
        if self.subtitle_style is not None:
            d["subtitle_style"] = self.subtitle_style.to_dict()
        if self.transition is not None:
            d["transition"] = self.transition.to_dict()
        if self.sfx:
            d["sfx"] = [s.to_dict() for s in self.sfx]
        if self.clip_start is not None:
            d["clip_start"] = self.clip_start
        if self.clip_end is not None:
            d["clip_end"] = self.clip_end
        if self.hook:  # 호환: False는 키 생략
            d["hook"] = True
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Scene:
        raw_hw = data.get("highlight_words", data.get("highlightWords", []))
        sub_style = (
            SubtitleStyle.from_dict(data["subtitle_style"])
            if data.get("subtitle_style")
            else None
        )
        transition = (
            TransitionConfig.from_dict(data["transition"])
            if data.get("transition")
            else None
        )
        raw_sfx = data.get("sfx", [])
        return cls(
            id=data["id"],
            timestamp=float(data["timestamp"]),
            duration=float(data["duration"]),
            type=data["type"],
            text=data["text"],
            voice_text=data.get("voice_text", data.get("voiceText", data["text"])),
            emphasis=data.get("emphasis", "medium"),
            highlight_words=tuple(raw_hw) if raw_hw else (),
            visual_type=data.get("visual_type", "image"),
            motion_prompt=data.get("motion_prompt"),
            subtitle_style=sub_style,
            transition=transition,
            sfx=tuple(SfxConfig.from_dict(s) for s in raw_sfx),
            clip_start=data.get("clip_start"),
            clip_end=data.get("clip_end"),
            hook=bool(data.get("hook", False)),
        )


SourceType = Literal["blind", "topic", "political"]


@dataclass(frozen=True)
class Metadata:
    """Script metadata."""
    title: str
    emotion_type: str  # EmotionType
    duration: float
    source_url: str = ""
    source_type: str = "blind"  # SourceType

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "emotion_type": self.emotion_type,
            "duration": self.duration,
            "source_url": self.source_url,
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Metadata:
        return cls(
            title=data["title"],
            emotion_type=data.get("emotion_type", data.get("emotionType", "relatable")),
            duration=float(data.get("duration", 45)),
            source_url=data.get("source_url", data.get("sourceUrl", "")),
            source_type=data.get("source_type", data.get("sourceType", "blind")),
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
