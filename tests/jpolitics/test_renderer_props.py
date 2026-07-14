"""renderer.py props 변환 + durationInFrames 단위 테스트 (Feature 027 Phase 3).

subprocess는 mock 처리 — 실제 Remotion/Node.js 불필요.
"""
from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.jpolitics.models.clip import CaptionCue, ClipResult
from src.jpolitics.video.renderer import (
    RenderError,
    _build_props,
    _duration_in_frames,
    render_moment_short,
)


# ─── 헬퍼 ──────────────────────────────────────────────────────────────────

def _make_clip_result(
    clip_path: str = "/tmp/clip.mp4",
    duration_sec: float = 42.5,
    hook_question: str = "왜 국회에서 이런 일이?",
    keywords: list[str] | None = None,
) -> ClipResult:
    moment_dict = {
        "start_sec": 10.0,
        "end_sec": 10.0 + duration_sec,
        "kind": "clash",
        "speaker": "추미애",
        "summary": "설전 테스트",
        "hook_question": hook_question,
        "keywords": keywords or ["국회", "설전"],
        "confidence": 0.9,
    }
    return ClipResult(
        source_video="/tmp/source.mp4",
        clip_path=clip_path,
        moment_dict=moment_dict,
        width=1080,
        height=1920,
        fps=30.0,
        duration_sec=duration_sec,
        crop_x=0.5,
    )


def _make_captions() -> list[CaptionCue]:
    return [
        CaptionCue(start_sec=0.0, end_sec=3.5, text="추미애 의원이 발언을 시작했습니다"),
        CaptionCue(start_sec=3.5, end_sec=7.0, text="나경원 의원이 반박에 나섰습니다"),
        CaptionCue(start_sec=7.0, end_sec=12.0, text="의장이 제지에 나섰습니다"),
    ]


# ─── _duration_in_frames ────────────────────────────────────────────────────

class TestDurationInFrames:
    def test_exact_seconds(self):
        assert _duration_in_frames(30.0) == 900

    def test_ceil_applied(self):
        # 42.5초 → 42.5 × 30 = 1275.0 → 1275 (올림 필요 없음)
        assert _duration_in_frames(42.5) == 1275

    def test_fractional_ceil(self):
        # 1.1초 → 1.1 × 30 = 33.0 → 33
        assert _duration_in_frames(1.1) == math.ceil(1.1 * 30)

    def test_non_multiple_ceil(self):
        # 1.03초 → 1.03 × 30 = 30.9 → 31 (올림)
        assert _duration_in_frames(1.03) == 31

    def test_zero_point_one(self):
        # 0.1초 → 0.1 × 30 = 3.0 → 3
        assert _duration_in_frames(0.1) == 3


# ─── _build_props ───────────────────────────────────────────────────────────

class TestBuildProps:
    def test_source_label_format(self):
        clip = _make_clip_result()
        props = _build_props(
            clip, [], channel="YTN", source_date="2016.12.15",
            clip_filename="clip.mp4",
        )
        assert props["sourceLabel"] == "출처: YTN (2016.12.15)"

    def test_clip_file_name(self):
        clip = _make_clip_result(clip_path="/tmp/moment_01.mp4")
        props = _build_props(
            clip, [], channel="KBS", source_date="2024.01.01",
            clip_filename="moment_01.mp4",
        )
        assert props["clipFileName"] == "moment_01.mp4"

    def test_hook_question_forwarded(self):
        clip = _make_clip_result(hook_question="국회에서 왜 이런 일이?")
        props = _build_props(
            clip, [], channel="MBC", source_date="2020.05.30",
            clip_filename="clip.mp4",
        )
        assert props["hookQuestion"] == "국회에서 왜 이런 일이?"

    def test_keywords_forwarded(self):
        clip = _make_clip_result(keywords=["설전", "호통"])
        props = _build_props(
            clip, [], channel="SBS", source_date="2022.03.09",
            clip_filename="clip.mp4",
        )
        assert props["hookKeywords"] == ["설전", "호통"]

    def test_duration_sec_forwarded(self):
        clip = _make_clip_result(duration_sec=55.0)
        props = _build_props(
            clip, [], channel="NATV", source_date="2021.09.01",
            clip_filename="clip.mp4",
        )
        assert props["durationSec"] == pytest.approx(55.0)

    def test_captions_converted(self):
        clip = _make_clip_result()
        cues = _make_captions()
        props = _build_props(
            clip, cues, channel="YTN", source_date="2016.12.15",
            clip_filename="clip.mp4",
        )
        assert len(props["captions"]) == 3
        first = props["captions"][0]
        assert first["startSec"] == pytest.approx(0.0)
        assert first["endSec"] == pytest.approx(3.5)
        assert first["text"] == "추미애 의원이 발언을 시작했습니다"

    def test_camel_case_keys_in_captions(self):
        clip = _make_clip_result()
        cues = [CaptionCue(start_sec=1.0, end_sec=4.0, text="테스트")]
        props = _build_props(
            clip, cues, channel="YTN", source_date="2024.01.01",
            clip_filename="clip.mp4",
        )
        caption = props["captions"][0]
        # camelCase 키 확인
        assert "startSec" in caption
        assert "endSec" in caption
        assert "text" in caption
        # snake_case 키 없어야 함
        assert "start_sec" not in caption
        assert "end_sec" not in caption

    def test_empty_captions(self):
        clip = _make_clip_result()
        props = _build_props(
            clip, [], channel="채널A", source_date="2023.11.22",
            clip_filename="clip.mp4",
        )
        assert props["captions"] == []

    def test_camel_hook_question_key_fallback(self):
        """moment_dict에 camelCase 키(hookQuestion)만 있어도 올바르게 읽힘."""
        clip = ClipResult(
            source_video="/tmp/src.mp4",
            clip_path="/tmp/clip.mp4",
            moment_dict={
                "start_sec": 0.0,
                "end_sec": 30.0,
                "kind": "laughter",
                "speaker": "박범계",
                "summary": "웃음 모먼트",
                "hookQuestion": "왜 웃음이 터졌을까?",   # camelCase
                "keywords": ["웃음"],
                "confidence": 0.8,
            },
            width=1080,
            height=1920,
            fps=30.0,
            duration_sec=30.0,
            crop_x=0.5,
        )
        props = _build_props(
            clip, [], channel="KBS", source_date="2025.01.01",
            clip_filename="clip.mp4",
        )
        assert props["hookQuestion"] == "왜 웃음이 터졌을까?"


# ─── render_moment_short (subprocess mock) ──────────────────────────────────

class TestRenderMomentShort:
    def test_successful_render(self, tmp_path: Path):
        clip = _make_clip_result(clip_path=str(tmp_path / "clip.mp4"))
        # 가짜 클립 파일 생성
        (tmp_path / "clip.mp4").write_bytes(b"fake_mp4_data")

        output = tmp_path / "output.mp4"

        def fake_run(cmd, **kwargs):
            output.write_bytes(b"0" * (1024 * 1024 * 5))
            m = MagicMock()
            m.returncode = 0
            return m

        with (
            patch("src.jpolitics.video.renderer.shutil.which", return_value="/usr/bin/npx"),
            patch("src.jpolitics.video.renderer.subprocess.run", side_effect=fake_run),
        ):
            result = render_moment_short(
                clip, _make_captions(),
                channel="YTN",
                source_date="2016.12.15",
                output_path=output,
            )

        assert result == output

    def test_npx_not_found_raises(self, tmp_path: Path):
        clip = _make_clip_result(clip_path=str(tmp_path / "clip.mp4"))
        (tmp_path / "clip.mp4").write_bytes(b"fake")

        with patch("src.jpolitics.video.renderer.shutil.which", return_value=None):
            with pytest.raises(RenderError, match="npx"):
                render_moment_short(
                    clip, [],
                    channel="YTN",
                    source_date="2024.01.01",
                    output_path=tmp_path / "out.mp4",
                )

    def test_nonzero_exit_raises(self, tmp_path: Path):
        clip = _make_clip_result(clip_path=str(tmp_path / "clip.mp4"))
        (tmp_path / "clip.mp4").write_bytes(b"fake")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Remotion error: composition not found"
        mock_result.stdout = ""

        with (
            patch("src.jpolitics.video.renderer.shutil.which", return_value="/usr/bin/npx"),
            patch("src.jpolitics.video.renderer.subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(RenderError, match="Remotion 렌더링 실패"):
                render_moment_short(
                    clip, [],
                    channel="YTN",
                    source_date="2024.01.01",
                    output_path=tmp_path / "out.mp4",
                )

    def test_subprocess_called_with_remotion_args(self, tmp_path: Path):
        clip = _make_clip_result(clip_path=str(tmp_path / "clip.mp4"))
        (tmp_path / "clip.mp4").write_bytes(b"fake")

        output = tmp_path / "output.mp4"

        def fake_run(cmd, **kwargs):
            output.write_bytes(b"0" * 1024)
            m = MagicMock()
            m.returncode = 0
            return m

        with (
            patch("src.jpolitics.video.renderer.shutil.which", return_value="/usr/bin/npx"),
            patch("src.jpolitics.video.renderer.subprocess.run", side_effect=fake_run) as mock_run,
        ):
            render_moment_short(
                clip, [],
                channel="SBS",
                source_date="2022.03.09",
                output_path=output,
            )

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "remotion" in cmd
        assert "render" in cmd
        assert "MomentShorts" in cmd
        assert "--props" in cmd

    def test_source_label_in_props(self, tmp_path: Path):
        """subprocess에 전달된 props 파일에 sourceLabel이 정확한 형식인지 검증."""
        clip = _make_clip_result(clip_path=str(tmp_path / "clip.mp4"))
        (tmp_path / "clip.mp4").write_bytes(b"fake")

        output = tmp_path / "output.mp4"
        captured_props: list[dict] = []

        import json as _json

        def fake_run(cmd, **kwargs):
            # --props 다음 인자가 props 파일 경로
            if "--props" in cmd:
                props_idx = cmd.index("--props") + 1
                props_path = Path(cmd[props_idx])
                if props_path.exists():
                    captured_props.append(_json.loads(props_path.read_text()))
            output.write_bytes(b"0" * 1024)
            m = MagicMock()
            m.returncode = 0
            return m

        with (
            patch("src.jpolitics.video.renderer.shutil.which", return_value="/usr/bin/npx"),
            patch("src.jpolitics.video.renderer.subprocess.run", side_effect=fake_run),
        ):
            render_moment_short(
                clip, [],
                channel="국회방송",
                source_date="2023.06.15",
                output_path=output,
            )

        # props 파일이 실제로 임시 파일이라 삭제 전에 캡처됨
        assert len(captured_props) == 1
        assert captured_props[0]["sourceLabel"] == "출처: 국회방송 (2023.06.15)"
