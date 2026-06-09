"""T011 [US1]: TTS 락인 가드 (SC-008, SC-013).

- VOICE = "ko-KR-InJoonNeural" 모듈 상수 어설션 (변경 시 fail)
- RATE = "+22%" 모듈 상수 어설션
- INTER_SCENE_GAP_MS = 300 모듈 상수 어설션
- synthesize() 시그니처에 voice/rate/gap 인자 부재 (호출 측 변경 불가)

RED 상태 — T018 구현 후 GREEN.
"""
from __future__ import annotations

import inspect

import pytest


def test_voice_constant_lockin() -> None:
    """V1 락인 보이스 고정."""
    from src.jpolitics.tts.voice import VOICE

    assert VOICE == "ko-KR-InJoonNeural"


def test_rate_constant_lockin() -> None:
    """V1 락인 속도 고정."""
    from src.jpolitics.tts.voice import RATE

    assert RATE == "+22%"


def test_inter_scene_gap_ms_lockin() -> None:
    """FR-036: 씬 간 무음 300 ms 고정."""
    from src.jpolitics.tts.voice import INTER_SCENE_GAP_MS

    assert INTER_SCENE_GAP_MS == 300


def test_synthesize_signature_has_no_voice_rate_gap_params() -> None:
    """synthesize() 시그니처에 voice/rate/gap 인자 부재 (호출 측 변경 진입점 차단)."""
    from src.jpolitics.tts.voice import synthesize

    sig = inspect.signature(synthesize)
    forbidden_params = {"voice", "rate", "gap", "gap_ms", "tts_voice", "tts_rate"}
    actual_params = set(sig.parameters.keys())
    overlap = forbidden_params & actual_params
    assert not overlap, (
        f"synthesize() must not accept voice/rate/gap params (lockin breach): {overlap}"
    )


def test_scene_timing_dataclass_exists() -> None:
    """SceneTiming 데이터클래스 export."""
    from src.jpolitics.tts.voice import SceneTiming

    timing = SceneTiming(scene_id=0, start_ms=0, end_ms=3000)
    assert timing.scene_id == 0
    assert timing.start_ms == 0
    assert timing.end_ms == 3000


def test_constants_match_module_constants() -> None:
    """TTS 모듈 상수와 jpolitics.constants 모듈 상수 일치."""
    from src.jpolitics import constants
    from src.jpolitics.tts import voice

    assert voice.VOICE == constants.TTS_VOICE
    assert voice.RATE == constants.TTS_RATE
    assert voice.INTER_SCENE_GAP_MS == constants.INTER_SCENE_GAP_MS
