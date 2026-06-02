"""Video generator factory."""
from __future__ import annotations

from src.video_gen.base import VideoGeneratorBase


def create_generator(provider: str = "deevid", gem_key: str | None = None) -> VideoGeneratorBase:
    """Create a video generator by provider name.

    Imports are lazy so that the heavy `playwright` dependency is only loaded
    when actually needed (i.e., the user picks a browser-automation provider).

    Provider priority (안정성·비용 순, 2026-05-19 Freepik 해지 후):
        1. gemini   — Veo 3 web automation (Gemini Pro 구독, 변동비 $0)  [Phase 2B]
        2. deevid   — Veo 3.1 web automation (무료 20 credits)
        3. seedance — API ($0.05/씬, SEEDANCE_API_KEY 필요)
        4. freepik  — 구독 해지로 비활성, 호환성을 위해 유지
    """
    if provider == "gemini":
        from src.video_gen.gemini_web_video_gen import GeminiWebVideoGenerator
        return GeminiWebVideoGenerator(gem_key=gem_key)
    if provider == "seedance":
        from src.video_gen.seedance_gen import SeedanceGenerator
        return SeedanceGenerator()
    if provider == "deevid":
        from src.video_gen.deevid_gen import DeevidGenerator
        return DeevidGenerator()
    if provider == "freepik":
        from src.video_gen.freepik_gen import FreepikBrowserGenerator
        return FreepikBrowserGenerator()
    raise ValueError(
        f"Unknown video generator: {provider!r}. "
        f"Available: 'gemini', 'deevid', 'seedance', 'freepik'"
    )
