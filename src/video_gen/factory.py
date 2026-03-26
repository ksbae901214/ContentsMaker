"""Video generator factory."""
from __future__ import annotations

from src.video_gen.base import VideoGeneratorBase
from src.video_gen.seedance_gen import SeedanceGenerator


def create_generator(provider: str = "seedance") -> VideoGeneratorBase:
    """Create a video generator by provider name."""
    generators = {
        "seedance": SeedanceGenerator,
    }
    cls = generators.get(provider)
    if cls is None:
        raise ValueError(f"Unknown video generator: {provider}")
    return cls()
