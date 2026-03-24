"""Manage reference images for consistent illustration generation.

Loads and selects reference images based on scene context
(characters, backgrounds, emotions) to pass to the image generation API.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

REFERENCES_DIR = PROJECT_ROOT / "data" / "references"
CHARACTERS_DIR = REFERENCES_DIR / "characters"
BACKGROUNDS_DIR = REFERENCES_DIR / "backgrounds"

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# Background keyword mapping: scene text keywords → background filename stems
# Order matters: first match wins, so more specific patterns go first
BACKGROUND_KEYWORDS: dict[str, list[str]] = {
    "bar": ["술집", "바에서", "맥주", "소주", "와인", "회식", "2차", "카페", "커피", "한잔"],
    "office": ["회사", "사무실", "직장", "출근", "퇴근", "동료", "상사", "부장", "팀장", "과장", "대리"],
    "apartment": ["집", "아파트", "거실", "방에서", "침실", "주방", "부엌", "냉장고", "소파", "TV"],
}


@dataclass(frozen=True)
class ReferenceSet:
    """Selected reference images for a single scene."""

    character_refs: tuple[Path, ...]
    background_ref: Path | None

    @property
    def all_paths(self) -> list[Path]:
        refs = list(self.character_refs)
        if self.background_ref:
            refs.append(self.background_ref)
        return refs

    @property
    def has_references(self) -> bool:
        return len(self.character_refs) > 0 or self.background_ref is not None


def is_available() -> bool:
    """Check if any reference images exist."""
    return REFERENCES_DIR.exists() and any(
        f.suffix.lower() in IMAGE_EXTENSIONS
        for f in REFERENCES_DIR.rglob("*")
        if f.is_file()
    )


def _find_images(directory: Path) -> list[Path]:
    """Find all image files in a directory."""
    if not directory.exists():
        return []
    return sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def _match_background(scene_text: str) -> Path | None:
    """Match scene text to the most relevant background image."""
    backgrounds = _find_images(BACKGROUNDS_DIR)
    if not backgrounds:
        return None

    bg_by_stem = {bg.stem.lower(): bg for bg in backgrounds}

    for bg_name, keywords in BACKGROUND_KEYWORDS.items():
        if any(kw in scene_text for kw in keywords):
            if bg_name in bg_by_stem:
                return bg_by_stem[bg_name]

    return None


def _select_character_refs(scene_text: str) -> tuple[Path, ...]:
    """Select character reference images based on scene context."""
    chars = _find_images(CHARACTERS_DIR)
    if not chars:
        return ()

    char_by_stem = {c.stem.lower(): c for c in chars}
    selected = []

    # Always include fullbody if available (style + proportions reference)
    if "fullbody" in char_by_stem:
        selected.append(char_by_stem["fullbody"])

    # Select expression sheet based on likely gender in scene
    female_keywords = ["여자", "여친", "아내", "엄마", "언니", "누나", "며느리", "시어머니", "여성"]
    male_keywords = ["남자", "남친", "남편", "아빠", "형", "오빠", "사위", "시아버지", "남성"]

    has_female = any(kw in scene_text for kw in female_keywords)
    has_male = any(kw in scene_text for kw in male_keywords)

    if has_female and "female_expressions" in char_by_stem:
        selected.append(char_by_stem["female_expressions"])
    if has_male and "male_expressions" in char_by_stem:
        selected.append(char_by_stem["male_expressions"])

    # If no gender detected, include fullbody only (already added above)
    if not selected and "fullbody" in char_by_stem:
        selected.append(char_by_stem["fullbody"])

    return tuple(selected)


def select_references(scene_text: str) -> ReferenceSet:
    """Select the best reference images for a given scene.

    Args:
        scene_text: The scene's text content (Korean) for context matching.

    Returns:
        ReferenceSet with selected character and background references.
    """
    if not is_available():
        return ReferenceSet(character_refs=(), background_ref=None)

    character_refs = _select_character_refs(scene_text)
    background_ref = _match_background(scene_text)

    if character_refs or background_ref:
        ref_names = [p.name for p in character_refs]
        if background_ref:
            ref_names.append(background_ref.name)
        logger.info("레퍼런스 선택: %s", ", ".join(ref_names))

    return ReferenceSet(
        character_refs=character_refs,
        background_ref=background_ref,
    )


def get_all_references() -> list[Path]:
    """Get all available reference images (for logging/debugging)."""
    if not REFERENCES_DIR.exists():
        return []
    return sorted(
        f for f in REFERENCES_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )
