"""모먼트 데이터 모델 (Feature 027) — frozen dataclass.

Moment = 영상 속 "감정이 터진 순간" 1개. 벤치마크 분석에서 도출한
조회수 상위 정치쇼츠의 소재 단위다. 정보 요약이 아니라 웃음·충돌·언성
같은 순간을 그대로 잘라내는 것이 신규 V3의 핵심.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.jpolitics.constants import MOMENT_KINDS


def _pick(d: dict, snake: str, camel: str, default=None):
    """snake_case 우선, camelCase 폴백 (프로젝트 직렬화 컨벤션)."""
    if snake in d:
        return d[snake]
    return d.get(camel, default)


@dataclass(frozen=True)
class Moment:
    """감정 모먼트 1개 — 검출 결과의 최소 단위."""

    start_sec: float
    end_sec: float
    kind: str                     # MOMENT_KINDS 중 하나
    speaker: str                  # 모먼트의 주인공 (불명이면 "")
    summary: str                  # 무슨 일이 있었는지 한 줄
    hook_question: str            # 질문형 떡밥 훅 (타이포 카드용)
    keywords: tuple[str, ...]     # 훅 카드 색 강조 키워드 1~3개
    confidence: float             # 검출 확신도 0~1

    def __post_init__(self) -> None:
        if self.end_sec <= self.start_sec:
            raise ValueError(
                f"end_sec({self.end_sec})는 start_sec({self.start_sec})보다 커야 합니다"
            )
        if self.kind not in MOMENT_KINDS:
            raise ValueError(f"알 수 없는 모먼트 종류: {self.kind!r} (허용: {MOMENT_KINDS})")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence는 0~1이어야 합니다: {self.confidence}")

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec

    def to_dict(self) -> dict:
        return {
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "kind": self.kind,
            "speaker": self.speaker,
            "summary": self.summary,
            "hook_question": self.hook_question,
            "keywords": list(self.keywords),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Moment":
        return cls(
            start_sec=float(_pick(d, "start_sec", "startSec", 0.0)),
            end_sec=float(_pick(d, "end_sec", "endSec", 0.0)),
            kind=str(d.get("kind", "other")),
            speaker=str(d.get("speaker", "")),
            summary=str(d.get("summary", "")),
            hook_question=str(_pick(d, "hook_question", "hookQuestion", "")),
            keywords=tuple(str(k) for k in d.get("keywords") or ()),
            confidence=float(d.get("confidence", 0.0)),
        )


@dataclass(frozen=True)
class MomentDetectionResult:
    """영상 1편에 대한 모먼트 검출 결과."""

    source_url: str
    video_title: str
    channel: str
    detector: str                       # "gemini_multimodal" | "transcript"
    moments: tuple[Moment, ...] = field(default_factory=tuple)

    def top(self, n: int) -> tuple[Moment, ...]:
        """확신도 내림차순 상위 n개."""
        return tuple(
            sorted(self.moments, key=lambda m: m.confidence, reverse=True)[:n]
        )

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "video_title": self.video_title,
            "channel": self.channel,
            "detector": self.detector,
            "moments": [m.to_dict() for m in self.moments],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MomentDetectionResult":
        return cls(
            source_url=str(_pick(d, "source_url", "sourceUrl", "")),
            video_title=str(_pick(d, "video_title", "videoTitle", "")),
            channel=str(d.get("channel", "")),
            detector=str(d.get("detector", "")),
            moments=tuple(Moment.from_dict(m) for m in d.get("moments") or ()),
        )

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))
        return path
