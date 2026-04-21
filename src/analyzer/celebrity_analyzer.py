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
    script = _fill_missing_image_query(script, info.name)

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


def _fill_missing_image_query(script: ShortsScript, name: str) -> ShortsScript:
    """Claude가 image_query를 생략한 씬에 폴백 쿼리 주입 (2026-04-21).

    우선순위:
      1. 씬 이미 image_query가 있으면 그대로 유지
      2. highlight_words 첫 번째를 확장 (예: "서울대" → "서울대학교")
      3. voice_text에서 핵심 명사 추출 (간단 휴리스틱)
      4. 그래도 없으면 인물명으로 폴백

    씬마다 다른 검색어가 돌아가도록 씬별 고유성을 최대한 보장한다.
    """
    from dataclasses import replace

    new_scenes = []
    for scene in script.scenes:
        if scene.image_query:
            new_scenes.append(scene)
            continue
        derived = _derive_image_query(scene.voice_text, scene.highlight_words, name)
        new_scenes.append(replace(scene, image_query=derived))

    return ShortsScript(
        metadata=script.metadata,
        scenes=tuple(new_scenes),
        audio=script.audio,
        background=script.background,
    )


# 자주 등장하는 약칭 → 검색어로 확장되는 매핑 (네이버 이미지 검색에 유리한 키워드).
_QUERY_EXPANSIONS: dict[str, str] = {
    "서울대": "서울대학교 정문",
    "연세대": "연세대학교 정문",
    "고려대": "고려대학교 정문",
    "하버드": "하버드 대학교",
    "국회": "국회의사당",
    "청와대": "청와대",
    "용산": "용산 대통령실",
    "판사": "법정 판사봉",
    "법조인": "법정 판사봉",
    "검사": "검찰청",
    "변호사": "법정",
    "국회의원": "국회 본회의장",
    "당대표": "정당 당대표",
    "대통령": "청와대",
    "장관": "정부종합청사",
    "의원": "국회 본회의장",
    "인사청문회": "인사청문회",
    "행정고시": "고시 시험",
    "사법시험": "고시 시험",
}


def _derive_image_query(
    voice_text: str, highlight_words: tuple[str, ...], name: str
) -> str:
    """highlight_words → 확장 매핑 → 원 단어 → 인물명 순으로 폴백."""
    for word in highlight_words:
        key = word.strip()
        if not key:
            continue
        if key in _QUERY_EXPANSIONS:
            return _QUERY_EXPANSIONS[key]
        # 키 부분 일치(예: "서울대를" 같은 조사 포함)
        for k, v in _QUERY_EXPANSIONS.items():
            if k in key:
                return v
        # 매핑 없으면 원 단어 그대로
        return key
    # highlight_words도 비어 있으면 voice_text에서 첫 2글자+ 명사 추출
    for k, v in _QUERY_EXPANSIONS.items():
        if k in voice_text:
            return v
    return name
