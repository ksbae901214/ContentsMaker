"""AI-driven YouTube Shorts idea generation from lawmaker video titles.

Calls Claude CLI to analyze recent video titles and generate
clickbait-worthy shorts ideas with NATV search keywords.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from src.analyzer.claude_analyzer import AnalyzerError, _call_claude
from src.analyzer.prompt_template import build_idea_prompt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoIdea:
    title: str          # 쇼츠 제목 (클릭베이트)
    hook: str           # 첫 3초 훅 한 문장
    angle: str          # 영상 각도/관점
    natv_keywords: str  # NATV 검색 키워드


def generate_video_ideas(
    lawmaker_name: str,
    video_titles: list[str],
    max_ideas: int = 5,
) -> list[VideoIdea]:
    """Generate YouTube Shorts ideas from recent lawmaker video titles.

    Args:
        lawmaker_name: Name of the lawmaker (e.g., "나경원")
        video_titles: List of recent video titles from YouTube search
        max_ideas: Maximum number of ideas to generate

    Returns:
        List of VideoIdea dataclasses

    Raises:
        AnalyzerError: If video_titles is empty or Claude fails
    """
    if not video_titles:
        raise AnalyzerError("영상 제목이 없습니다. 먼저 YouTube 검색을 실행하세요.")

    prompt = build_idea_prompt(lawmaker_name, video_titles, max_ideas)
    logger.info("아이디어 생성 시작: %s (%d개 제목)", lawmaker_name, len(video_titles))

    raw_json = _call_claude(prompt)
    return _parse_ideas(raw_json, max_ideas)


def _parse_ideas(raw: str, max_ideas: int) -> list[VideoIdea]:
    """Parse Claude's JSON response into a VideoIdea list."""
    data = _extract_json(raw)

    if isinstance(data, dict) and "result" in data:
        inner = data["result"]
        if isinstance(inner, str):
            return _parse_ideas(inner, max_ideas)
        data = inner

    ideas_raw = data.get("ideas", [])
    ideas = []
    for item in ideas_raw[:max_ideas]:
        ideas.append(VideoIdea(
            title=item.get("title", ""),
            hook=item.get("hook", ""),
            angle=item.get("angle", ""),
            natv_keywords=item.get("natv_keywords", ""),
        ))
    return ideas


def _extract_json(raw: str) -> dict:
    """Extract JSON dict from raw Claude output."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if m:
        return json.loads(m.group(1))

    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        return json.loads(m.group(0))

    raise AnalyzerError(f"아이디어 응답을 파싱할 수 없습니다: {raw[:200]}")
