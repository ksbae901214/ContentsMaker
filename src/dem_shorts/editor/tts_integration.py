"""T069: TTS 통합 — edge-tts 4 보이스 프리셋 매핑 (FR-022, FR-023).

기존 `src/tts/edge_tts_generator._generate_async`를 재사용.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# FR-022/FR-023: 4개 TTS 보이스 프리셋
# Azure/edge-tts 한국어 보이스 카탈로그에서 톤 스타일별로 매핑.
VOICE_PRESETS: dict[str, dict[str, str]] = {
    "male_strong": {
        "voice": "ko-KR-InJoonNeural",
        "rate": "+10%",
        "pitch": "-2Hz",
        "description": "남성, 힘있고 단호한 톤 (이재명 해설용)",
    },
    "male_stable": {
        "voice": "ko-KR-HyunsuNeural",
        "rate": "+5%",
        "pitch": "+0Hz",
        "description": "남성, 안정된 낭독 톤 (정청래 해설용)",
    },
    "female_calm": {
        "voice": "ko-KR-SunHiNeural",
        "rate": "+8%",
        "pitch": "+0Hz",
        "description": "여성, 차분한 진행 톤 (기본)",
    },
    "female_young": {
        "voice": "ko-KR-SunHiNeural",
        "rate": "+15%",
        "pitch": "+4Hz",
        "description": "여성, 젊고 활기찬 톤 (청년 이슈)",
    },
}

DEFAULT_VOICE_PRESET = "female_calm"


class TtsError(Exception):
    """Raised when TTS generation fails."""


@dataclass(frozen=True)
class TtsConfig:
    preset_id: str  # male_strong / male_stable / female_calm / female_young
    voice: str
    rate: str
    pitch: str


def get_voice_config(preset_id: str) -> TtsConfig:
    """Lookup preset → TtsConfig. Falls back to default if unknown."""
    preset = VOICE_PRESETS.get(preset_id, VOICE_PRESETS[DEFAULT_VOICE_PRESET])
    return TtsConfig(
        preset_id=preset_id if preset_id in VOICE_PRESETS else DEFAULT_VOICE_PRESET,
        voice=preset["voice"],
        rate=preset["rate"],
        pitch=preset["pitch"],
    )


def list_presets() -> list[str]:
    return list(VOICE_PRESETS.keys())


def synthesize(text: str, preset_id: str, output_path: Path) -> Path:
    """해설 문장을 MP3로 합성.

    기존 `src/tts/edge_tts_generator._generate_async`를 재사용.
    """
    if not text.strip():
        raise TtsError("empty text")

    cfg = get_voice_config(preset_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from src.tts.edge_tts_generator import _generate_async
    except ImportError as exc:
        raise TtsError(f"edge-tts 모듈 로드 실패: {exc}") from exc

    logger.info(
        "tts: preset=%s voice=%s rate=%s pitch=%s -> %s",
        cfg.preset_id, cfg.voice, cfg.rate, cfg.pitch, output_path,
    )
    try:
        asyncio.run(_generate_async(text, cfg.voice, cfg.rate, cfg.pitch, output_path))
    except Exception as exc:
        raise TtsError(f"edge-tts 합성 실패: {exc}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TtsError(f"TTS 출력 파일이 생성되지 않음: {output_path}")
    return output_path


def synthesize_blocks(
    blocks: list[dict],
    preset_id: str,
    output_dir: Path,
) -> list[Path]:
    """해설 블록 여러 개를 순차 합성 (blocks = [{start, end, text}, ...]).

    Returns: 각 블록별 MP3 파일 경로 리스트.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, b in enumerate(blocks):
        text = b.get("text", "").strip()
        if not text:
            continue
        out = output_dir / f"block_{i:03d}.mp3"
        synthesize(text, preset_id, out)
        paths.append(out)
    return paths
