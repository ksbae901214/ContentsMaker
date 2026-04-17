"""E2E 통합 스모크 — Quick Win 8개가 함께 동작하는지 검증.

각 QW를 개별 테스트는 통과시켰지만, 합쳐서 단일 파이프라인에 흘렸을 때
서로 깨지 않는지(스크립트 → auto_* 후처리 → Remotion props) 한 번에
검증한다. 영상 렌더는 비용 큼 — props 직전까지만 확인.

검증 범위:
- QW-01 hook 씬 hook=True 보존
- QW-02 highlight_category 보존
- QW-03 자막 외곽선은 컴포넌트 단계라 Python에선 검증 X (시각 검증 별도)
- QW-04 auto_assign_sfx 적용 (모든 씬에 SFX)
- QW-05 outro_template OUTRO_DURATION_SECONDS 일관성
- QW-06 auto_assign_transitions: high/hook 씬에 punch-zoom
- QW-07 find_hook_scene + intro_bgm_for_emotion: hook 있을 때 BGM 매칭
- QW-08 metadata_generator: 클릭베이트 가드 통과
"""
from __future__ import annotations

from src.analyzer.script_models import (
    AudioConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.video.bgm_matcher import find_hook_scene, intro_bgm_for_emotion
from src.video.outro_template import OUTRO_DURATION_SECONDS, OUTRO_SCENE_ID
from src.video.sfx_matcher import auto_assign_sfx
from src.video.transition_matcher import (
    PUNCH_ZOOM_DURATION_SECONDS,
    auto_assign_transitions,
)


def _typical_political_script() -> ShortsScript:
    """현실적인 NATV 정치 쇼츠 스크립트 — hook + 본문 + 결론."""
    return ShortsScript(
        metadata=Metadata(
            title="국회 4/15 본회의 발언 정리",
            emotion_type="angry",
            duration=30.0,
            source_type="political",
        ),
        scenes=(
            # QW-01 hook 씬
            Scene(id=1, timestamp=0, duration=2, type="title",
                  text="1분 정리", voice_text="1분 정리",
                  emphasis="high",
                  highlight_words=("1분",),
                  hook=True,
                  highlight_category="fact"),
            # 핵심 발언
            Scene(id=2, timestamp=2, duration=4, type="body",
                  text="국회 본회의\n발언 핵심", voice_text="본회의 발언 핵심을 봅시다",
                  emphasis="high",
                  highlight_words=("본회의", "핵심"),
                  highlight_category="fact"),
            # 비판 해설
            Scene(id=3, timestamp=6, duration=4, type="body",
                  text="문제 지적\n부분 분석", voice_text="문제 지적 부분을 봅시다",
                  emphasis="high",
                  highlight_words=("문제 지적",),
                  highlight_category="criticism"),
            # 마무리
            Scene(id=4, timestamp=10, duration=4, type="body",
                  text="결론과 의미", voice_text="결론과 의미를 정리합니다",
                  emphasis="medium",
                  highlight_words=("결론",)),
        ),
        audio=AudioConfig(tts_script="1분 정리. 본회의 발언. 문제 지적. 결론."),
    )


def test_all_quickwins_apply_together():
    """모든 자동화 함수를 순차 적용해 충돌 없이 ShortsScript에 모두 반영된다."""
    script = _typical_political_script()

    # QW-04 → QW-06 순서 (renderer.py와 동일)
    script = auto_assign_sfx(script)
    script = auto_assign_transitions(script)

    # QW-01 hook 보존
    assert script.scenes[0].hook is True
    # QW-02 highlight_category 보존
    assert script.scenes[0].highlight_category == "fact"
    assert script.scenes[2].highlight_category == "criticism"
    assert script.scenes[3].highlight_category == "neutral"

    # QW-04 모든 씬에 SFX 자동 할당
    for scene in script.scenes:
        assert len(scene.sfx) >= 1, f"scene {scene.id}: SFX 누락"
        assert scene.sfx[0].name.startswith("sfx/qw04_")

    # QW-06 hook + emphasis=high 씬에 punch-zoom
    assert script.scenes[0].transition is not None
    assert script.scenes[0].transition.type == "punch-zoom"
    assert script.scenes[0].transition.duration == PUNCH_ZOOM_DURATION_SECONDS
    assert script.scenes[1].transition.type == "punch-zoom"  # high
    assert script.scenes[2].transition.type == "punch-zoom"  # high
    # medium emphasis는 punch-zoom 받지 않음 (None 또는 다른 타입)
    s4 = script.scenes[3].transition
    assert s4 is None or s4.type != "punch-zoom"

    # QW-07 hook 있으니 인트로 BGM 매칭됨
    hook = find_hook_scene(script)
    assert hook is not None
    assert hook.id == 1
    track = intro_bgm_for_emotion(script.metadata.emotion_type)
    assert track.endswith(".mp3")


def test_outro_consistency_qw05():
    """QW-05 outro 상수가 적절한 값."""
    assert OUTRO_DURATION_SECONDS > 0
    assert OUTRO_SCENE_ID == -1


def test_clickbait_guard_qw08_blocks_input():
    """QW-08 metadata_generator의 클릭베이트 단어가 사실형으로 치환된다."""
    from src.upload.metadata_generator import (
        BANNED_CLICKBAIT_WORDS,
        _sanitize_clickbait,
    )
    # 금지어 1개는 반드시 정의되어 있어야 함
    assert len(BANNED_CLICKBAIT_WORDS) >= 5
    # 금지어 들어간 입력 → 치환 결과에 그대로 남으면 안 됨
    result, modified = _sanitize_clickbait("이거 충격 발언입니다")
    assert modified is True
    assert "충격" not in result, (
        f"_sanitize_clickbait가 '충격'을 그대로 둠 — QW-08 가드 실패: {result!r}"
    )


def test_quickwins_idempotent():
    """auto_* 함수는 idempotent — 두 번 호출해도 결과 동일."""
    script = _typical_political_script()
    once = auto_assign_transitions(auto_assign_sfx(script))
    twice = auto_assign_transitions(auto_assign_sfx(once))
    assert once.scenes[0].transition.type == twice.scenes[0].transition.type
    assert once.scenes[0].sfx[0].name == twice.scenes[0].sfx[0].name


def test_serializable_to_dict():
    """모든 QW가 적용된 스크립트가 직렬화 가능."""
    script = _typical_political_script()
    script = auto_assign_sfx(script)
    script = auto_assign_transitions(script)
    d = script.to_dict()
    # JSON 직렬화 가능 확인
    import json
    json_str = json.dumps(d, ensure_ascii=False)
    assert "hook" in json_str
    assert "punch-zoom" in json_str
    assert "highlight_category" in json_str
