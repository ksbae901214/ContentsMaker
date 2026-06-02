"""JSON Lines 로거 for 파이프라인·배치 작업.

파일 경로: data/dem_shorts/logs/batch/{date}_{job}.log
포맷: 한 줄당 JSON 객체 (batch-jobs.md 모니터링 섹션 참조)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

_LOG_ROOT = Path("data/dem_shorts/logs/batch")


def log_event(job: str, status: str, **extra: Any) -> None:
    """Append a JSON Lines event to the job's log file.

    Args:
        job: Job name (e.g., "poll-natv", "ranking-batch")
        status: Event status (e.g., "started", "done", "failed")
        **extra: Additional fields merged into the JSON record.
    """
    _LOG_ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = _LOG_ROOT / f"{now.strftime('%Y%m%d')}_{job}.log"
    record = {
        "ts": now.isoformat(timespec="seconds"),
        "job": job,
        "status": status,
        **extra,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_recent_events(job: str, limit: int = 100) -> list[dict]:
    """Read the last N events for a job across all date files (newest first)."""
    if not _LOG_ROOT.exists():
        return []
    files = sorted(_LOG_ROOT.glob(f"*_{job}.log"), reverse=True)
    events: list[dict] = []
    for f in files:
        for line in reversed(f.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(events) >= limit:
                return events
    return events
