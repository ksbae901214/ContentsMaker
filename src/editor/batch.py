"""Batch processing — sequential multi-job video generation.

All functions return new objects without mutating the input.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchJob:
    id: str
    input_type: str  # url, text, file
    input_data: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 - 1.0
    project_id: str | None = None
    error: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "input_type": self.input_type,
            "input_data": self.input_data,
            "status": self.status,
            "progress": self.progress,
            "project_id": self.project_id,
            "error": self.error,
            "created_at": self.created_at,
        }


def create_batch_jobs(items: list[dict]) -> list[BatchJob]:
    """Create batch jobs from input items."""
    now = datetime.now().isoformat()
    return [
        BatchJob(
            id=str(uuid4())[:8],
            input_type=item.get("input_type", "text"),
            input_data=item.get("input_data", ""),
            status="pending",
            progress=0.0,
            created_at=now,
        )
        for item in items
        if item.get("input_data", "").strip()
    ]


def batch_processor(
    jobs: list[BatchJob],
    process_fn: Callable[[BatchJob], str | None],
    on_update: Callable[[BatchJob], None] | None = None,
) -> list[BatchJob]:
    """Process batch jobs sequentially with per-job error isolation.

    Args:
        jobs: List of BatchJob to process
        process_fn: Function that takes a job and returns project_id or None
        on_update: Optional callback for status updates

    Returns:
        List of updated BatchJob with final statuses
    """
    results: list[BatchJob] = []

    for i, job in enumerate(jobs):
        # Mark as processing
        processing = BatchJob(
            id=job.id,
            input_type=job.input_type,
            input_data=job.input_data,
            status="processing",
            progress=(i / len(jobs)),
            created_at=job.created_at,
        )
        if on_update:
            on_update(processing)

        try:
            project_id = process_fn(job)
            completed = BatchJob(
                id=job.id,
                input_type=job.input_type,
                input_data=job.input_data,
                status="completed",
                progress=((i + 1) / len(jobs)),
                project_id=project_id,
                created_at=job.created_at,
            )
            results.append(completed)
            if on_update:
                on_update(completed)
            logger.info("Batch job %s completed: %s", job.id, project_id)

        except Exception as e:
            failed = BatchJob(
                id=job.id,
                input_type=job.input_type,
                input_data=job.input_data,
                status="failed",
                progress=((i + 1) / len(jobs)),
                error=str(e),
                created_at=job.created_at,
            )
            results.append(failed)
            if on_update:
                on_update(failed)
            logger.warning("Batch job %s failed: %s", job.id, e)

    return results
