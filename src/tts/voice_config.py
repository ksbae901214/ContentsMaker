"""Emotion-based voice configuration for edge-tts.

Constitution Principle V: Emotion-Driven Experience.
Each emotion type maps to a specific voice, speed, and pitch.
"""

VOICE_CONFIG: dict[str, dict[str, str]] = {
    "funny": {
        "voice": "ko-KR-SunHiNeural",
        "rate": "+20%",
        "pitch": "+0Hz",
    },
    "touching": {
        "voice": "ko-KR-SunHiNeural",
        "rate": "+20%",
        "pitch": "+0Hz",
    },
    "angry": {
        "voice": "ko-KR-SunHiNeural",
        "rate": "+20%",
        "pitch": "+0Hz",
    },
    "relatable": {
        "voice": "ko-KR-SunHiNeural",
        "rate": "+20%",
        "pitch": "+0Hz",
    },
}

GRADIENT_THEMES: dict[str, list[str]] = {
    "funny": ["#FF6B6B", "#FFA500", "#FFD93D"],
    "touching": ["#6A5ACD", "#9370DB", "#DDA0DD"],
    "angry": ["#DC143C", "#8B0000", "#B22222"],
    "relatable": ["#4169E1", "#1E90FF", "#87CEEB"],
}

BGM_FILES: dict[str, str] = {
    "funny": "funny.mp3",
    "touching": "touching.mp3",
    "angry": "angry.mp3",
    "relatable": "relatable.mp3",
}

HIGHLIGHT_COLORS: dict[str, str] = {
    "funny": "#FFD700",
    "touching": "#FF69B4",
    "angry": "#FF4444",
    "relatable": "#87CEEB",
}

DEFAULT_EMOTION = "relatable"


def get_voice_config(emotion_type: str) -> dict[str, str]:
    """Get voice config for an emotion type, falling back to default."""
    return VOICE_CONFIG.get(emotion_type, VOICE_CONFIG[DEFAULT_EMOTION])


def get_gradient(emotion_type: str) -> list[str]:
    """Get gradient colors for an emotion type."""
    return GRADIENT_THEMES.get(emotion_type, GRADIENT_THEMES[DEFAULT_EMOTION])


def get_bgm_file(emotion_type: str) -> str:
    """Get BGM filename for an emotion type."""
    return BGM_FILES.get(emotion_type, BGM_FILES[DEFAULT_EMOTION])


def get_highlight_color(emotion_type: str) -> str:
    """Get highlight color for an emotion type."""
    return HIGHLIGHT_COLORS.get(emotion_type, HIGHLIGHT_COLORS[DEFAULT_EMOTION])
