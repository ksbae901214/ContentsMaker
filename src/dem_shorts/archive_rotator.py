"""T119: 아카이브 순환 배치 (B-06).

3개월 이상된 source_videos 의 download_path 파일을 콜드 스토리지(외장 SSD 등)
로 이동하고 DB 의 download_path · status 를 갱신한다.

- cron: `0 3 * * 6` (매주 토 03:00)
- 명령: `python3 -m src.dem_shorts.cli archive-rotate [--days 90] [--cold-dir PATH]`
- 디스크 여유 100GB 미만 시 운영 측에서 외부 스크립트로 이 명령을 자동 트리거.

데이터 안전성:
- 새 위치로 안전하게 복사 후 원본 삭제 (`shutil.move`)
- 동일 파일명이 콜드에 이미 있으면 timestamp suffix 추가
- DB 변경은 파일 이동 성공 후에만 (실패 시 원본/DB 모두 그대로)
"""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_AGE_DAYS = 90
DEFAULT_COLD_DIR_ENV = "DEM_SHORTS_COLD_DIR"
DEFAULT_COLD_DIR = Path("data/dem_shorts/cold")
ROTATABLE_STATUSES = ("ready", "archived")


def resolve_cold_dir(cold_dir: Path | str | None = None) -> Path:
    """우선순위: 인자 → 환경변수 → 기본값."""
    if cold_dir:
        return Path(cold_dir)
    env = os.getenv(DEFAULT_COLD_DIR_ENV)
    if env:
        return Path(env)
    return DEFAULT_COLD_DIR


def select_targets(
    conn: sqlite3.Connection, *, days: int = DEFAULT_AGE_DAYS
) -> list[dict]:
    """`days` 일 이상된 영상 중 download_path 가 설정된 항목."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    placeholders = ",".join(["?"] * len(ROTATABLE_STATUSES))
    rows = conn.execute(
        f"""
        SELECT video_id, download_path, status, published_at
          FROM source_videos
         WHERE published_at < ?
           AND download_path IS NOT NULL
           AND download_path != ''
           AND status IN ({placeholders})
         ORDER BY published_at ASC
        """,
        (cutoff, *ROTATABLE_STATUSES),
    ).fetchall()
    return [dict(r) for r in rows]


def _is_under(path: Path, parent: Path) -> bool:
    """path 가 parent 디렉토리 하위에 있는지(이미 콜드) 검사."""
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except (ValueError, OSError):
        return False


def _unique_destination(cold_dir: Path, src: Path) -> Path:
    """동일 파일명이 이미 콜드에 있으면 `_YYYYMMDDHHMMSS` suffix 추가."""
    target = cold_dir / src.name
    if not target.exists():
        return target
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return cold_dir / f"{src.stem}_{stamp}{src.suffix}"


def _move_file(src: Path, cold_dir: Path) -> Path:
    cold_dir.mkdir(parents=True, exist_ok=True)
    dst = _unique_destination(cold_dir, src)
    shutil.move(str(src), str(dst))
    return dst


def rotate_archive(
    conn: sqlite3.Connection,
    *,
    days: int = DEFAULT_AGE_DAYS,
    cold_dir: Path | str | None = None,
    dry_run: bool = False,
) -> dict:
    """B-06 메인 진입점.

    Returns:
        {"rotated": int, "skipped": int, "missing": int, "failed": int, "dry_run": bool}
    """
    cold = resolve_cold_dir(cold_dir)
    targets = select_targets(conn, days=days)

    rotated = 0
    skipped = 0
    missing = 0
    failed = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for row in targets:
        src = Path(row["download_path"])

        # 이미 콜드 디렉토리 하위 → skip
        if _is_under(src, cold):
            skipped += 1
            continue

        if not src.exists():
            missing += 1
            logger.warning("missing source file: %s", src)
            continue

        if dry_run:
            rotated += 1
            continue

        try:
            dst = _move_file(src, cold)
        except OSError as exc:
            failed += 1
            logger.error("move failed: %s -> %s (%s)", src, cold, exc)
            continue

        try:
            conn.execute(
                """
                UPDATE source_videos
                   SET download_path=?, status='archived', updated_at=?
                 WHERE video_id=?
                """,
                (str(dst), now_iso, row["video_id"]),
            )
            rotated += 1
        except sqlite3.DatabaseError as exc:
            failed += 1
            logger.error("DB update failed for %s: %s", row["video_id"], exc)

    if not dry_run:
        conn.commit()

    summary = {
        "rotated": rotated,
        "skipped": skipped,
        "missing": missing,
        "failed": failed,
        "dry_run": dry_run,
        "cold_dir": str(cold),
    }
    logger.info("archive-rotate done %s", summary)
    return summary
