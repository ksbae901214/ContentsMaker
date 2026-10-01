"""V3.0 렌더 프롭 옵트인 (041 Phase A3).

궁서 헤드라인·인물 배지는 **미지정 시 기존 V2.1/V2.2 경로와 완전히 동일**해야
한다 (037 제목 100px Noto 고정 규격 보호).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.video.renderer import render_video

BASE_PROP_KEYS = {
    "scriptData", "audioFile", "sceneImages", "sceneVideos", "bgmFile",
    "introBgmFile", "sourceLabel", "backgroundVideoFile",
}


def _capture_props(output_dir, **kwargs) -> dict:
    captured: dict = {}

    def fake_run(cmd, **kw):
        for i, a in enumerate(cmd):
            if a == "--props" and i + 1 < len(cmd):
                captured["props"] = json.loads(open(cmd[i + 1]).read())
        for a in cmd:
            if isinstance(a, str) and a.endswith(".mp4"):
                open(a, "wb").write(b"0" * 2000)
        return MagicMock(returncode=0, stderr="", stdout="")

    with patch("src.video.renderer.shutil.which", return_value="/usr/bin/npx"), \
         patch("src.video.renderer.subprocess.run", side_effect=fake_run):
        render_video(auto_thumbnail=False, output_dir=output_dir, **kwargs)
    assert "props" in captured, "--props 경로가 포착되지 않았습니다"
    return captured["props"]


class TestDefaultsUnchanged:
    def test_v2_path_keeps_empty_headline_and_badge(self, sample_script, tmp_data_dir):
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(out, script=sample_script)
        assert props["headlineFont"] == ""
        assert props["headlineLetterSpacing"] == 0
        assert props["personBadge"] == ""

    def test_existing_prop_keys_survive(self, sample_script, tmp_data_dir):
        """기존 프롭이 하나라도 사라지면 V2 렌더가 조용히 깨진다."""
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(out, script=sample_script)
        assert BASE_PROP_KEYS <= set(props)


class TestProfileV3Props:
    def test_headline_font_and_spacing_pass_through(self, sample_script, tmp_data_dir):
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(
            out, script=sample_script,
            headline_font="GungSeo", headline_letter_spacing=-4,
        )
        assert props["headlineFont"] == "GungSeo"
        assert props["headlineLetterSpacing"] == -4

    def test_person_badge_passes_through(self, sample_script, tmp_data_dir):
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(
            out, script=sample_script, person_badge="이해민 · 수석 내정자")
        assert props["personBadge"] == "이해민 · 수석 내정자"

    def test_background_override_opt_in(self, sample_script, tmp_data_dir):
        """political_pro 는 배경을 검정으로 강제한다 — 명시 옵트인으로만 푼다."""
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(
            out, script=sample_script, respect_background_colors=True)
        assert props["respectBackgroundColors"] is True

    def test_background_override_defaults_false(self, sample_script, tmp_data_dir):
        """bg_colors 를 명시한 기존 config 10개의 동작이 바뀌면 안 된다."""
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(out, script=sample_script)
        assert props["respectBackgroundColors"] is False

    def test_headline_color_and_plain_overlays(self, sample_script, tmp_data_dir):
        """흰 캔버스에서는 반투명 검정 박스가 회색으로 보인다 — 박스를 끄고
        글자색을 어둡게 한다 (사용자 지시 2026-09-14)."""
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(
            out, script=sample_script,
            headline_color="#111111", overlay_boxes=False)
        assert props["headlineColor"] == "#111111"
        assert props["overlayBoxes"] is False

    def test_overlay_defaults_keep_v2_look(self, sample_script, tmp_data_dir):
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(out, script=sample_script)
        assert props["headlineColor"] == ""
        assert props["overlayBoxes"] is True

    def test_badge_is_trimmed(self, sample_script, tmp_data_dir):
        """배지는 우상단 한 줄이라 길면 화면을 가린다."""
        out = tmp_data_dir / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        props = _capture_props(
            out, script=sample_script, person_badge="가" * 200)
        assert 0 < len(props["personBadge"]) <= 40
