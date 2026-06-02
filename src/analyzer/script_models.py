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
    # QW-02: 강조 키워드 색 카테고리 — fact(노랑)/criticism(빨강)/neutral(emotion 색).
    # 기본 "neutral" — 기존 emotion 기반 동작 유지.
    highlight_category: str = "neutral"
    # Phase 9 추가 (2026-04-21): 씬별 이미지 검색어. 유명인 모드에서 "서울대를 졸업했습니다"
    # 씬의 image_query="서울대학교 정문" 식으로 내용에 맞는 이미지를 네이버에서 검색.
    # None이면 상위 로직이 인물명 등 기본값으로 폴백.
    image_query: str | None = None
    # Phase 9 YouTube 소스 (2026-05-28): 씬별 YouTube 검색어.
    # 설정 시 YouTube에서 실제 영상을 검색해 씬 배경에 사용.
    # None이면 image_query+name 또는 name으로 폴백.
    clip_query: str | None = None
    # Feature 011 V2 Phase B (2026-05-14): 정치 모드 자막 색·시각 연출.
    # subtitle_color: white(기본)/red(비판·충돌)/yellow(강조)/blue(인용)
    # subtitle_emphasis: True면 폰트 1.4x + 굵게
    # visual_layout: "normal"(기본) | "split"(좌·우 분할 화면)
    # secondary_clip_path: split 레이아웃 시 우측에 보일 보조 클립 경로
    subtitle_color: str = "white"
    subtitle_emphasis: bool = False
    visual_layout: str = "normal"
    secondary_clip_path: str | None = None
    # Phase 3 (2026-05-20): 분할 자식 씬 연속성. 같은 원본 텍스트가 _split_subtitle_segments로
    # N개 자식 씬으로 나뉘면 모두 같은 group_id. group_first=True인 첫 자식만 fade-in 실행,
    # 나머지는 텍스트만 교체(끊김 없음). None = 그룹 없음(독립 씬, 항상 fade-in).
    subtitle_group_id: int | None = None
    subtitle_group_first: bool = True

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
        if self.highlight_category and self.highlight_category != "neutral":
            d["highlight_category"] = self.highlight_category
        if self.image_query:  # None·빈 문자열은 키 생략
            d["image_query"] = self.image_query
        if self.clip_query:  # None·빈 문자열은 키 생략
            d["clip_query"] = self.clip_query
        # Feature 011 V2 Phase B — default가 아닐 때만 직렬화 (V1 호환)
        if self.subtitle_color != "white":
            d["subtitle_color"] = self.subtitle_color
        if self.subtitle_emphasis:
            d["subtitle_emphasis"] = True
        if self.visual_layout != "normal":
            d["visual_layout"] = self.visual_layout
        if self.secondary_clip_path:
            d["secondary_clip_path"] = self.secondary_clip_path
        # Phase 3 — default가 아닐 때만 직렬화 (V1·V2 JSON 호환)
        if self.subtitle_group_id is not None:
            d["subtitle_group_id"] = self.subtitle_group_id
        if not self.subtitle_group_first:  # default True → False만 직렬화
            d["subtitle_group_first"] = False
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
            highlight_category=str(
                data.get("highlight_category", data.get("highlightCategory", "neutral"))
            ),
            image_query=data.get("image_query", data.get("imageQuery")) or None,
            clip_query=data.get("clip_query", data.get("clipQuery")) or None,
            # Feature 011 V2 Phase B — default fallback으로 V1 JSON 호환
            subtitle_color=str(
                data.get("subtitle_color", data.get("subtitleColor", "white"))
            ),
            subtitle_emphasis=bool(
                data.get("subtitle_emphasis", data.get("subtitleEmphasis", False))
            ),
            visual_layout=str(
                data.get("visual_layout", data.get("visualLayout", "normal"))
            ),
            secondary_clip_path=(
                data.get("secondary_clip_path", data.get("secondaryClipPath")) or None
            ),
            # Phase 3 — default fallback (없으면 None / True)
            subtitle_group_id=data.get("subtitle_group_id", data.get("subtitleGroupId")),
            subtitle_group_first=bool(
                data.get("subtitle_group_first", data.get("subtitleGroupFirst", True))
            ),
        )


SourceType = Literal["blind", "topic", "political", "political_pro", "celebrity"]


@dataclass(frozen=True)
class Metadata:
    """Script metadata."""
    title: str
    emotion_type: str  # EmotionType
    duration: float
    source_url: str = ""
    source_type: str = "blind"  # SourceType
    # Feature 009 political_pro: 출처 표시용 (화면 하단 "출처: {channel} : {title}")
    source_channel: str = ""
    source_title: str = ""
    # 명시적 출처 라벨 — 설정되면 source_channel/title보다 우선해 그대로 하단에 표시.
    # 복수 출처 (예: "MBC뉴스, 헤럴드경제, 뉴스핌, 세계일보") 처리에 사용.
    source_label: str = ""
    # Feature 011 V2 political_pro 업그레이드 — gemini-code 지침
    # Phase A에서는 추적·디버깅 메타로만 보존, Phase B에서 렌더 분기에 활용 예정.
    format_type: str = ""           # "A"=인터뷰/논평/MBC라디오, "B"=현장/뉴스핌, ""=N/A
    format_reason: str = ""
    visual_directives: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d = {
            "title": self.title,
            "emotion_type": self.emotion_type,
            "duration": self.duration,
            "source_url": self.source_url,
            "source_type": self.source_type,
        }
        if self.source_channel:
            d["source_channel"] = self.source_channel
        if self.source_title:
            d["source_title"] = self.source_title
        if self.source_label:
            d["source_label"] = self.source_label
        # V2 부가 필드 (default가 아닐 때만 직렬화 → V1 JSON 호환)
        if self.format_type:
            d["format_type"] = self.format_type
        if self.format_reason:
            d["format_reason"] = self.format_reason
        if self.visual_directives:
            d["visual_directives"] = list(self.visual_directives)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Metadata:
        vd_raw = data.get("visual_directives", data.get("visualDirectives", ()))
        return cls(
            title=data["title"],
            emotion_type=data.get("emotion_type", data.get("emotionType", "relatable")),
            duration=float(data.get("duration", 45)),
            source_url=data.get("source_url", data.get("sourceUrl", "")),
            source_type=data.get("source_type", data.get("sourceType", "blind")),
            source_channel=data.get("source_channel", data.get("sourceChannel", "")),
            source_title=data.get("source_title", data.get("sourceTitle", "")),
            source_label=data.get("source_label", data.get("sourceLabel", "")),
            format_type=str(data.get("format_type", data.get("formatType", ""))),
            format_reason=str(data.get("format_reason", data.get("formatReason", ""))),
            visual_directives=tuple(vd_raw) if vd_raw else (),
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
