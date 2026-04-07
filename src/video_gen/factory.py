"""Video generator factory."""
from __future__ import annotations

from src.video_gen.base import VideoGeneratorBase


def create_generator(provider: str = "seedance") -> VideoGeneratorBase:
    """Create a video generator by provider name.

    Imports are lazy so that the heavy `playwright` dependency is only loaded
    when actually needed (i.e., the user picks the deevid provider).
    """
    if provider == "seedance":
        from src.video_gen.seedance_gen import SeedanceGenerator
        return SeedanceGenerator()
    if provider == "deevid":
        from src.video_gen.deevid_gen import DeevidGenerator
        return DeevidGenerator()
    raise ValueError(
        f"Unknown video generator: {provider!r}. "
        f"Available: 'seedance', 'deevid'"
    )
