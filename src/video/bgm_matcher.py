"""QW-07 — Auto-assign intro buildup BGM to hook scenes.

Why:
    정치 유튜브 §1.2 + §4.1 패턴 — 첫 1.5~2.5초 hook 구간에 인트로 빌드업
    BGM(긴장감 점진 상승)을 깔아 시각 임팩트와 청각 임팩트를 일치시킨다.
    기존 use_bgm 플래그는 영상 전체에 단일 BGM만 깔았다.

자산:
    public/bgm/intro_buildup_*.mp3 (CC0 또는 라이선스 명시,
    public/bgm/LICENSES.md 참조)
    Remotion 은 staticFile("bgm/intro_buildup_xxx.mp3") 로 직접 로드.

매칭 규칙:
    - hook=True 씬이 있으면 emotion 별로 트랙 선택
    - 트랙은 INTRO_BGM_TRACKS 인덱스 회전 (단조로움 방지)
    - hook 씬이 없으면 None — 인트로 BGM 미적용
"""
from __future__ import annotations

from src.analyzer.script_models import Scene, ShortsScript
from src.config.settings import PROJECT_ROOT

PUBLIC_BGM_DIR = PROJECT_ROOT / "public" / "bgm"

# 사전 수집된 인트로 빌드업 트랙. Remotion staticFile() 기준 상대 경로.
INTRO_BGM_TRACKS: tuple[str, ...] = (
    "intro_buildup_alien_trailer.mp3",
    "intro_buildup_suspense.mp3",
)

# emotion → 트랙 인덱스 매핑. 두 트랙을 톤에 맞게 분배.
_EMOTION_TRACK_INDEX: dict[str, int] = {
    "angry": 0,        # alien_trailer (강한 긴장)
    "relatable": 0,    # alien_trailer (분석/공감 — 진중)
    "touching": 1,     # suspense (부드러운 빌드업)
    "funny": 1,        # suspense (가벼운 긴장)
}


def intro_bgm_for_emotion(emotion: str) -> str:
    """Emotion 에 맞는 인트로 빌드업 트랙 파일명 반환.

    미지의 emotion 은 첫 트랙으로 폴백한다.
    """
    idx = _EMOTION_TRACK_INDEX.get(emotion, 0)
    if idx >= len(INTRO_BGM_TRACKS):
        idx = 0
    return INTRO_BGM_TRACKS[idx]


def find_hook_scene(script: ShortsScript) -> Scene | None:
    """ShortsScript에서 첫 번째 hook=True 씬을 반환. 없으면 None."""
    for scene in script.scenes:
        if scene.hook is True:
            return scene
    return None
