"""QW-04 — Auto-assign cut transition SFX (whoosh / impact / chime).

Why:
    정치 유튜브 표준 패턴(§4.2)은 모든 컷 전환에 짧은 SFX(주로 whoosh)를
    배치한다. ContentsMaker 는 Scene.sfx 인프라가 이미 존재하지만 디폴트가
    비어있어 사용자가 수동 지정해야 했고, 결과적으로 거의 모든 영상이 무음
    컷이었다. 이 모듈은 씬 type / emphasis 만 보고 SFX를 자동 할당해서
    매 영상마다 일관된 청각 임팩트를 보장한다.

자산:
    public/sfx/qw04_*.mp3 (Mixkit 라이선스, public/sfx/LICENSES.md 참조)
    Remotion 은 staticFile("sfx/qw04_xxx.mp3") 로 직접 로드 — 별도 복사 불필요.

매칭 규칙:
    - type=="title"           → impact (오프닝 punch)
    - emphasis=="high"        → impact (강조 발언)
    - 그 외                   → whoosh (인덱스로 회전, 단조로움 방지)
    - 사용자 수동 지정 sfx 가 있으면 보존 (덮어쓰지 않음)
"""
from __future__ import annotations

from dataclasses import replace

from src.analyzer.script_models import Scene, ShortsScript, SfxConfig

# Remotion 은 staticFile() 로 public/ 기준 상대경로를 받는다 → "sfx/" prefix 유지.
WHOOSH_SOUNDS: tuple[str, ...] = (
    "sfx/qw04_whoosh_cinematic",
    "sfx/qw04_whoosh_fast",
    "sfx/qw04_whoosh_windy",
)
IMPACT_SOUND: str = "sfx/qw04_impact_big"
DING_SOUND: str = "sfx/qw04_ding_crystal"

# 볼륨 가이드(§4.1): 효과음 -10 ~ -15 dB 정도. 스케일에서 0.18~0.25 가 안전.
_WHOOSH_VOLUME = 0.18
_IMPACT_VOLUME = 0.25


def _pick_sfx_for_scene(scene: Scene, index: int) -> tuple[SfxConfig, ...]:
    """Pick SFX for a single scene based on its role and position."""
    if scene.type == "title":
        return (
            SfxConfig(
                name=IMPACT_SOUND,
                category="emphasis",
                offset_ms=0,
                volume=_IMPACT_VOLUME,
            ),
        )

    if scene.emphasis == "high":
        return (
            SfxConfig(
                name=IMPACT_SOUND,
                category="emphasis",
                offset_ms=0,
                volume=_IMPACT_VOLUME,
            ),
        )

    whoosh = WHOOSH_SOUNDS[index % len(WHOOSH_SOUNDS)]
    return (
        SfxConfig(
            name=whoosh,
            category="surprise",
            offset_ms=0,
            volume=_WHOOSH_VOLUME,
        ),
    )


def auto_assign_sfx(script: ShortsScript) -> ShortsScript:
    """Return a new ShortsScript with auto-assigned cut-transition SFX.

    Existing scene.sfx (user-specified) is preserved as-is.
    Frozen dataclass — original script is not mutated.
    """
    new_scenes = []
    for idx, scene in enumerate(script.scenes):
        if scene.sfx:
            new_scenes.append(scene)
            continue
        new_scenes.append(replace(scene, sfx=_pick_sfx_for_scene(scene, idx)))
    return replace(script, scenes=tuple(new_scenes))
