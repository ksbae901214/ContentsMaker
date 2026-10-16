"""데이터 산출물 정리 — 보수적 보관 정책 기반 스캔/삭제.

정책 (Feature 026):
- ``temp`` / ``tmp``: 임시 파일 — 24시간 경과 시 삭제 대상
- 중간산출물 (``images`` / ``videos`` / ``audio`` / ``natv_clips``):
  keep_days(기본 30일) 경과 시 삭제 대상
- 프로젝트 폴더 (``political_pro/*`` / ``info_v1/*``): 폴더 안 가장 최근 파일이
  project_keep_days(기본 7일) 지나면 완성본 mp4(최신 1개)·그 썸네일·텍스트
  (.md/.txt/.json)만 남기고 소스·씬 클립·TTS·하위 폴더를 삭제. ``_`` 로 시작하는
  폴더(채널 자산 등)는 건드리지 않음
- 그 외 디렉토리(``outputs`` / ``raw`` / ``scripts`` / ``tts_cache`` 등)는
  스캔 자체를 하지 않으므로 절대 삭제되지 않음

사용 흐름: ``scan_cleanup_targets()`` (dry-run, 부작용 없음) →
사용자 확인 후 ``execute_cleanup()`` (실제 삭제).
"""
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# 삭제 대상 카테고리 — 여기 없는 디렉토리는 절대 건드리지 않는다.
TEMP_DIR_NAMES = ("temp", "tmp")
INTERMEDIATE_DIR_NAMES = ("images", "videos", "audio", "natv_clips")

PROJECT_PARENT_DIR_NAMES = ("political_pro", "info_v1")
PROJECT_KEEP_SUFFIXES = (".md", ".txt", ".json")
_NON_FINAL_VIDEO_PREFIXES = ("scene_", "src_")

DEFAULT_TEMP_MAX_AGE_HOURS = 24
DEFAULT_KEEP_DAYS = 30
DEFAULT_PROJECT_KEEP_DAYS = 7

_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class CleanupTarget:
    """삭제 대상 파일 1개."""

    path: Path
    size_bytes: int
    age_days: float
    category: str  # "temp" | "intermediate" | "project"


@dataclass(frozen=True)
class CleanupReport:
    """스캔 결과 — 삭제하지 않고 대상만 나열한다."""

    targets: tuple[CleanupTarget, ...]
    total_bytes: int


@dataclass(frozen=True)
class CleanupResult:
    """실제 삭제 결과."""

    deleted: tuple[Path, ...]
    freed_bytes: int
    errors: tuple[str, ...]


def _scan_dir(
    base: Path, category: str, max_age_seconds: float, now: float
) -> list[CleanupTarget]:
    if not base.is_dir():
        return []
    targets: list[CleanupTarget] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            logger.warning("stat 실패, 건너뜀: %s (%s)", path, exc)
            continue
        age_seconds = now - stat.st_mtime
        if age_seconds <= max_age_seconds:
            continue
        targets.append(
            CleanupTarget(
                path=path,
                size_bytes=stat.st_size,
                age_days=age_seconds / _SECONDS_PER_DAY,
                category=category,
            )
        )
    return targets


def _list_files(base: Path) -> list[tuple[Path, int, float]]:
    """(path, size, mtime) 목록 — 심볼릭 링크·stat 실패는 제외."""
    files: list[tuple[Path, int, float]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            logger.warning("stat 실패, 건너뜀: %s (%s)", path, exc)
            continue
        files.append((path, stat.st_size, stat.st_mtime))
    return files


def _project_keep_set(root: Path, files: list[tuple[Path, int, float]]) -> set[Path]:
    """프로젝트 폴더에서 남길 파일 — 최신 완성본 mp4 + 썸네일 + 최상위 텍스트."""
    top = [(p, m) for p, _, m in files if p.parent == root]
    keep = {p for p, _ in top if p.suffix.lower() in PROJECT_KEEP_SUFFIXES}
    finals = [
        (p, m) for p, m in top
        if p.suffix.lower() == ".mp4" and not p.name.startswith(_NON_FINAL_VIDEO_PREFIXES)
    ]
    if finals:
        latest = max(finals, key=lambda pm: pm[1])[0]
        keep |= {latest, root / f"{latest.stem}.thumb.png"}
    return keep


def _scan_projects(
    parent: Path, max_age_seconds: float, now: float
) -> list[CleanupTarget]:
    if not parent.is_dir():
        return []
    targets: list[CleanupTarget] = []
    for root in sorted(parent.iterdir()):
        if not root.is_dir() or root.is_symlink() or root.name.startswith(("_", ".")):
            continue
        files = _list_files(root)
        if not files:
            continue
        age_seconds = now - max(m for _, _, m in files)
        if age_seconds <= max_age_seconds:
            continue
        keep = _project_keep_set(root, files)
        targets.extend(
            CleanupTarget(
                path=p,
                size_bytes=size,
                age_days=age_seconds / _SECONDS_PER_DAY,
                category="project",
            )
            for p, size, _ in files
            if p not in keep
        )
    return targets


def scan_cleanup_targets(
    data_dir: Path,
    *,
    now: float | None = None,
    temp_max_age_hours: float = DEFAULT_TEMP_MAX_AGE_HOURS,
    keep_days: float = DEFAULT_KEEP_DAYS,
    project_keep_days: float = DEFAULT_PROJECT_KEEP_DAYS,
) -> CleanupReport:
    """삭제 대상 파일을 스캔한다 (부작용 없음, dry-run).

    Args:
        data_dir: 프로젝트 data/ 디렉토리
        now: 기준 시각 (epoch seconds). 미지정 시 현재 시각.
        temp_max_age_hours: temp/tmp 보관 시간 (기본 24시간)
        keep_days: 중간산출물 보관 일수 (기본 30일)
        project_keep_days: 프로젝트 폴더 보관 일수 (기본 7일, 마지막 작업 기준)
    """
    if now is None:
        now = time.time()

    targets: list[CleanupTarget] = []
    for name in TEMP_DIR_NAMES:
        targets.extend(
            _scan_dir(
                data_dir / name, "temp", temp_max_age_hours * _SECONDS_PER_HOUR, now
            )
        )
    for name in INTERMEDIATE_DIR_NAMES:
        targets.extend(
            _scan_dir(
                data_dir / name,
                "intermediate",
                keep_days * _SECONDS_PER_DAY,
                now,
            )
        )
    for name in PROJECT_PARENT_DIR_NAMES:
        targets.extend(
            _scan_projects(data_dir / name, project_keep_days * _SECONDS_PER_DAY, now)
        )

    return CleanupReport(
        targets=tuple(targets),
        total_bytes=sum(t.size_bytes for t in targets),
    )


def _remove_empty_parents(directory: Path) -> None:
    """비워진 폴더를 프로젝트 상위(political_pro 등) 직전까지 위로 올라가며 지운다."""
    while directory.name and directory.parent.name and (
        directory.name not in PROJECT_PARENT_DIR_NAMES
    ):
        try:
            directory.rmdir()  # 비어 있지 않으면 OSError — 거기서 멈춘다
        except OSError:
            return
        directory = directory.parent


def execute_cleanup(report: CleanupReport) -> CleanupResult:
    """스캔된 대상 파일들을 실제로 삭제한다.

    이미 사라진 파일은 조용히 건너뛰고, 그 외 실패는 errors에 수집한다
    (한 파일의 실패가 전체 정리를 중단시키지 않도록).
    """
    deleted: list[Path] = []
    errors: list[str] = []
    freed = 0
    for target in report.targets:
        try:
            target.path.unlink()
        except FileNotFoundError:
            continue  # 스캔 이후 외부에서 이미 삭제됨 — 집계 제외
        except OSError as exc:
            logger.error("삭제 실패: %s (%s)", target.path, exc)
            errors.append(f"{target.path}: {exc}")
            continue
        deleted.append(target.path)
        freed += target.size_bytes
        if target.category == "project":
            _remove_empty_parents(target.path.parent)

    return CleanupResult(
        deleted=tuple(deleted), freed_bytes=freed, errors=tuple(errors)
    )
