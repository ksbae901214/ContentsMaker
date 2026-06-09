"""T010 [US1]: JpoliticsScript / JpoliticsScene / AudioConfig 모델 검증.

RED 상태로 작성됨 — 구현(T016, T017)이 완료되면 GREEN.
"""
from __future__ import annotations

import dataclasses

import pytest


def test_jpolitics_script_module_importable() -> None:
    """T016 구현 후 `src.jpolitics.models.script`가 import 가능해야 함."""
    from src.jpolitics.models import script  # noqa: F401


def test_jpolitics_scene_is_frozen_dataclass() -> None:
    """JpoliticsScene은 frozen dataclass (헌법 VI 불변성)."""
    from src.jpolitics.models.script import JpoliticsScene

    assert dataclasses.is_dataclass(JpoliticsScene)
    # frozen 어설션 — 인스턴스 생성 후 필드 수정 시도 → FrozenInstanceError
    scene = JpoliticsScene(
        id=0,
        timestamp=0.0,
        duration=3.0,
        type="title",
        text="테스트",
        voice_text="테스트 발언입니다.",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        scene.id = 99  # type: ignore[misc]


def test_audio_config_has_lockin_literal_types() -> None:
    """JpoliticsAudioConfig의 voice/rate/gap/sfx/bgm은 모두 Literal 락인."""
    from src.jpolitics.models.script import JpoliticsAudioConfig

    audio = JpoliticsAudioConfig(tts_script="안녕하세요")
    assert audio.tts_voice == "ko-KR-InJoonNeural"
    assert audio.tts_rate == "+22%"
    assert audio.inter_scene_gap_ms == 300
    assert audio.sfx_enabled is False
    assert audio.bgm_enabled is False


def test_scene_layout_4_kinds() -> None:
    """visual_layout은 4종 중 하나여야 함."""
    from src.jpolitics.models.script import JpoliticsScene

    valid_layouts = ["normal", "vs_card", "grid_2x2", "data_card"]
    for layout in valid_layouts:
        scene = JpoliticsScene(
            id=0,
            timestamp=0.0,
            duration=3.0,
            type="body",
            text="t",
            voice_text="t",
            visual_layout=layout,  # type: ignore[arg-type]
        )
        assert scene.visual_layout == layout


def test_scene_transition_effect_lockin_none() -> None:
    """FR-035: transition_effect는 항상 "none"."""
    from src.jpolitics.models.script import JpoliticsScene

    scene = JpoliticsScene(
        id=0, timestamp=0.0, duration=3.0, type="body", text="t", voice_text="t"
    )
    assert scene.transition_effect == "none"


def test_scene_sfx_trigger_lockin_none() -> None:
    """FR-034: sfx_trigger는 항상 None."""
    from src.jpolitics.models.script import JpoliticsScene

    scene = JpoliticsScene(
        id=0, timestamp=0.0, duration=3.0, type="body", text="t", voice_text="t"
    )
    assert scene.sfx_trigger is None


def test_scene_roundtrip_to_dict_from_dict() -> None:
    """to_dict ↔ from_dict 라운드트립 유지."""
    from src.jpolitics.models.script import JpoliticsScene

    original = JpoliticsScene(
        id=1,
        timestamp=3.0,
        duration=4.5,
        type="body",
        text="발언",
        voice_text="이 발언은 중요합니다.",
        visual_layout="vs_card",
        subtitle_color="yellow",
        subtitle_emphasis=True,
        headline_pin=None,
        data_emphasis_color="red",
    )
    d = original.to_dict()
    restored = JpoliticsScene.from_dict(d)
    assert restored == original


def test_scene_from_dict_accepts_camelcase() -> None:
    """camelCase 키도 받아 deserialize."""
    from src.jpolitics.models.script import JpoliticsScene

    data = {
        "id": 0,
        "timestamp": 0.0,
        "duration": 3.0,
        "type": "title",
        "text": "헤드라인",
        "voiceText": "헤드라인 음성",
        "visualLayout": "vs_card",
        "subtitleColor": "yellow",
        "headlinePin": "테스트 헤드",
    }
    scene = JpoliticsScene.from_dict(data)
    assert scene.voice_text == "헤드라인 음성"
    assert scene.visual_layout == "vs_card"
    assert scene.headline_pin == "테스트 헤드"


def test_scene_max_duration_5_seconds() -> None:
    """씬 1개 길이는 5초 이내 (V1/V2 동일 제약)."""
    from src.jpolitics.models.script import JpoliticsScene

    # 정상 케이스 통과
    JpoliticsScene(
        id=0, timestamp=0.0, duration=5.0, type="body", text="t", voice_text="t"
    )

    # validate() 호출 시 5.01초는 fail (구현에서 raise ValueError)
    with pytest.raises(ValueError, match="duration"):
        JpoliticsScene(
            id=0,
            timestamp=0.0,
            duration=5.01,
            type="body",
            text="t",
            voice_text="t",
        ).validate()


def test_metadata_duration_30_to_60() -> None:
    """영상 전체 길이는 30~60초 (FR-016)."""
    from src.jpolitics.models.script import JpoliticsMetadata

    JpoliticsMetadata(
        title="t",
        source_type="jpolitics_youtube",
        duration_sec=45.0,
        created_at="2026-06-05T10:00:00",
    ).validate()

    with pytest.raises(ValueError):
        JpoliticsMetadata(
            title="t",
            source_type="jpolitics_youtube",
            duration_sec=29.9,
            created_at="2026-06-05T10:00:00",
        ).validate()

    with pytest.raises(ValueError):
        JpoliticsMetadata(
            title="t",
            source_type="jpolitics_youtube",
            duration_sec=60.5,
            created_at="2026-06-05T10:00:00",
        ).validate()


def test_script_module_exports_5_entities() -> None:
    """data-model.md E1-E5 5 엔티티 모두 export."""
    from src.jpolitics.models import script

    for name in (
        "JpoliticsScript",
        "JpoliticsScene",
        "JpoliticsMetadata",
        "JpoliticsAudioConfig",
        "JpoliticsBackgroundConfig",
    ):
        assert hasattr(script, name), f"{name} not exported"
