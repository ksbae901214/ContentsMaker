"""모먼트 클립 제작 (Feature 027 Phase 2).

모먼트를 원본 영상에서 잘라내고 9:16 풀블리드로 크롭·스케일한다.
원본 음성 그대로 유지 (TTS·효과음 0).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.jpolitics.constants import MAX_MOMENT_SECONDS, MIN_MOMENT_SECONDS
from src.jpolitics.logger import logger
from src.jpolitics.models.clip import ClipResult
from src.jpolitics.models.moment import Moment

# ffmpeg 출력 해상도 (쇼츠 9:16)
OUT_WIDTH = 1080
OUT_HEIGHT = 1920


class ClipMakeError(Exception):
    """클립 생성 실패 — 길이 범위 초과, ffmpeg 오류 등."""


def _probe_streams(path: Path) -> list[dict]:
    """ffprobe JSON 스트림 목록 반환."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise ClipMakeError(f"ffprobe 실패: {result.stderr[:200]}")
    return json.loads(result.stdout).get("streams", [])


def _probe_video_info(path: Path) -> tuple[int, int, float, float]:
    """(width, height, fps, duration_sec) 반환."""
    streams = _probe_streams(path)
    for s in streams:
        if s.get("codec_type") == "video":
            w = int(s.get("width", 0))
            h = int(s.get("height", 0))
            # fps: "30/1" 또는 "30000/1001" 형태
            r_str = s.get("r_frame_rate") or s.get("avg_frame_rate") or "30/1"
            num, _, den = r_str.partition("/")
            fps = float(num) / float(den) if float(den) else 30.0
            dur = float(s.get("duration") or 0.0)
            return w, h, fps, dur
    raise ClipMakeError(f"영상 스트림을 찾을 수 없습니다: {path}")


def _build_crop_filter(src_w: int, src_h: int, crop_x: float) -> str:
    """소스 해상도에 맞는 vf 필터 문자열 반환.

    16:9 (가로 > 세로) → 세로 기준으로 9:16 크롭 후 1080×1920 스케일.
    이미 세로 (9:16 이하) → 1080×1920 스케일만.
    """
    is_landscape = src_w > src_h
    if is_landscape:
        # 9:16 크롭 너비 = src_h * 9 / 16
        crop_w_expr = "ih*9/16"
        # 크롭 x 오프셋 = (iw - crop_w) * crop_x
        x_offset = f"(iw-ih*9/16)*{crop_x:.4f}"
        return (
            f"crop={crop_w_expr}:ih:{x_offset}:0,"
            f"scale={OUT_WIDTH}:{OUT_HEIGHT}"
        )
    # 세로 영상: 그대로 스케일
    return f"scale={OUT_WIDTH}:{OUT_HEIGHT}"


def _run_ffmpeg(cmd: list[str]) -> None:
    """ffmpeg 실행. returncode != 0 이면 ClipMakeError."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise ClipMakeError(f"ffmpeg 실패 (rc={result.returncode}): {result.stderr[-400:]}")


def make_moment_clip(
    source_video: Path,
    moment: Moment,
    output_path: Path,
    *,
    pad_before: float = 0.5,
    pad_after: float = 0.5,
    crop_x: float = 0.5,
) -> ClipResult:
    """모먼트를 9:16 풀블리드 클립으로 잘라낸다.

    Args:
        source_video: 원본 영상 경로.
        moment: 잘라낼 모먼트.
        output_path: 출력 MP4 경로.
        pad_before: 시작 여유 (초, 기본 0.5).
        pad_after: 종료 여유 (초, 기본 0.5).
        crop_x: 가로 영상 크롭 중심 0(왼쪽)~1(오른쪽), 기본 0.5.

    Returns:
        ClipResult (frozen dataclass).

    Raises:
        ClipMakeError: ffmpeg 오류 또는 클립 길이가 5~61초 범위를 벗어난 경우.
    """
    if not source_video.exists():
        raise ClipMakeError(f"원본 영상을 찾을 수 없습니다: {source_video}")

    src_w, src_h, _, total_dur = _probe_video_info(source_video)

    start = max(0.0, moment.start_sec - pad_before)
    end = moment.end_sec + pad_after
    if total_dur > 0:
        end = min(end, total_dur)

    expected_dur = end - start
    if expected_dur < MIN_MOMENT_SECONDS:
        raise ClipMakeError(
            f"클립 길이({expected_dur:.1f}s)가 최소 {MIN_MOMENT_SECONDS}s 미만입니다."
        )

    vf = _build_crop_filter(src_w, src_h, crop_x)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", str(source_video),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ]
    logger.info(
        "클립 제작: %s → %s (%.1fs~%.1fs, crop_x=%.2f)",
        source_video.name, output_path.name, start, end, crop_x,
    )
    _run_ffmpeg(cmd)

    # ffprobe로 실제 결과 검증
    out_w, out_h, out_fps, out_dur = _probe_video_info(output_path)

    if not (MIN_MOMENT_SECONDS <= out_dur <= MAX_MOMENT_SECONDS + 1):
        raise ClipMakeError(
            f"클립 길이 범위 초과: {out_dur:.1f}s "
            f"(허용 범위 {MIN_MOMENT_SECONDS}~{MAX_MOMENT_SECONDS}s)"
        )

    logger.info(
        "클립 완료: %s | %dx%d %.1ffps %.1fs",
        output_path.name, out_w, out_h, out_fps, out_dur,
    )
    return ClipResult(
        source_video=str(source_video),
        clip_path=str(output_path),
        moment_dict=moment.to_dict(),
        width=out_w,
        height=out_h,
        fps=out_fps,
        duration_sec=out_dur,
        crop_x=crop_x,
    )
