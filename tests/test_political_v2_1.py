"""정치쇼츠 V2.1 (scripts/render_political_v2_1.py + political_upload_package.py) 테스트."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.render_political_v2_1 import (
    build_script, resolve_hook_cut, scene_type, shift_timings, validate_config,
)
from scripts.political_upload_package import (
    build_description, build_hashtags, build_upload_package_md,
    lint_yt_title, suggest_upload_time,
)


def base_cfg(**over) -> dict:
    cfg = {
        "slug": "test_v21",
        "title": "상단 배너 제목",
        "yt_title": "죽창 들자던 조국, 이젠 말끝으로 사상검증",
        "persons": ["조국", "이준석"],
        "sources": {
            "a": {"query": "인물 A 발언"},
            "b": {"url": "https://youtube.com/watch?v=x"},
        },
        "scenes": [
            {"type": "title", "color": "yellow", "emph": True, "source": "a",
             "text": "훅 자막", "voice": "훅 나레이션입니다.", "hl": ["훅"]},
            {"type": "body", "color": "white", "source": "b",
             "text": "본문 자막", "voice": "본문 나레이션입니다."},
        ],
        "hook": {"source": "a", "start_sec": 10.0, "duration": 3.0,
                 "text": "훅\n원본 발언", "hl": ["훅"]},
    }
    cfg.update(over)
    return cfg


# ── config 검증 ─────────────────────────────────────────────────────
class TestValidateConfig:
    def test_valid_config_passes(self):
        validate_config(base_cfg())

    def test_missing_required_key(self):
        cfg = base_cfg()
        del cfg["scenes"]
        with pytest.raises(ValueError, match="scenes"):
            validate_config(cfg)

    def test_hook_source_not_in_sources(self):
        cfg = base_cfg(hook={"source": "nope", "duration": 3.0})
        with pytest.raises(ValueError, match="hook.source"):
            validate_config(cfg)

    def test_hook_duration_out_of_range(self):
        cfg = base_cfg(hook={"source": "a", "duration": 0.5})
        with pytest.raises(ValueError, match="hook.duration"):
            validate_config(cfg)

    def test_bad_scene_color(self):
        cfg = base_cfg()
        cfg["scenes"][0]["color"] = "green"
        with pytest.raises(ValueError, match="color"):
            validate_config(cfg)

    def test_no_hook_is_valid(self):
        cfg = base_cfg()
        del cfg["hook"]
        validate_config(cfg)


# ── 씬 type 강제 ───────────────────────────────────────────────────
class TestSceneType:
    def test_comment_coerced_to_body(self):
        assert scene_type({"type": "comment"}) == "body"

    def test_default_is_body(self):
        assert scene_type({}) == "body"

    def test_title_kept(self):
        assert scene_type({"type": "title"}) == "title"


# ── 타이밍 시프트 ──────────────────────────────────────────────────
class TestShiftTimings:
    def test_shift_applies_offset(self):
        timings = [{"scene_id": 1, "start_ms": 0, "end_ms": 4000},
                   {"scene_id": 2, "start_ms": 4000, "end_ms": 9000}]
        shifted = shift_timings(timings, 3000)
        assert shifted[0] == {"scene_id": 1, "start_ms": 3000, "end_ms": 7000}
        assert shifted[1] == {"scene_id": 2, "start_ms": 7000, "end_ms": 12000}

    def test_original_not_mutated(self):
        timings = [{"scene_id": 1, "start_ms": 0, "end_ms": 4000}]
        shift_timings(timings, 3000)
        assert timings[0]["start_ms"] == 0


# ── 훅 컷 계산 ─────────────────────────────────────────────────────
class TestResolveHookCut:
    def test_explicit_start_sec(self):
        start, dur = resolve_hook_cut({"start_sec": 10.0, "duration": 3.0}, 100.0)
        assert (start, dur) == (10.0, 3.0)

    def test_frac_based_start(self):
        start, dur = resolve_hook_cut({"frac": 0.5, "duration": 2.0}, 100.0)
        assert start == pytest.approx(50.0)
        assert dur == 2.0

    def test_clamped_when_source_short(self):
        start, dur = resolve_hook_cut({"start_sec": 50.0, "duration": 3.0}, 4.0)
        assert start + dur <= 4.0    # 컷 구간이 소스 길이를 넘지 않음
        assert start < 4.0

    def test_duration_capped_at_max(self):
        _, dur = resolve_hook_cut({"start_sec": 0.0, "duration": 99.0}, 100.0)
        assert dur == 10.0    # 실촬영 훅은 문장 완결 우선 — 10s 상한

    def test_sentence_length_hook_allowed(self):
        # 사용자 피드백(2026-07-14): 문장 끝맺음 전에 씬 전환 금지 → 6s 훅 허용
        validate_config(base_cfg(hook={"source": "a", "start_sec": 305.3,
                                       "duration": 6.0}))


# ── 스크립트 구성 ──────────────────────────────────────────────────
class TestBuildScript:
    def test_hook_scene_prepended(self):
        script = build_script(base_cfg(), hook_dur=3.0)
        assert len(script.scenes) == 3
        s0 = script.scenes[0]
        assert s0.voice_text == ""          # TTS 없음 — 원본 육성
        assert s0.hook is True
        assert s0.duration == 3.0
        assert s0.subtitle_color == "yellow"
        assert s0.text == "훅\n원본 발언"

    def test_config_scenes_shifted_by_one(self):
        script = build_script(base_cfg(), hook_dur=3.0)
        assert [s.id for s in script.scenes] == [0, 1, 2]
        assert script.scenes[1].voice_text == "훅 나레이션입니다."
        assert script.scenes[1].hook is False

    def test_tts_script_excludes_hook(self):
        script = build_script(base_cfg(), hook_dur=3.0)
        assert "원본 발언" not in script.audio.tts_script
        assert "훅 나레이션입니다." in script.audio.tts_script

    def test_no_hook_matches_v2_layout(self):
        cfg = base_cfg()
        del cfg["hook"]
        script = build_script(cfg, hook_dur=0.0)
        assert len(script.scenes) == 2
        assert script.scenes[0].id == 0
        assert script.scenes[0].voice_text == "훅 나레이션입니다."
        assert script.scenes[0].hook is True

    def test_comment_type_never_emitted(self):
        cfg = base_cfg()
        cfg["scenes"][1]["type"] = "comment"
        script = build_script(cfg, hook_dur=3.0)
        assert all(s.type != "comment" for s in script.scenes)

    def test_hook_subtitle_falls_back_to_yt_title(self):
        cfg = base_cfg()
        del cfg["hook"]["text"]
        script = build_script(cfg, hook_dur=3.0)
        assert script.scenes[0].text == cfg["yt_title"]

    def test_hook_subtitle_positioned_bottom(self):
        # 훅 자막은 영상을 가리지 않도록 기본 하단 배치
        script = build_script(base_cfg(), hook_dur=3.0)
        assert script.scenes[0].subtitle_position == "bottom"
        assert script.scenes[1].subtitle_position == ""    # 일반 씬은 기존 동작

    def test_hook_subtitle_position_serialized_roundtrip(self):
        from src.analyzer.script_models import Scene
        script = build_script(base_cfg(), hook_dur=3.0)
        d = script.scenes[0].to_dict()
        assert d["subtitle_position"] == "bottom"
        assert Scene.from_dict(d).subtitle_position == "bottom"
        # 기본값("")은 직렬화 키 생략 (기존 JSON 호환)
        assert "subtitle_position" not in script.scenes[1].to_dict()


# ── 제목 린트 ──────────────────────────────────────────────────────
class TestLintYtTitle:
    def test_good_title_no_warnings(self):
        assert lint_yt_title("죽창 들자던 조국, 이젠 말끝으로 사상검증", ["조국"]) == []

    def test_short_title_warns(self):
        assert any("이상" in w for w in lint_yt_title("짧은 제목", None))

    def test_long_title_warns(self):
        assert any("이하" in w for w in lint_yt_title("가" * 40, None))

    def test_missing_person_warns(self):
        warnings = lint_yt_title("아무 실명 없는 열여덟자짜리 제목입니다", ["조국"])
        assert any("실명" in w for w in warnings)

    def test_sokbo_style_warns(self):
        warnings = lint_yt_title("속보 조국 발언 논란 확산 중입니다", ["조국"])
        assert any("속보" in w for w in warnings)


# ── 해시태그 / 설명 / 업로드 시각 ──────────────────────────────────
class TestUploadPackageParts:
    def test_hashtags_from_persons(self):
        assert build_hashtags({"persons": ["조국", "이준석"]}) == ["#조국", "#이준석"]

    def test_explicit_hashtags_normalized_and_capped(self):
        tags = build_hashtags({"hashtags": ["a", "#b", "c", "d", "e"]})
        assert tags == ["#a", "#b", "#c", "#d"]

    def test_upload_time_same_weekday_before_20(self):
        monday = _next_weekday(datetime(2026, 1, 1), 0)
        t = suggest_upload_time(monday.replace(hour=10))
        assert (t.date(), t.hour) == (monday.date(), 20)

    def test_upload_time_after_20_rolls_forward(self):
        monday = _next_weekday(datetime(2026, 1, 1), 0)
        t = suggest_upload_time(monday.replace(hour=21))
        assert (t - monday.replace(hour=20)).days == 1
        assert t.weekday() == 1

    def test_upload_time_weekend_rolls_to_monday(self):
        saturday = _next_weekday(datetime(2026, 1, 1), 5)
        t = suggest_upload_time(saturday.replace(hour=12))
        assert t.weekday() == 0
        assert t.hour == 20

    def test_description_contains_source_and_tags(self):
        desc = build_description(base_cfg(youtube_url="https://youtu.be/x",
                                          source_channel="채널A"),
                                 ["#조국"])
        assert "채널A" in desc and "#조국" in desc and "https://youtu.be/x" in desc


def _next_weekday(base: datetime, weekday: int) -> datetime:
    return base + timedelta(days=(weekday - base.weekday()) % 7)


# ── 업로드 패키지 md ────────────────────────────────────────────────
class TestBuildUploadPackageMd:
    def test_contains_all_sections(self):
        cfg = base_cfg(yt_title_alt="B안 제목입니다 열여덟자 채우기용",
                       pinned_comment="고정댓글 문안")
        monday = _next_weekday(datetime(2026, 1, 1), 0).replace(hour=20)
        md = build_upload_package_md(
            cfg, Path("out.mp4"), monday,
            thumbnails=[Path("t1.png"), Path("t2.png")],
        )
        assert cfg["yt_title"] in md
        assert "B안 제목입니다" in md
        assert "#조국" in md
        assert "고정댓글 문안" in md
        assert "t1.png" in md
        assert "FR-020" in md          # 자동 업로드 차단 경고 유지

    def test_no_alt_title_omits_b_line(self):
        cfg = base_cfg()
        monday = _next_weekday(datetime(2026, 1, 1), 0).replace(hour=20)
        md = build_upload_package_md(cfg, Path("out.mp4"), monday)
        assert "- B:" not in md
