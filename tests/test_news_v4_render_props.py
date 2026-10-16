"""V4.0 뉴스 카드 렌더 프롭 옵트인 (042 Phase C).

`news_card` 미지정이면 V2.1/V2.2/V3.0 경로와 **완전히 동일**해야 한다.
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
                files = [p["file"] for p in (props.get("newsCard") or {}).get("photos", [])]
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


def _card(tmp_path: Path) -> dict:
    a = tmp_path / "a.jpg"
    b = tmp_path / "fb.png"
    a.write_bytes(b"\xff\xd8jpg")
    b.write_bytes(b"\x89PNGpng")
    return {
        "photos": [
            {"path": str(a), "fit": "cover", "start_ms": 0, "end_ms": 6930},
            {"path": str(b), "fit": "contain", "start_ms": 6930, "end_ms": 10330},
        ],
        "captions": [
            {"text": "관객 130만 명을 돌파하며", "start_ms": 0, "end_ms": 2000,
             "hl": ["130만"], "color": "white"},
        ],
        "credit_line": "출처 : 연합뉴스 · 한동훈 페이스북",
        "font_family": "BM Dohyeon",
    }


@pytest.fixture
def out_dir(tmp_data_dir):
    out = tmp_data_dir / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


class TestDefaultsUnchanged:
    def test_no_news_card_key_by_default(self, sample_script, out_dir):
        props = _capture(out_dir, script=sample_script)["props"]
        assert "newsCard" not in props

    def test_headline_plain_and_badge_boxed_defaults(self, sample_script, out_dir):
        props = _capture(out_dir, script=sample_script)["props"]
        assert props["headlinePlain"] is False
        assert props["badgeBoxed"] is None


class TestNewsCardProps:
    def test_photos_copied_and_referenced(self, sample_script, out_dir, tmp_path):
        got = _capture(out_dir, script=sample_script, news_card=_card(tmp_path))
        photos = got["props"]["newsCard"]["photos"]
        assert [p["fit"] for p in photos] == ["cover", "contain"]
        assert [(p["startMs"], p["endMs"]) for p in photos] == [(0, 6930), (6930, 10330)]
        assert photos[0]["file"].endswith(".jpg")
        assert photos[1]["file"].endswith(".png")
        assert all(got["present"])

    def test_photos_cleaned_after_render(self, sample_script, out_dir, tmp_path):
        got = _capture(out_dir, script=sample_script, news_card=_card(tmp_path))
        for p in got["props"]["newsCard"]["photos"]:
            assert not (got["public"] / p["file"]).exists()

    def test_captions_camel_case(self, sample_script, out_dir, tmp_path):
        card = _capture(out_dir, script=sample_script,
                        news_card=_card(tmp_path))["props"]["newsCard"]
        assert card["captions"] == [{
            "text": "관객 130만 명을 돌파하며", "startMs": 0, "endMs": 2000,
            "hl": ["130만"], "color": "white",
        }]
        assert card["creditLine"] == "출처 : 연합뉴스 · 한동훈 페이스북"
        assert card["fontFamily"] == "BM Dohyeon"

    def test_default_source_label_suppressed(self, sample_script, out_dir, tmp_path):
        """출처는 카드가 자기 위치·스타일로 그린다 — 기본 박스 라벨과 중복 금지."""
        props = _capture(out_dir, script=sample_script, news_card=_card(tmp_path))["props"]
        assert props["sourceLabel"] == ""

    def test_missing_photo_file_fails_fast(self, sample_script, out_dir, tmp_path):
        card = _card(tmp_path)
        card["photos"][1]["path"] = str(tmp_path / "nope.jpg")
        with pytest.raises(FileNotFoundError, match="nope.jpg"):
            _capture(out_dir, script=sample_script, news_card=card)

    def test_missing_photo_leaves_nothing_in_public(self, sample_script, out_dir, tmp_path):
        """앞 사진을 복사한 뒤 뒤 사진에서 멈추면 public/ 에 찌꺼기가 남았다
        (예외가 렌더 try/finally 정리 구간보다 앞에서 난다 — 2026-09-30 실측 4개)."""
        from datetime import datetime as real_datetime

        from src.config.settings import PROJECT_ROOT

        class FixedDT(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(1999, 1, 1, 0, 0, 0)

        # 파일명이 초 단위 타임스탬프라 앞 테스트의 찌꺼기와 이름이 겹치면 검사가
        # 헛돈다 — 고유 타임스탬프로 고정해 정확한 파일명을 본다.
        leaked = PROJECT_ROOT / "public" / "news_19990101_000000_00.jpg"
        leaked.unlink(missing_ok=True)
        card = _card(tmp_path)
        card["photos"][1]["path"] = str(tmp_path / "nope.jpg")
        with patch("src.video.renderer.datetime", FixedDT), \
             pytest.raises(FileNotFoundError):
            _capture(out_dir, script=sample_script, news_card=card)
        exists = leaked.exists()
        leaked.unlink(missing_ok=True)
        assert not exists

    def test_plain_headline_and_boxed_badge_pass_through(self, sample_script, out_dir):
        props = _capture(out_dir, script=sample_script, headline_plain=True,
                         badge_boxed=True, overlay_boxes=False)["props"]
        assert props["headlinePlain"] is True
        assert props["badgeBoxed"] is True
        assert props["overlayBoxes"] is False
