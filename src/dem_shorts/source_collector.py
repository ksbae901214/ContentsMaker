"""NATV 소스 영상 수집 파이프라인.

책임:
- T030 parse_session_type(): 제목·설명에서 세션 타입 자동 분류 (FR-003)
- T031 poll_natv(): 채널 폴링 + DB upsert + 6h 초과 제외 (FR-001, FR-002)
- T032 download_video(): yt-dlp로 원본 다운로드 (FR-002)
- T034 update_exclusion(): dem_score=0 인 영상 excluded 처리 (FR-005)

Output: `source_videos` 테이블 + `data/dem_shorts/archive/{video_id}.mp4`
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.dem_shorts.config import MAX_VIDEO_DURATION_SEC
from src.dem_shorts.utils.paths import archive_path

logger = logging.getLogger(__name__)


# ─────────────── Session type classification (FR-003) ───────────────

_SESSION_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    # Order matters: more specific first
    ("audit", ("국정감사", "국감")),
    ("hearing", ("청문회",)),
    ("committee", ("상임위원회", "위원회", "상임위", "법사위", "기재위", "환노위")),
    ("plenary", ("본회의",)),
    ("press", ("기자회견",)),
]


def parse_session_type(title: str, description: str) -> str:
    """영상 제목·설명에서 본회의/상임위/국감/청문회/기자회견/기타 분류.

    분류 기준 (우선순위 순):
        audit > hearing > committee > plenary > press > other
    """
    corpus = f"{title}\n{description}"
    for session_type, keywords in _SESSION_KEYWORDS:
        for kw in keywords:
            if kw in corpus:
                return session_type
    return "other"


# ─────────────── ISO8601 duration parsing ───────────────

_ISO_DURATION_RE = re.compile(
    r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$"
)


def parse_youtube_duration(iso: str) -> int:
    """YouTube API의 ISO 8601 duration을 초 단위로 변환.

    "PT1H30M" → 5400
    "PT45M30S" → 2730
    invalid → 0
    """
    if not iso:
        return 0
    m = _ISO_DURATION_RE.match(iso)
    if not m:
        return 0
    h = int(m.group("h") or 0)
    mn = int(m.group("m") or 0)
    s = int(m.group("s") or 0)
    return h * 3600 + mn * 60 + s


# ─────────────── Duration limit (FR-002) ───────────────


def _exceeds_duration_limit(duration_sec: int) -> bool:
    return duration_sec > MAX_VIDEO_DURATION_SEC


# ─────────────── NATV polling (FR-001) ───────────────


def poll_natv(conn, *, since_hours: int = 24, dry_run: bool = False) -> list[dict]:
    """NATV 채널 최근 N시간 신규 영상 감지 → source_videos upsert.

    Args:
        conn: sqlite3.Connection
        since_hours: 최근 N시간 (로깅·반환 필터용). 실제 폴링은 항상 최대 50개.
        dry_run: True → DB 저장 없이 감지된 신규 영상만 반환.

    Returns:
        신규 레코드 dict 리스트 (video_id, title, published_at, excluded_reason, dem_score=0).

    Raises:
        YoutubeQuotaExceeded, YoutubeApiError (upstream)
    """
    from src.dem_shorts.youtube_client import (
        list_recent_videos,
        resolve_channel_id,
    )

    channel_id = resolve_channel_id()
    videos = list_recent_videos(channel_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    new_records: list[dict] = []
    for v in videos:
        existing = conn.execute(
            "SELECT 1 FROM source_videos WHERE video_id = ?", (v.video_id,)
        ).fetchone()
        if existing:
            continue

        duration_sec = parse_youtube_duration(v.duration_iso)
        session_type = parse_session_type(v.title, v.description)

        if _exceeds_duration_limit(duration_sec):
            excluded_reason = "length_over_6h"
            status = "excluded"
        else:
            excluded_reason = None
            status = "new"

        record = {
            "video_id": v.video_id,
            "title": v.title,
            "description": v.description,
            "published_at": v.published_at,
            "duration_sec": duration_sec,
            "thumbnail_url": v.thumbnail_url,
            "session_type": session_type,
            "excluded_reason": excluded_reason,
            "status": status,
            "dem_score": 0.0,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        new_records.append(record)

        if dry_run:
            continue

        # migration 002 이후 target_perspective/perspective_score 컬럼 존재
        has_perspective_cols = any(
            r["name"] == "target_perspective"
            for r in conn.execute("PRAGMA table_info(source_videos)")
        )
        if has_perspective_cols:
            from src.dem_shorts.config import DEFAULT_PERSPECTIVE
            conn.execute(
                """
                INSERT INTO source_videos
                  (video_id, title, description, published_at, duration_sec,
                   thumbnail_url, session_type, dem_score, excluded_reason,
                   status, created_at, updated_at,
                   target_perspective, perspective_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["video_id"],
                    record["title"],
                    record["description"],
                    record["published_at"],
                    record["duration_sec"],
                    record["thumbnail_url"],
                    record["session_type"],
                    record["dem_score"],
                    record["excluded_reason"],
                    record["status"],
                    record["created_at"],
                    record["updated_at"],
                    DEFAULT_PERSPECTIVE,
                    record["dem_score"],  # 초기값: dem_score와 동일 (추후 재계산 시 분리)
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO source_videos
                  (video_id, title, description, published_at, duration_sec,
                   thumbnail_url, session_type, dem_score, excluded_reason,
                   status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["video_id"],
                    record["title"],
                    record["description"],
                    record["published_at"],
                    record["duration_sec"],
                    record["thumbnail_url"],
                    record["session_type"],
                    record["dem_score"],
                    record["excluded_reason"],
                    record["status"],
                    record["created_at"],
                    record["updated_at"],
                ),
            )
    if not dry_run:
        conn.commit()
    return new_records


# ─────────────── Video download (FR-002) ───────────────


class DownloadError(Exception):
    """yt-dlp 다운로드 실패."""


def download_video(video_id: str, *, output_dir: Path | None = None) -> Path:
    """yt-dlp로 영상 다운로드 → archive_path(video_id).

    1080p 우선, 실패 시 최선 화질로 폴백.
    재시도는 호출자(B-02 배치 워커)가 담당.

    Returns:
        다운로드된 파일 경로.

    Raises:
        DownloadError
    """
    out_path = (output_dir / f"{video_id}.mp4") if output_dir else archive_path(video_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_path),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except FileNotFoundError as exc:
        raise DownloadError(
            "yt-dlp not installed. Run: pip3 install yt-dlp"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DownloadError(f"yt-dlp timed out for {video_id}") from exc

    if result.returncode != 0:
        raise DownloadError(
            f"yt-dlp failed (exit {result.returncode}): {result.stderr[:300]}"
        )
    if not out_path.exists():
        raise DownloadError(f"yt-dlp finished but output missing: {out_path}")
    return out_path


# ─────────────── Exclusion update (FR-005) ───────────────


def update_exclusion(conn, video_id: str, *, reason: str) -> None:
    """단일 영상을 excluded 상태로 전환.

    reason은 모델 _EXCLUDED_REASONS enum 값이어야 함.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE source_videos
        SET status = 'excluded',
            excluded_reason = ?,
            updated_at = ?
        WHERE video_id = ?
        """,
        (reason, now_iso, video_id),
    )
    conn.commit()
