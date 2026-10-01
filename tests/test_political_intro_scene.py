"""인트로 씬(훅 앞 상황 설명 TTS) 테스트 — V2.1 / V2.2 공통.

`scenes[0]` 에 `"intro": true` 를 달면 그 씬이 원본 육성 훅보다 **먼저** 나온다.
등장인물이 여럿인 소재(청문회·국정감사)는 맥락 없이 첫 육성을 들려주면
누가 누구에게 하는 말인지 몰라 이탈한다는 사용자 지시(2026-09-15).

036 "훅은 가장 센 컷" 규칙과 맞바꾸는 것이라 인트로는 **1개·4초 상한**으로 묶는다.
`intro` 키가 없으면 전 경로가 기존 동작 그대로여야 한다 (회귀 보호).
"""
from __future__ import annotations

import pytest

from scripts.render_political_v2_1 import (
    INTRO_MAX_SEC, build_insert_silence_filter, build_script,
    config_scene_index, hook_scene_id, intro_offset, intro_warnings,
    is_intro_scene, shift_timings_after, with_hook_timing,
)
from scripts.render_political_v2_1 import validate_config as v21_validate
from scripts.render_political_v2_2 import (
    build_script as v22_build_script,
    clip_max_sec, first_clip_index,
)
from scripts.render_political_v2_2 import validate_config as v22_validate
from scripts.shorts_format import PROFILE_V3, V2_1, V2_2, rules_for_format


def v21_cfg(**over) -> dict:
    cfg = {
        "slug": "test_intro_v21",
        "title": "상단 배너 제목",
        "yt_title": "죽창 들자던 조국, 이젠 말끝으로 사상검증",
        "persons": ["조국"],
        "sources": {"a": {"query": "인물 A 발언"}, "b": {"url": "https://y/x"}},
        "scenes": [
            {"intro": True, "source": "a",
             "text": "김승원 법무부 장관\n후보자 인사청문회",
             "voice": "오늘 열린 김승원 법무부 장관 후보자 인사청문회입니다."},
            {"source": "b", "text": "본문 자막", "voice": "본문 나레이션입니다."},
        ],
        "hook": {"source": "a", "start_sec": 10.0, "duration": 3.0,
                 "text": "훅\n원본 발언"},
    }
    cfg.update(over)
    return cfg


def v22_cfg(**over) -> dict:
    cfg = {
        "slug": "test_intro_v22",
        "title": "상단 배너 제목",
        "yt_title": "죽창 들자던 조국, 이젠 말끝으로 사상검증",
        "persons": ["조국"],
        "sources": {"a": {"query": "인물 A 발언"}, "b": {"url": "https://y/x"}},
        "scenes": [
            {"intro": True, "mode": "tts", "source": "a",
             "text": "김승원 법무부 장관\n후보자 인사청문회",
             "voice": "오늘 열린 김승원 법무부 장관 후보자 인사청문회입니다."},
            {"mode": "clip", "source": "a", "start_sec": 10.0, "duration": 5.0,
             "text": "훅\n원본 발언"},
            {"mode": "clip", "source": "b", "start_sec": 42.0, "duration": 4.0,
             "text": "반박 발언"},
            {"mode": "tts", "source": "a", "text": "논평 자막",
             "voice": "논평 나레이션입니다."},
        ],
    }
    cfg.update(over)
    return cfg


# ── 인트로 판별 ─────────────────────────────────────────────────────
class TestIntroDetection:
    def test_plain_scene_is_not_intro(self):
        assert is_intro_scene({"text": "x", "voice": "y"}) is False

    def test_flagged_scene_is_intro(self):
        assert is_intro_scene({"intro": True}) is True

    def test_offset_one_when_scene0_flagged(self):
        assert intro_offset(v21_cfg()) == 1

    def test_offset_zero_without_flag(self):
        cfg = v21_cfg()
        del cfg["scenes"][0]["intro"]
        assert intro_offset(cfg) == 0

    def test_offset_zero_on_empty_scenes(self):
        assert intro_offset({"scenes": []}) == 0
        assert intro_offset({}) == 0

    def test_hook_scene_id_follows_intro(self):
        assert hook_scene_id(v21_cfg()) == 1
        cfg = v21_cfg()
        del cfg["scenes"][0]["intro"]
        assert hook_scene_id(cfg) == 0


# ── 가드레일: 1개 · 4초 상한 ────────────────────────────────────────
class TestIntroGuards:
    def test_intro_on_later_scene_rejected(self):
        cfg = v21_cfg()
        cfg["scenes"][1]["intro"] = True
        with pytest.raises(ValueError, match="intro"):
            v21_validate(cfg)

    def test_two_intros_rejected_in_v22(self):
        cfg = v22_cfg()
        cfg["scenes"][3]["intro"] = True
        with pytest.raises(ValueError, match="intro"):
            v22_validate(cfg)

    def test_long_intro_warns(self):
        cfg = v21_cfg()
        cfg["scenes"][0]["voice"] = "가" * 200      # 4초를 훌쩍 넘김
        assert any("인트로" in w for w in intro_warnings(cfg))

    def test_short_intro_no_warning(self):
        assert intro_warnings(v21_cfg()) == []

    def test_intro_without_hook_warns(self):
        cfg = v21_cfg()
        del cfg["hook"]
        assert any("훅" in w for w in intro_warnings(cfg))

    def test_cap_is_four_seconds(self):
        assert INTRO_MAX_SEC == 4.0


# ── V2.1: 씬 순서 [인트로 → 훅 → 본문] ──────────────────────────────
class TestV21BuildScript:
    def test_intro_precedes_hook(self):
        script = build_script(v21_cfg(), hook_dur=3.0)
        assert [s.id for s in script.scenes] == [0, 1, 2]
        assert script.scenes[0].voice_text.startswith("오늘 열린")
        assert script.scenes[1].voice_text == ""          # 훅 = 원본 육성
        assert script.scenes[2].voice_text == "본문 나레이션입니다."

    def test_hook_scene_keeps_hook_styling(self):
        s1 = build_script(v21_cfg(), hook_dur=3.0).scenes[1]
        assert s1.hook is True
        assert s1.type == "title"
        assert s1.subtitle_color == "yellow"
        assert s1.duration == 3.0
        assert s1.text == "훅\n원본 발언"

    def test_intro_scene_is_plain_body(self):
        s0 = build_script(v21_cfg(), hook_dur=3.0).scenes[0]
        assert s0.hook is False
        assert s0.type == "body"
        assert s0.subtitle_color == "white"

    def test_tts_script_order_intro_then_body(self):
        script = build_script(v21_cfg(), hook_dur=3.0)
        tts = script.audio.tts_script
        assert tts.index("오늘 열린") < tts.index("본문 나레이션")
        assert "원본 발언" not in tts

    def test_without_intro_unchanged(self):
        """회귀 보호 — intro 키가 없으면 훅이 그대로 scene 0."""
        cfg = v21_cfg()
        del cfg["scenes"][0]["intro"]
        script = build_script(cfg, hook_dur=3.0)
        assert script.scenes[0].hook is True
        assert script.scenes[0].voice_text == ""
        assert [s.id for s in script.scenes] == [0, 1, 2]

    def test_without_hook_intro_is_just_first_scene(self):
        cfg = v21_cfg()
        del cfg["hook"]
        script = build_script(cfg, hook_dur=0.0)
        assert len(script.scenes) == 2
        assert script.scenes[0].voice_text.startswith("오늘 열린")


# ── 씬 id → config 인덱스 매핑 ──────────────────────────────────────
class TestConfigSceneIndex:
    def test_no_hook_is_identity(self):
        assert [config_scene_index(i, hook_sid=-1) for i in range(3)] == [0, 1, 2]

    def test_hook_first_shifts_all(self):
        assert [config_scene_index(i, hook_sid=0) for i in (1, 2, 3)] == [0, 1, 2]

    def test_intro_then_hook(self):
        # 씬 0=인트로(cfg 0), 1=훅(cfg 없음), 2=본문(cfg 1)
        assert config_scene_index(0, hook_sid=1) == 0
        assert config_scene_index(2, hook_sid=1) == 1
        assert config_scene_index(3, hook_sid=1) == 2


# ── 오디오: 인트로 뒤에 훅 길이만큼 무음 삽입 ───────────────────────
class TestShiftTimingsAfter:
    def test_only_later_scenes_shift(self):
        timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 3700},
                   {"scene_id": 2, "start_ms": 3700, "end_ms": 9000}]
        out = shift_timings_after(timings, at_ms=3700, offset_ms=3000)
        assert out[0] == {"scene_id": 0, "start_ms": 0, "end_ms": 3700}
        assert out[1] == {"scene_id": 2, "start_ms": 6700, "end_ms": 12000}

    def test_outro_shifts_too(self):
        timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 1000},
                   {"scene_id": -1, "start_ms": 5000, "end_ms": 9000}]
        out = shift_timings_after(timings, at_ms=1000, offset_ms=2000)
        assert out[1]["start_ms"] == 7000

    def test_original_not_mutated(self):
        timings = [{"scene_id": 2, "start_ms": 4000, "end_ms": 9000}]
        shift_timings_after(timings, at_ms=0, offset_ms=3000)
        assert timings[0]["start_ms"] == 4000


class TestInsertSilenceFilter:
    def test_splits_at_cut_point_and_delays_tail(self):
        f = build_insert_silence_filter(at_ms=3700, pad_ms=3000)
        assert "atrim=end=3.700" in f
        assert "atrim=start=3.700" in f
        assert "adelay=6700:all=1" in f     # at + pad
        assert "amix=inputs=2:normalize=0" in f
        assert f.endswith("[aout]")

    def test_zero_cut_point_is_plain_front_pad(self):
        f = build_insert_silence_filter(at_ms=0, pad_ms=3000)
        assert "adelay=3000:all=1" in f
        assert "amix" not in f             # 앞 패딩은 분할이 필요 없다


# ── V2.2: 첫 clip 씬이 훅 ───────────────────────────────────────────
class TestV22Intro:
    def test_valid_intro_config_passes(self):
        assert v22_validate(v22_cfg()) == []

    def test_first_clip_index_follows_intro(self):
        assert first_clip_index(v22_cfg()) == 1
        cfg = v22_cfg()
        cfg["scenes"] = cfg["scenes"][1:]
        assert first_clip_index(cfg) == 0

    def test_tts_scene0_without_intro_flag_still_rejected(self):
        cfg = v22_cfg()
        del cfg["scenes"][0]["intro"]
        with pytest.raises(ValueError, match="clip"):
            v22_validate(cfg)

    def test_scene_after_intro_must_be_clip(self):
        cfg = v22_cfg()
        cfg["scenes"][1] = {"mode": "tts", "source": "a", "text": "x",
                            "voice": "나레이션."}
        with pytest.raises(ValueError, match="clip"):
            v22_validate(cfg)

    def test_hook_styling_moves_to_first_clip(self):
        script = v22_build_script(v22_cfg(), {1: 5.0, 2: 4.0})
        assert script.scenes[0].hook is False
        assert script.scenes[0].type == "body"
        assert script.scenes[1].hook is True
        assert script.scenes[1].type == "title"
        assert script.scenes[1].subtitle_color == "yellow"
        assert script.scenes[1].subtitle_position == "bottom"

    def test_hook_text_falls_back_to_yt_title(self):
        cfg = v22_cfg()
        del cfg["scenes"][1]["text"]
        script = v22_build_script(cfg, {1: 5.0, 2: 4.0})
        assert script.scenes[1].text == cfg["yt_title"]

    def test_intro_voice_included_in_tts_script(self):
        script = v22_build_script(v22_cfg(), {1: 5.0, 2: 4.0})
        tts = script.audio.tts_script
        assert tts.index("오늘 열린") < tts.index("논평 나레이션")

    def test_hook_clip_cap_moves_with_intro(self):
        # 훅은 10s 상한, 본문 클립은 12s
        assert clip_max_sec(1, hook_idx=1) == 10.0
        assert clip_max_sec(2, hook_idx=1) == 12.0

    def test_clip_max_sec_default_unchanged(self):
        assert clip_max_sec(0) == 10.0
        assert clip_max_sec(1) == 12.0

    def test_over_cap_hook_clip_rejected_at_new_index(self):
        cfg = v22_cfg()
        cfg["scenes"][1]["duration"] = 11.0      # 훅 상한 10s 초과
        with pytest.raises(ValueError, match="duration"):
            v22_validate(cfg)

    def test_intro_not_counted_as_commentary(self):
        """인트로는 논평이 아니다 — TTS 논평 권장 개수(최대 2개)에서 빠진다."""
        cfg = v22_cfg()
        cfg["scenes"].append({"mode": "tts", "source": "a", "text": "정리",
                              "voice": "두 번째 논평입니다."})
        assert not any("tts 씬" in w for w in v22_validate(cfg))

    def test_intro_only_still_needs_commentary(self):
        cfg = v22_cfg()
        del cfg["scenes"][3]          # 유일한 논평 씬 제거
        with pytest.raises(ValueError, match="논평"):
            v22_validate(cfg)

    def test_body_clip_over_10s_allowed(self):
        cfg = v22_cfg()
        cfg["scenes"][2]["duration"] = 11.0      # 본문 상한 12s 이내
        v22_validate(cfg)


# ── 훅 씬 타이밍 주입 ────────────────────────────────────────────────
class TestWithHookTiming:
    """훅 씬은 voice 가 없어 TTS 타이밍에 안 잡힌다.

    renderer.py 는 timing_map 에 없는 씬의 timestamp 를 build_script 값
    (`float(sid)`) 그대로 둔다. 훅이 scene 0 일 때는 0.0 이라 우연히 맞지만,
    인트로가 앞에 오면 훅 sid=1 → timestamp 1.0 초가 되어 인트로 자막을 덮는다
    (2026-09-15 렌더 실측). 그래서 훅 구간을 명시적으로 넣어 준다.
    """

    def test_hook_timing_inserted_after_intro(self):
        timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 3700},
                   {"scene_id": 2, "start_ms": 10100, "end_ms": 16700}]
        out = with_hook_timing(timings, hook_sid=1, at_ms=3700, hook_ms=6400)
        hook = next(t for t in out if t["scene_id"] == 1)
        assert hook == {"scene_id": 1, "start_ms": 3700, "end_ms": 10100}

    def test_existing_timings_untouched(self):
        timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 3700}]
        out = with_hook_timing(timings, hook_sid=1, at_ms=3700, hook_ms=6400)
        assert {"scene_id": 0, "start_ms": 0, "end_ms": 3700} in out
        assert len(out) == 2

    def test_original_not_mutated(self):
        timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 3700}]
        with_hook_timing(timings, hook_sid=1, at_ms=3700, hook_ms=6400)
        assert len(timings) == 1

    def test_hook_first_needs_no_entry(self):
        """훅이 scene 0 이면 기존 동작(timestamp 0.0)이 이미 맞다 — 건드리지 않는다."""
        timings = [{"scene_id": 1, "start_ms": 3000, "end_ms": 9000}]
        assert with_hook_timing(timings, hook_sid=0, at_ms=0, hook_ms=3000) == timings


# ── 인트로 = V2.1/V2.2 기본 지침 (사용자 확정 2026-09-15) ────────────
class TestIntroIsDefaultRule:
    """훅 앞 한 줄 상황 설명은 V2 포맷의 **기본**이다.

    035/036/039/040 과 같은 방침 — 경고만 하고 차단하지 않는다
    (기존 config 는 유지, 신규만 기준을 적용).
    """

    def test_v2_formats_require_intro(self):
        assert rules_for_format(V2_1).intro_required is True
        assert rules_for_format(V2_2).intro_required is True

    def test_profile_v3_exempt(self):
        # 041 V3.0 은 훅 육성 뒤 전체 나레이션 구조라 별도 상황 설명이 중복된다
        assert rules_for_format(PROFILE_V3).intro_required is False

    def test_missing_intro_warns_on_v21(self):
        cfg = v21_cfg()
        del cfg["scenes"][0]["intro"]
        assert any("인트로" in w for w in intro_warnings(cfg))

    def test_missing_intro_warns_on_v22(self):
        cfg = v22_cfg()
        cfg["scenes"][0] = {"mode": "clip", "source": "a", "start_sec": 5.0,
                            "duration": 4.0, "text": "훅"}
        assert any("인트로" in w for w in intro_warnings(cfg))

    def test_present_intro_no_warning(self):
        assert intro_warnings(v21_cfg()) == []

    def test_profile_v3_missing_intro_silent(self):
        cfg = v21_cfg(format="profile_v3")
        del cfg["scenes"][0]["intro"]
        assert intro_warnings(cfg) == []

    def test_gate_off_bypasses(self):
        cfg = v21_cfg(intro_gate="off")
        del cfg["scenes"][0]["intro"]
        assert intro_warnings(cfg) == []

    def test_checklist_mentions_intro(self):
        for fmt in (V2_1, V2_2):
            assert any("인트로" in c for c in rules_for_format(fmt).checklist)

    def test_never_blocks_render(self):
        """경고지 차단이 아니다 — 인트로 없는 기존 config 도 validate 통과."""
        cfg = v21_cfg()
        del cfg["scenes"][0]["intro"]
        v21_validate(cfg)
