"""Abstract base class for AI video generators."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoResult:
    path: str
    duration_ms: int
    resolution: str
    cost_usd: float
    source_image: str | None
    prompt: str


@dataclass(frozen=True)
class VideoStatus:
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 - 1.0
    error: str | None = None
    result: VideoResult | None = None


class VideoGenerationError(Exception):
    """Raised when video generation fails."""


class VideoGeneratorBase(ABC):
    """Abstract interface for AI video clip generation."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
    ) -> str:
        """Start video generation. Returns task_id."""

    @abstractmethod
    async def get_status(self, task_id: str) -> VideoStatus:
        """Check generation status."""

    @abstractmethod
    async def download(self, task_id: str, output_path: str) -> VideoResult:
        """Download completed video to local path."""

    @abstractmethod
    def estimate_cost(
        self,
        duration: float = 5.0,
        resolution: str = "720p",
    ) -> float:
        """Estimate cost in USD for a single clip."""

    async def generate_and_wait(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
        output_path: str | None = None,
        poll_interval: float = 10.0,
        max_wait: float = 600.0,
    ) -> VideoResult:
        """Generate a video and wait for completion.

        Orchestrates the full flow: generate -> poll status -> download.
        Like ordering food at a restaurant and waiting for the bell to ring,
        this method submits the job, checks back periodically, and picks up
        the result when it is ready.

        Args:
            prompt: Text prompt describing the desired video.
            duration: Clip duration in seconds.
            resolution: Target resolution (e.g. "720p", "1080p").
            source_image: Optional source image path for image-to-video.
            output_path: Local path to save the downloaded video.
            poll_interval: Seconds between status checks.
            max_wait: Maximum seconds to wait before timing out.

        Returns:
            VideoResult with the downloaded file path and metadata.

        Raises:
            VideoGenerationError: On timeout or generation failure.
        """
        task_id = await self.generate(
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            source_image=source_image,
        )
        logger.info("Video generation started: task_id=%s", task_id)

        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.get_status(task_id)

            if status.status == "completed":
                logger.info("Video generation completed: task_id=%s", task_id)
                download_path = output_path or f"{task_id}.mp4"
                return await self.download(task_id, download_path)

            if status.status == "failed":
                error_msg = status.error or "Unknown error"
                raise VideoGenerationError(
                    f"Video generation failed (task_id={task_id}): {error_msg}"
                )

            logger.info(
                "Video generation in progress: task_id=%s, progress=%.0f%%",
                task_id, status.progress * 100,
            )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise VideoGenerationError(
            f"Video generation timeout: task_id={task_id}, "
            f"waited {max_wait}s (max_wait={max_wait}s)"
        )
