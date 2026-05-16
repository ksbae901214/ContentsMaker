"""T064: Claude CLI로 해설 자막 후보 3개 생성 (FR-020, R-09).

기존 `src/analyzer/claude_analyzer._call_claude`를 재사용하여 비용 0원 유지 (원칙 I).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from src.dem_shorts.editor.commentary_prompt import build_commentary_prompt

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 15  # FR-024, 1줄당 15자


class CommentaryGenError(Exception):
    """Raised when commentary generation fails."""


@dataclass(frozen=True)
class CommentaryContext:
    """Commentary 생성 컨텍스트."""

    politician_name: str
    stt_text: str
    tone_guide: str
    tone_hint: str
    session_type: str
    is_election_period: bool = False


def _call_claude(prompt: str) -> str:
    """기존 analyzer.claude_analyzer의 Claude CLI 호출 재사용."""
    from src.analyzer.claude_analyzer import AnalyzerError
    from src.analyzer.claude_analyzer import _call_claude as _claude_cli

    try:
        return _claude_cli(prompt)
    except AnalyzerError as exc:
        raise CommentaryGenError(f"Claude CLI 실패: {exc}") from exc


def parse_candidates(raw: str) -> list[dict]:
    """Claude 응답에서 candidates 리스트 추출.

    Accepts:
    - `{"candidates": [...]}` top-level
    - Top-level list `[...]`
    - Markdown code block wrapping either

    Raises:
        CommentaryGenError: 파싱 실패 or 빈 리스트.
    """
    data = None

    # Try direct JSON parse
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try markdown code block
    if data is None:
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

    # Try raw JSON object or array from text
    if data is None:
        for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
            m = re.search(pattern, raw)
            if m:
                try:
                    data = json.loads(m.group(0))
                    break
                except json.JSONDecodeError:
                    continue

    if data is None:
        raise CommentaryGenError(f"Claude 응답을 JSON으로 파싱할 수 없습니다: {raw[:200]}")

    # Normalize structure
    if isinstance(data, dict) and "candidates" in data:
        candidates = data["candidates"]
    elif isinstance(data, list):
        candidates = data
    else:
        raise CommentaryGenError(f"예상한 'candidates' 키가 없음: {raw[:200]}")

    if not isinstance(candidates, list) or not candidates:
        raise CommentaryGenError("빈 candidates 리스트")

    normalized: list[dict] = []
    for c in candidates:
        if not isinstance(c, dict) or "text" not in c:
            continue
        normalized.append({
            "text": str(c["text"]).strip(),
            "confidence": float(c.get("confidence", 0.5)),
        })
    if not normalized:
        raise CommentaryGenError("파싱 후 유효한 candidate 0개")
    return normalized


def filter_by_max_chars(candidates: list[dict], max_chars: int = DEFAULT_MAX_CHARS) -> list[dict]:
    """15자(기본) 초과 후보 제외."""
    return [c for c in candidates if len(c["text"]) <= max_chars]


def generate_commentary_candidates(
    ctx: CommentaryContext,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[dict]:
    """FR-020: Claude CLI로 해설 후보 3개 생성 → 15자 필터.

    Returns: [{"text": "...", "confidence": 0.8}, ...]
    """
    prompt = build_commentary_prompt(
        politician_name=ctx.politician_name,
        stt_text=ctx.stt_text,
        tone_guide=ctx.tone_guide,
        tone_hint=ctx.tone_hint,
        session_type=ctx.session_type,
        is_election_period=ctx.is_election_period,
    )

    logger.info("commentary_gen: calling Claude CLI (politician=%s)", ctx.politician_name)
    try:
        raw = _call_claude(prompt)
    except CommentaryGenError:
        raise
    except Exception as exc:  # broad — wrap to our error type
        raise CommentaryGenError(f"Claude 호출 실패: {exc}") from exc

    candidates = parse_candidates(raw)
    filtered = filter_by_max_chars(candidates, max_chars=max_chars)
    logger.info(
        "commentary_gen: %d candidates parsed, %d remaining after %d-char filter",
        len(candidates), len(filtered), max_chars,
    )
    if not filtered:
        # 모두 길이 초과 — 원본 후보를 잘라서 돌려주기보다는 에러로 명시
        raise CommentaryGenError(
            f"모든 후보가 {max_chars}자를 초과. 원본 후보: "
            + "; ".join(c["text"][:30] for c in candidates)
        )
    return filtered
