"""Tests for src/scraper/youtube_news_searcher.py (Feature 023)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.scraper.youtube_news_searcher import (
    YouTubeNewsSearchError,
    build_scene_clips,
    cut_scene_clip,
    safe_search_keyword,
    search_and_download_news_clips,
)


# ────────────────── safe_search_keyword ──────────────────


def test_safe_search_keyword_strips_whitespace_and_quotes():
    assert safe_search_keyword('  "스타벅스 5.18 논란"  ') == "스타벅스 5.18 논란"


def test_safe_search_keyword_normalizes_internal_whitespace():
    assert safe_search_keyword("스타벅스\n5.18\t탱크데이") == "스타벅스 5.18 탱크데이"


def test_safe_search_keyword_caps_length():
    long = "스" * 200
    result = safe_search_keyword(long, max_chars=50)
    assert len(result) == 50


def test_safe_search_keyword_empty_input():
    assert safe_search_keyword("") == ""
    assert safe_search_keyword(None) == ""  # type: ignore[arg-type]


# ────────────────── search_and_download_news_clips ──────────────────


def test_search_and_download_empty_keyword_skipped(tmp_path):
    """빈 키워드는 None으로 채워서 인덱스 보존."""
    results = search_and_download_news_clips([""], out_dir=tmp_path)
    assert len(results) == 1
    assert results[0] is None


def test_search_and_download_yt_dlp_failure_returns_none(tmp_path):
    """yt-dlp 호출 실패 → 해당 인덱스 None."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="No matches found",
        )
        results = search_and_download_news_clips(["존재하지않는키워드xyz123"], out_dir=tmp_path)
    assert len(results) == 1
    assert results[0] is None


def test_search_and_download_success(tmp_path):
    """yt-dlp 성공 → 다운로드된 파일 경로 반환."""
    fake_file = tmp_path / "search00_test.mp4"
    fake_file.write_bytes(b"fake")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f"{fake_file}\n",
            stderr="",
        )
        results = search_and_download_news_clips(["스타벅스 5.18"], out_dir=tmp_path)

    assert len(results) == 1
    assert results[0] == fake_file


def test_search_and_download_glob_fallback(tmp_path):
    """stdout 비어있어도 glob으로 파일 찾음."""
    fake_file = tmp_path / "search00_actual.mp4"
    fake_file.write_bytes(b"fake")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        results = search_and_download_news_clips(["test"], out_dir=tmp_path)

    assert len(results) == 1
    assert results[0] == fake_file


def test_search_and_download_multiple_keywords_preserves_order(tmp_path):
    """여러 키워드 — 일부 실패, 일부 성공 시 길이·순서 보존."""
    file1 = tmp_path / "search00_a.mp4"
    file1.write_bytes(b"a")
    file2 = tmp_path / "search02_c.mp4"
    file2.write_bytes(b"c")

    call_count = [0]

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        n = call_count[0]
        if n == 1:
            return MagicMock(returncode=0, stdout=str(file1) + "\n", stderr="")
        if n == 2:
            return MagicMock(returncode=1, stdout="", stderr="fail")
        if n == 3:
            return MagicMock(returncode=0, stdout=str(file2) + "\n", stderr="")
        raise RuntimeError("unexpected call")

    with patch("subprocess.run", side_effect=fake_run):
        results = search_and_download_news_clips(
            ["kw1", "kw2", "kw3"], out_dir=tmp_path,
        )
    assert len(results) == 3
    assert results[0] == file1
    assert results[1] is None
    assert results[2] == file2


# ────────────────── cut_scene_clip ──────────────────


def test_cut_scene_clip_ffmpeg_invoked_with_crop(tmp_path):
    """9:16 크롭 명령에 scale + crop 필터 포함."""
    src = tmp_path / "src.mp4"
    src.write_bytes(b"src")
    out = tmp_path / "out.mp4"

    def fake_run(cmd, *args, **kwargs):
        # ffmpeg 명령 확인
        assert cmd[0] == "ffmpeg"
        assert "-ss" in cmd and "5.0" in cmd
        assert "-t" in cmd
        # 9:16 크롭 필터
        vf_idx = cmd.index("-vf")
        assert "scale=-2:1920" in cmd[vf_idx + 1]
        assert "crop=1080:1920" in cmd[vf_idx + 1]
        # 오디오 제거
        assert "-an" in cmd
        out.write_bytes(b"out")  # 출력 파일 생성 흉내
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        result = cut_scene_clip(src, output=out, start_sec=5.0, duration_sec=6.0)

    assert result == out
    assert out.exists()


def test_cut_scene_clip_no_crop_keeps_aspect(tmp_path):
    """crop_9x16=False면 -vf 필터 없음."""
    src = tmp_path / "src.mp4"
    src.write_bytes(b"src")
    out = tmp_path / "out.mp4"

    def fake_run(cmd, *args, **kwargs):
        assert "-vf" not in cmd  # 크롭 필터 없음
        out.write_bytes(b"out")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        cut_scene_clip(src, output=out, start_sec=0, duration_sec=3.0, crop_9x16=False)


def test_cut_scene_clip_ffmpeg_failure_raises(tmp_path):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"src")
    out = tmp_path / "out.mp4"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="ffmpeg failed",
        )
        with pytest.raises(YouTubeNewsSearchError, match="ffmpeg cut 실패"):
            cut_scene_clip(src, output=out, start_sec=0, duration_sec=3.0)


# ────────────────── build_scene_clips (통합) ──────────────────


def test_build_scene_clips_happy_path(tmp_path):
    """검색·다운로드·cut 흐름이 차례로 호출되고 결과가 매핑됨."""
    durations = [4.0, 5.0]
    keywords = ["kw1", "kw2"]

    # 다운로드 결과 mock
    src1 = tmp_path / "sources" / "search00_a.mp4"
    src2 = tmp_path / "sources" / "search01_b.mp4"

    def fake_download(kws, *, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        src1.write_bytes(b"src1")
        src2.write_bytes(b"src2")
        return [src1, src2]

    def fake_duration(p: Path) -> float:
        return 60.0  # 충분히 긴 소스

    def fake_cut(src, *, output, start_sec, duration_sec, **kwargs):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"cut")
        return output

    with patch(
        "src.scraper.youtube_news_searcher.search_and_download_news_clips",
        side_effect=fake_download,
    ), patch(
        "src.scraper.youtube_news_searcher.get_video_duration_sec",
        side_effect=fake_duration,
    ), patch(
        "src.scraper.youtube_news_searcher.cut_scene_clip",
        side_effect=fake_cut,
    ):
        clips = build_scene_clips(
            durations, keywords=keywords, out_dir=tmp_path,
        )

    assert len(clips) == 2
    assert clips[0] == tmp_path / "scenes" / "s00.mp4"
    assert clips[1] == tmp_path / "scenes" / "s01.mp4"


def test_build_scene_clips_failed_source_returns_none(tmp_path):
    """검색 실패한 씬은 None이 들어가도 다른 씬은 정상 처리."""
    durations = [3.0, 4.0]
    keywords = ["kw1", "fail"]

    src1 = tmp_path / "sources" / "search00_a.mp4"

    def fake_download(kws, *, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        src1.write_bytes(b"src1")
        return [src1, None]

    def fake_cut(src, *, output, start_sec, duration_sec, **kwargs):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"cut")
        return output

    with patch(
        "src.scraper.youtube_news_searcher.search_and_download_news_clips",
        side_effect=fake_download,
    ), patch(
        "src.scraper.youtube_news_searcher.get_video_duration_sec",
        return_value=30.0,
    ), patch(
        "src.scraper.youtube_news_searcher.cut_scene_clip",
        side_effect=fake_cut,
    ):
        clips = build_scene_clips(
            durations, keywords=keywords, out_dir=tmp_path,
        )

    assert len(clips) == 2
    assert clips[0] is not None
    assert clips[1] is None  # 다운로드 실패한 씬


def test_build_scene_clips_mismatched_lengths(tmp_path):
    """durations/keywords 길이 다르면 짧은 쪽 기준으로 처리."""
    with patch(
        "src.scraper.youtube_news_searcher.search_and_download_news_clips",
        return_value=[None],
    ):
        clips = build_scene_clips(
            [3.0, 4.0, 5.0],  # 3개
            keywords=["kw1"],  # 1개
            out_dir=tmp_path,
        )
    assert len(clips) == 1  # 짧은 쪽 기준


# ────────────────── crop_mode / letterbox ──────────────────


def test_cut_scene_clip_letterbox_mode(tmp_path):
    """crop_mode='letterbox' → letterbox vf filter (위아래 검은 여백)."""
    src = tmp_path / "src.mp4"
    src.write_bytes(b"src")
    out = tmp_path / "out.mp4"

    def fake_run(cmd, *args, **kwargs):
        vf_idx = cmd.index("-vf")
        vf = cmd[vf_idx + 1]
        assert "pad=1080:1920" in vf, f"Expected letterbox pad, got: {vf}"
        assert "scale=1080:-2" in vf, f"Expected letterbox scale, got: {vf}"
        # Must NOT use crop
        assert "crop=1080:1920" not in vf
        out.write_bytes(b"out")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        result = cut_scene_clip(
            src, output=out, start_sec=0, duration_sec=3.0, crop_mode="letterbox",
        )

    assert result == out


def test_cut_scene_clip_crop_mode_explicit_crop(tmp_path):
    """crop_mode='crop' → same crop filter as crop_9x16=True."""
    src = tmp_path / "src.mp4"
    src.write_bytes(b"src")
    out = tmp_path / "out.mp4"

    def fake_run(cmd, *args, **kwargs):
        vf_idx = cmd.index("-vf")
        vf = cmd[vf_idx + 1]
        assert "scale=-2:1920" in vf
        assert "crop=1080:1920" in vf
        out.write_bytes(b"out")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        cut_scene_clip(src, output=out, start_sec=0, duration_sec=3.0, crop_mode="crop")


def test_cut_scene_clip_crop_mode_none_no_filter(tmp_path):
    """crop_mode=None and crop_9x16=False → no -vf filter."""
    src = tmp_path / "src.mp4"
    src.write_bytes(b"src")
    out = tmp_path / "out.mp4"

    def fake_run(cmd, *args, **kwargs):
        assert "-vf" not in cmd
        out.write_bytes(b"out")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        cut_scene_clip(
            src, output=out, start_sec=0, duration_sec=3.0,
            crop_mode=None, crop_9x16=False,
        )


def test_build_scene_clips_passes_crop_mode_letterbox(tmp_path):
    """build_scene_clips(crop_mode='letterbox') passes it to cut_scene_clip."""
    src = tmp_path / "sources" / "search00_a.mp4"
    captured_modes: list = []

    def fake_download(kws, *, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        src.write_bytes(b"src")
        return [src]

    def fake_cut(s, *, output, start_sec, duration_sec, crop_mode="crop", **kwargs):
        captured_modes.append(crop_mode)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"cut")
        return output

    with patch(
        "src.scraper.youtube_news_searcher.search_and_download_news_clips",
        side_effect=fake_download,
    ), patch(
        "src.scraper.youtube_news_searcher.get_video_duration_sec",
        return_value=30.0,
    ), patch(
        "src.scraper.youtube_news_searcher.cut_scene_clip",
        side_effect=fake_cut,
    ):
        build_scene_clips([4.0], keywords=["kw1"], out_dir=tmp_path, crop_mode="letterbox")

    assert captured_modes == ["letterbox"]
