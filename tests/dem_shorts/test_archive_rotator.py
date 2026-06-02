"""T119: 아카이브 순환 배치 테스트 (B-06).

- 90일 (기본) 이상된 source_videos 의 download_path 파일을 콜드 스토리지로 이동
- DB의 download_path 갱신 + status='archived'
- 이미 콜드 디렉토리에 있는 파일은 skip
- dry_run 은 파일/DB 변경 없음
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, init_db


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "state.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def _write_dummy(path: Path, size_bytes: int = 1024) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size_bytes)
    return path


def _add_video(
    conn,
    video_id: str,
    *,
    published_at: datetime,
    download_path: str | None,
    status: str = "ready",
):
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO source_videos
          (video_id, title, published_at, duration_sec, session_type,
           download_path, status, created_at, updated_at)
        VALUES (?, 't', ?, 600, 'committee', ?, ?, ?, ?)
        """,
        (video_id, published_at.isoformat(), download_path, status, now, now),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# select_targets
# ---------------------------------------------------------------------------


def test_select_targets_picks_old_videos(db, tmp_path):
    from src.dem_shorts.archive_rotator import select_targets

    now_dt = datetime.now(timezone.utc)
    archive = tmp_path / "archive"
    old_path = _write_dummy(archive / "old.mp4")
    new_path = _write_dummy(archive / "new.mp4")

    _add_video(db, "old", published_at=now_dt - timedelta(days=120), download_path=str(old_path))
    _add_video(db, "new", published_at=now_dt - timedelta(days=10), download_path=str(new_path))

    targets = select_targets(db, days=90)
    ids = [t["video_id"] for t in targets]
    assert "old" in ids
    assert "new" not in ids


def test_select_targets_skips_videos_without_download_path(db):
    from src.dem_shorts.archive_rotator import select_targets

    now_dt = datetime.now(timezone.utc)
    _add_video(db, "v1", published_at=now_dt - timedelta(days=100), download_path=None)
    targets = select_targets(db, days=90)
    assert all(t["video_id"] != "v1" for t in targets)


def test_select_targets_skips_excluded_status(db, tmp_path):
    from src.dem_shorts.archive_rotator import select_targets

    now_dt = datetime.now(timezone.utc)
    p = _write_dummy(tmp_path / "x.mp4")
    _add_video(
        db, "ex", published_at=now_dt - timedelta(days=200),
        download_path=str(p), status="excluded",
    )
    targets = select_targets(db, days=90)
    assert all(t["video_id"] != "ex" for t in targets)


# ---------------------------------------------------------------------------
# rotate_archive
# ---------------------------------------------------------------------------


def test_rotate_moves_file_and_updates_db(db, tmp_path):
    from src.dem_shorts.archive_rotator import rotate_archive

    now_dt = datetime.now(timezone.utc)
    archive = tmp_path / "archive"
    cold = tmp_path / "cold"
    src = _write_dummy(archive / "old.mp4", size_bytes=2048)

    _add_video(db, "old", published_at=now_dt - timedelta(days=120), download_path=str(src))

    summary = rotate_archive(db, days=90, cold_dir=cold)
    assert summary["rotated"] == 1
    assert summary["skipped"] == 0

    # 원본은 사라지고 콜드에 동일 사이즈 파일
    assert not src.exists()
    moved = cold / "old.mp4"
    assert moved.exists()
    assert moved.stat().st_size == 2048

    row = db.execute(
        "SELECT download_path, status FROM source_videos WHERE video_id='old'"
    ).fetchone()
    assert row["download_path"] == str(moved)
    assert row["status"] == "archived"


def test_rotate_skips_if_file_already_under_cold(db, tmp_path):
    """이미 콜드 디렉토리 하위에 있는 파일은 재이동 안 함."""
    from src.dem_shorts.archive_rotator import rotate_archive

    now_dt = datetime.now(timezone.utc)
    cold = tmp_path / "cold"
    already = _write_dummy(cold / "already.mp4")

    _add_video(
        db, "already", published_at=now_dt - timedelta(days=200),
        download_path=str(already), status="archived",
    )

    summary = rotate_archive(db, days=90, cold_dir=cold)
    assert summary["rotated"] == 0
    assert summary["skipped"] >= 1
    assert already.exists()


def test_rotate_dry_run_no_side_effects(db, tmp_path):
    from src.dem_shorts.archive_rotator import rotate_archive

    now_dt = datetime.now(timezone.utc)
    archive = tmp_path / "archive"
    cold = tmp_path / "cold"
    src = _write_dummy(archive / "old.mp4")

    _add_video(db, "old", published_at=now_dt - timedelta(days=120), download_path=str(src))

    summary = rotate_archive(db, days=90, cold_dir=cold, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["rotated"] == 1
    # 실제 파일/DB 변화 없음
    assert src.exists()
    assert not (cold / "old.mp4").exists()
    row = db.execute(
        "SELECT download_path FROM source_videos WHERE video_id='old'"
    ).fetchone()
    assert row["download_path"] == str(src)


def test_rotate_handles_missing_source_file(db, tmp_path):
    """download_path 가 DB에 있어도 실제 파일이 없으면 missing 으로 카운트."""
    from src.dem_shorts.archive_rotator import rotate_archive

    now_dt = datetime.now(timezone.utc)
    cold = tmp_path / "cold"
    fake = tmp_path / "archive" / "ghost.mp4"  # 존재하지 않음

    _add_video(
        db, "ghost", published_at=now_dt - timedelta(days=120), download_path=str(fake)
    )

    summary = rotate_archive(db, days=90, cold_dir=cold)
    assert summary["rotated"] == 0
    assert summary["missing"] == 1
