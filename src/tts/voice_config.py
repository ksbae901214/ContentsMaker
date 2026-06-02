"""Emotion-based voice configuration for edge-tts.

Constitution Principle V: Emotion-Driven Experience.
Each emotion type maps to a specific voice, speed, and pitch.
"""

# edge-tts 지원 한국어 목소리: SunHiNeural(여), InJoonNeural(남), HyunsuMultilingualNeural(남·다국어)
VOICE_CONFIG: dict[str, dict[str, str]] = {
    "funny": {
        "voice": "ko-KR-SunHiNeural",   # 밝고 활기찬 여성 — 빠른 리듬
        "rate": "+25%",
        "pitch": "+2Hz",
    },
    "touching": {
        "voice": "ko-KR-SunHiNeural",   # 여성 — 느리고 여운 있게
        "rate": "+10%",
        "pitch": "-2Hz",
    },
    "angry": {
        "voice": "ko-KR-InJoonNeural",  # 남성 — 권위·신뢰 어조
        "rate": "+15%",
        "pitch": "+0Hz",
    },
    "relatable": {
        "voice": "ko-KR-SunHiNeural",   # 기본 여성 — 친근한 톤
        "rate": "+20%",
        "pitch": "+0Hz",
    },
}

# celebrity source_type 전용: 다국어 남성 내레이터 (외국 이름 발음 자연스러움)
CELEBRITY_VOICE_CONFIG: dict[str, str] = {
    "voice": "ko-KR-HyunsuMultilingualNeural",
    "rate": "+22%",
    "pitch": "+0Hz",
}

GRADIENT_THEMES: dict[str, list[str]] = {
    "funny": ["#FF6B6B", "#FFA500", "#FFD93D"],
    "touching": ["#6A5ACD", "#9370DB", "#DDA0DD"],
    "angry": ["#DC143C", "#8B0000", "#B22222"],
    "relatable": ["#4169E1", "#1E90FF", "#87CEEB"],
}

BGM_FILES: dict[str, list[str]] = {
    # 인덱스 0=잔잔/짧은 영상, 1=중간, 2=에너지/긴 영상
    "funny":     ["funny_1.mp3",     "funny_2.mp3",     "funny_3.mp3"],
    "touching":  ["touching_1.mp3",  "touching_2.mp3",  "touching_3.mp3"],
    "angry":     ["angry_1.mp3",     "angry_2.mp3",     "angry_3.mp3"],
    "relatable": ["relatable_1.mp3", "relatable_2.mp3", "relatable_3.mp3"],
    # celebrity source_type 전용: 인물 소개·업적 내레이션 톤
    "celebrity": ["celebrity_1.mp3", "celebrity_2.mp3", "celebrity_3.mp3"],
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


def get_bgm_file(emotion_type: str, seed: str | None = None) -> str:
    """Get BGM filename for an emotion type, rotating tracks via seed or random."""
    from pathlib import Path
    tracks = BGM_FILES.get(emotion_type, BGM_FILES[DEFAULT_EMOTION])
    # Prefer tracks that actually exist on disk
    try:
        from src.config.settings import PROJECT_ROOT
        existing = [t for t in tracks if (Path(PROJECT_ROOT) / "data" / "bgm" / t).exists()]
    except Exception:
        existing = tracks
    pool = existing if existing else tracks
    if seed is not None:
        import hashlib
        idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(pool)
    else:
        import random
        idx = random.randrange(len(pool))
    return pool[idx]


def select_bgm_for_script(script: "ShortsScript") -> str:  # type: ignore[name-defined]
    """Script 내용을 분석해 가장 어울리는 BGM 트랙 파일명 반환.

    celebrity source_type이면 celebrity 전용 풀 사용.
    그 외: 에너지 점수(0~1) → 트랙 인덱스:
        0.0~0.33 : _1 (잔잔 — 씬 수가 적거나 감성 위주)
        0.33~0.67: _2 (중간 — 일반적인 영상)
        0.67~1.0 : _3 (에너지 — hook 多, 강조 씬 多, 긴 영상)
    """
    from pathlib import Path

    source_type = getattr(script.metadata, "source_type", "")
    is_celebrity = source_type == "celebrity"

    emotion = (script.metadata.emotion_type or DEFAULT_EMOTION)
    pool_key = "celebrity" if is_celebrity else emotion
    tracks = BGM_FILES.get(pool_key, BGM_FILES[DEFAULT_EMOTION])

    # 존재하는 파일만 후보로
    try:
        from src.config.settings import PROJECT_ROOT
        existing = [t for t in tracks if (Path(PROJECT_ROOT) / "data" / "bgm" / t).exists()]
    except Exception:
        existing = tracks
    pool = existing if existing else tracks

    # 에너지 점수 계산
    scenes = script.scenes
    hook_count = sum(1 for s in scenes if getattr(s, "hook", False))
    emphasis_count = sum(1 for s in scenes if getattr(s, "subtitle_emphasis", False))
    total_duration = sum(getattr(s, "duration", 0) for s in scenes)
    scene_count = len(scenes)

    energy = 0.0
    # hook 씬: 강한 시청각 임팩트 → 에너지 ↑
    if hook_count >= 2:
        energy += 0.4
    elif hook_count == 1:
        energy += 0.25
    # 강조 자막 비율
    if scene_count > 0:
        emphasis_ratio = emphasis_count / scene_count
        energy += emphasis_ratio * 0.3
    # 영상 길이: 45초 초과 시 지속력 있는 트랙 선호
    if total_duration > 55:
        energy += 0.3
    elif total_duration > 40:
        energy += 0.15

    energy = min(1.0, energy)

    # 에너지 → 트랙 인덱스 (0, 1, 2)
    idx = min(len(pool) - 1, int(energy * len(pool)))
    return pool[idx]


def get_highlight_color(emotion_type: str) -> str:
    """Get highlight color for an emotion type."""
    return HIGHLIGHT_COLORS.get(emotion_type, HIGHLIGHT_COLORS[DEFAULT_EMOTION])
