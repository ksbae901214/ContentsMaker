"""T018 [US1]: TTS 합성 — V1 락인 (InJoonNeural +22%) + 씬 간 gap 300 ms.

직접 edge-tts 호출, voice/rate/gap 인자 부재 (락인 가드).
씬 간 무음 300 ms는 ffmpeg `anullsrc`로 정확 생성 후 concat.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TYPE_CHECKING

import edge_tts

if TYPE_CHECKING:
    from src.jpolitics.models.script import JpoliticsScript

from src.jpolitics.constants import INTER_SCENE_GAP_MS, TTS_RATE, TTS_VOICE
from src.jpolitics.logger import get_logger

# Lock-in 모듈 상수 (테스트 어설션 대상 — 변경 금지)
VOICE: Final[str] = TTS_VOICE  # "ko-KR-InJoonNeural"
RATE: Final[str] = TTS_RATE  # "+22%"
INTER_SCENE_GAP_MS_CONST: Final[int] = INTER_SCENE_GAP_MS  # 300

# 테스트가 import할 alias
INTER_SCENE_GAP_MS = INTER_SCENE_GAP_MS_CONST  # type: ignore[misc]

logger = get_logger("tts.voice")


@dataclass(frozen=True)
class SceneTiming:
    """씬별 오디오 타이밍 (Remotion 동기화)."""

    scene_id: int
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


async def _synthesize_single(text: str, output_path: Path) -> int:
    """edge-tts로 단일 텍스트 합성, 결과 mp3 길이(ms) 반환."""
    communicate = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE)
    await communicate.save(str(output_path))
    return _probe_duration_ms(output_path)


def _probe_duration_ms(audio_path: Path) -> int:
    """ffprobe로 mp3 duration 추출 (ms 단위)."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(float(result.stdout.strip()) * 1000)


def _generate_silence(duration_ms: int, output_path: Path) -> None:
    """ffmpeg anullsrc로 정확한 무음 mp3 생성."""
    seconds = duration_ms / 1000.0
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=mono:sample_rate=24000",
            "-t",
            f"{seconds:.3f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "32k",
            "-loglevel",
            "error",
            str(output_path),
        ],
        check=True,
    )


def _concat_mp3s(parts: list[Path], output_path: Path) -> None:
    """ffmpeg concat demuxer로 mp3 파일들 이어붙이기."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
        list_file = Path(f.name)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                "-loglevel",
                "error",
                str(output_path),
            ],
            check=True,
        )
    finally:
        list_file.unlink(missing_ok=True)


async def _synthesize_async(
    script: "JpoliticsScript", output_path: Path
) -> tuple[Path, list[SceneTiming]]:
    """씬별 합성 + 씬 간 300 ms 무음 삽입 + concat."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timings: list[SceneTiming] = []
    parts: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="jpolitics_tts_") as tmp:
        tmp_dir = Path(tmp)
        # 무음 파일 1회 생성 (재사용)
        silence_path = tmp_dir / "silence.mp3"
        _generate_silence(INTER_SCENE_GAP_MS_CONST, silence_path)

        cursor_ms = 0
        for i, scene in enumerate(script.scenes):
            scene_audio = tmp_dir / f"scene_{scene.id}.mp3"
            duration_ms = await _synthesize_single(scene.voice_text, scene_audio)
            parts.append(scene_audio)
            timings.append(
                SceneTiming(
                    scene_id=scene.id,
                    start_ms=cursor_ms,
                    end_ms=cursor_ms + duration_ms,
                )
            )
            cursor_ms += duration_ms

            # 마지막 씬이 아니면 gap 삽입 (FR-036)
            if i < len(script.scenes) - 1:
                parts.append(silence_path)
                cursor_ms += INTER_SCENE_GAP_MS_CONST

        _concat_mp3s(parts, output_path)

    logger.info(
        "TTS 합성 완료: %s (%d 씬, 총 %.1f초)",
        output_path,
        len(script.scenes),
        cursor_ms / 1000.0,
    )
    return output_path, timings


def synthesize(
    script: "JpoliticsScript", output_path: Path
) -> tuple[Path, list[SceneTiming]]:
    """씬 단위 edge-tts 합성 + 300 ms gap concat. 락인 가드: voice/rate/gap 인자 부재.

    Args:
        script: V3 JpoliticsScript
        output_path: 최종 mp3 출력 경로

    Returns:
        (output_path, scene_timings)
    """
    return asyncio.run(_synthesize_async(script, output_path))
