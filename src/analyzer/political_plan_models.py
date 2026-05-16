"""Data models for political shorts planner (Feature 009).

Frozen dataclasses per Constitution Principle VI (immutability).
RTF 영상생성지침 6요소 + angle 메타데이터.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


_ALLOWED_ANGLES = ("title_anchor", "audience_resonance", "comparison")
Angle = Literal["title_anchor", "audience_resonance", "comparison"]

# Feature 011 V2 — gemini-code 지침 반영
_ALLOWED_FORMAT_TYPES = ("A", "B")  # A=인터뷰/논평/MBC라디오, B=현장/뉴스핌
_ALLOWED_SUBTITLE_COLORS = ("white", "red", "yellow", "blue")
FormatType = Literal["A", "B"]


class PlanValidationError(ValueError):
    """Raised when ShortsPlan / Narration / ThreePlansResult validation fails."""


# ─────────────────────────────── Narration ───────────────────────────────


@dataclass(frozen=True)
class Narration:
    """Timing-tagged narration line within a ShortsPlan.

    Times are RELATIVE to the clip (not absolute video time).
    Example: (0~3초): "지금 이 장면, 그냥 넘어가면 안 됩니다"

    V2 (Feature 011): subtitle_color + subtitle_emphasis로 자막 시각 연출.
    """
    start_sec: float
    end_sec: float
    text: str
    # V2 — gemini-code 지침: 자막 색·강조 (Phase A에서는 메타데이터만, Phase B에서 렌더 적용)
    subtitle_color: str = "white"
    subtitle_emphasis: bool = False

    def __post_init__(self) -> None:
        if not (self.text or "").strip():
            raise PlanValidationError("Narration.text는 비어 있을 수 없습니다")
        if self.start_sec < 0:
            raise PlanValidationError(f"Narration.start_sec >= 0 필요 (현재 {self.start_sec})")
        if self.end_sec <= self.start_sec:
            raise PlanValidationError(
                f"Narration.end_sec > start_sec 필요 (start={self.start_sec}, end={self.end_sec})"
            )
        if self.subtitle_color not in _ALLOWED_SUBTITLE_COLORS:
            raise PlanValidationError(
                f"subtitle_color는 {_ALLOWED_SUBTITLE_COLORS} 중 하나 (현재 {self.subtitle_color!r})"
            )

    def to_dict(self) -> dict:
        d = {
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "text": self.text,
        }
        # V2: default가 아닐 때만 직렬화 (V1 JSON과 호환 유지)
        if self.subtitle_color != "white":
            d["subtitle_color"] = self.subtitle_color
        if self.subtitle_emphasis:
            d["subtitle_emphasis"] = True
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Narration:
        return cls(
            start_sec=float(data.get("start_sec", data.get("startSec", 0.0))),
            end_sec=float(data.get("end_sec", data.get("endSec", 0.0))),
            text=str(data.get("text", "")),
            subtitle_color=str(
                data.get("subtitle_color", data.get("subtitleColor", "white"))
            ),
            subtitle_emphasis=bool(
                data.get("subtitle_emphasis", data.get("subtitleEmphasis", False))
            ),
        )


# ─────────────────────────────── ShortsPlan ───────────────────────────────


@dataclass(frozen=True)
class ShortsPlan:
    """RTF 6요소 기반 단일 숏츠 기획안 + angle 메타데이터.

    6 elements:
        1) topic        — 한 줄 핵심 이슈
        2) hook         — 0~3초 후킹 문구
        3) clip_*       — 사용 구간 + 선택 이유
        4) flow_*       — 시작·중간·클라이맥스 흐름
        5) narrations   — 타이밍별 나레이션 목록
        6) cta          — 마무리 유도 문구

    V2 (Feature 011): format_type/format_reason/visual_directives 추가.
    """
    topic: str
    hook: str
    clip_start_sec: float
    clip_end_sec: float
    clip_reason: str
    flow_intro: str
    flow_middle: str
    flow_climax: str
    narrations: tuple[Narration, ...]
    cta: str
    angle: Angle
    # V2 — gemini-code 지침 (Phase A): 콘텐츠 포맷 분류 + 시각 연출 지시
    format_type: FormatType = "A"  # A=인터뷰/논평/MBC라디오, B=현장/뉴스핌
    format_reason: str = ""
    visual_directives: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required_text_fields = {
            "topic": self.topic,
            "hook": self.hook,
            "clip_reason": self.clip_reason,
            "flow_intro": self.flow_intro,
            "flow_middle": self.flow_middle,
            "flow_climax": self.flow_climax,
            "cta": self.cta,
        }
        for name, value in required_text_fields.items():
            if not (value or "").strip():
                raise PlanValidationError(f"ShortsPlan.{name}는 비어 있을 수 없습니다")

        if self.clip_start_sec < 0:
            raise PlanValidationError(
                f"clip_start_sec >= 0 필요 (현재 {self.clip_start_sec})"
            )
        if self.clip_end_sec <= self.clip_start_sec:
            raise PlanValidationError(
                f"clip_end_sec > clip_start_sec 필요 "
                f"(start={self.clip_start_sec}, end={self.clip_end_sec})"
            )

        if not self.narrations:
            raise PlanValidationError("narrations는 최소 1개 이상")
        if not all(isinstance(n, Narration) for n in self.narrations):
            raise PlanValidationError("narrations 항목은 모두 Narration 타입이어야 함")

        if self.angle not in _ALLOWED_ANGLES:
            raise PlanValidationError(
                f"angle은 {_ALLOWED_ANGLES} 중 하나여야 함 (현재 {self.angle!r})"
            )
        # V2 검증: format_type 화이트리스트
        if self.format_type not in _ALLOWED_FORMAT_TYPES:
            raise PlanValidationError(
                f"format_type은 {_ALLOWED_FORMAT_TYPES} 중 하나 (현재 {self.format_type!r})"
            )

    def to_dict(self) -> dict:
        d = {
            "topic": self.topic,
            "hook": self.hook,
            "clip_start_sec": self.clip_start_sec,
            "clip_end_sec": self.clip_end_sec,
            "clip_reason": self.clip_reason,
            "flow_intro": self.flow_intro,
            "flow_middle": self.flow_middle,
            "flow_climax": self.flow_climax,
            "narrations": [n.to_dict() for n in self.narrations],
            "cta": self.cta,
            "angle": self.angle,
        }
        # V2: default가 아닐 때만 직렬화 (V1 호환)
        # format_type은 default("A")여도 항상 직렬화 — Phase B/C에서 분기 키로 사용
        d["format_type"] = self.format_type
        if self.format_reason:
            d["format_reason"] = self.format_reason
        if self.visual_directives:
            d["visual_directives"] = list(self.visual_directives)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ShortsPlan:
        narr_raw = data.get("narrations", [])
        # V2: visual_directives는 list 또는 tuple 모두 수용
        vd_raw = data.get("visual_directives", data.get("visualDirectives", ()))
        return cls(
            topic=str(data.get("topic", "")),
            hook=str(data.get("hook", "")),
            clip_start_sec=float(data.get("clip_start_sec", data.get("clipStartSec", 0.0))),
            clip_end_sec=float(data.get("clip_end_sec", data.get("clipEndSec", 0.0))),
            clip_reason=str(data.get("clip_reason", data.get("clipReason", ""))),
            flow_intro=str(data.get("flow_intro", data.get("flowIntro", ""))),
            flow_middle=str(data.get("flow_middle", data.get("flowMiddle", ""))),
            flow_climax=str(data.get("flow_climax", data.get("flowClimax", ""))),
            narrations=tuple(Narration.from_dict(n) for n in narr_raw),
            cta=str(data.get("cta", "")),
            angle=str(data.get("angle", "")),  # type: ignore[arg-type]
            # V2 — default fallback으로 V1 JSON 그대로 로드 가능
            format_type=str(data.get("format_type", data.get("formatType", "A"))),  # type: ignore[arg-type]
            format_reason=str(data.get("format_reason", data.get("formatReason", ""))),
            visual_directives=tuple(vd_raw) if vd_raw else (),
        )


# ─────────────────────────────── ThreePlansResult ───────────────────────────────


@dataclass(frozen=True)
class ThreePlansResult:
    """Container for the 3-plan generation output.

    Exactly 3 plans, each with a distinct angle (FR-006).
    """
    plans: tuple[ShortsPlan, ShortsPlan, ShortsPlan]
    youtube_url: str
    video_path: str
    video_duration_sec: float
    transcript_path: str
    video_title: str
    generated_at: str  # ISO 8601
    # Feature 009: 출처 표시용 채널명 (yt-dlp uploader). 비어있으면 미사용.
    video_channel: str = ""

    def __post_init__(self) -> None:
        if len(self.plans) != 3:
            raise PlanValidationError(
                f"ThreePlansResult.plans는 정확히 3개여야 함 (현재 {len(self.plans)})"
            )
        angles = [p.angle for p in self.plans]
        if len(set(angles)) != 3:
            raise PlanValidationError(
                f"3개 plan의 angle은 서로 달라야 함 (현재 {angles})"
            )

    def to_dict(self) -> dict:
        d = {
            "plans": [p.to_dict() for p in self.plans],
            "youtube_url": self.youtube_url,
            "video_path": self.video_path,
            "video_duration_sec": self.video_duration_sec,
            "transcript_path": self.transcript_path,
            "video_title": self.video_title,
            "generated_at": self.generated_at,
        }
        if self.video_channel:
            d["video_channel"] = self.video_channel
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ThreePlansResult:
        plans_raw = data.get("plans", [])
        plans_tuple = tuple(ShortsPlan.from_dict(p) for p in plans_raw)
        return cls(
            plans=plans_tuple,  # type: ignore[arg-type]
            youtube_url=str(data.get("youtube_url", data.get("youtubeUrl", ""))),
            video_path=str(data.get("video_path", data.get("videoPath", ""))),
            video_duration_sec=float(data.get("video_duration_sec", data.get("videoDurationSec", 0.0))),
            transcript_path=str(data.get("transcript_path", data.get("transcriptPath", ""))),
            video_title=str(data.get("video_title", data.get("videoTitle", ""))),
            generated_at=str(data.get("generated_at", data.get("generatedAt", ""))),
            video_channel=str(data.get("video_channel", data.get("videoChannel", ""))),
        )
