"""QW-06 — Auto-assign punch-zoom transitions to high-impact scenes.

Why:
    정치 유튜브 §3.3 패턴은 핵심 발언 직전에 0.2초 펀치 줌을 깔아 시각적
    임팩트를 만든다. ContentsMaker 의 TransitionConfig 인프라는 있었지만
    LLM 이 transition 을 거의 명시하지 않아 모든 컷이 단조로운 fade 였다.
    이 모듈은 emphasis="high" 와 hook 씬에 자동으로 punch-zoom 을 붙여서
    매 영상마다 일관된 시각 펀치를 보장한다.

매칭 규칙:
    - hook=True              → punch-zoom (오프닝 임팩트)
    - emphasis=="high"       → punch-zoom (강조 발언 진입)
    - 그 외 (medium/low)     → 변경 없음 (기존 transition 또는 None 보존)
    - 사용자 수동 transition 보존 (덮어쓰지 않음, idempotent)
"""
from __future__ import annotations

from dataclasses import replace

from src.analyzer.script_models import Scene, ShortsScript, TransitionConfig

PUNCH_ZOOM_DURATION_SECONDS: float = 0.2  # 6 frames at 30fps


def _should_apply_punch_zoom(scene: Scene) -> bool:
    """High emphasis 발언이거나 hook 씬이면 punch-zoom 자동 매칭."""
    if scene.transition is not None:
        return False  # 사용자 지정 보존
    return scene.hook is True or scene.emphasis == "high"


def auto_assign_transitions(script: ShortsScript) -> ShortsScript:
    """Return a new ShortsScript with auto-assigned punch-zoom transitions.

    Existing scene.transition (user-specified) is preserved as-is.
    Frozen dataclass — original script is not mutated.
    """
    new_scenes = []
    for scene in script.scenes:
        if _should_apply_punch_zoom(scene):
            new_scenes.append(
                replace(
                    scene,
                    transition=TransitionConfig(
                        type="punch-zoom",
                        duration=PUNCH_ZOOM_DURATION_SECONDS,
                    ),
                )
            )
        else:
            new_scenes.append(scene)
    return replace(script, scenes=tuple(new_scenes))
