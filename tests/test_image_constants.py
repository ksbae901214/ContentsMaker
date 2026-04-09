"""Unit tests for shared image prompt constants.

These constants are the single source of truth for the "no text / no ghost"
guards used by both the web UI (via prompt_builder.py) and e2e scripts.
"""
from __future__ import annotations

from src.illustrator.image_constants import (
    ANATOMY_GUARD,
    NO_TEXT_GUARD,
    PHOTO_STYLE_FOOTER,
    PHOTO_STYLE_PREFIX,
)


class TestNoTextGuard:
    def test_mentions_core_no_text_keywords(self) -> None:
        """Must cover the generic text ban."""
        assert "NO text" in NO_TEXT_GUARD
        assert "NO letters" in NO_TEXT_GUARD
        assert "NO numbers" in NO_TEXT_GUARD
        assert "NO words" in NO_TEXT_GUARD
        assert "NO labels" in NO_TEXT_GUARD
        assert "NO signs with writing" in NO_TEXT_GUARD

    def test_blocks_every_common_language(self) -> None:
        """Must explicitly ban every common language Nano Banana might try."""
        for lang in ("English", "Korean", "Chinese", "Japanese"):
            assert f"NO {lang} text" in NO_TEXT_GUARD, f"missing {lang}"

    def test_blocks_text_bearing_surfaces(self) -> None:
        """Must name the specific surfaces where text sneaks in."""
        # Screens & displays
        assert "NO computer monitors with visible text" in NO_TEXT_GUARD
        assert "NO tablet screens with text" in NO_TEXT_GUARD
        assert "NO phone screens with text" in NO_TEXT_GUARD
        # Paper & documents
        assert "NO documents with text" in NO_TEXT_GUARD
        assert "NO clipboards with text" in NO_TEXT_GUARD
        # Signs & labels (general spaces)
        assert "NO menu boards" in NO_TEXT_GUARD
        assert "NO store signs" in NO_TEXT_GUARD
        assert "NO product labels" in NO_TEXT_GUARD
        # Identity
        assert "NO name tags" in NO_TEXT_GUARD
        assert "NO ID badges" in NO_TEXT_GUARD

    def test_final_clause_demands_zero_characters(self) -> None:
        assert "ZERO readable characters" in NO_TEXT_GUARD


class TestPhotoStylePrefix:
    def test_anchors_on_photography_vocabulary(self) -> None:
        """Must lead with camera/photo words so diffusion stays out of illustration mode."""
        assert "DSLR" in PHOTO_STYLE_PREFIX
        assert "photograph" in PHOTO_STYLE_PREFIX.lower()
        assert "85mm" in PHOTO_STYLE_PREFIX
        assert "bokeh" in PHOTO_STYLE_PREFIX


class TestPhotoStyleFooter:
    def test_includes_full_no_text_guard(self) -> None:
        """Footer must embed the full guard, not a subset."""
        assert NO_TEXT_GUARD in PHOTO_STYLE_FOOTER

    def test_blocks_stylized_outputs(self) -> None:
        """Footer must explicitly reject cartoon/anime/illustration."""
        for forbidden in ("NO cartoon", "NO anime", "NO illustration",
                          "NO drawing", "NO webtoon", "NO manga"):
            assert forbidden in PHOTO_STYLE_FOOTER, f"missing {forbidden}"

    def test_declares_real_photograph(self) -> None:
        assert "REAL PHOTOGRAPH" in PHOTO_STYLE_FOOTER

    def test_enforces_vertical_aspect(self) -> None:
        assert "9:16" in PHOTO_STYLE_FOOTER


class TestAnatomyGuard:
    def test_bans_common_mutations(self) -> None:
        assert "exactly two hands" in ANATOMY_GUARD
        assert "five fingers each" in ANATOMY_GUARD
        assert "NO extra limbs" in ANATOMY_GUARD
        assert "NO deformed hands" in ANATOMY_GUARD


class TestPromptLengthBudget:
    """Guard against the constants growing so long that diffusion models
    start truncating or ignoring parts. Nano Banana Pro reliably handles
    ~2000 chars; we keep a safety margin.
    """

    def test_no_text_guard_under_2000_chars(self) -> None:
        assert len(NO_TEXT_GUARD) < 2000, len(NO_TEXT_GUARD)

    def test_photo_footer_under_2500_chars(self) -> None:
        assert len(PHOTO_STYLE_FOOTER) < 2500, len(PHOTO_STYLE_FOOTER)
