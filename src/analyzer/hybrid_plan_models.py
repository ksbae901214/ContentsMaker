"""Data models for the political shorts V3 — hybrid format.

The hybrid format alternates between TTS commentary beats (Charon voice on a
muted source clip) and original beats (source clip with its own audio
preserved, subtitle overlay added). Total runtime ~45s, split roughly 50/50
between TTS and original.

Frozen dataclasses per project convention (immutability).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Reuse V2 angle whitelist so plan-selection UI behaves identically.
from src.analyzer.political_plan_models import _ALLOWED_ANGLES  # noqa: F401
from src.analyzer.political_plan_models import (
    _ALLOWED_SUBTITLE_COLORS,
    PlanValidationError,
)

Angle = Literal["title_anchor", "audience_resonance", "comparison"]
BeatKind = Literal["tts", "original"]
BgmMode = Literal["mute", "duck", "keep"]

_ALLOWED_BEAT_KINDS = ("tts", "original")
_ALLOWED_BGM_MODES = ("mute", "duck", "keep")

# 검증 룰: original/tts 합산 18~30초 허용, 전체 ≤ 50초 (outro 4s + 여유)
MIN_KIND_SECONDS = 12.0   # ±5초 여유까지 고려해 살짝 완화 (Charon 변동 대응)
MAX_KIND_SECONDS = 32.0
MAX_TOTAL_SECONDS = 50.0
MAX_SUBTITLE_CHARS_PER_LINE = 21
MAX_QUOTE_LINES = 3


@dataclass(frozen=True)
class HybridBeat:
    """One beat in a hybrid shorts plan.

    Either a TTS commentary (Charon reads `tts_text`, subtitle from `subtitle`)
    or an original quote (source clip [clip_start_sec, clip_end_sec] plays with
    its own audio while `quote_lines` is overlaid as a multi-line subtitle).
    """
    kind: BeatKind
    duration_sec: float  # estimated; renderer may correct from TTS/clip length

    # ── TTS-beat fields ──
    subtitle: str = ""
    tts_text: str = ""
    subtitle_color: str = "white"
    subtitle_emphasis: bool = False

    # ── original-beat fields ──
    clip_start_sec: float = 0.0
    clip_end_sec: float = 0.0
    speaker_name: str = ""
    quote_lines: tuple[str, ...] = ()
    bgm_mode: BgmMode = "mute"
    # source label override (e.g. "장동혁 대표 (Channel A 기자회견)").
    # Empty → renderer falls back to plan-level source_channel.
    source_label: str = ""
    # Optional separate source file for the clip (e.g. an external press
    # conference video). Renderer interprets relative paths against output_dir.
    source_clip_path: str = ""

    def __post_init__(self) -> None:
        if self.kind not in _ALLOWED_BEAT_KINDS:
            raise PlanValidationError(
                f"HybridBeat.kind은 {_ALLOWED_BEAT_KINDS} 중 하나 (현재 {self.kind!r})"
            )
        if self.duration_sec <= 0:
            raise PlanValidationError(
                f"HybridBeat.duration_sec > 0 필요 (현재 {self.duration_sec})"
            )

        if self.kind == "tts":
            if not (self.subtitle or "").strip():
                raise PlanValidationError("TTS 비트는 subtitle 필수")
            if not (self.tts_text or "").strip():
                raise PlanValidationError("TTS 비트는 tts_text 필수 (Charon 입력)")
            if self.subtitle_color not in _ALLOWED_SUBTITLE_COLORS:
                raise PlanValidationError(
                    f"subtitle_color는 {_ALLOWED_SUBTITLE_COLORS} 중 하나"
                )
        else:  # original
            if self.clip_end_sec <= self.clip_start_sec:
                raise PlanValidationError(
                    f"original 비트: clip_end > clip_start 필요 "
                    f"(start={self.clip_start_sec}, end={self.clip_end_sec})"
                )
            if not self.quote_lines:
                raise PlanValidationError("original 비트: quote_lines ≥1 필요")
            if len(self.quote_lines) > MAX_QUOTE_LINES:
                raise PlanValidationError(
                    f"original 비트: quote_lines ≤ {MAX_QUOTE_LINES} (자막 화면 한계)"
                )
            for ln in self.quote_lines:
                if len(ln) > MAX_SUBTITLE_CHARS_PER_LINE + 6:  # ASR 보정 여유
                    raise PlanValidationError(
                        f"original 비트 quote_lines 한 줄이 너무 김 "
                        f"(>{MAX_SUBTITLE_CHARS_PER_LINE + 6}자): {ln!r}"
                    )
            if self.bgm_mode not in _ALLOWED_BGM_MODES:
                raise PlanValidationError(
                    f"bgm_mode는 {_ALLOWED_BGM_MODES} 중 하나"
                )

    def to_dict(self) -> dict:
        d: dict = {"kind": self.kind, "duration_sec": self.duration_sec}
        if self.kind == "tts":
            d.update({
                "subtitle": self.subtitle,
                "tts_text": self.tts_text,
                "subtitle_color": self.subtitle_color,
                "subtitle_emphasis": self.subtitle_emphasis,
            })
        else:
            d.update({
                "clip_start_sec": self.clip_start_sec,
                "clip_end_sec": self.clip_end_sec,
                "speaker_name": self.speaker_name,
                "quote_lines": list(self.quote_lines),
                "bgm_mode": self.bgm_mode,
            })
            if self.source_label:
                d["source_label"] = self.source_label
            if self.source_clip_path:
                d["source_clip_path"] = self.source_clip_path
        return d

    @classmethod
    def from_dict(cls, data: dict) -> HybridBeat:
        kind = data["kind"]
        if kind == "tts":
            return cls(
                kind="tts",
                duration_sec=float(data["duration_sec"]),
                subtitle=str(data.get("subtitle", "")),
                tts_text=str(data.get("tts_text", "")),
                subtitle_color=str(data.get("subtitle_color", "white")),
                subtitle_emphasis=bool(data.get("subtitle_emphasis", False)),
            )
        return cls(
            kind="original",
            duration_sec=float(data["duration_sec"]),
            clip_start_sec=float(data.get("clip_start_sec", 0.0)),
            clip_end_sec=float(data.get("clip_end_sec", 0.0)),
            speaker_name=str(data.get("speaker_name", "")),
            quote_lines=tuple(data.get("quote_lines", ())),
            bgm_mode=str(data.get("bgm_mode", "mute")),
            source_label=str(data.get("source_label", "")),
            source_clip_path=str(data.get("source_clip_path", "")),
        )


@dataclass(frozen=True)
class HybridShortsPlan:
    """V3 하이브리드 정치쇼츠 기획안.

    hook(TTS) + beats(교차) + cta(TTS) 구조.
    검증: original/tts 합산이 각각 [MIN_KIND, MAX_KIND] 범위 + 전체 ≤ MAX_TOTAL.
    """
    topic: str
    hook: HybridBeat
    beats: tuple[HybridBeat, ...]
    cta: HybridBeat
    angle: Angle
    source_url: str = ""
    source_channel: str = ""
    source_title: str = ""
    # 화자별 외부 영상이 있다면 여기에 매핑 (e.g. "장동혁 대표" → jang_clip.mp4 경로)
    extra_clip_sources: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (("topic", self.topic),):
            if not (value or "").strip():
                raise PlanValidationError(f"HybridShortsPlan.{name} 비어 있을 수 없음")
        if self.angle not in _ALLOWED_ANGLES:
            raise PlanValidationError(
                f"angle은 {_ALLOWED_ANGLES} 중 하나 (현재 {self.angle!r})"
            )
        if self.hook.kind != "tts":
            raise PlanValidationError("hook 비트는 반드시 kind='tts'")
        if self.cta.kind != "tts":
            raise PlanValidationError("cta 비트는 반드시 kind='tts'")
        if not self.beats:
            raise PlanValidationError("beats ≥1 필요")

        # 원본 비트 사이에 TTS 비트가 끼어들어야 함 (논평 흐름).
        # 연속된 두 original 비트가 있으면 거부.
        prev_kind: str | None = None
        for b in self.beats:
            if prev_kind == "original" and b.kind == "original":
                raise PlanValidationError(
                    "beats: 연속된 두 'original' 비트 금지 (사이에 TTS 비트 필요)"
                )
            prev_kind = b.kind

        # 50:50 검증 (±5초 허용)
        all_beats: tuple[HybridBeat, ...] = (self.hook, *self.beats, self.cta)
        tts_sec = sum(b.duration_sec for b in all_beats if b.kind == "tts")
        orig_sec = sum(b.duration_sec for b in all_beats if b.kind == "original")
        total_sec = tts_sec + orig_sec

        if not (MIN_KIND_SECONDS <= tts_sec <= MAX_KIND_SECONDS):
            raise PlanValidationError(
                f"TTS 합산 {tts_sec:.1f}s가 [{MIN_KIND_SECONDS}, {MAX_KIND_SECONDS}] 범위 밖"
            )
        if not (MIN_KIND_SECONDS <= orig_sec <= MAX_KIND_SECONDS):
            raise PlanValidationError(
                f"원본 합산 {orig_sec:.1f}s가 [{MIN_KIND_SECONDS}, {MAX_KIND_SECONDS}] 범위 밖"
            )
        if total_sec > MAX_TOTAL_SECONDS:
            raise PlanValidationError(
                f"총합 {total_sec:.1f}s > 한계 {MAX_TOTAL_SECONDS}s"
            )

    @property
    def tts_seconds(self) -> float:
        all_beats = (self.hook, *self.beats, self.cta)
        return sum(b.duration_sec for b in all_beats if b.kind == "tts")

    @property
    def original_seconds(self) -> float:
        all_beats = (self.hook, *self.beats, self.cta)
        return sum(b.duration_sec for b in all_beats if b.kind == "original")

    @property
    def total_seconds(self) -> float:
        return self.tts_seconds + self.original_seconds

    def all_beats(self) -> tuple[HybridBeat, ...]:
        return (self.hook, *self.beats, self.cta)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "hook": self.hook.to_dict(),
            "beats": [b.to_dict() for b in self.beats],
            "cta": self.cta.to_dict(),
            "angle": self.angle,
            "source_url": self.source_url,
            "source_channel": self.source_channel,
            "source_title": self.source_title,
            "extra_clip_sources": dict(self.extra_clip_sources),
            "_meta": {
                "tts_sec": self.tts_seconds,
                "original_sec": self.original_seconds,
                "total_sec": self.total_seconds,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> HybridShortsPlan:
        return cls(
            topic=data["topic"],
            hook=HybridBeat.from_dict(data["hook"]),
            beats=tuple(HybridBeat.from_dict(b) for b in data["beats"]),
            cta=HybridBeat.from_dict(data["cta"]),
            angle=data["angle"],
            source_url=data.get("source_url", ""),
            source_channel=data.get("source_channel", ""),
            source_title=data.get("source_title", ""),
            extra_clip_sources=dict(data.get("extra_clip_sources", {})),
        )


@dataclass(frozen=True)
class ThreeHybridPlansResult:
    """Container for 3 angle-variant HybridShortsPlans + Stage A pool."""
    plans: tuple[HybridShortsPlan, HybridShortsPlan, HybridShortsPlan]
    candidates_pool: tuple[dict, ...]  # Stage A 출력 그대로 (디버깅·재선택용)
    youtube_url: str = ""
    video_title: str = ""
    video_channel: str = ""
    video_path: str = ""
    transcript_path: str = ""
    video_duration_sec: float = 0.0
    generated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "plans": [p.to_dict() for p in self.plans],
            "candidates_pool": list(self.candidates_pool),
            "youtube_url": self.youtube_url,
            "video_title": self.video_title,
            "video_channel": self.video_channel,
            "video_path": self.video_path,
            "transcript_path": self.transcript_path,
            "video_duration_sec": self.video_duration_sec,
            "generated_at": self.generated_at,
            "schema_version": "v3-hybrid-1",
        }

    @classmethod
    def from_dict(cls, data: dict) -> ThreeHybridPlansResult:
        plans = tuple(HybridShortsPlan.from_dict(p) for p in data["plans"])
        if len(plans) != 3:
            raise PlanValidationError(
                f"plans 배열 3개 필요 (받음 {len(plans)})"
            )
        return cls(
            plans=plans,  # type: ignore[arg-type]
            candidates_pool=tuple(data.get("candidates_pool", ())),
            youtube_url=data.get("youtube_url", ""),
            video_title=data.get("video_title", ""),
            video_channel=data.get("video_channel", ""),
            video_path=data.get("video_path", ""),
            transcript_path=data.get("transcript_path", ""),
            video_duration_sec=float(data.get("video_duration_sec", 0.0)),
            generated_at=data.get("generated_at", ""),
        )
