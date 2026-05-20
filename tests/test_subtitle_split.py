"""Tests for src/editor/subtitle_split.py — 공용 자막 분할 + 줄바꿈 모듈.

2026-05-20 Phase 7: political_planner.py에서 추출. 모든 영상 생성 경로가 공유.
"""
from __future__ import annotations

from src.analyzer.script_models import (
    AudioConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.editor.subtitle_split import (
    _MAX_SUBTITLE_CHARS,
    _insert_linebreak,
    _split_subtitle_segments,
    apply_subtitle_split,
)


def _make_script(scenes: list[Scene]) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(title="t", emotion_type="angry", duration=30),
        scenes=tuple(scenes),
        audio=AudioConfig(tts_script="x"),
    )


class TestApplySubtitleSplit:
    def test_short_scene_gets_linebreak_only(self):
        """15~28자 씬은 명시적 '\\n' 삽입만 — 분할 안 함, group_id None."""
        scene = Scene(
            id=0, timestamp=0, duration=3, type="body",
            text="서울시장 후보들의 부동산 공급 정책을 비교",  # 25자
            voice_text="서울시장 후보들의 부동산 공급 정책을 비교",
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        assert len(result.scenes) == 1
        assert "\n" in result.scenes[0].text
        assert result.scenes[0].subtitle_group_id is None  # 분할 없음 → 그룹 없음

    def test_long_scene_splits_with_group_id(self):
        """28자 초과 씬은 자식들로 분할, 동일 group_id 부여."""
        long_text = "사업성을 높여서 공급을 늘리자는 건 같은데 재건축 재개발에 적대적이었던 민주당 출신이 신속 공급을 말합니다"
        scene = Scene(
            id=0, timestamp=0, duration=6, type="body",
            text=long_text, voice_text=long_text,
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        assert len(result.scenes) >= 2
        gids = {s.subtitle_group_id for s in result.scenes}
        assert len(gids) == 1 and None not in gids
        # 첫 자식 group_first=True
        assert result.scenes[0].subtitle_group_first is True
        for s in result.scenes[1:]:
            assert s.subtitle_group_first is False

    def test_preserves_v2_fields(self):
        """subtitle_color / subtitle_emphasis / hook / image_query 모두 자식에 전파."""
        scene = Scene(
            id=0, timestamp=0, duration=6, type="body",
            text="아주 긴 텍스트가 여기에 들어가서 분할이 필요한 정도로 길게 작성된 자막",
            voice_text="x",
            subtitle_color="red",
            subtitle_emphasis=True,
            hook=True,
            highlight_category="criticism",
            image_query="검색어",
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        assert len(result.scenes) >= 2
        for s in result.scenes:
            assert s.subtitle_color == "red"
            assert s.subtitle_emphasis is True
            assert s.highlight_category == "criticism"
            assert s.image_query == "검색어"
        # hook은 첫 자식만 (펀치줌 1회만 발동)
        assert result.scenes[0].hook is True
        for s in result.scenes[1:]:
            assert s.hook is False

    def test_idempotent_on_already_split(self):
        """이미 분할된 스크립트에 다시 호출해도 안전 (각 씬 max_chars 이내)."""
        scene = Scene(
            id=0, timestamp=0, duration=3, type="body",
            text="짧은 자막", voice_text="짧은 자막",
            subtitle_group_id=5, subtitle_group_first=True,
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        # 그룹 ID는 유지 (재할당 안 함)
        assert result.scenes[0].subtitle_group_id == 5

    def test_multiple_scenes_get_different_group_ids(self):
        """여러 긴 씬이 분할되면 각자 다른 group_id."""
        scenes = [
            Scene(id=0, timestamp=0, duration=6, type="body",
                  text="사업성을 높여서 공급을 늘리자는 건 같은데 재건축 재개발에 적대적이었던",
                  voice_text="x"),
            Scene(id=1, timestamp=6, duration=6, type="body",
                  text="이번 지방선거 후보자 4명 중 1명이 다주택자라는 충격적 결과가 발표",
                  voice_text="y"),
        ]
        script = _make_script(scenes)
        result = apply_subtitle_split(script)
        # 두 그룹의 자식들이 서로 다른 group_id
        gid0 = result.scenes[0].subtitle_group_id
        gid_last = result.scenes[-1].subtitle_group_id
        assert gid0 is not None
        assert gid_last is not None
        assert gid0 != gid_last

    def test_voice_text_per_child(self):
        """각 자식의 voice_text가 자기 자막 텍스트 (\\n 제거)."""
        long_text = "이번 지방선거 후보자 4명 중 1명이 다주택자라는 충격적 결과"
        scene = Scene(
            id=0, timestamp=0, duration=6, type="body",
            text=long_text, voice_text=long_text,
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        for s in result.scenes:
            expected = s.text.replace("\n", " ").strip()
            assert s.voice_text == expected

    def test_duration_distributed_by_chars(self):
        """자식 duration은 글자수 비율로 분배."""
        long_text = "AAA BBBB CCCCC DDDDDD EEEEEEE 여덟글자입니다 아홉글자입니다요"
        scene = Scene(
            id=0, timestamp=0, duration=10, type="body",
            text=long_text, voice_text=long_text,
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        # 모든 자식 duration 합 = 원본 duration (반올림 오차 허용)
        total_dur = sum(s.duration for s in result.scenes)
        assert abs(total_dur - 10.0) < 0.5

    def test_empty_text_scene_preserved(self):
        """빈 텍스트 씬은 그대로 보존 (분할 X)."""
        scene = Scene(
            id=0, timestamp=0, duration=2, type="title",
            text="", voice_text="",
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        assert len(result.scenes) == 1

    def test_existing_linebreak_preserved_when_short(self):
        """이미 '\\n' 있고 각 줄 28자 이내면 그대로 유지."""
        scene = Scene(
            id=0, timestamp=0, duration=3, type="body",
            text="첫 줄입니다\n둘째 줄입니다", voice_text="x",
        )
        script = _make_script([scene])
        result = apply_subtitle_split(script)
        assert len(result.scenes) == 1
        assert "\n" in result.scenes[0].text


class TestPureFunctions:
    def test_split_subtitle_short_text(self):
        assert _split_subtitle_segments("짧음") == ["짧음"]

    def test_split_subtitle_long_text(self):
        text = "이번 지방선거 후보자 4명 중 1명이 다주택자라는 충격적 결과"
        segs = _split_subtitle_segments(text)
        assert len(segs) >= 2

    def test_insert_linebreak_short(self):
        assert _insert_linebreak("짧음") == "짧음"

    def test_insert_linebreak_long(self):
        out = _insert_linebreak("이번 정치권에서는 새로운 소식이 발표됨")
        assert "\n" in out

    def test_max_chars_constant(self):
        assert _MAX_SUBTITLE_CHARS == 28
