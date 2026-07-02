"""클립 결과 데이터 모델 (Feature 027 Phase 2) — frozen dataclass.

ClipResult = 모먼트를 9:16 풀블리드로 잘라낸 클립 1개.
CaptionCue = 클립 기준 상대 시간으로 정렬된 자막 큐 1개.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def _pick(d: dict, snake: str, camel: str, default=None):
    """snake_case 우선, camelCase 폴백 (프로젝트 직렬화 컨벤션)."""
    if snake in d:
        return d[snake]
    return d.get(camel, default)


@dataclass(frozen=True)
class CaptionCue:
    """클립 기준 상대 시간의 자막 큐 1개."""

    start_sec: float   # 클립 시작 기준 상대 시간
    end_sec: float     # 클립 시작 기준 상대 시간
    text: str          # 1~2줄로 분리된 자막 텍스트 (줄바꿈 포함 가능)

    def to_dict(self) -> dict:
        return {
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CaptionCue":
        return cls(
            start_sec=float(_pick(d, "start_sec", "startSec", 0.0)),
            end_sec=float(_pick(d, "end_sec", "endSec", 0.0)),
            text=str(d.get("text", "")),
        )


@dataclass(frozen=True)
class ClipResult:
    """모먼트 클립 1개의 처리 결과."""

    source_video: str    # 원본 영상 경로
    clip_path: str       # 출력 클립 경로
    moment_dict: dict    # Moment.to_dict() 직렬화 (frozen dict 대체)
    width: int           # 출력 너비 (1080)
    height: int          # 출력 높이 (1920)
    fps: float           # 프레임레이트 (30.0)
    duration_sec: float  # 클립 실제 길이
    crop_x: float        # 크롭 중심 0~1

    def to_dict(self) -> dict:
        return {
            "source_video": self.source_video,
            "clip_path": self.clip_path,
            "moment": self.moment_dict,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration_sec": self.duration_sec,
            "crop_x": self.crop_x,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClipResult":
        return cls(
            source_video=str(_pick(d, "source_video", "sourceVideo", "")),
            clip_path=str(_pick(d, "clip_path", "clipPath", "")),
            moment_dict=dict(d.get("moment") or {}),
            width=int(d.get("width", 1080)),
            height=int(d.get("height", 1920)),
            fps=float(d.get("fps", 30.0)),
            duration_sec=float(_pick(d, "duration_sec", "durationSec", 0.0)),
            crop_x=float(_pick(d, "crop_x", "cropX", 0.5)),
        )

    def save(self, work_dir: Path, n: int) -> Path:
        """work_dir/clip_{n}.json 으로 저장."""
        work_dir.mkdir(parents=True, exist_ok=True)
        out = work_dir / f"clip_{n}.json"
        out.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))
        return out
