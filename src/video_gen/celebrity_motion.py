"""Celebrity-portrait motion prompt builder (Phase 9-4, v2 2026-04-21).

Celebrity shorts feed the image-to-video model with a **real person's photo**.
This requires stronger identity-preservation guards + scene-aware motion hints
so the generated clip matches the narration's mood.

v2 (2026-04-21): Scene voice_text + emphasis 반영. Freepik이 동일 인물 이미지로
여러 씬을 변주할 때 "대본과 관련 없어 보이는" 문제 해소.
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

# Emphasis별 카메라 워크 — 씬의 강도에 맞춰 변주 (얼굴은 항상 유지).
CAMERA_BY_EMPHASIS = {
    "high": (
        "Bold but smooth camera push-in (~8% zoom over the clip). "
        "The subject holds a confident, steady gaze. Dramatic but controlled. "
    ),
    "medium": (
        "Slow gentle camera push-in with minimal parallax (~5% zoom). "
        "No rotation, no tilt, no pan. The movement is subtle. "
    ),
    "low": (
        "Completely static locked camera, NO zoom, NO pan. "
        "Only the subject breathes naturally with micro-blinks. "
    ),
}

# Scene type별 기본 카메라 (emphasis 보조).
CAMERA_BY_TYPE = {
    "title": CAMERA_BY_EMPHASIS["low"],      # 훅 씬은 얼굴 고정이 최우선
    "comment": CAMERA_BY_EMPHASIS["low"],    # 마무리도 안정적으로
}


def _mood_from_voice(voice_text: str, emphasis: str) -> str:
    """Scene의 짧은 분위기 힌트. 한글 voice_text를 영어 mood descriptor로."""
    t = (voice_text or "").strip()
    if not t:
        return "neutral contemplative mood."
    # 간단 키워드 매핑 (정치 쇼츠 빈출 표현)
    if any(w in t for w in ("비판", "반대", "공격", "논란", "조작", "사기")):
        return "serious critical mood, subject looking resolute."
    if any(w in t for w in ("감동", "헌신", "눈물", "슬프", "안타깝")):
        return "heartfelt emotional mood, gentle and warm expression."
    if any(w in t for w in ("재밌", "흥미", "놀랍", "반전", "특이")):
        return "intriguing curious mood, slight hint of wonder."
    if any(w in t for w in ("현재", "지금은", "앞으로", "주목")):
        return "thoughtful present-day mood, a looking-forward expression."
    return "calm narrative mood, subject faces the camera with quiet confidence."


def build_celebrity_motion_prompt(scene: Scene, person_name: str = "") -> str:
    """Build a motion prompt for a celebrity portrait scene.

    Rules (v2, 2026-04-21):
    1. 씬에 사용자 편집 `motion_prompt`가 있으면 그대로 사용.
    2. scene.type이 title/comment면 static camera (얼굴 안정).
    3. 그 외 body 씬은 emphasis(high/medium/low)별 카메라 차별화.
    4. scene.voice_text에서 간단 mood 추출 → 프롬프트에 자연어 힌트.
    5. 항상 identity guard + MOTION_GUARD를 덧붙여 얼굴 왜곡 방지.
    """
    if scene.motion_prompt:
        return scene.motion_prompt

    camera = CAMERA_BY_TYPE.get(scene.type)
    if camera is None:
        camera = CAMERA_BY_EMPHASIS.get(scene.emphasis, CAMERA_BY_EMPHASIS["medium"])

    subject_hint = (
        f"The subject is {person_name}. " if person_name else ""
    )
    mood_hint = _mood_from_voice(scene.voice_text, scene.emphasis)
    context_hint = (
        f"The scene's narration covers: "
        f"\"{scene.voice_text[:60]}\". {mood_hint} "
        if scene.voice_text else mood_hint
    )
    return (
        f"{camera}{CELEBRITY_IDENTITY_GUARD}{MOTION_GUARD}"
        f"{subject_hint}{context_hint}"
    )


# Legacy constants kept for backward compat (일부 테스트에서 참조).
GENTLE_PORTRAIT_CAMERA = CAMERA_BY_EMPHASIS["medium"]
STATIC_PORTRAIT_CAMERA = CAMERA_BY_EMPHASIS["low"]
