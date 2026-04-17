"""T063: Segment cutter — ffmpeg로 구간 자르기 + 9:16 세로 변환 (FR-017, FR-018).

NATV 원본 영상은 16:9 가로형이므로, 쇼츠 1080x1920 포맷으로 크롭/패딩 변환이 필요.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.dem_shorts.config import (
    CUT_MAX_SEC,
    RENDER_AUDIO_BITRATE,
    RENDER_CRF,
    SHORTS_HEIGHT,
    SHORTS_WIDTH,
)


class SegmentCutError(Exception):
    """Raised when segment cut fails."""


def validate_cut_duration(start_sec: float, end_sec: float) -> None:
    """FR-018: cut duration ≤ 60s."""
    if start_sec < 0:
        raise SegmentCutError(f"start_sec must be >= 0: {start_sec}")
    duration = end_sec - start_sec
    if duration <= 0:
        raise SegmentCutError(
            f"cut duration must be positive: start={start_sec} end={end_sec}"
        )
    if duration > CUT_MAX_SEC:
        raise SegmentCutError(
            f"cut duration {duration}s exceeds {CUT_MAX_SEC}s limit (FR-018)"
        )


def build_ffmpeg_cmd(
    *,
    input_path: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
    width: int = SHORTS_WIDTH,
    height: int = SHORTS_HEIGHT,
) -> list[str]:
    """FFmpeg 명령어 생성. 9:16 비율 세로형 변환 + 구간 자르기.

    변환 전략:
    - 원본 가운데를 기준으로 높이 맞춤으로 크롭
    - 결과가 1080x1920보다 작으면 검은색 패딩
    """
    validate_cut_duration(start_sec, end_sec)
    duration = end_sec - start_sec

    # 세로 포맷 변환: scale + pad (크롭은 얼굴 손실 가능성 → 패딩 선택)
    vf = (
        f"scale='if(gt(a,{width}/{height}),{width},-2)':'if(gt(a,{width}/{height}),-2,{height})',"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )

    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ss",
        f"{start_sec}",
        "-t",
        f"{duration}",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        str(RENDER_CRF),
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        RENDER_AUDIO_BITRATE,
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def cut_segment(
    *,
    input_path: Path,
    output_path: Path,
    start_sec: float,
    end_sec: float,
) -> Path:
    """구간 자르기 + 9:16 변환을 실제 실행."""
    if not input_path.exists():
        raise SegmentCutError(f"input not found: {input_path}")
    if shutil.which("ffmpeg") is None:
        raise SegmentCutError("ffmpeg not installed or not on PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_ffmpeg_cmd(
        input_path=input_path,
        output_path=output_path,
        start_sec=start_sec,
        end_sec=end_sec,
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise SegmentCutError(
            f"ffmpeg failed (exit {result.returncode}): {result.stderr[:500]}"
        )
    if not output_path.exists():
        raise SegmentCutError(f"output not produced: {output_path}")
    size = output_path.stat().st_size
    if size < 1000:
        raise SegmentCutError(
            f"output too small ({size} bytes) — empty container, ffmpeg may have failed silently. "
            f"stderr: {result.stderr[:300]}"
        )
    return output_path
