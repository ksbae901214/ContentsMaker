"""Tests for Seedance video generator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.video_gen.base import VideoGenerationError, VideoResult, VideoStatus
from src.video_gen.seedance_gen import (
    SEEDANCE_COSTS,
    SeedanceError,
    SeedanceGenerator,
)


class TestEstimateCost:
    """estimate_cost should scale linearly by duration and use resolution-based pricing."""

    def test_720p_5s(self):
        gen = SeedanceGenerator.__new__(SeedanceGenerator)
        gen.api_key = "test-key"
        gen.api_base = "https://api.seedance.ai/v1"
        gen._client = None

        assert gen.estimate_cost(duration=5.0, resolution="720p") == 0.05

    def test_1080p_5s(self):
        gen = SeedanceGenerator.__new__(SeedanceGenerator)
        gen.api_key = "test-key"
        gen.api_base = "https://api.seedance.ai/v1"
        gen._client = None

        assert gen.estimate_cost(duration=5.0, resolution="1080p") == 0.25

    def test_720p_10s_doubles(self):
        gen = SeedanceGenerator.__new__(SeedanceGenerator)
        gen.api_key = "test-key"
        gen.api_base = "https://api.seedance.ai/v1"
        gen._client = None

        assert gen.estimate_cost(duration=10.0, resolution="720p") == 0.10

    def test_unknown_resolution_falls_back_to_720p(self):
        gen = SeedanceGenerator.__new__(SeedanceGenerator)
        gen.api_key = "test-key"
        gen.api_base = "https://api.seedance.ai/v1"
        gen._client = None

        assert gen.estimate_cost(duration=5.0, resolution="4k") == 0.05

    def test_costs_dict_values(self):
        assert SEEDANCE_COSTS == {"720p": 0.05, "1080p": 0.25}


class TestApiKeyMissing:
    """Operations should raise SeedanceError when API key is not set."""

    @patch.dict("os.environ", {}, clear=True)
    def test_generate_raises_without_api_key(self):
        gen = SeedanceGenerator()
        with pytest.raises(SeedanceError, match="SEEDANCE_API_KEY"):
            asyncio.get_event_loop().run_until_complete(
                gen.generate("test prompt")
            )

    @patch.dict("os.environ", {}, clear=True)
    def test_get_status_raises_without_api_key(self):
        gen = SeedanceGenerator()
        with pytest.raises(SeedanceError, match="SEEDANCE_API_KEY"):
            asyncio.get_event_loop().run_until_complete(
                gen.get_status("task-123")
            )

    @patch.dict("os.environ", {}, clear=True)
    def test_download_raises_without_api_key(self):
        gen = SeedanceGenerator()
        with pytest.raises(SeedanceError, match="SEEDANCE_API_KEY"):
            asyncio.get_event_loop().run_until_complete(
                gen.download("task-123", "/tmp/out.mp4")
            )


@pytest.mark.asyncio
class TestGenerate:
    """Test generate() API call."""

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_generate_returns_task_id(self):
        gen = SeedanceGenerator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task_id": "task-abc-123"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        gen._client = mock_client

        task_id = await gen.generate("a manga scene of a wedding")

        assert task_id == "task-abc-123"
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert "generate" in call_kwargs[0][0]

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_generate_with_source_image(self):
        gen = SeedanceGenerator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task_id": "task-img-456"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        gen._client = mock_client

        task_id = await gen.generate(
            "animate this image",
            source_image="/path/to/image.png",
        )

        assert task_id == "task-img-456"
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["source_image"] == "/path/to/image.png"


@pytest.mark.asyncio
class TestGetStatus:
    """Test get_status() polling."""

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_get_status_processing(self):
        gen = SeedanceGenerator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task_id": "task-abc",
            "status": "processing",
            "progress": 0.5,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        gen._client = mock_client

        status = await gen.get_status("task-abc")

        assert status.task_id == "task-abc"
        assert status.status == "processing"
        assert status.progress == 0.5
        assert status.result is None

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_get_status_completed(self):
        gen = SeedanceGenerator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task_id": "task-done",
            "status": "completed",
            "progress": 1.0,
            "download_url": "https://cdn.seedance.ai/videos/task-done.mp4",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        gen._client = mock_client

        status = await gen.get_status("task-done")

        assert status.status == "completed"
        assert status.progress == 1.0

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_get_status_failed(self):
        gen = SeedanceGenerator()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task_id": "task-fail",
            "status": "failed",
            "progress": 0.0,
            "error": "Content policy violation",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        gen._client = mock_client

        status = await gen.get_status("task-fail")

        assert status.status == "failed"
        assert status.error == "Content policy violation"


@pytest.mark.asyncio
class TestDownload:
    """Test download() video file saving."""

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_download_saves_file(self, tmp_path):
        gen = SeedanceGenerator()
        output_path = str(tmp_path / "scene_01.mp4")

        # Mock info response to get download URL and metadata
        info_response = MagicMock()
        info_response.status_code = 200
        info_response.json.return_value = {
            "task_id": "task-dl",
            "status": "completed",
            "progress": 1.0,
            "download_url": "https://cdn.seedance.ai/videos/task-dl.mp4",
            "duration_ms": 5000,
            "resolution": "720p",
            "cost_usd": 0.05,
            "prompt": "a manga scene",
        }
        info_response.raise_for_status = MagicMock()

        # Build an async context manager for client.stream()
        chunks = [b"fake video data chunk1", b"chunk2"]

        class _FakeStream:
            def __init__(self):
                self.status_code = 200

            def raise_for_status(self):
                pass

            async def aiter_bytes(self, chunk_size=65536):
                for c in chunks:
                    yield c

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=info_response)
        mock_client.stream = MagicMock(return_value=_FakeStream())
        gen._client = mock_client

        result = await gen.download("task-dl", output_path)

        assert isinstance(result, VideoResult)
        assert result.path == output_path
        assert result.duration_ms == 5000
        assert result.resolution == "720p"


@pytest.mark.asyncio
class TestGenerateAndWait:
    """Test the full generate_and_wait flow: generate -> poll -> download."""

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_full_flow(self, tmp_path):
        gen = SeedanceGenerator()
        output_path = str(tmp_path / "result.mp4")

        expected_result = VideoResult(
            path=output_path,
            duration_ms=5000,
            resolution="720p",
            cost_usd=0.05,
            source_image=None,
            prompt="manga scene",
        )

        gen.generate = AsyncMock(return_value="task-flow-1")
        gen.get_status = AsyncMock(
            side_effect=[
                VideoStatus(task_id="task-flow-1", status="processing", progress=0.3),
                VideoStatus(task_id="task-flow-1", status="processing", progress=0.7),
                VideoStatus(task_id="task-flow-1", status="completed", progress=1.0),
            ]
        )
        gen.download = AsyncMock(return_value=expected_result)

        result = await gen.generate_and_wait(
            prompt="manga scene",
            output_path=output_path,
            poll_interval=0.01,
        )

        assert result == expected_result
        gen.generate.assert_called_once()
        assert gen.get_status.call_count == 3
        gen.download.assert_called_once_with("task-flow-1", output_path)

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_timeout_raises(self, tmp_path):
        gen = SeedanceGenerator()
        output_path = str(tmp_path / "timeout.mp4")

        gen.generate = AsyncMock(return_value="task-timeout")
        gen.get_status = AsyncMock(
            return_value=VideoStatus(
                task_id="task-timeout", status="processing", progress=0.1,
            )
        )

        with pytest.raises(VideoGenerationError, match="timeout|Timeout"):
            await gen.generate_and_wait(
                prompt="slow scene",
                output_path=output_path,
                poll_interval=0.01,
                max_wait=0.05,
            )

    @patch.dict("os.environ", {"SEEDANCE_API_KEY": "test-key-123"})
    async def test_failed_status_raises(self, tmp_path):
        gen = SeedanceGenerator()
        output_path = str(tmp_path / "failed.mp4")

        gen.generate = AsyncMock(return_value="task-fail")
        gen.get_status = AsyncMock(
            return_value=VideoStatus(
                task_id="task-fail",
                status="failed",
                progress=0.0,
                error="Generation failed: content policy",
            )
        )

        with pytest.raises(VideoGenerationError, match="failed"):
            await gen.generate_and_wait(
                prompt="bad scene",
                output_path=output_path,
                poll_interval=0.01,
            )


async def _async_iter(items):
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item
