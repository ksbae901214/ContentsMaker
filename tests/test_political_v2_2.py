"""정치쇼츠 V2.2 (scripts/render_political_v2_2.py) 테스트 — 원본 육성 릴레이 포맷."""
from __future__ import annotations

import pytest

from scripts.render_political_v2_2 import (
    build_assemble_filter, build_script, build_timeline, clip_audio_ratio,
    clip_max_sec, resolve_clip_cut, scene_mode, validate_config,
)


def base_cfg(**over) -> dict:
    cfg = {
        "slug": "test_v22",
        "title": "상단 배너 제목",
        "yt_title": "죽창 들자던 조국, 이젠 말끝으로 사상검증",
        "persons": ["조국", "이준석"],
        "sources": {
            "a": {"query": "인물 A 발언"},
            "b": {"url": "https://youtube.com/watch?v=x"},
        },
        "scenes": [
            {"mode": "clip", "source": "a", "start_sec": 10.0, "duration": 3.0,
             "text": "훅\n원본 발언", "hl": ["훅"]},
            {"mode": "clip", "source": "b", "start_sec": 42.0, "duration": 4.0,
             "text": "반박 발언", "speaker": "이준석"},
            {"mode": "tts", "source": "a", "frac": 0.5, "color": "red",
             "emph": True, "text": "논평 자막", "voice": "논평 나레이션입니다.",
             "hl": ["논평"]},
            {"mode": "clip", "source": "a", "start_sec": 90.0, "duration": 5.0,
             "text": "재반박\n마무리 발언"},
        ],
    }
    cfg.update(over)
    return cfg


# ── scene mode ──────────────────────────────────────────────────────
class TestSceneMode:
    def test_default_is_tts(self):
        assert scene_mode({}) == "tts"

    def test_clip_kept(self):
        assert scene_mode({"mode": "clip"}) == "clip"


# ── config 검증 ─────────────────────────────────────────────────────
class TestValidateConfig:
    def test_valid_config_passes_no_warnings(self):
        assert validate_config(base_cfg()) == []

    def test_missing_required_key(self):
        cfg = base_cfg()
        del cfg["scenes"]
        with pytest.raises(ValueError, match="scenes"):
            validate_config(cfg)

    def test_unknown_mode_rejected(self):
        cfg = base_cfg()
        cfg["scenes"][1]["mode"] = "clipp"
        with pytest.raises(ValueError, match="mode"):
            validate_config(cfg)

    def test_scene0_must_be_clip(self):
        cfg = base_cfg()
        cfg["scenes"][0]["mode"] = "tts"
        cfg["scenes"][0]["voice"] = "나레이션"
        with pytest.raises(ValueError, match=r"scene\[0\]"):
            validate_config(cfg)

    def test_clip_duration_out_of_range(self):
        for bad in (0.5, 12.5):
            cfg = base_cfg()
            cfg["scenes"][1]["duration"] = bad
            with pytest.raises(ValueError, match="duration"):
                validate_config(cfg)

    def test_hook_clip_capped_at_10s_body_at_12s(self):
        # scene 0(훅)은 10s 상한 유지(스와이프 방어), 본문 클립은 문장 완결
        # 우선으로 12s까지 허용 (브리핑 끊어읽기 포즈 실측 반영)
        cfg = base_cfg()
        cfg["scenes"][1]["duration"] = 11.75
        validate_config(cfg)
        cfg2 = base_cfg()
        cfg2["scenes"][0]["duration"] = 11.0
        with pytest.raises(ValueError, match="duration"):
            validate_config(cfg2)

    def test_clip_source_not_in_sources(self):
        cfg = base_cfg()
        cfg["scenes"][1]["source"] = "nope"
        with pytest.raises(ValueError, match="source"):
            validate_config(cfg)

    def test_no_tts_scene_rejected(self):
        cfg = base_cfg()
        cfg["scenes"] = [s for s in cfg["scenes"] if s["mode"] == "clip"]
        with pytest.raises(ValueError, match="tts"):
            validate_config(cfg)

    def test_tts_missing_voice_rejected(self):
        cfg = base_cfg()
        del cfg["scenes"][2]["voice"]
        with pytest.raises(ValueError, match="voice"):
            validate_config(cfg)

    def test_bad_color_rejected(self):
        cfg = base_cfg()
        cfg["scenes"][2]["color"] = "green"
        with pytest.raises(ValueError, match="color"):
            validate_config(cfg)

    def test_clip_text_required_except_scene0(self):
        cfg = base_cfg()
        del cfg["scenes"][1]["text"]
        with pytest.raises(ValueError, match="text"):
            validate_config(cfg)

    def test_scene0_text_optional_falls_back_to_yt_title(self):
        cfg = base_cfg()
        del cfg["scenes"][0]["text"]
        validate_config(cfg)          # 에러 없음 — build_script에서 yt_title 폴백

    def test_three_tts_scenes_warn(self):
        cfg = base_cfg()
        extra = {"mode": "tts", "source": "a", "voice": "추가 나레이션",
                 "text": "추가"}
        cfg["scenes"] = cfg["scenes"] + [dict(extra), dict(extra)]
        warnings = validate_config(cfg)
        assert any("tts" in w.lower() for w in warnings)

    def test_single_clip_warns(self):
        cfg = base_cfg()
        cfg["scenes"] = [cfg["scenes"][0], cfg["scenes"][2]]
        warnings = validate_config(cfg)
        assert any("클립" in w for w in warnings)


# ── 클립 컷 계산 ────────────────────────────────────────────────────
class TestResolveClipCut:
    def test_explicit_start_sec(self):
        start, dur = resolve_clip_cut(
            {"start_sec": 10.0, "duration": 3.0}, 100.0, max_sec=10.0)
        assert (start, dur) == (10.0, 3.0)

    def test_duration_capped_at_max_sec(self):
        _, dur = resolve_clip_cut(
            {"start_sec": 0.0, "duration": 99.0}, 100.0, max_sec=12.0)
        assert dur == 12.0

    def test_body_clip_over_10s_kept(self):
        start, dur = resolve_clip_cut(
            {"start_sec": 102.85, "duration": 11.75}, 139.0, max_sec=12.0)
        assert start == 102.85
        assert dur == pytest.approx(11.7333, abs=1e-3)   # 30fps 격자 반올림

    def test_duration_quantized_to_30fps_grid(self):
        # 씬 경계가 정수 프레임에 떨어져야 립싱크 반프레임 오차가 없다
        _, dur = resolve_clip_cut(
            {"start_sec": 0.0, "duration": 7.25}, 100.0, max_sec=10.0)
        assert (dur * 30) == pytest.approx(round(dur * 30))
        assert dur == pytest.approx(218 / 30, abs=1e-6)  # 7.25s(217.5f) → 218프레임

    def test_clamped_when_source_short(self):
        start, dur = resolve_clip_cut(
            {"start_sec": 50.0, "duration": 3.0}, 4.0, max_sec=10.0)
        assert start + dur <= 4.0

    def test_max_by_scene_index(self):
        assert clip_max_sec(0) == 10.0
        assert clip_max_sec(1) == 12.0


# ── 타임라인 조립 (핵심) ────────────────────────────────────────────
def specs_from(*items) -> list[dict]:
    return [dict(scene_id=i, **it) for i, it in enumerate(items)]


class TestBuildTimeline:
    def test_interleaved_clip_tts(self):
        specs = specs_from(
            {"mode": "clip", "duration_ms": 3000},
            {"mode": "clip", "duration_ms": 4000},
            {"mode": "tts"},
            {"mode": "clip", "duration_ms": 5000},
        )
        tts = [{"scene_id": 2, "start_ms": 120, "end_ms": 6120}]
        timings, placements = build_timeline(specs, tts)
        assert timings == [
            {"scene_id": 0, "start_ms": 0, "end_ms": 3000},
            {"scene_id": 1, "start_ms": 3000, "end_ms": 7000},
            {"scene_id": 2, "start_ms": 7000, "end_ms": 13000},
            {"scene_id": 3, "start_ms": 13000, "end_ms": 18000},
        ]
        assert placements == [
            {"src_start_ms": 120, "src_end_ms": 6120, "dst_ms": 7000},
        ]

    def test_two_tts_scenes(self):
        specs = specs_from(
            {"mode": "clip", "duration_ms": 2000},
            {"mode": "tts"},
            {"mode": "clip", "duration_ms": 3000},
            {"mode": "tts"},
        )
        tts = [{"scene_id": 1, "start_ms": 0, "end_ms": 5000},
               {"scene_id": 3, "start_ms": 5000, "end_ms": 8000}]
        timings, placements = build_timeline(specs, tts)
        assert timings[-1] == {"scene_id": 3, "start_ms": 10000, "end_ms": 13000}
        assert placements[1] == {"src_start_ms": 5000, "src_end_ms": 8000,
                                 "dst_ms": 10000}

    def test_missing_tts_timing_raises(self):
        specs = specs_from({"mode": "clip", "duration_ms": 2000},
                           {"mode": "tts"})
        with pytest.raises(ValueError, match="타이밍"):
            build_timeline(specs, [])

    def test_outro_timing_ignored(self):
        specs = specs_from({"mode": "clip", "duration_ms": 2000},
                           {"mode": "tts"})
        tts = [{"scene_id": 1, "start_ms": 0, "end_ms": 4000},
               {"scene_id": -1, "start_ms": 4000, "end_ms": 6000}]
        timings, _ = build_timeline(specs, tts)
        assert len(timings) == 2

    def test_inputs_not_mutated(self):
        specs = specs_from({"mode": "clip", "duration_ms": 2000},
                           {"mode": "tts"})
        tts = [{"scene_id": 1, "start_ms": 100, "end_ms": 4000}]
        build_timeline(specs, tts)
        assert tts[0]["start_ms"] == 100
        assert "start_ms" not in specs[0]


# ── 클립 오디오 비중 ────────────────────────────────────────────────
class TestClipAudioRatio:
    def test_ratio(self):
        timings = [
            {"scene_id": 0, "start_ms": 0, "end_ms": 3000},
            {"scene_id": 1, "start_ms": 3000, "end_ms": 7000},
            {"scene_id": 2, "start_ms": 7000, "end_ms": 13000},
            {"scene_id": 3, "start_ms": 13000, "end_ms": 18000},
        ]
        ratio = clip_audio_ratio(timings, clip_ids={0, 1, 3})
        assert ratio == pytest.approx(12000 / 18000)

    def test_empty_timings_zero(self):
        assert clip_audio_ratio([], clip_ids=set()) == 0.0


# ── ffmpeg 필터 구성 ────────────────────────────────────────────────
class TestBuildAssembleFilter:
    def test_filter_contains_trim_delay_mix_pad(self):
        placements = [{"src_start_ms": 120, "src_end_ms": 6120, "dst_ms": 7000}]
        f = build_assemble_filter(placements, total_ms=18000)
        assert "atrim=start=0.120:end=6.120" in f
        assert "adelay=7000:all=1" in f
        assert "amix=inputs=1:normalize=0" in f
        assert "apad=whole_dur=18.000" in f
        assert f.endswith("[aout]")

    def test_two_placements_mixed(self):
        placements = [
            {"src_start_ms": 0, "src_end_ms": 5000, "dst_ms": 2000},
            {"src_start_ms": 5000, "src_end_ms": 8000, "dst_ms": 10000},
        ]
        f = build_assemble_filter(placements, total_ms=13000)
        assert "amix=inputs=2:normalize=0" in f
        assert "[s0][s1]" in f


# ── 스크립트 구성 ──────────────────────────────────────────────────
class TestBuildScript:
    def clip_durs(self) -> dict[int, float]:
        return {0: 3.0, 1: 4.0, 3: 5.0}

    def test_clip_scenes_have_no_tts(self):
        script = build_script(base_cfg(), self.clip_durs())
        assert [s.voice_text for s in script.scenes] == \
            ["", "", "논평 나레이션입니다.", ""]

    def test_scene0_is_hook_title_yellow_bottom(self):
        s0 = build_script(base_cfg(), self.clip_durs()).scenes[0]
        assert s0.type == "title"
        assert s0.hook is True
        assert s0.duration == 3.0
        assert s0.subtitle_color == "yellow"
        assert s0.subtitle_position == "bottom"
        assert s0.text == "훅\n원본 발언"

    def test_later_clips_are_body_not_hook(self):
        script = build_script(base_cfg(), self.clip_durs())
        for s in script.scenes[1:]:
            assert s.hook is False
        assert script.scenes[1].type == "body"
        assert script.scenes[3].subtitle_color == "yellow"
        assert script.scenes[3].subtitle_position == "bottom"

    def test_speaker_label_prefixed(self):
        script = build_script(base_cfg(), self.clip_durs())
        assert script.scenes[1].text == "[이준석]\n반박 발언"

    def test_tts_scene_keeps_v21_styling(self):
        s2 = build_script(base_cfg(), self.clip_durs()).scenes[2]
        assert s2.voice_text == "논평 나레이션입니다."
        assert s2.subtitle_color == "red"
        assert s2.subtitle_emphasis is True
        assert s2.subtitle_position == ""

    def test_tts_script_joins_only_tts_voices(self):
        script = build_script(base_cfg(), self.clip_durs())
        assert script.audio.tts_script == "논평 나레이션입니다."

    def test_scene0_text_falls_back_to_yt_title(self):
        cfg = base_cfg()
        del cfg["scenes"][0]["text"]
        script = build_script(cfg, self.clip_durs())
        assert script.scenes[0].text == cfg["yt_title"]

    def test_clip_color_overridable(self):
        cfg = base_cfg()
        cfg["scenes"][1]["color"] = "red"
        script = build_script(cfg, self.clip_durs())
        assert script.scenes[1].subtitle_color == "red"


# ── 034: 제목 패키징 강제화 (V2.2 도 동일 게이트) ───────────────────
class TestValidateConfigTitleGate:
    def test_hashtag_title_blocked(self):
        cfg = base_cfg(yt_title="죽창 들자던 조국, 이젠 사상검증 #조국")
        with pytest.raises(ValueError, match="해시태그"):
            validate_config(cfg)

    def test_report_title_blocked(self):
        cfg = base_cfg(yt_title="윤석열 397억은 1심인데 이재명은 재판조차 안 한다")
        with pytest.raises(ValueError, match="보도체"):
            validate_config(cfg)

    def test_lint_off_bypasses_gate(self):
        cfg = base_cfg(yt_title="이재명 434억은 재판조차 안 한다",
                       yt_title_lint="off")
        assert validate_config(cfg) == []
