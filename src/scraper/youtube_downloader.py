"""YouTube video download and clip extraction for political commentary mode.

Uses yt-dlp (subprocess) for downloading and ffmpeg for clip/audio extraction.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class YouTubeDownloadError(Exception):
    """Raised when YouTube download or processing fails."""


# ── Download ──────────────────────────────────────────────────────────────


def download_video(url: str, output_dir: Path) -> Path:
    """Download a YouTube video as MP4. Returns path to downloaded file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", template,
        "--no-playlist",
        "--quiet",
        url,
    ]
    logger.info("YouTube 영상 다운로드: %s", url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise YouTubeDownloadError(
            f"yt-dlp 다운로드 실패: {result.stderr[:300]}"
        )

    mp4_files = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not mp4_files:
        raise YouTubeDownloadError("다운로드된 MP4 파일을 찾을 수 없습니다.")

    path = mp4_files[-1]
    logger.info("다운로드 완료: %s (%.1f MB)", path.name, path.stat().st_size / 1e6)
    return path


def download_subtitles(
    url: str, output_dir: Path, lang: str = "ko"
) -> Path | None:
    """Download auto-generated Korean subtitles as VTT. Returns None if unavailable."""
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "%(id)s")

    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "vtt",
        "--skip-download",
        "-o", template,
        "--no-playlist",
        "--quiet",
        url,
    ]
    logger.info("자막 다운로드 시도: %s (lang=%s)", url, lang)
    subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    vtt_files = sorted(output_dir.glob(f"*.{lang}.vtt"), key=lambda p: p.stat().st_mtime)
    if not vtt_files:
        logger.warning("한국어 자막을 찾을 수 없습니다.")
        return None

    logger.info("자막 다운로드 완료: %s", vtt_files[-1].name)
    return vtt_files[-1]


# ── VTT Parsing ───────────────────────────────────────────────────────────

_VTT_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")


def _parse_ts(ts_str: str) -> float:
    """Convert "HH:MM:SS.mmm" to seconds."""
    m = _VTT_TS.match(ts_str)
    if not m:
        return 0.0
    h, mn, s, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    return h * 3600 + mn * 60 + s + ms / 1000


def parse_vtt_subtitles(vtt_path: Path) -> list[dict]:
    """Parse VTT file into timestamped segments.

    Returns: [{"start": 0.0, "end": 3.5, "text": "발언..."}, ...]
    Deduplicates consecutive identical text (common in auto-captions).
    """
    lines = vtt_path.read_text(encoding="utf-8").splitlines()
    segments: list[dict] = []
    prev_text = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for timestamp line: "00:00:01.000 --> 00:00:03.500"
        if "-->" in line:
            parts = line.split("-->")
            start = _parse_ts(parts[0].strip())
            end = _parse_ts(parts[1].strip().split()[0])

            # Collect text lines until blank
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                # Strip VTT tags like <c> </c>
                cleaned = re.sub(r"<[^>]+>", "", lines[i]).strip()
                if cleaned:
                    text_lines.append(cleaned)
                i += 1

            text = " ".join(text_lines)
            if text and text != prev_text:
                segments.append({"start": start, "end": end, "text": text})
                prev_text = text
        else:
            i += 1

    logger.info("자막 파싱 완료: %d 세그먼트", len(segments))
    return segments


# ── ffmpeg Clip Extraction ────────────────────────────────────────────────


def extract_clip(
    video_path: Path, start: float, end: float, output_path: Path
) -> Path:
    """Extract a clip from video. Falls back to re-encode if copy fails."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try fast copy first
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(video_path),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1000:
        logger.info("클립 추출 완료 (copy): %.1fs-%.1fs", start, end)
        return output_path

    # Fallback: re-encode
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(video_path),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise YouTubeDownloadError(f"클립 추출 실패: {result.stderr[:200]}")

    logger.info("클립 추출 완료 (re-encode): %.1fs-%.1fs", start, end)
    return output_path


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Extract audio track from video as MP3."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "24000",
        "-ab", "128k",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise YouTubeDownloadError(f"오디오 추출 실패: {result.stderr[:200]}")

    logger.info("오디오 추출 완료: %s", output_path.name)
    return output_path


def extract_scene_clips(
    clip_path: Path,
    scenes: list,
    output_dir: Path,
) -> list[dict]:
    """Extract individual video segments for each clip-type scene.

    Args:
        clip_path: Full clip video file.
        scenes: List of Scene objects (only type="clip" scenes are processed).
        output_dir: Where to save per-scene MP4 files.

    Returns: [{"scene_id": N, "video_path": str}, ...]
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for scene in scenes:
        if scene.type != "clip":
            continue
        if scene.clip_start is None or scene.clip_end is None:
            continue

        out = output_dir / f"scene_{scene.id:02d}.mp4"
        try:
            extract_clip(clip_path, scene.clip_start, scene.clip_end, out)
            results.append({"scene_id": scene.id, "video_path": str(out)})
        except YouTubeDownloadError as e:
            logger.warning("씬 %d 클립 추출 실패: %s", scene.id, e)

    logger.info("씬 클립 추출 완료: %d/%d", len(results), sum(1 for s in scenes if s.type == "clip"))
    return results
