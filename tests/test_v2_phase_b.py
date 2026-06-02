"""Phase B tests — Remotion 시각 연출 (subtitle_color, visual_layout, split-screen).

V2 (Feature 011 Phase B):
- Scene에 subtitle_color/subtitle_emphasis/visual_layout/secondary_clip_path 추가
- plan_to_script가 Narration.subtitle_color → Scene.subtitle_color로 매핑
- visual_directives에 "분할" 또는 "split" 키워드 → 매칭되는 씬에 visual_layout="split"
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.analyzer.political_plan_models import (
    Narration,
    ShortsPlan,
)
from src.analyzer.political_planner import plan_to_script


# ─────────────────────────── Scene V2 fields ───────────────────────────


def test_scene_subtitle_color_round_trip():
    s = Scene(
        id=0, timestamp=0, duration=3.0, type="title",
        text="x", voice_text="x",
        subtitle_color="red", subtitle_emphasis=True,
    )
    d = s.to_dict()
    assert d.get("subtitle_color") == "red"
    assert d.get("subtitle_emphasis") is True
    restored = Scene.from_dict(d)
    assert restored == s


def test_scene_v1_default_subtitle_color():
    """V1 JSON (subtitle_color 없음) → default white."""
    v1 = {
        "id": 0, "timestamp": 0, "duration": 3.0, "type": "title",
        "text": "x", "voice_text": "x", "emphasis": "medium",
        "highlight_words": [],
    }
    s = Scene.from_dict(v1)
    assert s.subtitle_color == "white"
    assert s.subtitle_emphasis is False


def test_scene_visual_layout_split():
    s = Scene(
        id=0, timestamp=0, duration=3.0, type="title",
        text="x", voice_text="x",
        visual_layout="split",
        secondary_clip_path="/tmp/past.mp4",
    )
    d = s.to_dict()
    assert d.get("visual_layout") == "split"
    assert d.get("secondary_clip_path") == "/tmp/past.mp4"
    restored = Scene.from_dict(d)
    assert restored == s


def test_scene_v1_default_visual_layout():
    v1 = {
        "id": 0, "timestamp": 0, "duration": 3.0, "type": "title",
        "text": "x", "voice_text": "x", "emphasis": "medium",
        "highlight_words": [],
    }
    s = Scene.from_dict(v1)
    assert s.visual_layout == "normal"
    assert s.secondary_clip_path is None


# ─────────────────────────── plan_to_script V2 mapping ───────────────────────────


def test_plan_to_script_maps_subtitle_color_to_scenes():
    """Narration.subtitle_color → Scene.subtitle_color로 매핑."""
    plan = ShortsPlan(
        topic="t", hook="hook",
        clip_start_sec=0, clip_end_sec=20, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(start_sec=0, end_sec=3, text="첫줄", subtitle_color="red", subtitle_emphasis=True),
            Narration(start_sec=3, end_sec=6, text="둘째", subtitle_color="yellow"),
            Narration(start_sec=6, end_sec=9, text="셋째", subtitle_color="white"),
        ),
        cta="cta", angle="title_anchor",
    )
    script = plan_to_script(
        plan, video_title="t", video_duration_sec=120.0,
        youtube_url="https://youtu.be/x",
    )
    # body 씬(narration 매핑 결과)에 색·강조 보존
    body_scenes = [s for s in script.scenes if s.type == "body"]
    assert any(s.subtitle_color == "red" for s in body_scenes), \
        f"body 씬에 red 자막 부재 — colors={[s.subtitle_color for s in body_scenes]}"
    # red 씬은 emphasis도 True
    red_scene = next(s for s in body_scenes if s.subtitle_color == "red")
    assert red_scene.subtitle_emphasis is True


def test_plan_to_script_split_directive_no_longer_auto_applied():
    """2026-05-16 사용자 피드백: split-screen 자동 매핑 비활성화.

    visual_directives에 '분할' 키워드가 있어도 visual_layout='normal' 유지.
    이유: political_pro 모드는 원본 영상 1개라 좌·우 분할이 의미 없고 어색.
    진짜 비교 클립(secondary_clip_path)이 있을 때만 split 활용 — Phase D로 미룸.
    """
    plan = ShortsPlan(
        topic="t", hook="h",
        clip_start_sec=0, clip_end_sec=20, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(start_sec=0, end_sec=3, text="x"),
        ),
        cta="cta", angle="title_anchor",
        visual_directives=(
            "0~3초: 좌(과거) 우(현재) 분할로 모순 강조",
        ),
    )
    script = plan_to_script(
        plan, video_title="t", video_duration_sec=60.0,
        youtube_url="https://youtu.be/x",
    )
    # 모든 씬이 normal 유지 (split 자동 적용 안 됨)
    assert all(s.visual_layout == "normal" for s in script.scenes), \
        f"split 씬 발견 — layouts={[s.visual_layout for s in script.scenes]}"


def test_plan_to_script_no_split_directive_keeps_normal():
    """visual_directives가 비어있거나 split 키워드 없으면 모든 씬 visual_layout='normal'."""
    plan = ShortsPlan(
        topic="t", hook="h",
        clip_start_sec=0, clip_end_sec=20, clip_reason="r",
        flow_intro="i", flow_middle="m", flow_climax="c",
        narrations=(
            Narration(start_sec=0, end_sec=3, text="x"),
        ),
        cta="cta", angle="title_anchor",
        visual_directives=(
            "12초 부근 핵심 키워드 큰 자막",  # 자막 강조만, layout 변경 없음
            "발화자 클로즈업으로 줌 인",
        ),
    )
    script = plan_to_script(
        plan, video_title="t", video_duration_sec=60.0,
        youtube_url="https://youtu.be/x",
    )
    assert all(s.visual_layout == "normal" for s in script.scenes)


# ─────────────────────────── Renderer source-label V2 (color) ───────────────────────────


def test_subtitle_color_to_hex_mapping():
    """렌더 단계에서 subtitle_color 키워드를 실제 hex로 매핑."""
    from src.video.subtitle_color_map import SUBTITLE_COLOR_HEX, get_subtitle_hex
    assert get_subtitle_hex("white") == SUBTITLE_COLOR_HEX["white"]
    assert get_subtitle_hex("red").lower().startswith("#")
    assert get_subtitle_hex("yellow") != get_subtitle_hex("white")
    # unknown → fallback white
    assert get_subtitle_hex("unknown_color") == SUBTITLE_COLOR_HEX["white"]
