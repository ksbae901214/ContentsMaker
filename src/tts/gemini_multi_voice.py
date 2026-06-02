"""다중 화자 Gemini TTS (Phase 3A) — 정치_pro format_type=C 신규 옵션.

기존 단일 화자 (Charon 앵커) 락인 포맷은 유지하고, 명시적으로 활성화한
``--multi-voice`` 플래그에서만 사용된다. 영상 락인 포맷에는 영향 없음.

설계:
  - 씬 metadata에 ``speaker`` 필드 추가 ("anchor" / "reporter") — None이면 anchor.
  - 화자별로 묶어 한 번씩 TTS 호출 → 시간 순서대로 segment 결합.
  - 각 segment를 ffmpeg concat으로 단일 mp3 생성, timing은 각 호출의 길이로 계산.

예시 흐름:
    anchor:   "오늘은 이 뉴스를 다룹니다."
    reporter: "현장에서 김기자입니다."
    anchor:   "어떻게 된 일인가요?"
    reporter: "..."
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR
from src.tts.gemini_tts_generator import _call_gemini_tts, _pcm_to_mp3

logger = logging.getLogger(__name__)

ANCHOR_VOICE_DEFAULT = "Charon"
REPORTER_VOICE_DEFAULT = "Kore"


class MultiVoiceError(Exception):
    """다중 화자 TTS 합성 실패."""


def get_speaker(scene) -> str:
    """씬의 화자 역할 추출 — 락인 포맷 보호를 위해 기본은 'anchor'."""
    # Scene dataclass에 speaker 필드가 추가되면 직접 사용. 없으면 metadata.
    return getattr(scene, "speaker", None) or "anchor"


def generate_multi_voice_with_timing(
    script: ShortsScript,
    *,
    anchor_voice: str = ANCHOR_VOICE_DEFAULT,
    reporter_voice: str = REPORTER_VOICE_DEFAULT,
    api_key: str | None = None,
    style_prompt: str | None = None,
    temperature: float | None = None,
    output_dir: Path | None = None,
) -> tuple[Path, list[dict]]:
    """다중 화자로 ShortsScript → 단일 mp3 + scene_timings.

    Returns: ``(audio_path, [{"scene_id", "start_ms", "end_ms"}, ...])``

    Raises:
        MultiVoiceError: 빈 스크립트, ffmpeg 실패, Gemini 호출 실패.
    """
    import os
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise MultiVoiceError("GEMINI_API_KEY 미설정")

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    segments: list[dict] = []  # {scene_id, mp3_path, duration_ms}
    cursor_ms = 0
    timings: list[dict] = []

    for scene in script.scenes:
        text = (scene.voice_text or "").strip()
        if not text:
            continue
        speaker = get_speaker(scene)
        voice = reporter_voice if speaker == "reporter" else anchor_voice

        try:
            pcm = _call_gemini_tts(
                text, voice, key,
                style_prompt=style_prompt,
                temperature=temperature,
            )
        except Exception as e:
            raise MultiVoiceError(
                f"씬 {scene.id} TTS 실패 ({voice}): {e}"
            ) from e

        seg_mp3 = target_dir / f"{ts}_seg_{scene.id:02d}_{speaker}.mp3"
        _pcm_to_mp3(pcm, seg_mp3)
        duration_ms = _probe_duration_ms(seg_mp3)

        segments.append({"path": seg_mp3, "duration_ms": duration_ms})
        timings.append({
            "scene_id": scene.id,
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + duration_ms,
        })
        cursor_ms += duration_ms

    if not segments:
        raise MultiVoiceError("음성 텍스트 없음 — 모든 씬 voice_text 비어 있음")

    out_path = target_dir / f"{ts}_multi_voice.mp3"
    _concat_mp3(segments, out_path)
    logger.info("다중 화자 TTS 완료: %d 세그먼트 → %s", len(segments), out_path)
    return out_path, timings


def _probe_duration_ms(path: Path) -> int:
    """ffprobe로 mp3 길이 측정 (ms)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise MultiVoiceError(f"ffprobe 실패: {r.stderr.strip()}")
    return int(float(r.stdout.strip()) * 1000)


def _concat_mp3(segments: list[dict], output_path: Path) -> None:
    """ffmpeg concat demuxer로 mp3 이어붙이기."""
    concat_list = output_path.with_suffix(".concat.txt")
    concat_list.write_text(
        "\n".join(f"file '{s['path'].resolve()}'" for s in segments),
        encoding="utf-8",
    )
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list), "-c", "copy", str(output_path)],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            raise MultiVoiceError(f"ffmpeg concat 실패: {r.stderr[-300:]}")
    finally:
        concat_list.unlink(missing_ok=True)
