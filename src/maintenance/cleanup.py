"""데이터 산출물 정리 — 보수적 보관 정책 기반 스캔/삭제.

정책 (Feature 026):
- ``temp`` / ``tmp``: 임시 파일 — 24시간 경과 시 삭제 대상
- 중간산출물 (``images`` / ``videos`` / ``audio`` / ``natv_clips``):
  keep_days(기본 30일) 경과 시 삭제 대상
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

DEFAULT_TEMP_MAX_AGE_HOURS = 24
DEFAULT_KEEP_DAYS = 30

_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class CleanupTarget:
    """삭제 대상 파일 1개."""

    path: Path
    size_bytes: int
    age_days: float
    category: str  # "temp" | "intermediate"


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


def scan_cleanup_targets(
    data_dir: Path,
    *,
    now: float | None = None,
    temp_max_age_hours: float = DEFAULT_TEMP_MAX_AGE_HOURS,
    keep_days: float = DEFAULT_KEEP_DAYS,
) -> CleanupReport:
    """삭제 대상 파일을 스캔한다 (부작용 없음, dry-run).

    Args:
        data_dir: 프로젝트 data/ 디렉토리
        now: 기준 시각 (epoch seconds). 미지정 시 현재 시각.
        temp_max_age_hours: temp/tmp 보관 시간 (기본 24시간)
        keep_days: 중간산출물 보관 일수 (기본 30일)
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

    return CleanupReport(
        targets=tuple(targets),
        total_bytes=sum(t.size_bytes for t in targets),
    )


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

    return CleanupResult(
        deleted=tuple(deleted), freed_bytes=freed, errors=tuple(errors)
    )
