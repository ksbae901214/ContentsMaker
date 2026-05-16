"""YouTube video download and clip extraction for political commentary mode.

Uses yt-dlp (subprocess) for downloading and ffmpeg for clip/audio extraction.
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class TranscriptUnavailableError(Exception):
    """VTT·Whisper STT 모두 실패하거나 영상이 없을 때 — 환각 방지용 fail-loud 신호."""


class YouTubeDownloadError(Exception):
    """Raised when YouTube download or processing fails."""


# ── Download ──────────────────────────────────────────────────────────────


def get_video_metadata(url: str) -> dict:
    """Fetch video metadata (title + channel/uploader) without downloading.

    Returns: ``{"title": str, "channel": str, "id": str, "duration_sec": float}``.
    Empty strings on extraction failure (never raises — caller decides fallback).
    """
    try:
        import yt_dlp
    except ImportError:
        return {"title": "", "channel": "", "id": "", "duration_sec": 0.0}

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False) or {}
        return {
            "title": (info.get("title") or "").strip(),
            "channel": (info.get("channel") or info.get("uploader") or "").strip(),
            "id": (info.get("id") or "").strip(),
            "duration_sec": float(info.get("duration") or 0.0),
        }
    except Exception as e:
        logger.warning("get_video_metadata 실패 (%s): %s", url, e)
        return {"title": "", "channel": "", "id": "", "duration_sec": 0.0}


def download_video(url: str, output_dir: Path) -> Path:
    """Download a YouTube video as MP4. Returns path to downloaded file.

    Resolution order for the returned path:
    1. yt-dlp's ``--print after_move:filepath`` stdout (trusted when present).
    2. Glob ``*.mp4`` in ``output_dir``, **excluding ``scene_*.mp4``** — those
       are per-scene clips written by the segment cutter into the same
       directory, and their mtime is newer than the YouTube download on repeat
       runs (which would silently feed a 6-second piece back into the cutter
       and blow up at 791s seek).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", template,
        "--no-playlist",
        "--print", "after_move:filepath",
        "--no-simulate",
        "--quiet",
        url,
    ]
    logger.info("YouTube 영상 다운로드: %s", url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise YouTubeDownloadError(
            f"yt-dlp 다운로드 실패: {result.stderr[:300]}"
        )

    # Prefer the exact path reported by yt-dlp.
    for line in (result.stdout or "").splitlines():
        candidate = Path(line.strip())
        if candidate.suffix.lower() == ".mp4" and candidate.exists():
            logger.info(
                "다운로드 완료: %s (%.1f MB)",
                candidate.name, candidate.stat().st_size / 1e6,
            )
            return candidate

    # Fallback: glob but skip scene_*.mp4 pieces left by the segment cutter.
    mp4_files = sorted(
        (p for p in output_dir.glob("*.mp4") if not p.name.startswith("scene_")),
        key=lambda p: p.stat().st_mtime,
    )
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
        sys.executable, "-m", "yt_dlp",
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


# ── Transcript fallback (VTT → Whisper STT) ──────────────────────────────
# 버그: 자막 없는 NATV 영상에서 빈 transcript로 analyze_topic을 호출해 Claude가
# 환각을 일으키는 문제 수정 (2026-04-20). 자막이 없으면 Whisper STT로 폴백하고,
# 둘 다 실패 시 TranscriptUnavailableError로 명시적으로 실패한다.


def _whisper_transcribe(video_path: Path, *, model_name: str = "large-v3") -> list[dict]:
    """Whisper 로컬 STT. 실패 시 예외 전파.

    Returns: [{"start": float, "end": float, "text": str}, ...]
    """
    import whisper  # type: ignore

    model = whisper.load_model(model_name)
    result = model.transcribe(str(video_path), language="ko", verbose=False)
    segments = []
    for seg in result.get("segments", []):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        segments.append({
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": text,
        })
    return segments


def transcribe_video_or_fallback(
    *,
    url: str,
    video_path: Path,
    out_dir: Path,
    lang: str = "ko",
) -> list[dict]:
    """NATV 영상 transcript 확보 — VTT 우선, 실패 시 Whisper STT 폴백.

    환각 방지 (bugfix 2026-04-20):
      1) yt-dlp로 한국어 자막 VTT 다운로드 시도
      2) VTT 없거나 비어 있으면 Whisper STT로 대체 (무거움, 수 분 소요)
      3) Whisper마저 실패하면 `TranscriptUnavailableError` 발생 → 상위에서 사용자 안내

    Raises:
        TranscriptUnavailableError: 영상 파일 없음, 자막/STT 모두 실패, 결과 비어 있음.
    """
    if not video_path.exists():
        raise TranscriptUnavailableError(
            f"video_not_found: {video_path} — 영상 다운로드가 먼저 완료되어야 합니다."
        )

    vtt = download_subtitles(url, out_dir, lang=lang)
    if vtt is not None:
        transcript = parse_vtt_subtitles(vtt)
        if transcript:
            logger.info("VTT 자막 %d세그먼트 확보", len(transcript))
            return transcript
        logger.warning("VTT 파싱 결과가 비어 Whisper STT 폴백을 시도합니다.")

    logger.info("자막 없음 — Whisper STT 폴백 (%s)", video_path.name)
    try:
        result = _whisper_transcribe(video_path)
    except Exception as exc:
        raise TranscriptUnavailableError(
            f"자막 없음 + Whisper STT 실패: {exc}. "
            "수동으로 대본을 입력하거나 자막이 있는 영상을 사용하세요."
        ) from exc

    if not result:
        raise TranscriptUnavailableError(
            "자막·Whisper 모두 비어 transcript 확보 실패. "
            "음질이 낮거나 무음 영상일 수 있습니다."
        )
    logger.info("Whisper STT %d세그먼트 확보", len(result))
    return result
