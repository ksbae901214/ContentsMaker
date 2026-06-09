"""T017 [US1]: JpoliticsPlan / Narration / ThreePlansResult.

기획안 1편 + 3 plans 묶음 모델.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Angle = Literal["title_anchor", "audience_resonance", "comparison"]
FormatType = Literal["A", "B", "C"]
LayoutClassification = Literal[
    "talking_head", "vs_2way", "comparison_grid", "data_comparison"
]
VisualLayout = Literal["normal", "vs_card", "grid_2x2", "data_card"]
SubtitleColor = Literal["white", "yellow", "red", "blue"]


class PlanValidationError(Exception):
    """기획안 검증 실패."""


def validate_headline_pin(headline: str) -> None:
    """FR-011: 8~14자 한글 헤드라인."""
    if not isinstance(headline, str):
        raise ValueError("headline_pin must be str")
    n = len(headline)
    if n < 8 or n > 14:
        raise ValueError(
            f"headline_pin length must be 8~14 chars (got {n}: '{headline}')"
        )


# ─────────────────────────── Narration ───────────────────────────


@dataclass(frozen=True)
class Narration:
    """기획안 내 씬별 나레이션."""

    scene_id: int
    text: str  # 자막
    voice_text: str  # TTS 원문
    visual_layout: VisualLayout = "normal"
    subtitle_color: SubtitleColor = "white"
    subtitle_emphasis: bool = False
    cards_metadata: tuple[dict[str, Any], ...] | None = None
    clip_search_query: str | None = None  # FR-037 Claude 결정
    clip_source_timestamp: tuple[float, float] | None = None  # FR-037

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "scene_id": self.scene_id,
            "text": self.text,
            "voice_text": self.voice_text,
            "visual_layout": self.visual_layout,
            "subtitle_color": self.subtitle_color,
            "subtitle_emphasis": self.subtitle_emphasis,
        }
        if self.cards_metadata is not None:
            d["cards_metadata"] = list(self.cards_metadata)
        if self.clip_search_query is not None:
            d["clip_search_query"] = self.clip_search_query
        if self.clip_source_timestamp is not None:
            d["clip_source_timestamp"] = list(self.clip_source_timestamp)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Narration":
        cards_raw = data.get("cards_metadata") or data.get("cardsMetadata")
        ts_raw = data.get("clip_source_timestamp") or data.get("clipSourceTimestamp")
        scene_id_raw = data.get("scene_id")
        if scene_id_raw is None:
            scene_id_raw = data.get("sceneId", 0)
        return cls(
            scene_id=int(scene_id_raw or 0),  # type: ignore[arg-type]
            text=str(data.get("text") or ""),
            voice_text=str(data.get("voice_text") or data.get("voiceText") or ""),
            visual_layout=str(data.get("visual_layout") or data.get("visualLayout") or "normal"),  # type: ignore[arg-type]
            subtitle_color=str(data.get("subtitle_color") or data.get("subtitleColor") or "white"),  # type: ignore[arg-type]
            subtitle_emphasis=bool(data.get("subtitle_emphasis") or data.get("subtitleEmphasis") or False),
            cards_metadata=tuple(cards_raw) if cards_raw else None,
            clip_search_query=data.get("clip_search_query") or data.get("clipSearchQuery"),
            clip_source_timestamp=(
                (float(ts_raw[0]), float(ts_raw[1])) if ts_raw else None
            ),
        )


# ─────────────────────────── JpoliticsPlan ───────────────────────────


@dataclass(frozen=True)
class JpoliticsPlan:
    rank: int  # 1~3
    angle: Angle
    format_type: FormatType
    layout_classification: LayoutClassification
    topic: str
    hook: str
    clip_section: str
    reason: str
    flow_intro: str
    flow_middle: str
    flow_climax: str
    narrations: tuple[Narration, ...]
    cta: str
    headline_pin: str
    youtube_search_keywords: tuple[str, ...] | None = None  # topic 모드만

    def validate(self) -> None:
        if self.rank not in (1, 2, 3):
            raise PlanValidationError(f"rank must be 1/2/3 (got {self.rank})")
        validate_headline_pin(self.headline_pin)
        if not 3 <= len(self.narrations) <= 30:
            raise PlanValidationError(
                f"narrations count must be 3~30 (got {len(self.narrations)})"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "rank": self.rank,
            "angle": self.angle,
            "format_type": self.format_type,
            "layout_classification": self.layout_classification,
            "topic": self.topic,
            "hook": self.hook,
            "clip_section": self.clip_section,
            "reason": self.reason,
            "flow_intro": self.flow_intro,
            "flow_middle": self.flow_middle,
            "flow_climax": self.flow_climax,
            "narrations": [n.to_dict() for n in self.narrations],
            "cta": self.cta,
            "headline_pin": self.headline_pin,
        }
        if self.youtube_search_keywords is not None:
            d["youtube_search_keywords"] = list(self.youtube_search_keywords)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsPlan":
        narrs = data.get("narrations") or []
        kws = data.get("youtube_search_keywords") or data.get("youtubeSearchKeywords")
        return cls(
            rank=int(data["rank"]),
            angle=str(data["angle"]),  # type: ignore[arg-type]
            format_type=str(data.get("format_type") or data.get("formatType") or "A"),  # type: ignore[arg-type]
            layout_classification=str(  # type: ignore[arg-type]
                data.get("layout_classification") or data.get("layoutClassification") or "talking_head"
            ),
            topic=str(data["topic"]),
            hook=str(data["hook"]),
            clip_section=str(data.get("clip_section") or data.get("clipSection") or ""),
            reason=str(data["reason"]),
            flow_intro=str(data.get("flow_intro") or data.get("flowIntro") or ""),
            flow_middle=str(data.get("flow_middle") or data.get("flowMiddle") or ""),
            flow_climax=str(data.get("flow_climax") or data.get("flowClimax") or ""),
            narrations=tuple(Narration.from_dict(n) for n in narrs),
            cta=str(data["cta"]),
            headline_pin=str(data.get("headline_pin") or data.get("headlinePin") or ""),
            youtube_search_keywords=tuple(kws) if kws else None,
        )


# ─────────────────────────── ThreePlansResult ───────────────────────────


@dataclass(frozen=True)
class JpoliticsThreePlansResult:
    plans: tuple[JpoliticsPlan, JpoliticsPlan, JpoliticsPlan]
    video_title: str
    video_duration_sec: float
    output_dir: str
    created_at: str
    youtube_url: str | None = None
    topic: str | None = None
    video_path: str | None = None
    transcript_path: str | None = None

    def validate(self) -> None:
        if len(self.plans) != 3:
            raise PlanValidationError("plans must have exactly 3 elements")
        angles = {p.angle for p in self.plans}
        if len(angles) != 3:
            raise PlanValidationError(f"3 plans must have distinct angles (got {angles})")
        for p in self.plans:
            p.validate()
        if (self.youtube_url is None) == (self.topic is None):
            raise PlanValidationError("exactly one of youtube_url/topic must be set")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "plans": [p.to_dict() for p in self.plans],
            "video_title": self.video_title,
            "video_duration_sec": self.video_duration_sec,
            "output_dir": self.output_dir,
            "created_at": self.created_at,
        }
        if self.youtube_url is not None:
            d["youtube_url"] = self.youtube_url
        if self.topic is not None:
            d["topic"] = self.topic
        if self.video_path is not None:
            d["video_path"] = self.video_path
        if self.transcript_path is not None:
            d["transcript_path"] = self.transcript_path
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JpoliticsThreePlansResult":
        plans = [JpoliticsPlan.from_dict(p) for p in data["plans"]]
        if len(plans) != 3:
            raise PlanValidationError(f"plans must have 3 elements (got {len(plans)})")
        return cls(
            plans=(plans[0], plans[1], plans[2]),
            video_title=str(data.get("video_title") or data.get("videoTitle") or ""),
            video_duration_sec=float(data.get("video_duration_sec") or data.get("videoDurationSec") or 0),
            output_dir=str(data.get("output_dir") or data.get("outputDir") or ""),
            created_at=str(data.get("created_at") or data.get("createdAt") or ""),
            youtube_url=data.get("youtube_url") or data.get("youtubeUrl"),
            topic=data.get("topic"),
            video_path=data.get("video_path") or data.get("videoPath"),
            transcript_path=data.get("transcript_path") or data.get("transcriptPath"),
        )
