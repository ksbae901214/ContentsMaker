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

DEFAULT_EMOTION = "relatable"


def get_voice_config(emotion_type: str) -> dict[str, str]:
    """Get voice config for an emotion type, falling back to default."""
    return VOICE_CONFIG.get(emotion_type, VOICE_CONFIG[DEFAULT_EMOTION])


def get_gradient(emotion_type: str) -> list[str]:
    """Get gradient colors for an emotion type."""
    return GRADIENT_THEMES.get(emotion_type, GRADIENT_THEMES[DEFAULT_EMOTION])
