"""V5.0 EvidenceLayer 렌더 프롭 옵트인 (043 Phase C).

`evidence_layer` 미지정이면 V2.1/V2.2/V3.0/V4.0 경로와 **완전히 동일**해야 한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.video.renderer import render_video


def _capture(output_dir, **kwargs) -> dict:
    captured: dict = {}

    def fake_run(cmd, **kw):
        for i, a in enumerate(cmd):
            if a == "--props" and i + 1 < len(cmd):
                props = json.loads(open(cmd[i + 1]).read())
                captured["props"] = props
                public = Path(cmd[cmd.index("render") + 1]).parents[4] / "public"
                files = [e["file"] for e in (props.get("evidenceLayer") or {}).get("evidence", [])]
                captured["present"] = [(public / f).exists() for f in files]
                captured["public"] = public
        for a in cmd:
            if isinstance(a, str) and a.endswith(".mp4"):
                open(a, "wb").write(b"0" * 2000)
        return MagicMock(returncode=0, stderr="", stdout="")

    with patch("src.video.renderer.shutil.which", return_value="/usr/bin/npx"), \
         patch("src.video.renderer.subprocess.run", side_effect=fake_run):
        render_video(auto_thumbnail=False, output_dir=output_dir, **kwargs)
    return captured


def _layer(tmp_path: Path) -> dict:
    img = tmp_path / "upload_date.png"
    img.write_bytes(b"\x89PNGpng")
    return {
        "headline": ["한동훈 2달만에", "KTX-SRT 결합 증편 성과?"],
        "headline_colors": ["#FFE14D", "#3FE0F0"],
        "captions": [{"text": "시의원들이 찬양한 날", "start_ms": 0, "end_ms": 1200,
                      "hl": ["찬양"]}],
        "pops": [{"text": "8월 2일!", "start_ms": 1200, "end_ms": 3000}],
        "evidence": [{"path": str(img), "start_ms": 1200, "end_ms": 5000, "marks": [
            {"kind": "underline", "x": 0.1, "y": 0.6, "w": 0.5, "h": 0.04}]}],
        "flashes": [1200],
        "framing": [{"scene_id": 0, "zoom": 1.2, "focus_x": 0.3}],
        "channel_label": "",
        "source_label": "영상출처: 입국열차, 강성범TV",
        "font_family": "BM Dohyeon",
    }


@pytest.fixture
def out_dir(tmp_data_dir):
    out = tmp_data_dir / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


class TestDefaultsUnchanged:
    def test_no_evidence_key_by_default(self, sample_script, out_dir):
        props = _capture(out_dir, script=sample_script)["props"]
        assert "evidenceLayer" not in props


class TestEvidenceLayerProps:
    def test_camel_case_and_copy(self, sample_script, out_dir, tmp_path):
        got = _capture(out_dir, script=sample_script, evidence_layer=_layer(tmp_path))
        layer = got["props"]["evidenceLayer"]
        assert layer["headline"] == ["한동훈 2달만에", "KTX-SRT 결합 증편 성과?"]
        assert layer["headlineColors"] == ["#FFE14D", "#3FE0F0"]
        assert layer["captions"] == [
            {"text": "시의원들이 찬양한 날", "startMs": 0, "endMs": 1200, "hl": ["찬양"]}]
        assert layer["pops"] == [{"text": "8월 2일!", "startMs": 1200, "endMs": 3000}]
        ev = layer["evidence"][0]
        assert ev["file"].endswith(".png") and (ev["startMs"], ev["endMs"]) == (1200, 5000)
        assert ev["marks"][0]["kind"] == "underline"
        assert layer["flashesMs"] == [1200]
        assert layer["framing"] == [{"sceneId": 0, "zoom": 1.2, "focusX": 0.3}]
        assert layer["sourceLabel"] == "영상출처: 입국열차, 강성범TV"
        assert layer["fontFamily"] == "BM Dohyeon"
        assert all(got["present"])

    def test_default_source_label_suppressed(self, sample_script, out_dir, tmp_path):
        """출처는 레이어가 우상단에 그린다 — 하단 기본 박스 라벨과 중복 금지."""
        props = _capture(out_dir, script=sample_script,
                         evidence_layer=_layer(tmp_path))["props"]
        assert props["sourceLabel"] == ""

    def test_evidence_cleaned_after_render(self, sample_script, out_dir, tmp_path):
        got = _capture(out_dir, script=sample_script, evidence_layer=_layer(tmp_path))
        for e in got["props"]["evidenceLayer"]["evidence"]:
            assert not (got["public"] / e["file"]).exists()

    def test_missing_evidence_fails_fast(self, sample_script, out_dir, tmp_path):
        layer = _layer(tmp_path)
        layer["evidence"][0]["path"] = str(tmp_path / "nope.png")
        with pytest.raises(FileNotFoundError, match="nope.png"):
            _capture(out_dir, script=sample_script, evidence_layer=layer)
