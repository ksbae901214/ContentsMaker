"""ClipMaker 테스트 (Feature 027 Phase 2).

ffmpeg으로 합성 테스트 영상을 생성한 뒤 make_moment_clip()을 실제 실행해 검증.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.jpolitics.models.moment import Moment
from src.jpolitics.video.clip_maker import ClipMakeError, make_moment_clip


# ── 합성 영상 fixture ──────────────────────────────────────────────────────

def _make_video(path: Path, duration: float = 10.0, width: int = 1920, height: int = 1080) -> Path:
    """ffmpeg testsrc + sine 으로 합성 영상을 생성한다."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate=30:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"합성 영상 생성 실패: {result.stderr[-300:]}"
    return path


@pytest.fixture(scope="module")
def landscape_video(tmp_path_factory) -> Path:
    """5초 합성 가로(1920×1080) 영상."""
    d = tmp_path_factory.mktemp("clip_maker")
    return _make_video(d / "landscape.mp4", duration=10.0, width=1920, height=1080)


@pytest.fixture(scope="module")
def portrait_video(tmp_path_factory) -> Path:
    """10초 합성 세로(1080×1920) 영상."""
    d = tmp_path_factory.mktemp("clip_maker_portrait")
    return _make_video(d / "portrait.mp4", duration=10.0, width=1080, height=1920)


def _moment(start: float = 1.0, end: float = 7.0) -> Moment:
    return Moment(
        start_sec=start,
        end_sec=end,
        kind="clash",
        speaker="테스트",
        summary="합성 영상 테스트",
        hook_question="왜 이 순간?",
        keywords=("테스트",),
        confidence=0.9,
    )


# ── 기본 동작 테스트 ───────────────────────────────────────────────────────

class TestMakeMomentClip:
    def test_landscape_produces_portrait(self, landscape_video: Path, tmp_path: Path):
        """가로 영상 → 1080×1920 세로 클립 생성."""
        out = tmp_path / "clip.mp4"
        result = make_moment_clip(
            source_video=landscape_video,
            moment=_moment(1.0, 7.0),
            output_path=out,
            pad_before=0.5,
            pad_after=0.5,
        )
        assert out.exists()
        assert result.width == 1080
        assert result.height == 1920
        assert result.duration_sec == pytest.approx(7.0, abs=0.5)

    def test_audio_track_exists(self, landscape_video: Path, tmp_path: Path):
        """출력 클립에 오디오 스트림이 있어야 한다."""
        out = tmp_path / "clip_audio.mp4"
        make_moment_clip(
            source_video=landscape_video,
            moment=_moment(1.0, 7.0),
            output_path=out,
        )
        import json as _json, subprocess as _sub
        probe = _sub.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(out)],
            capture_output=True, text=True,
        )
        streams = _json.loads(probe.stdout).get("streams", [])
        codec_types = [s.get("codec_type") for s in streams]
        assert "audio" in codec_types

    def test_portrait_video_no_crop_error(self, portrait_video: Path, tmp_path: Path):
        """세로 영상은 크롭 없이 스케일만 — 오류 없어야 한다."""
        out = tmp_path / "clip_portrait.mp4"
        result = make_moment_clip(
            source_video=portrait_video,
            moment=_moment(1.0, 7.0),
            output_path=out,
        )
        assert result.width == 1080
        assert result.height == 1920

    def test_crop_x_boundary_zero(self, landscape_video: Path, tmp_path: Path):
        """crop_x=0.0 (왼쪽 정렬) — 오류 없어야 한다."""
        out = tmp_path / "clip_left.mp4"
        result = make_moment_clip(
            source_video=landscape_video,
            moment=_moment(1.0, 7.0),
            output_path=out,
            crop_x=0.0,
        )
        assert result.clip_path == str(out)

    def test_crop_x_boundary_one(self, landscape_video: Path, tmp_path: Path):
        """crop_x=1.0 (오른쪽 정렬) — 오류 없어야 한다."""
        out = tmp_path / "clip_right.mp4"
        result = make_moment_clip(
            source_video=landscape_video,
            moment=_moment(1.0, 7.0),
            output_path=out,
            crop_x=1.0,
        )
        assert result.clip_path == str(out)

    def test_moment_extends_beyond_video_clamp(self, landscape_video: Path, tmp_path: Path):
        """모먼트 end_sec가 영상 길이를 초과해도 클램프되어 성공해야 한다."""
        out = tmp_path / "clip_clamp.mp4"
        # 합성 영상 10초, 모먼트는 3~9초 + pad_after 3초 → 클램프되어 10초 경계
        result = make_moment_clip(
            source_video=landscape_video,
            moment=_moment(3.0, 9.0),
            output_path=out,
            pad_before=0.5,
            pad_after=3.0,
        )
        assert result.duration_sec > 0

    def test_too_short_clip_raises(self, landscape_video: Path, tmp_path: Path):
        """결과 클립이 5초 미만이면 ClipMakeError를 발생시킨다."""
        out = tmp_path / "clip_short.mp4"
        # pad 없음, 모먼트 1초짜리
        with pytest.raises(ClipMakeError):
            make_moment_clip(
                source_video=landscape_video,
                moment=_moment(3.0, 4.0),
                output_path=out,
                pad_before=0.0,
                pad_after=0.0,
            )

    def test_nonexistent_source_raises(self, tmp_path: Path):
        """존재하지 않는 원본 영상은 ClipMakeError."""
        with pytest.raises(ClipMakeError):
            make_moment_clip(
                source_video=tmp_path / "no_such.mp4",
                moment=_moment(),
                output_path=tmp_path / "out.mp4",
            )

    def test_clip_result_roundtrip(self, landscape_video: Path, tmp_path: Path):
        """ClipResult.save() / from_dict() 왕복 직렬화 검증."""
        out = tmp_path / "clip_rt.mp4"
        result = make_moment_clip(
            source_video=landscape_video,
            moment=_moment(1.0, 7.0),
            output_path=out,
        )
        saved = result.save(tmp_path, 1)
        import json as _json
        restored = result.__class__.from_dict(_json.loads(saved.read_text()))
        assert restored.width == result.width
        assert restored.height == result.height
        assert restored.clip_path == result.clip_path
