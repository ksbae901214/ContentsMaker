"""T118: YouTube 메트릭 갱신 배치 (B-05, FR-038 리포트 입력).

`uploaded_shorts` 테이블의 view_count/like_count/comment_count/metrics_updated_at
을 YouTube Data API v3 `videos.list`(part=statistics) 응답으로 주기 갱신한다.

정책:
- 업로드 24시간 이내는 "fresh" — 15분 주기 호출(운영)
- 그 외는 1시간 주기(기본 cron `0 * * * *`)
- API 응답에서 사라진 video_id 는 `is_taken_down=1` 로 마킹 (운영자 후속 대응)
- 쿼터 보호: 호출당 최대 50개 (videos.list 1회 호출 ≈ 3 unit)

cron: `0 * * * *` (B-05)
명령: `python3 -m src.dem_shorts.cli metrics-update [--limit 30] [--dry-run]`
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Iterable

from src.dem_shorts.config import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)

FRESH_WINDOW_HOURS = 24
DEFAULT_BATCH_LIMIT = 30
TAKEDOWN_REASON = "youtube_api_missing"


def is_fresh(
    uploaded_at: datetime,
    *,
    now: datetime | None = None,
    hours: int = FRESH_WINDOW_HOURS,
) -> bool:
    """업로드 후 `hours` 시간 이내면 True.

    운영 cron 은 fresh 구간만 더 잦게 갱신해 쿼터를 아낀다.
    """
    now = now or datetime.now(timezone.utc)
    if uploaded_at.tzinfo is None:
        uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
    return (now - uploaded_at) < timedelta(hours=hours)


# ---------------------------------------------------------------------------
# YouTube API 호출 (테스트에서 monkeypatch)
# ---------------------------------------------------------------------------


def fetch_videos_stats(
    video_ids: Iterable[str],
    *,
    api_key: str | None = None,
) -> dict[str, dict[str, int]]:
    """YouTube Data API v3 videos.list(part=statistics) 호출.

    Returns:
        {video_id: {"view_count", "like_count", "comment_count"}, ...}

    응답에 없는 video_id는 생략 — 호출자가 테이크다운으로 간주한다.
    """
    ids = [vid for vid in video_ids if vid]
    if not ids:
        return {}

    key = api_key or YOUTUBE_API_KEY
    if not key:
        logger.warning("YOUTUBE_API_KEY not configured; skipping metrics fetch")
        return {}

    try:
        from googleapiclient.discovery import build  # type: ignore
    except ImportError:  # pragma: no cover — runtime-only dep
        logger.warning(
            "google-api-python-client not installed; run pip install -r requirements-dem-shorts.txt"
        )
        return {}

    svc = build("youtube", "v3", developerKey=key)
    # videos.list 는 1회 호출당 최대 50 id 허용
    out: dict[str, dict[str, int]] = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        try:
            resp = svc.videos().list(
                id=",".join(chunk), part="statistics"
            ).execute()
        except Exception as exc:  # pragma: no cover — 네트워크 실패
            logger.error("videos.list failed: %s", exc)
            continue
        for item in resp.get("items", []):
            stats = item.get("statistics", {}) or {}
            out[item["id"]] = {
                "view_count": int(stats.get("viewCount") or 0),
                "like_count": int(stats.get("likeCount") or 0),
                "comment_count": int(stats.get("commentCount") or 0),
            }
    return out


# ---------------------------------------------------------------------------
# DB 조회 / 쓰기
# ---------------------------------------------------------------------------


def select_targets(
    conn: sqlite3.Connection,
    *,
    limit: int = DEFAULT_BATCH_LIMIT,
) -> list[dict]:
    """갱신 대상 uploaded_shorts 레코드.

    - `is_taken_down=0` (아직 살아 있는 영상)
    - `youtube_video_id` NOT NULL
    - 업로드 최신순 (fresh 우선)
    """
    rows = conn.execute(
        """
        SELECT id, draft_id, youtube_video_id, uploaded_at, metrics_updated_at
        FROM uploaded_shorts
        WHERE is_taken_down = 0
          AND youtube_video_id IS NOT NULL
          AND youtube_video_id != ''
        ORDER BY uploaded_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def _apply_stats(
    conn: sqlite3.Connection,
    row: dict,
    stats: dict[str, int],
    *,
    now_iso: str,
) -> None:
    conn.execute(
        """
        UPDATE uploaded_shorts
           SET view_count=?, like_count=?, comment_count=?, metrics_updated_at=?
         WHERE id=?
        """,
        (
            int(stats.get("view_count") or 0),
            int(stats.get("like_count") or 0),
            int(stats.get("comment_count") or 0),
            now_iso,
            row["id"],
        ),
    )


def _mark_takedown(
    conn: sqlite3.Connection, row: dict, *, now_iso: str, reason: str
) -> None:
    conn.execute(
        """
        UPDATE uploaded_shorts
           SET is_taken_down=1, takedown_reason=?, metrics_updated_at=?
         WHERE id=?
        """,
        (reason, now_iso, row["id"]),
    )


# ---------------------------------------------------------------------------
# 배치 진입점
# ---------------------------------------------------------------------------


def update_metrics(
    conn: sqlite3.Connection,
    *,
    limit: int = DEFAULT_BATCH_LIMIT,
    dry_run: bool = False,
) -> dict:
    """B-05: 업로드된 쇼츠의 조회수·좋아요·댓글 수를 갱신한다.

    Args:
        conn: SQLite connection.
        limit: 1회 배치에서 갱신할 최대 업로드 수. YouTube videos.list 는
               50 id/호출 이므로 쿼터가 넉넉하면 그대로 두면 된다.
        dry_run: True면 DB 변경 없이 결과만 반환.

    Returns:
        {"updated": int, "taken_down": int, "dry_run": bool}
    """
    targets = select_targets(conn, limit=limit)
    if not targets:
        return {"updated": 0, "taken_down": 0, "dry_run": dry_run}

    ids = [t["youtube_video_id"] for t in targets]
    stats_by_id = fetch_videos_stats(ids)

    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0
    taken_down = 0
    for row in targets:
        yid = row["youtube_video_id"]
        stats = stats_by_id.get(yid)
        if stats is None:
            taken_down += 1
            if not dry_run:
                _mark_takedown(conn, row, now_iso=now_iso, reason=TAKEDOWN_REASON)
            continue
        updated += 1
        if not dry_run:
            _apply_stats(conn, row, stats, now_iso=now_iso)

    if not dry_run:
        conn.commit()

    logger.info(
        "metrics-update done updated=%d taken_down=%d dry_run=%s",
        updated,
        taken_down,
        dry_run,
    )
    return {"updated": updated, "taken_down": taken_down, "dry_run": dry_run}
