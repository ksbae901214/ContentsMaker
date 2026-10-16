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


# ── 프로젝트 폴더 정리 (data/political_pro/*, data/info_v1/*) ──────────────
# 마지막 작업 후 7일이 지난 프로젝트는 완성본 mp4(최신 1개)·썸네일·텍스트만 남긴다.


def _project(data_dir: Path, name: str, age_days: float, now: float) -> Path:
    root = data_dir / "political_pro" / name
    _make_file(root / "20261001_100000_제목.mp4", age_days * DAY + 60, now)  # 이전 렌더
    _make_file(root / "20261001_100000_제목.thumb.png", age_days * DAY + 60, now)
    _make_file(root / "20261001_110000_제목.mp4", age_days * DAY, now)  # 최신 렌더
    _make_file(root / "20261001_110000_제목.thumb.png", age_days * DAY, now)
    _make_file(root / "20261001_110000_제목.mp3", age_days * DAY, now)
    _make_file(root / "20261001_110000_제목.timing.json", age_days * DAY, now)
    _make_file(root / "scene_1_00.mp4", age_days * DAY, now)
    _make_file(root / "src_news.mp4", age_days * DAY, now)
    _make_file(root / "src_news.title.txt", age_days * DAY, now)
    _make_file(root / "upload_package.md", age_days * DAY, now)
    _make_file(root / "_verify" / "f1.png", age_days * DAY, now)
    _make_file(root / "thumb_candidates" / "c.png", age_days * DAY, now)
    return root


def test_old_project_keeps_only_final_video_and_text(data_dir: Path):
    now = time.time()
    root = _project(data_dir, "20261001_topic_v2_2", age_days=8, now=now)

    targeted = {t.path for t in scan_cleanup_targets(data_dir, now=now).targets}

    kept = {
        root / "20261001_110000_제목.mp4",
        root / "20261001_110000_제목.thumb.png",
        root / "20261001_110000_제목.timing.json",
        root / "src_news.title.txt",
        root / "upload_package.md",
    }
    removed = {
        root / "20261001_100000_제목.mp4",
        root / "20261001_100000_제목.thumb.png",
        root / "20261001_110000_제목.mp3",
        root / "scene_1_00.mp4",
        root / "src_news.mp4",
        root / "_verify" / "f1.png",
        root / "thumb_candidates" / "c.png",
    }
    assert removed <= targeted
    assert not (kept & targeted)


def test_recent_project_untouched(data_dir: Path):
    now = time.time()
    _project(data_dir, "20261014_topic_v5", age_days=3, now=now)

    report = scan_cleanup_targets(data_dir, now=now)

    assert report.targets == ()


def test_project_age_uses_newest_file(data_dir: Path):
    """오래된 파일이 있어도 최근에 재렌더한 프로젝트는 건드리지 않는다."""
    now = time.time()
    root = _project(data_dir, "20261001_rerender", age_days=20, now=now)
    _make_file(root / "20261016_090000_제목.mp4", 1 * DAY, now)

    report = scan_cleanup_targets(data_dir, now=now)

    assert report.targets == ()


def test_underscore_dirs_and_info_v1_handled(data_dir: Path):
    now = time.time()
    channel = _make_file(data_dir / "info_v1" / "_channel" / "logo.png", 90 * DAY, now)
    info = data_dir / "info_v1" / "octopus"
    final = _make_file(info / "octopus.mp4", 10 * DAY, now)
    img = _make_file(info / "images" / "01.png", 10 * DAY, now)
    tts = _make_file(info / "tts_raw.mp3", 10 * DAY, now)

    targeted = {t.path for t in scan_cleanup_targets(data_dir, now=now).targets}

    assert channel not in targeted
    assert final not in targeted
    assert {img, tts} <= targeted


def test_project_keep_days_parameter(data_dir: Path):
    now = time.time()
    _project(data_dir, "20261010_topic", age_days=4, now=now)

    report = scan_cleanup_targets(data_dir, now=now, project_keep_days=3)

    assert report.targets != ()


def test_execute_removes_emptied_project_subdirs(data_dir: Path):
    now = time.time()
    root = _project(data_dir, "20261001_topic", age_days=8, now=now)
    clips = data_dir / "political_pro" / "topic_123_clips"
    _make_file(clips / "scenes" / "s.mp4", 30 * DAY, now)

    execute_cleanup(scan_cleanup_targets(data_dir, now=now))

    assert not (root / "_verify").exists()
    assert not (root / "thumb_candidates").exists()
    assert (root / "20261001_110000_제목.mp4").exists()
    assert not clips.exists()
    assert (data_dir / "political_pro").is_dir()
