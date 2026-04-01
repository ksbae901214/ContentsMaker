"""Seedance 2.0 video generator implementation.

Generates AI video clips via Seedance 2.0 API.
Requires SEEDANCE_API_KEY environment variable.
"""
from __future__ import annotations

import logging
import os

from src.video_gen.base import VideoGeneratorBase, VideoResult, VideoStatus

logger = logging.getLogger(__name__)

SEEDANCE_COSTS = {
    "720p": 0.05,   # per 5-second clip
    "1080p": 0.25,
}


class SeedanceError(Exception):
    """Raised when Seedance API call fails."""


class SeedanceGenerator(VideoGeneratorBase):
    """Seedance 2.0 AI video generation."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("SEEDANCE_API_KEY", "")
        if not self.api_key:
            logger.warning("SEEDANCE_API_KEY not set — video generation disabled")

    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
    ) -> str:
        if not self.api_key:
            raise SeedanceError(
                "SEEDANCE_API_KEY가 설정되지 않았습니다. "
                ".env.local에 SEEDANCE_API_KEY를 추가하세요."
            )

        # TODO: Implement actual Seedance API call
        # POST /generate with prompt, duration, resolution, source_image
        # Returns task_id
        raise SeedanceError("Seedance API 통합 미구현 — API 키 설정 후 구현 예정")

    async def get_status(self, task_id: str) -> VideoStatus:
        if not self.api_key:
            raise SeedanceError("SEEDANCE_API_KEY not set")

        # TODO: GET /task/{task_id}
        raise SeedanceError("Seedance API 통합 미구현")

    async def download(self, task_id: str, output_path: str) -> VideoResult:
        if not self.api_key:
            raise SeedanceError("SEEDANCE_API_KEY not set")

        # TODO: GET /task/{task_id}/download
        raise SeedanceError("Seedance API 통합 미구현")

    def estimate_cost(
        self,
        duration: float = 5.0,
        resolution: str = "720p",
    ) -> float:
        base = SEEDANCE_COSTS.get(resolution, SEEDANCE_COSTS["720p"])
        return base * (duration / 5.0)
