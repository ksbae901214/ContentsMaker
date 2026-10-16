"""정보쇼츠 V1.0 Remotion 렌더러 — public 자산 준비·프레임 계산 테스트 (045)."""
from __future__ import annotations

from src.video.info_renderer import FPS, duration_frames, stage_assets, thumbnail_props


def _props(img: str) -> dict:
    return {
        "titleLines": ["제목"], "watermark": "made by x", "canvasColor": "#F6EFE1",
        "images": [{"path": img, "startMs": 0, "endMs": 1000, "zoomStartMs": None}],
        "captions": [], "durationMs": 1000,
    }


def test_duration_frames_rounds_up_with_tail():
    assert duration_frames(1000) == FPS + FPS // 2
    assert duration_frames(1001) == FPS + 1 + FPS // 2


def test_stage_assets_copies_files_and_rewrites_paths(tmp_path):
    img = tmp_path / "chapter_00.png"
    img.write_bytes(b"png")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"mp3")
    fonts = tmp_path / "fonts_src"
    fonts.mkdir()
    (fonts / "X.ttf").write_bytes(b"ttf")
    public = tmp_path / "public"

    props, staged = stage_assets(_props(str(img)), audio, public, tag="t1", fonts_dir=fonts)

    assert props["images"][0]["file"] == "info_t1_img_00.png"
    assert "path" not in props["images"][0]
    assert props["audioFile"] == "info_t1_audio.mp3"
    assert (public / "info_t1_img_00.png").read_bytes() == b"png"
    assert (public / "fonts" / "X.ttf").exists()
    # 폰트는 계속 쓰므로 정리 대상이 아니다
    assert public / "info_t1_img_00.png" in staged
    assert public / "fonts" / "X.ttf" not in staged


def test_stage_assets_does_not_mutate_input(tmp_path):
    img = tmp_path / "c.png"
    img.write_bytes(b"x")
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"x")
    original = _props(str(img))
    stage_assets(original, audio, tmp_path / "pub", tag="t2", fonts_dir=tmp_path)
    assert original["images"][0]["path"] == str(img)


def test_thumbnail_props_cover_only_no_captions_no_zoom():
    props = {**_props("/x/cover.png"), "captions": [{"lines": ["a"], "startMs": 0, "endMs": 900}],
             "images": [{"path": "/x/cover.png", "startMs": 0, "endMs": 4000, "zoomStartMs": None},
                        {"path": "/x/c1.png", "startMs": 4000, "endMs": 9000, "zoomStartMs": 5000}]}
    thumb = thumbnail_props(props)
    assert thumb["captions"] == []
    assert [i["path"] for i in thumb["images"]] == ["/x/cover.png"]
    assert thumb["images"][0]["zoomStartMs"] is None
    assert len(props["images"]) == 2  # 원본 불변


def test_stage_assets_without_audio(tmp_path):
    img = tmp_path / "c.png"
    img.write_bytes(b"x")
    props, staged = stage_assets(_props(str(img)), None, tmp_path / "pub", tag="t3", fonts_dir=tmp_path)
    assert props["audioFile"] == ""
    assert len(staged) == 1
