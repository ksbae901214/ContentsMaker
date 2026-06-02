"""Build motion prompts for image-to-video models (Kling 2.5, etc).

Centralizes the "no ghost character / subject preservation / anatomy"
guards so both standalone e2e scripts and the web UI
(app/api/generate/route.ts) produce consistent video quality.

Background:
- Kling 2.5 occasionally "reveals" or "hallucinates" new characters
  mid-clip when the starting image has dim lighting or a single lonely
  subject (nurse scenes 4/5 in the e2e run).
- It also sometimes adds extra limbs or duplicates hands during motion.
- This module applies a universal MOTION_GUARD to every prompt, and
  picks STATIC vs DYNAMIC camera motion based on scene attributes so
  high-emphasis body scenes (which are the most prone to hallucination)
  default to a locked camera.
"""
from __future__ import annotations

from src.analyzer.script_models import Scene


# Universal guard appended to every motion prompt. Covers the
# "ghost character appears mid-shot" and "extra hand grows" failures.
MOTION_GUARD = (
    "All subjects in the starting frame remain fully visible in frame the entire clip. "
    "Do NOT introduce, reveal, or add any new characters, people, or objects mid-shot. "
    "No ghostly figures, no transparent figures, no sudden appearances. "
    "Preserve anatomical correctness — exactly two hands per person, five fingers each, "
    "no extra limbs, no duplicated body parts, hands stay in their original positions. "
)


# Static camera — for quiet intimate scenes where motion is risky.
STATIC_CAMERA = (
    "Static locked camera, NO zoom, NO pan, NO dolly, NO camera movement at all. "
    "The subjects breathe naturally and blink slowly with very subtle facial movement. "
)


# Dynamic camera — for lighter/more active scenes.
DYNAMIC_CAMERA = (
    "Slow cinematic camera movement — gentle push-in or soft parallax only. "
    "The subject's facial expression and body language subtly animates. "
)


def build_motion_prompt(scene: Scene) -> str:
    """Build a motion prompt for a single scene.

    Rules:
    1. If the scene already has a user-edited ``motion_prompt`` (e.g. from
       the scene editor), use it verbatim.
    2. Otherwise, pick static vs dynamic camera based on scene attributes,
       append the universal MOTION_GUARD, and end with a short hint from
       the voice/text line so the model knows what's happening.

    Static camera is chosen for ``emphasis == "high"`` body scenes
    because those are the most likely to be dark/intimate/single-subject —
    exactly the configurations where Kling 2.5 hallucinated the "ghost
    patient" in the nurse pipeline.
    """
    if scene.motion_prompt:
        return scene.motion_prompt

    use_static = scene.emphasis == "high" and scene.type == "body"
    camera = STATIC_CAMERA if use_static else DYNAMIC_CAMERA

    hint = (scene.voice_text or scene.text or "").strip()[:80]
    return f"{camera}{MOTION_GUARD}{hint}"
