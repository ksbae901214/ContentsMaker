"""Abstract base class for AI video generators."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
