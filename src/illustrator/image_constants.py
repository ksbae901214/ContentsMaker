"""Shared image prompt constants used by prompt_builder.py and scripts.

Centralizes NO_TEXT_GUARD / PHOTO_STYLE / PHOTO_STYLE_FOOTER so that the web UI
(app/api/generate/route.ts → prompt_builder.py) and standalone e2e scripts
(scripts/e2e_*.py) produce the same quality.

Background:
- Realistic-mode images were rendering foreign-language text on signs,
  medication labels, monitors, and name tags. The e2e nurse script solved
  this with an 8-level domain-specific guard.
- This module generalizes that guard so any topic (not just hospitals)
  gets the same text-free quality.
"""
from __future__ import annotations


# Strong, domain-neutral no-text guard.
# Covers every common text-bearing surface (signs, labels, screens,
# documents) plus every language so diffusion models can't sneak in
# foreign characters into a Korean shorts video.
NO_TEXT_GUARD = (
    "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, "
    "NO watermarks, NO subtitles, NO UI elements, NO titles, NO labels, NO signs with writing, "
    "NO name tags, NO ID badges, NO uniform patches with text, "
    "NO documents with text, NO papers with text, NO clipboards with text, "
    "NO computer monitors with visible text, NO tablet screens with text, NO phone screens with text, "
    "NO TV screens with text, NO whiteboards, NO bulletin boards, NO posters with text, "
    "NO menu boards, NO store signs, NO book covers with text, NO product labels, "
    "NO equipment displays with text, NO charts with text, "
    "NO English text, NO Korean text, NO Chinese text, NO Japanese text, NO any language text, "
    "the image must contain ZERO readable characters of any language anywhere, "
    "if any text-like marks accidentally appear they must be unreadable abstract patterns only"
)


# Photo-style prefix — must lead every realistic prompt so diffusion models
# anchor on photography vocabulary (not illustration).
PHOTO_STYLE_PREFIX = (
    "Professional DSLR photograph, photorealistic, shot on Sony A7R IV, "
    "85mm prime lens, f/1.8 bokeh, Korean drama cinematography, natural lighting. "
)


# Photo-style footer — appended after the per-scene description.
# Includes the aspect ratio, the full NO_TEXT_GUARD, and an anti-cartoon
# block so the model stays in photo-realism mode.
PHOTO_STYLE_FOOTER = (
    " vertical 9:16 aspect ratio for YouTube Shorts, "
    + NO_TEXT_GUARD
    + ", NO cartoon, NO anime, NO illustration, NO painting, NO drawing, NO webtoon, NO manga, "
    "this is a REAL PHOTOGRAPH not a drawing"
)


# Anatomy guard — appended to every realistic prompt because diffusion
# models frequently produce extra hands/fingers.
ANATOMY_GUARD = (
    "anatomically correct, exactly two hands with five fingers each, "
    "exactly two arms, exactly two legs, exactly one head, exactly two eyes, "
    "NO extra limbs, NO extra fingers, NO duplicated body parts, NO deformed hands"
)
