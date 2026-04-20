"""Celebrity-introduction analyzer (Phase 9-3).

Converts a CelebrityInfo (from Namuwiki) into a ShortsScript by calling
Claude via `claude -p`. Reuses the shared infrastructure in claude_analyzer:
_call_claude, _parse_response, _apply_voice_config, _ensure_line_breaks.

After parsing, we enforce `source_type="celebrity"` and force
`metadata.source_url = info.source_url` (the Namuwiki page) regardless of
what the model returned — attribution must not be lost.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from src.analyzer.celebrity_prompt import build_celebrity_prompt
from src.analyzer.claude_analyzer import (
    _apply_voice_config,
    _call_claude,
    _ensure_line_breaks,
    _parse_response,
)
from src.analyzer.script_models import Metadata, ShortsScript
from src.config.settings import DATA_SCRIPTS_DIR
from src.scraper.celebrity_models import CelebrityInfo

logger = logging.getLogger(__name__)


class CelebrityAnalyzerError(Exception):
    """Raised when celebrity analysis fails."""


def analyze_celebrity(
    info: CelebrityInfo,
    output_dir: Path | None = None,
) -> tuple[ShortsScript, Path]:
    """Analyze a CelebrityInfo and generate a ShortsScript.

    Returns (ShortsScript, file_path).
    """
    prompt = build_celebrity_prompt(info)

    logger.info("Claude Code 유명인 분석 시작: %s", info.name)
    raw_json = _call_claude(prompt)
    script = _parse_response(raw_json)

    script = _force_celebrity_metadata(script, info)
    script = _apply_voice_config(script)
    script = _ensure_line_breaks(script)

    target_dir = output_dir or DATA_SCRIPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in info.name[:30] if c.isalnum() or c in " _-")
    safe_name = safe_name.strip().replace(" ", "_") or "celebrity"
    filename = f"{timestamp}_celebrity_{safe_name}.json"
    file_path = target_dir / filename

    script.save(file_path)
    logger.info("유명인 스크립트 저장: %s", file_path)

    return script, file_path


def _force_celebrity_metadata(
    script: ShortsScript, info: CelebrityInfo
) -> ShortsScript:
    """Overwrite source_type/source_url so attribution is never lost."""
    needs_update = (
        script.metadata.source_type != "celebrity"
        or script.metadata.source_url != info.source_url
    )
    if not needs_update:
        return script

    new_metadata = Metadata(
        title=script.metadata.title,
        emotion_type=script.metadata.emotion_type,
        duration=script.metadata.duration,
        source_url=info.source_url,
        source_type="celebrity",
    )
    return ShortsScript(
        metadata=new_metadata,
        scenes=script.scenes,
        audio=script.audio,
        background=script.background,
    )
