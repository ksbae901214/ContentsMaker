"""Edge-TTS generator — converts ShortsScript to voice MP3.

Uses Microsoft Edge's free TTS engine via edge-tts library.
Generates per-scene audio segments and concatenates them for
precise scene-to-audio timing synchronization.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import struct
from datetime import datetime
from pathlib import Path

import edge_tts

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR
from src.video.outro_template import OUTRO_VOICE_TEXT

logger = logging.getLogger(__name__)

# QW-05: 단일 출처 (src/video/outro_template.py)에서 가져온 표준화된 아웃트로 음성 텍스트.
OUTRO_TEXT = OUTRO_VOICE_TEXT

_SSML_BREAK_RE = re.compile(r"<break\s+time=['\"][^'\"]*['\"]\s*/?>")


def _strip_ssml_tags(text: str) -> str:
    """Remove SSML break tags from text for edge-tts compatibility.

    edge-tts escapes XML tags, causing them to be read aloud.
    Punctuation already provides natural pauses in edge-tts.
    """
    cleaned = _SSML_BREAK_RE.sub("", text)
    cleaned = re.sub(r"  +", " ", cleaned)
    return cleaned.strip()


class TTSError(Exception):
    """Raised when TTS generation fails."""


def generate_voice(script: ShortsScript, output_dir: Path | None = None) -> Path:
    """Generate voice MP3 from a ShortsScript (legacy simple mode).

    Returns path to the generated MP3 file.
    """
    tts_text = _strip_ssml_tags(script.audio.tts_script)
    if not tts_text or not tts_text.strip():
        raise TTSError("TTS 스크립트가 비어있습니다")

    voice = script.audio.voice
    rate = script.audio.rate
    pitch = script.audio.pitch

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = _safe_filename(script.metadata.title)
    output_path = target_dir / f"{timestamp}_{safe_title}.mp3"

    try:
        asyncio.run(_generate_async(tts_text, voice, rate, pitch, output_path))
    except Exception as e:
        raise TTSError(f"TTS 생성 실패: {e}") from e

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TTSError(f"TTS 파일이 생성되지 않았습니다: {output_path}")

    logger.info("TTS 저장 완료: %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)
    return output_path


def _group_scenes_by_subtitle_group(scenes) -> list[list]:
    """연속된 같은 subtitle_group_id 씬들을 묶음. group_id=None은 단독 그룹.

    Phase 6 (2026-05-20): 분할 자식들을 1번에 TTS 합성 → 양 끝 무음 누적 제거.
    """
    if not scenes:
        return []
    groups: list[list] = []
    current: list = [scenes[0]]
    for s in scenes[1:]:
        prev = current[-1]
        # 연속이고 같은 group_id이며 둘 다 None이 아니면 같은 그룹
        if (
            s.subtitle_group_id is not None
            and prev.subtitle_group_id == s.subtitle_group_id
        ):
            current.append(s)
        else:
            groups.append(current)
            current = [s]
    groups.append(current)
    return groups


def generate_voice_with_timing(
    script: ShortsScript,
    output_dir: Path | None = None,
) -> tuple[Path, list[dict]]:
    """Generate per-scene TTS audio and concatenate with precise timing.

    Strategy: group consecutive scenes by subtitle_group_id, synthesize each
    group as ONE TTS call (eliminates accumulated silence at segment boundaries),
    then split timing per scene by character ratio.

    Phase 6 (2026-05-20): 분할 자식 씬들의 TTS 텀 단축. 같은 group_id 자식들은
    " ".join 후 1번 합성 → 양 끝 무음 누적 제거 → 자연스러운 흐름.

    Returns (audio_path, scene_timings) where scene_timings is:
    [{"scene_id": int, "start_ms": int, "end_ms": int}, ...]
    """
    voice = script.audio.voice
    rate = script.audio.rate
    pitch = script.audio.pitch

    target_dir = output_dir or DATA_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = _safe_filename(script.metadata.title)

    # Phase 6: 자막 그룹 단위로 묶어서 합성 — 분할 자식들 사이 무음 누적 제거.
    grouped = _group_scenes_by_subtitle_group(list(script.scenes))

    # Generate per-group audio segments
    scene_segments: list[dict] = []
    temp_files: list[Path] = []

    for gi, group in enumerate(grouped):
        # 자막용 text는 \n 보존, voice_text는 SSML strip + \n → space
        texts: list[str] = []
        for s in group:
            t = _strip_ssml_tags((s.voice_text or "").replace("\n", " "))
            texts.append(t)
        # 빈 텍스트 자식 제외
        valid_idx = [i for i, t in enumerate(texts) if t]
        if not valid_idx:
            continue
        valid_scenes = [group[i] for i in valid_idx]
        valid_texts = [texts[i] for i in valid_idx]

        # 그룹 자식들을 공백으로 join → 1번 합성. 양 끝 무음이 그룹 전체에 1쌍만 적용됨.
        combined = " ".join(valid_texts)
        seg_path = target_dir / f"{timestamp}_grp_{gi:02d}.mp3"
        temp_files.append(seg_path)

        try:
            asyncio.run(_generate_async(combined, voice, rate, pitch, seg_path))
        except Exception as e:
            logger.warning("그룹 %d TTS 실패: %s", gi, e)
            continue

        if not seg_path.exists() or seg_path.stat().st_size == 0:
            logger.warning("그룹 %d TTS 빈 파일", gi)
            continue

        group_dur_ms = _get_mp3_duration_ms(seg_path)

        if len(valid_scenes) == 1:
            # 단일 씬 — 직접 할당
            scene_segments.append({
                "scene_id": valid_scenes[0].id,
                "path": seg_path,
                "duration_ms": group_dur_ms,
            })
            logger.info(
                "  씬 %d: %.2fs (%s)",
                valid_scenes[0].id, group_dur_ms / 1000, valid_texts[0][:30],
            )
        else:
            # 그룹 자식 — 글자수 비율로 timing 분배. 마지막 자식이 그룹 end 보장.
            total_chars = sum(len(t) for t in valid_texts)
            cum_ms = 0
            for ci, (sc, tx) in enumerate(zip(valid_scenes, valid_texts)):
                if ci == len(valid_scenes) - 1:
                    child_ms = group_dur_ms - cum_ms  # 잔여 — 누적 오차 흡수
                else:
                    child_ms = int(group_dur_ms * len(tx) / total_chars)
                scene_segments.append({
                    "scene_id": sc.id,
                    "path": seg_path if ci == 0 else None,  # concat은 첫 자식에서만
                    "duration_ms": child_ms,
                })
                cum_ms += child_ms
            logger.info(
                "  그룹 %d (%d자식): %.2fs '%s'",
                gi, len(valid_scenes), group_dur_ms / 1000, combined[:40],
            )

    # Generate outro segment
    outro_path = target_dir / f"{timestamp}_seg_outro.mp3"
    temp_files.append(outro_path)
    try:
        asyncio.run(_generate_async(OUTRO_TEXT, voice, rate, pitch, outro_path))
        outro_dur_ms = _get_mp3_duration_ms(outro_path) if outro_path.exists() else 0
    except Exception:
        outro_dur_ms = 0

    # Concatenate all segments into one MP3. 그룹 자식들은 첫 자식의 path만 보유 (공유 합성),
    # 나머지는 None — concat 시 None은 건너뜀.
    output_path = target_dir / f"{timestamp}_{safe_title}.mp3"
    _concat_mp3(
        [s["path"] for s in scene_segments if s.get("path") is not None]
        + ([outro_path] if outro_dur_ms > 0 else []),
        output_path,
    )

    # Build timing map
    timings: list[dict] = []
    cursor_ms = 0
    for seg in scene_segments:
        timings.append({
            "scene_id": seg["scene_id"],
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + seg["duration_ms"],
        })
        cursor_ms += seg["duration_ms"]

    if outro_dur_ms > 0:
        timings.append({
            "scene_id": -1,
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + outro_dur_ms,
        })

    # Save timing
    timing_path = output_path.with_suffix(".timing.json")
    timing_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2))

    # Cleanup temp segments
    for f in temp_files:
        if f.exists():
            f.unlink()

    total_dur = timings[-1]["end_ms"] / 1000 if timings else 0
    logger.info("TTS 완료: %d씬 + 아웃트로, 총 %.1fs", len(scene_segments), total_dur)

    return output_path, timings


def _get_mp3_duration_ms(path: Path) -> int:
    """Get MP3 duration in milliseconds from MPEG frame header.

    Correctly handles both MPEG1 and MPEG2/2.5 bitrate tables.
    edge-tts outputs MPEG2 Layer3 at 24kHz/48kbps.
    """
    # Bitrate tables: [index] → kbps
    MPEG1_L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    MPEG2_L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]

    try:
        file_size = path.stat().st_size
        if file_size < 100:
            return 0

        with open(path, "rb") as f:
            data = f.read(8192)

        for i in range(len(data) - 4):
            if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
                header = struct.unpack(">I", data[i : i + 4])[0]
                version_bits = (header >> 19) & 0x3  # 11=MPEG1, 10=MPEG2, 00=MPEG2.5
                bitrate_idx = (header >> 12) & 0xF

                if 0 < bitrate_idx < 15:
                    if version_bits == 3:  # MPEG1
                        bitrate_kbps = MPEG1_L3[bitrate_idx]
                    else:  # MPEG2 or MPEG2.5
                        bitrate_kbps = MPEG2_L3[bitrate_idx]

                    if bitrate_kbps > 0:
                        return int((file_size * 8 * 1000) / (bitrate_kbps * 1000))

        return 0
    except Exception:
        return 0


def _concat_mp3(paths: list[Path], output: Path) -> None:
    """Concatenate MP3 files by raw byte concatenation."""
    with open(output, "wb") as out:
        for p in paths:
            if p.exists():
                out.write(p.read_bytes())


def _safe_filename(title: str) -> str:
    safe = "".join(c for c in title[:30] if c.isalnum() or c in " _-")
    return safe.strip().replace(" ", "_") or "untitled"


async def _generate_async(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
) -> None:
    """Async edge-tts generation."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(str(output_path))
