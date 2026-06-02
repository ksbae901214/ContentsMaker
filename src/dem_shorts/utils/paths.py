"""data/dem_shorts/* 경로 헬퍼.

Usage:
    from src.dem_shorts.utils.paths import archive_path, transcript_path
    p = archive_path("abc123")   # → Path("data/dem_shorts/archive/abc123.mp4")
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path("data/dem_shorts")

ARCHIVE_DIR = ROOT / "archive"
RAW_DIR = ROOT / "raw"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SEGMENTS_DIR = ROOT / "segments"
DRAFTS_DIR = ROOT / "drafts"
OUTPUTS_DIR = ROOT / "outputs"
BGM_DIR = ROOT / "bgm"
LOGS_DIR = ROOT / "logs"
DB_PATH = ROOT / "state.db"
BGM_MANIFEST = BGM_DIR / "bgm_manifest.json"


def ensure_dirs() -> None:
    """Create all data directories if missing."""
    for d in (
        ARCHIVE_DIR,
        RAW_DIR,
        TRANSCRIPTS_DIR,
        SEGMENTS_DIR,
        DRAFTS_DIR,
        OUTPUTS_DIR,
        BGM_DIR,
        LOGS_DIR,
        LOGS_DIR / "batch",
    ):
        d.mkdir(parents=True, exist_ok=True)


def archive_path(video_id: str, ext: str = "mp4") -> Path:
    return ARCHIVE_DIR / f"{video_id}.{ext}"


def transcript_path(video_id: str) -> Path:
    return TRANSCRIPTS_DIR / f"{video_id}.json"


def segments_path(video_id: str) -> Path:
    return SEGMENTS_DIR / f"{video_id}.json"


def draft_path(draft_id: int) -> Path:
    return DRAFTS_DIR / f"{draft_id}.json"


def output_path(draft_id: int, ext: str = "mp4") -> Path:
    return OUTPUTS_DIR / f"draft_{draft_id}.{ext}"
