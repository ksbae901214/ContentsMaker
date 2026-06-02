"""Seedance 2.0 video generator implementation.

Generates AI video clips via Seedance 2.0 API.
Requires SEEDANCE_API_KEY environment variable.

Think of this as a remote video studio: you submit a scene description,
the studio works on it, and you pick up the finished clip when it is ready.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

from src.video_gen.base import (
    VideoGenerationError,
    VideoGeneratorBase,
    VideoResult,
    VideoStatus,
)

logger = logging.getLogger(__name__)

SEEDANCE_COSTS = {
    "720p": 0.05,   # per 5-second clip
    "1080p": 0.25,
}

_DEFAULT_API_BASE = "https://api.seedance.ai/v1"


class SeedanceError(VideoGenerationError):
    """Raised when Seedance API call fails."""


class SeedanceGenerator(VideoGeneratorBase):
    """Seedance 2.0 AI video generation."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("SEEDANCE_API_KEY", "")
        self.api_base = os.environ.get("SEEDANCE_API_BASE", _DEFAULT_API_BASE)
        self._client: httpx.AsyncClient | None = None

        if not self.api_key:
            logger.warning("SEEDANCE_API_KEY not set — video generation disabled")

    def _ensure_client(self) -> httpx.AsyncClient:
        """Return the httpx client, creating one lazily if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    def _require_api_key(self) -> None:
        """Raise if the API key is missing."""
        if not self.api_key:
            raise SeedanceError(
                "SEEDANCE_API_KEY가 설정되지 않았습니다. "
                ".env.local에 SEEDANCE_API_KEY를 추가하세요."
            )

    async def generate(
        self,
        prompt: str,
        duration: float = 5.0,
        resolution: str = "720p",
        source_image: str | None = None,
    ) -> str:
        """Start video generation via Seedance API. Returns task_id."""
        self._require_api_key()
        client = self._ensure_client()

        payload = {
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
        }
        if source_image is not None:
            payload = {**payload, "source_image": source_image}

        logger.info(
            "Seedance generate: prompt=%.60s, duration=%.1fs, resolution=%s",
            prompt, duration, resolution,
        )

        try:
            response = await client.post("/generate", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SeedanceError(
                f"Seedance API 요청 실패 (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise SeedanceError(
                f"Seedance API 연결 실패: {exc}"
            ) from exc

        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            raise SeedanceError(
                f"Seedance API 응답에 task_id가 없습니다: {data}"
            )

        logger.info("Seedance task created: %s", task_id)
        return task_id

    async def get_status(self, task_id: str) -> VideoStatus:
        """Check generation status for a given task."""
        self._require_api_key()
        client = self._ensure_client()

        try:
            response = await client.get(f"/tasks/{task_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SeedanceError(
                f"Seedance 상태 조회 실패 (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise SeedanceError(
                f"Seedance API 연결 실패: {exc}"
            ) from exc

        data = response.json()
        return VideoStatus(
            task_id=data.get("task_id", task_id),
            status=data.get("status", "pending"),
            progress=float(data.get("progress", 0.0)),
            error=data.get("error"),
        )

    async def download(self, task_id: str, output_path: str) -> VideoResult:
        """Download completed video to a local file."""
        self._require_api_key()
        client = self._ensure_client()

        # First get task info to find the download URL and metadata
        try:
            info_response = await client.get(f"/tasks/{task_id}")
            info_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SeedanceError(
                f"Seedance 태스크 조회 실패 (HTTP {exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise SeedanceError(
                f"Seedance API 연결 실패: {exc}"
            ) from exc

        info = info_response.json()
        download_url = info.get("download_url")
        if not download_url:
            raise SeedanceError(
                f"다운로드 URL이 없습니다 (task_id={task_id}). "
                f"상태: {info.get('status')}"
            )

        # Stream download the video file
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(out, "wb") as f:
                    async for chunk in stream.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
        except httpx.HTTPStatusError as exc:
            raise SeedanceError(
                f"Seedance 다운로드 실패 (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.RequestError as exc:
            raise SeedanceError(
                f"Seedance 다운로드 연결 실패: {exc}"
            ) from exc

        logger.info("Video downloaded: %s", output_path)

        return VideoResult(
            path=output_path,
            duration_ms=int(info.get("duration_ms", 5000)),
            resolution=info.get("resolution", "720p"),
            cost_usd=float(info.get("cost_usd", 0.0)),
            source_image=info.get("source_image"),
            prompt=info.get("prompt", ""),
        )

    def estimate_cost(
        self,
        duration: float = 5.0,
        resolution: str = "720p",
    ) -> float:
        """Estimate cost for a clip. Scales linearly with duration."""
        base = SEEDANCE_COSTS.get(resolution, SEEDANCE_COSTS["720p"])
        return base * (duration / 5.0)
