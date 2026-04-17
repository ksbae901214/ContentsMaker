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

# QW-02: 카테고리별 키워드 강조 색 — emotion 색보다 우선 적용.
# 정치 유튜브 §2.3 패턴: 사실·숫자는 노랑, 비판은 빨강으로 분리해 시각 신호 차별화.
CATEGORY_HIGHLIGHT_COLORS: dict[str, str] = {
    "fact": "#FFD54F",       # 정보·숫자·일자 — 정보성 노랑
    "criticism": "#F44336",  # 비판·문제 지적 — 날카로운 빨강
}

DEFAULT_EMOTION = "relatable"


def resolve_highlight_color(category: str, emotion_type: str) -> str:
    """QW-02: 씬의 highlight_category가 있으면 그 색, 아니면 emotion 색.

    Args:
        category: "fact" / "criticism" / "neutral" (또는 임의 문자열)
        emotion_type: "funny" / "touching" / "angry" / "relatable"

    Returns:
        hex color. neutral 또는 미지의 category는 emotion 색으로 폴백.
    """
    if category in CATEGORY_HIGHLIGHT_COLORS:
        return CATEGORY_HIGHLIGHT_COLORS[category]
    return HIGHLIGHT_COLORS.get(emotion_type, HIGHLIGHT_COLORS[DEFAULT_EMOTION])

# Korean voice catalog for edge-tts with metadata
KOREAN_VOICES: list[dict[str, str]] = [
    {
        "name": "ko-KR-SunHiNeural",
        "gender": "female",
        "tone": "bright",
        "description": "밝고 활기찬 여성 음성 (기본값)",
    },
    {
        "name": "ko-KR-InJoonNeural",
        "gender": "male",
        "tone": "calm",
        "description": "차분하고 신뢰감 있는 남성 음성",
    },
    {
        "name": "ko-KR-BongJinNeural",
        "gender": "male",
        "tone": "deep",
        "description": "깊고 무게감 있는 남성 음성",
    },
    {
        "name": "ko-KR-GookMinNeural",
        "gender": "male",
        "tone": "neutral",
        "description": "중립적이고 안정감 있는 남성 음성",
    },
    {
        "name": "ko-KR-JiMinNeural",
        "gender": "female",
        "tone": "soft",
        "description": "부드럽고 감성적인 여성 음성",
    },
    {
        "name": "ko-KR-SeoHyeonNeural",
        "gender": "female",
        "tone": "professional",
        "description": "전문적이고 또렷한 여성 음성",
    },
    {
        "name": "ko-KR-SoonBokNeural",
        "gender": "female",
        "tone": "warm",
        "description": "따뜻하고 친근한 여성 음성",
    },
    {
        "name": "ko-KR-YuJinNeural",
        "gender": "female",
        "tone": "clear",
        "description": "맑고 깨끗한 여성 음성",
    },
]


def get_korean_voices() -> list[dict[str, str]]:
    """Get all available Korean TTS voices with metadata."""
    return KOREAN_VOICES


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
