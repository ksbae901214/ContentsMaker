"""Regression tests for src.illustrator.prompt_builder.

The realistic preset was upgraded to use shared constants from
src.illustrator.image_constants. These tests make sure:
1. The realistic preset still contains the strong NO_TEXT_GUARD.
2. The other 3 presets (webtoon / 3d_pixar / anime) were NOT touched.
"""
from __future__ import annotations

from src.illustrator.image_constants import (
    ANATOMY_GUARD,
    NO_TEXT_GUARD,
    PHOTO_STYLE_FOOTER,
    PHOTO_STYLE_PREFIX,
)
from src.illustrator.prompt_builder import (
    IMAGE_STYLE_PRESETS,
    STYLE_INSTRUCTIONS_FOR_CLAUDE,
)


class TestRealisticPreset:
    """The realistic preset is the one we upgraded."""

    def test_exists(self) -> None:
        assert "realistic" in IMAGE_STYLE_PRESETS

    def test_uses_shared_photo_style_prefix(self) -> None:
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert PHOTO_STYLE_PREFIX in preset

    def test_uses_shared_photo_style_footer(self) -> None:
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert PHOTO_STYLE_FOOTER in preset

    def test_uses_shared_anatomy_guard(self) -> None:
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert ANATOMY_GUARD in preset

    def test_embeds_no_text_guard_via_footer(self) -> None:
        """Because PHOTO_STYLE_FOOTER contains NO_TEXT_GUARD, the full
        guard must appear inside the preset."""
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert NO_TEXT_GUARD in preset

    def test_bans_text_surfaces(self) -> None:
        """Spot-check the generalized (non-hospital) text bans."""
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert "NO store signs" in preset
        assert "NO menu boards" in preset
        assert "NO phone screens with text" in preset

    def test_explicitly_rejects_illustration_mode(self) -> None:
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert "NO illustration" in preset
        assert "NO cartoon" in preset
        assert "REAL PHOTOGRAPH" in preset

    def test_anchored_on_photography_vocabulary(self) -> None:
        preset = IMAGE_STYLE_PRESETS["realistic"]
        assert "DSLR" in preset
        assert "photograph" in preset.lower()


class TestOtherPresetsUnchanged:
    """Make sure we only touched the realistic preset."""

    def test_webtoon_still_has_webtoon_vocabulary(self) -> None:
        preset = IMAGE_STYLE_PRESETS["webtoon"]
        assert "Korean webtoon" in preset

    def test_3d_pixar_still_has_pixar_vocabulary(self) -> None:
        preset = IMAGE_STYLE_PRESETS["3d_pixar"]
        assert "3D Pixar" in preset
        assert "Pixar" in preset

    def test_anime_still_has_anime_vocabulary(self) -> None:
        preset = IMAGE_STYLE_PRESETS["anime"]
        assert "anime" in preset.lower()
        # Should not have been accidentally converted into photography
        assert "DSLR" not in preset

    def test_non_realistic_presets_do_not_use_photo_prefix(self) -> None:
        """The other presets must NOT contain the photo-specific prefix."""
        for style in ("webtoon", "3d_pixar", "anime"):
            assert PHOTO_STYLE_PREFIX not in IMAGE_STYLE_PRESETS[style], style


class TestRealisticClaudeInstructions:
    """The Claude-side instruction block was strengthened for realistic."""

    def test_mentions_realistic_style(self) -> None:
        info = STYLE_INSTRUCTIONS_FOR_CLAUDE["realistic"]
        assert "사진" in info["style_name"] or "photorealistic" in info["style_name"].lower()

    def test_requirements_include_text_ban_surfaces(self) -> None:
        """The Korean instruction for Claude must list the specific surfaces
        (menus, signs, screens, documents, product labels) so Claude's
        generated English prompts inherit the same ban."""
        reqs = STYLE_INSTRUCTIONS_FOR_CLAUDE["realistic"]["requirements"]
        # Must cover every language mention
        assert "언어" in reqs
        # Must list concrete surfaces that cause text leaks
        assert any(keyword in reqs for keyword in ("간판", "표지판"))
        assert "이름표" in reqs or "명찰" in reqs
        assert "모니터" in reqs or "화면" in reqs

    def test_forbids_illustration_words(self) -> None:
        reqs = STYLE_INSTRUCTIONS_FOR_CLAUDE["realistic"]["requirements"]
        assert "illustration" in reqs
        assert "cartoon" in reqs
