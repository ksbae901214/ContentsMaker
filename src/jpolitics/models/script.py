"""T016 [US1]: JpoliticsScript / JpoliticsScene / Audio / Background / Metadata.

격리 모드 V3 데이터 모델. 기존 V1/V2 `src/analyzer/script_models.py`와 독립.

Lock-in (사용자 명시):
- AudioConfig: voice/rate/gap/sfx/bgm 모두 Literal 고정
- Scene: transition_effect="none", sfx_trigger=None (FR-034/035)
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final, Literal

from src.jpolitics.models.politician_card import PoliticianCard

# Lock-in 락인 값 (변경 불가, 모듈 외부 import 권장 안 함)
LOCKIN_TTS_VOICE: Final[str] = "ko-KR-InJoonNeural"
LOCKIN_TTS_RATE: Final[str] = "+22%"
LOCKIN_INTER_SCENE_GAP_MS: Final[int] = 300
LOCKIN_SFX_ENABLED: Final[bool] = False
LOCKIN_BGM_ENABLED: Final[bool] = False

VisualLayout = Literal["normal", "vs_card", "grid_2x2", "data_card"]
SubtitleColor = Literal["white", "yellow", "red", "blue"]
DataEmphasisColor = Literal["red", "yellow", "blue"]
SceneType = Literal["title", "body", "comment"]
SourceType = Literal["jpolitics_youtube", "jpolitics_topic"]


# ─────────────────────────── JpoliticsMetadata ───────────────────────────


@dataclass(frozen=True)
class JpoliticsMetadata:
    """E1.metadata — 영상 메타데이터."""

    title: str
    source_type: SourceType
    duration_sec: float
    created_at: str  # ISO8601
    source_url: str | None = None
    source_label: str | None = None
    topic: str | None = None

    def validate(self) -> None:
        if not 30.0 <= self.duration_sec <= 60.0:
            raise ValueError(
                f"metadata.duration_sec must be 30~60 (got {self.duration_sec})"
            )
        if not 1 <= len(self.title) <= 100:
            raise ValueError(f"metadata.title length must be 1~100 (got {len(self.title)})")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "title": self.title,
            "source_type": self.source_type,
            "duration_sec": self.duration_sec,
            "created_at": self.created_at,
        }
        if self.source_url is not None:
            d["source_url"] = self.source_url
        if self.source_label is not None:
            d["source_label"] = self.source_label
        if self.topic is not None:
            d["topic"] = self.topic
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsMetadata":
        return cls(
            title=str(data["title"]),
            source_type=data.get("source_type") or data.get("sourceType"),  # type: ignore[arg-type]
            duration_sec=float(data.get("duration_sec") or data.get("durationSec")),  # type: ignore[arg-type]
            created_at=str(data.get("created_at") or data.get("createdAt")),
            source_url=data.get("source_url") or data.get("sourceUrl"),
            source_label=data.get("source_label") or data.get("sourceLabel"),
            topic=data.get("topic"),
        )


# ─────────────────────────── JpoliticsAudioConfig ───────────────────────────


@dataclass(frozen=True)
class JpoliticsAudioConfig:
    """E1.audio — TTS 락인 (변경 불가)."""

    tts_script: str
    tts_voice: Literal["ko-KR-InJoonNeural"] = "ko-KR-InJoonNeural"
    tts_rate: Literal["+22%"] = "+22%"
    inter_scene_gap_ms: Literal[300] = 300
    sfx_enabled: Literal[False] = False
    bgm_enabled: Literal[False] = False
    audio_path: str | None = None  # public/audio.mp3 상대경로

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tts_script": self.tts_script,
            "tts_voice": self.tts_voice,
            "tts_rate": self.tts_rate,
            "inter_scene_gap_ms": self.inter_scene_gap_ms,
            "sfx_enabled": self.sfx_enabled,
            "bgm_enabled": self.bgm_enabled,
        }
        if self.audio_path is not None:
            d["audio_path"] = self.audio_path
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsAudioConfig":
        return cls(
            tts_script=str(data.get("tts_script") or data.get("ttsScript") or ""),
            audio_path=data.get("audio_path") or data.get("audioPath"),
        )


# ─────────────────────────── JpoliticsBackgroundConfig ───────────────────────────


@dataclass(frozen=True)
class JpoliticsBackgroundConfig:
    """E1.background — 그라데이션 배경."""

    type: Literal["gradient"] = "gradient"
    colors: tuple[str, str] = ("#1a1a2e", "#16213e")

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "colors": list(self.colors)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsBackgroundConfig":
        colors = data.get("colors") or ["#1a1a2e", "#16213e"]
        return cls(
            type=data.get("type", "gradient"),
            colors=(str(colors[0]), str(colors[1])),
        )


# ─────────────────────────── JpoliticsScene ───────────────────────────


@dataclass(frozen=True)
class JpoliticsScene:
    """E2 — 단일 씬."""

    id: int
    timestamp: float
    duration: float
    type: SceneType
    text: str
    voice_text: str
    visual_layout: VisualLayout = "normal"
    subtitle_color: SubtitleColor = "white"
    subtitle_emphasis: bool = False
    headline_pin: str | None = None  # 씬 0에만 설정 (FR-011)
    comparison_cards: tuple[PoliticianCard, ...] | None = None
    data_emphasis_color: DataEmphasisColor = "red"
    clip_path: str | None = None
    clip_search_query: str | None = None  # FR-037
    clip_source_timestamp: tuple[float, float] | None = None  # FR-037
    transition_effect: Literal["none"] = "none"  # FR-035
    sfx_trigger: Literal[None] = None  # FR-034

    def validate(self) -> None:
        if self.duration > 5.0:
            raise ValueError(
                f"scene.duration must be ≤ 5.0 (got {self.duration})"
            )
        if self.duration < 0.5:
            raise ValueError(
                f"scene.duration must be ≥ 0.5 (got {self.duration})"
            )
        if not 1 <= len(self.text) <= 200:
            raise ValueError(f"scene.text length must be 1~200 (got {len(self.text)})")
        # vs_card → 카드 2개 / grid_2x2 → 3~4개 / data_card → 1개
        if self.visual_layout == "vs_card":
            if not self.comparison_cards or len(self.comparison_cards) != 2:
                raise ValueError("vs_card requires exactly 2 comparison_cards")
        elif self.visual_layout == "grid_2x2":
            if not self.comparison_cards or not 3 <= len(self.comparison_cards) <= 4:
                raise ValueError("grid_2x2 requires 3~4 comparison_cards")
        elif self.visual_layout == "data_card":
            if not self.comparison_cards or len(self.comparison_cards) != 1:
                raise ValueError("data_card requires exactly 1 comparison_card")
            card = self.comparison_cards[0]
            if not card.data_value:
                raise ValueError("data_card requires data_value")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "timestamp": self.timestamp,
            "duration": self.duration,
            "type": self.type,
            "text": self.text,
            "voice_text": self.voice_text,
            "visual_layout": self.visual_layout,
            "subtitle_color": self.subtitle_color,
            "subtitle_emphasis": self.subtitle_emphasis,
            "data_emphasis_color": self.data_emphasis_color,
            "transition_effect": self.transition_effect,
            "sfx_trigger": self.sfx_trigger,
        }
        if self.headline_pin is not None:
            d["headline_pin"] = self.headline_pin
        if self.comparison_cards is not None:
            d["comparison_cards"] = [c.to_dict() for c in self.comparison_cards]
        if self.clip_path is not None:
            d["clip_path"] = self.clip_path
        if self.clip_search_query is not None:
            d["clip_search_query"] = self.clip_search_query
        if self.clip_source_timestamp is not None:
            d["clip_source_timestamp"] = list(self.clip_source_timestamp)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsScene":
        # camelCase 호환
        def g(snake: str, camel: str | None = None, default: Any = None) -> Any:
            return data.get(snake, data.get(camel, default) if camel else default)

        cards_raw = g("comparison_cards", "comparisonCards")
        cards: tuple[PoliticianCard, ...] | None = (
            tuple(PoliticianCard.from_dict(c) for c in cards_raw)
            if cards_raw
            else None
        )
        ts_raw = g("clip_source_timestamp", "clipSourceTimestamp")
        ts: tuple[float, float] | None = (
            (float(ts_raw[0]), float(ts_raw[1])) if ts_raw else None
        )
        return cls(
            id=int(data["id"]),
            timestamp=float(data["timestamp"]),
            duration=float(data["duration"]),
            type=str(data["type"]),  # type: ignore[arg-type]
            text=str(data["text"]),
            voice_text=str(g("voice_text", "voiceText", "")),
            visual_layout=str(g("visual_layout", "visualLayout", "normal")),  # type: ignore[arg-type]
            subtitle_color=str(g("subtitle_color", "subtitleColor", "white")),  # type: ignore[arg-type]
            subtitle_emphasis=bool(g("subtitle_emphasis", "subtitleEmphasis", False)),
            headline_pin=g("headline_pin", "headlinePin"),
            comparison_cards=cards,
            data_emphasis_color=str(g("data_emphasis_color", "dataEmphasisColor", "red")),  # type: ignore[arg-type]
            clip_path=g("clip_path", "clipPath"),
            clip_search_query=g("clip_search_query", "clipSearchQuery"),
            clip_source_timestamp=ts,
        )


# ─────────────────────────── JpoliticsScript ───────────────────────────


@dataclass(frozen=True)
class JpoliticsScript:
    """E1 — 쇼츠 스크립트 1편."""

    metadata: JpoliticsMetadata
    scenes: tuple[JpoliticsScene, ...]
    audio: JpoliticsAudioConfig
    background: JpoliticsBackgroundConfig = field(
        default_factory=JpoliticsBackgroundConfig
    )

    def validate(self) -> None:
        self.metadata.validate()
        if not 3 <= len(self.scenes) <= 30:
            raise ValueError(f"scenes count must be 3~30 (got {len(self.scenes)})")
        for s in self.scenes:
            s.validate()
        # 헤드라인 핀: 씬 0에만 (FR-011)
        for i, s in enumerate(self.scenes):
            if i != 0 and s.headline_pin is not None:
                raise ValueError(f"scene {i} has headline_pin (only scene 0 allowed)")

    @property
    def headline_pin(self) -> str:
        """첫 씬의 headline_pin을 영상 전체 헤드라인으로 사용."""
        if self.scenes and self.scenes[0].headline_pin:
            return self.scenes[0].headline_pin
        return self.metadata.title[:14]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "scenes": [s.to_dict() for s in self.scenes],
            "audio": self.audio.to_dict(),
            "background": self.background.to_dict(),
            "headline_pin": self.headline_pin,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsScript":
        return cls(
            metadata=JpoliticsMetadata.from_dict(data["metadata"]),
            scenes=tuple(JpoliticsScene.from_dict(s) for s in data["scenes"]),
            audio=JpoliticsAudioConfig.from_dict(data["audio"]),
            background=JpoliticsBackgroundConfig.from_dict(
                data.get("background", {"type": "gradient", "colors": ["#1a1a2e", "#16213e"]})
            ),
        )

    def with_scene_updated(self, scene_id: int, **changes: Any) -> "JpoliticsScript":
        """불변성 유지: 새 인스턴스 반환."""
        new_scenes = tuple(
            replace(s, **changes) if s.id == scene_id else s for s in self.scenes
        )
        return replace(self, scenes=new_scenes)
