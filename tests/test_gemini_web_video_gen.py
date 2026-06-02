"""Phase 2B: Veo 3 영상 생성기 + factory 통합 테스트."""
from __future__ import annotations

import pytest

from src.video_gen.base import VideoGenerationError, VideoGeneratorBase
from src.video_gen.factory import create_generator
from src.video_gen.gemini_web_video_gen import GeminiWebVideoGenerator


class TestFactory:
    def test_gemini_provider_returns_subclass(self):
        gen = create_generator("gemini")
        assert isinstance(gen, VideoGeneratorBase)
        assert isinstance(gen, GeminiWebVideoGenerator)

    def test_deevid_still_works(self):
        gen = create_generator("deevid")
        assert isinstance(gen, VideoGeneratorBase)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            create_generator("openai_sora")


class TestGeminiWebVideoGenerator:
    def test_estimate_cost_is_zero(self):
        gen = GeminiWebVideoGenerator()
        assert gen.estimate_cost(duration=8.0) == 0.0

    @pytest.mark.asyncio
    async def test_generate_returns_task_id(self):
        gen = GeminiWebVideoGenerator()
        task_id = await gen.generate("test prompt")
        assert task_id and len(task_id) == 12

    @pytest.mark.asyncio
    async def test_get_status_unknown_task(self):
        gen = GeminiWebVideoGenerator()
        status = await gen.get_status("nonexistent")
        assert status.status == "failed"

    @pytest.mark.asyncio
    async def test_download_before_complete_raises(self):
        gen = GeminiWebVideoGenerator()
        task_id = await gen.generate("test")
        with pytest.raises(VideoGenerationError, match="완료 안 됨"):
            await gen.download(task_id, "/tmp/x.mp4")

    @pytest.mark.asyncio
    async def test_ensure_session_without_profile_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.video_gen.gemini_web_video_gen.GEMINI_PROFILE_DIR",
            tmp_path / "missing",
        )
        gen = GeminiWebVideoGenerator()
        with pytest.raises(VideoGenerationError, match="세션 없음"):
            await gen._ensure_session()
