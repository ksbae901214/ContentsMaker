"""T013 [US1]: Renderer subprocess mock + 자산 복사 검증.

RED 상태 — T023 구현 후 GREEN.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_renderer_module_importable() -> None:
    from src.jpolitics.video import renderer  # noqa: F401


def test_render_invokes_remotion_cli_with_cwd_remotion_v3(tmp_path: Path) -> None:
    """render() 는 cwd=src/video/remotion_v3 으로 npx remotion render 호출."""
    from src.jpolitics.constants import REMOTION_V3_DIR
    from src.jpolitics.video import renderer

    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"\x00" * 100)
    output_path = tmp_path / "video.mp4"

    fake_script = MagicMock()
    fake_script.to_dict.return_value = {
        "metadata": {
            "title": "t",
            "sourceType": "jpolitics_youtube",
            "durationSec": 30.0,
            "createdAt": "2026-06-05T10:00:00",
        },
        "scenes": [],
        "audio": {
            "ttsVoice": "ko-KR-InJoonNeural",
            "ttsRate": "+22%",
            "ttsScript": "t",
            "interSceneGapMs": 300,
            "sfxEnabled": False,
            "bgmEnabled": False,
        },
        "background": {"type": "gradient", "colors": ["#1a1a2e", "#16213e"]},
        "headlinePin": "테스트 헤드라인",
    }

    with patch("subprocess.run") as run_mock:
        run_mock.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        renderer.render(
            script=fake_script,
            audio_path=audio_path,
            scene_timings=[],
            output_path=output_path,
        )

    assert run_mock.called
    call_args = run_mock.call_args
    cmd = call_args.args[0]
    assert "npx" in cmd[0] or cmd[0] == "npx"
    assert "remotion" in cmd
    assert "render" in cmd
    # cwd kwarg는 src/video/remotion_v3 이어야 함
    cwd = call_args.kwargs.get("cwd") or (
        call_args.args[1] if len(call_args.args) > 1 else None
    )
    assert str(cwd) == str(REMOTION_V3_DIR)


def test_render_copies_audio_to_remotion_v3_public(tmp_path: Path) -> None:
    """render() 는 audio.mp3를 remotion_v3/public/ 으로 복사."""
    from src.jpolitics.constants import REMOTION_V3_PUBLIC_DIR
    from src.jpolitics.video import renderer

    audio_src = tmp_path / "src_audio.mp3"
    audio_src.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)
    output_path = tmp_path / "video.mp4"

    fake_script = MagicMock()
    fake_script.to_dict.return_value = {
        "metadata": {"title": "t", "sourceType": "jpolitics_youtube", "durationSec": 30.0, "createdAt": "2026-06-05T10:00:00"},
        "scenes": [],
        "audio": {"ttsVoice": "ko-KR-InJoonNeural", "ttsRate": "+22%", "ttsScript": "t", "interSceneGapMs": 300, "sfxEnabled": False, "bgmEnabled": False},
        "background": {"type": "gradient", "colors": ["#1a1a2e", "#16213e"]},
        "headlinePin": "테스트",
    }

    with patch("subprocess.run") as run_mock:
        run_mock.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        renderer.render(
            script=fake_script,
            audio_path=audio_src,
            scene_timings=[],
            output_path=output_path,
        )

    copied_audio = REMOTION_V3_PUBLIC_DIR / "audio.mp3"
    assert copied_audio.exists(), "audio.mp3 must be copied to remotion_v3/public/"


def test_render_passes_props_as_json(tmp_path: Path) -> None:
    """render() 는 --props='<JSON>' 으로 props 전달."""
    from src.jpolitics.video import renderer

    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"\x00" * 100)
    output_path = tmp_path / "video.mp4"

    fake_script = MagicMock()
    fake_script.to_dict.return_value = {
        "metadata": {"title": "테스트 영상", "sourceType": "jpolitics_youtube", "durationSec": 30.0, "createdAt": "2026-06-05T10:00:00"},
        "scenes": [],
        "audio": {"ttsVoice": "ko-KR-InJoonNeural", "ttsRate": "+22%", "ttsScript": "t", "interSceneGapMs": 300, "sfxEnabled": False, "bgmEnabled": False},
        "background": {"type": "gradient", "colors": ["#1a1a2e", "#16213e"]},
        "headlinePin": "테스트",
    }

    with patch("subprocess.run") as run_mock:
        run_mock.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        renderer.render(
            script=fake_script,
            audio_path=audio_path,
            scene_timings=[],
            output_path=output_path,
        )

    cmd = run_mock.call_args.args[0]
    # --props 또는 --props-json 인자 검색
    props_arg_idx = next(
        (i for i, a in enumerate(cmd) if str(a).startswith("--props")), -1
    )
    assert props_arg_idx >= 0, "--props 인자 없음"
    # 값이 다음 인자 또는 = 형식
    props_str = (
        cmd[props_arg_idx].split("=", 1)[1]
        if "=" in str(cmd[props_arg_idx])
        else cmd[props_arg_idx + 1]
    )
    parsed = json.loads(props_str)
    assert parsed["metadata"]["title"] == "테스트 영상"
