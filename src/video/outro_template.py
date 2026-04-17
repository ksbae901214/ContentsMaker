"""QW-05 — Standardized CTA outro template (single source of truth).

Why a separate module:
    Both the TTS generator (spoken outro) and the Remotion renderer (on-screen
    CTA) used to hard-code their own outro strings, which drifted out of sync.
    This module centralises the spoken text, visual CTA lines, duration, and
    the scene_id contract (=-1) so the spoken voice and the visible captions
    always match.

Consumers:
    - src.tts.edge_tts_generator (imports OUTRO_TEXT)
    - src.video.remotion (Outro.tsx receives ctaLines via props)
"""
from __future__ import annotations

# Voice text — read aloud at the end of every shorts video.
# Periods provide natural pauses for edge-tts.
OUTRO_VOICE_TEXT: str = (
    "구독과 좋아요. 그리고 알림 설정도 잊지 마세요. 다음 영상에서 만나요."
)

# Visual CTA lines — rendered as stacked subtitles in Outro.tsx.
# Each line ≤30 chars for 9:16 mobile readability (정치 유튜브 일반 규격).
OUTRO_CTA_LINES: tuple[str, ...] = (
    "구독과 좋아요 부탁드립니다",
    "알림 설정도 잊지 마세요",
    "다음 영상에서 만나요!",
)

# Outro duration (seconds). Matches Remotion ShortsComposition's
# OUTRO_DURATION_FRAMES (= FPS * 4).
OUTRO_DURATION_SECONDS: float = 4.0

# Pipeline contract: scene_id=-1 designates the outro segment in
# scene_timings (see CLAUDE.md "Per-scene TTS timing").
OUTRO_SCENE_ID: int = -1


def build_outro_props() -> dict:
    """Build the props dict consumed by the Remotion Outro component.

    Centralised here so the renderer doesn't duplicate the constants.
    """
    return {
        "ctaLines": list(OUTRO_CTA_LINES),
        "durationSeconds": OUTRO_DURATION_SECONDS,
    }
