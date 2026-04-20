"""Celebrity-portrait motion prompt builder (Phase 9-4).

Celebrity shorts feed the image-to-video model with a **real person's photo**.
This requires stronger identity-preservation guards than the general
motion_prompt_builder — a misplaced limb is ugly for a generic scene, but
altering a real person's face is a trust-breaker (and in some jurisdictions,
raises publicity-rights concerns).

This module layers additional constraints on top of the shared MOTION_GUARD:

1. **Identity lock** — no face morphing, age changes, gender swap, or
   likeness mutation.
2. **Gentle motion only** — subtle push-in or soft parallax; avoid fast
   camera moves that cause face distortion.
3. **Background stability** — no new people entering frame.
4. **Mouth closed / neutral** — avoid "deepfake speech" motion artifacts,
   since the portrait is paired with off-screen narration, not sync-dub.
"""
from __future__ import annotations

from src.analyzer.script_models import Scene
from src.video_gen.motion_prompt_builder import MOTION_GUARD


CELEBRITY_IDENTITY_GUARD = (
    "Preserve the person's exact facial identity, age, and appearance — "
    "do not morph, age, de-age, or change the face in any way. "
    "Do not alter hair color, skin tone, facial features, or expression drastically. "
    "Keep the mouth gently closed or neutral — no speaking animation, no lip sync. "
    "Background remains stable; no new people or objects appear. "
)

# Gentle camera — the default for portrait photos in celebrity intros.
GENTLE_PORTRAIT_CAMERA = (
    "Slow gentle camera push-in with minimal parallax. No rotation, no tilt, no pan. "
    "Movement is subtle enough that the viewer barely notices — about 5% zoom over the clip. "
)

# Static camera — for high-emphasis title scenes where face must stay rock-stable.
STATIC_PORTRAIT_CAMERA = (
    "Completely static locked camera, NO zoom, NO pan, NO movement. "
    "Only the subject breathes naturally with micro-blinks. "
)


def build_celebrity_motion_prompt(scene: Scene, person_name: str = "") -> str:
    """Build a motion prompt for a celebrity portrait scene.

    Rules:
    1. If scene already has a user-edited ``motion_prompt``, honor it verbatim.
    2. Title scenes → STATIC camera (face must be clearly readable).
    3. Body/comment scenes → GENTLE push-in.
    4. Always append the celebrity identity guard + universal motion guard.
    """
    if scene.motion_prompt:
        return scene.motion_prompt

    camera = STATIC_PORTRAIT_CAMERA if scene.type == "title" else GENTLE_PORTRAIT_CAMERA
    subject_hint = (
        f"The subject is {person_name}. " if person_name else ""
    )
    return f"{camera}{CELEBRITY_IDENTITY_GUARD}{MOTION_GUARD}{subject_hint}"
