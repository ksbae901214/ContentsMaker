"""Tests for src/maintenance/cleanup.py — 데이터 정리 정책.

정책:
- temp/tmp: 24시간 경과 파일 삭제 대상
- 중간산출물(images/videos/audio/natv_clips): keep_days(기본 30일) 경과 파일 삭제 대상
- outputs/raw/scripts/tts_cache 등 나머지: 절대 건드리지 않음
- dry-run 기본 — execute_cleanup()을 호출해야만 실제 삭제
"""
import time
from pathlib import Path

import pytest

from src.maintenance.cleanup import (
    CleanupReport,
    execute_cleanup,
    scan_cleanup_targets,
)

HOUR = 3600
DAY = 86400


def _make_file(path: Path, age_seconds: float, now: float, size: int = 10) -> Path:
    """age_seconds 전에 수정된 것처럼 mtime을 조작한 파일 생성."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    mtime = now - age_seconds
    import os

    os.utime(path, (mtime, mtime))
    return path


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


def test_old_temp_file_is_targeted(data_dir: Path):
    now = time.time()
    old = _make_file(data_dir / "temp" / "old.mp4", age_seconds=25 * HOUR, now=now)
    fresh = _make_file(data_dir / "temp" / "fresh.mp4", age_seconds=1 * HOUR, now=now)

    report = scan_cleanup_targets(data_dir, now=now)

    targeted = {t.path for t in report.targets}
    assert old in targeted
    assert fresh not in targeted


def test_tmp_dir_also_covered(data_dir: Path):
    now = time.time()
    old = _make_file(data_dir / "tmp" / "stale.bin", age_seconds=48 * HOUR, now=now)

    report = scan_cleanup_targets(data_dir, now=now)

    assert old in {t.path for t in report.targets}


def test_old_intermediate_targeted_fresh_kept(data_dir: Path):
    now = time.time()
    old = _make_file(data_dir / "images" / "a.png", age_seconds=31 * DAY, now=now)
    recent = _make_file(data_dir / "videos" / "b.mp4", age_seconds=10 * DAY, now=now)

    report = scan_cleanup_targets(data_dir, now=now)

    targeted = {t.path for t in report.targets}
    assert old in targeted
    assert recent not in targeted


def test_keep_days_parameter_respected(data_dir: Path):
    now = time.time()
    f = _make_file(data_dir / "audio" / "v.mp3", age_seconds=10 * DAY, now=now)

    report = scan_cleanup_targets(data_dir, now=now, keep_days=7)

    assert f in {t.path for t in report.targets}


def test_protected_dirs_never_targeted(data_dir: Path):
    now = time.time()
    protected = [
        _make_file(data_dir / "outputs" / "final.mp4", age_seconds=400 * DAY, now=now),
        _make_file(data_dir / "raw" / "post.json", age_seconds=400 * DAY, now=now),
        _make_file(data_dir / "scripts" / "s.json", age_seconds=400 * DAY, now=now),
        _make_file(data_dir / "tts_cache" / "h.mp3", age_seconds=400 * DAY, now=now),
        _make_file(data_dir / "references" / "r.png", age_seconds=400 * DAY, now=now),
    ]

    report = scan_cleanup_targets(data_dir, now=now)

    targeted = {t.path for t in report.targets}
    for p in protected:
        assert p not in targeted, f"{p} must never be targeted"


def test_missing_dirs_are_fine(data_dir: Path):
    data_dir.mkdir(parents=True)
    report = scan_cleanup_targets(data_dir, now=time.time())
    assert report.targets == ()
    assert report.total_bytes == 0


def test_total_bytes_sums_target_sizes(data_dir: Path):
    now = time.time()
    _make_file(data_dir / "temp" / "a.bin", age_seconds=30 * HOUR, now=now, size=100)
    _make_file(data_dir / "temp" / "b.bin", age_seconds=30 * HOUR, now=now, size=50)

    report = scan_cleanup_targets(data_dir, now=now)

    assert report.total_bytes == 150


def test_scan_does_not_delete(data_dir: Path):
    now = time.time()
    old = _make_file(data_dir / "temp" / "old.bin", age_seconds=30 * HOUR, now=now)

    scan_cleanup_targets(data_dir, now=now)

    assert old.exists(), "scan은 dry-run — 파일을 삭제하면 안 됨"


def test_execute_deletes_only_targets(data_dir: Path):
    now = time.time()
    old = _make_file(data_dir / "temp" / "old.bin", age_seconds=30 * HOUR, now=now, size=20)
    keep = _make_file(data_dir / "temp" / "fresh.bin", age_seconds=1 * HOUR, now=now)
    out = _make_file(data_dir / "outputs" / "f.mp4", age_seconds=400 * DAY, now=now)

    report = scan_cleanup_targets(data_dir, now=now)
    result = execute_cleanup(report)

    assert not old.exists()
    assert keep.exists()
    assert out.exists()
    assert result.freed_bytes == 20
    assert old in result.deleted


def test_execute_handles_already_deleted_file(data_dir: Path):
    now = time.time()
    old = _make_file(data_dir / "temp" / "old.bin", age_seconds=30 * HOUR, now=now)
    report = scan_cleanup_targets(data_dir, now=now)
    old.unlink()  # 외부에서 먼저 삭제된 상황

    result = execute_cleanup(report)

    assert result.deleted == ()
    assert result.freed_bytes == 0


def test_report_is_immutable(data_dir: Path):
    report = CleanupReport(targets=(), total_bytes=0)
    with pytest.raises(Exception):
        report.total_bytes = 1  # type: ignore[misc]
