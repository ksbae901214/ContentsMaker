"""Build image generation prompts from scene data.

Converts each scene's text into a descriptive prompt
for manga/webtoon-style illustration generation.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from src.analyzer.script_models import ShortsScript, Scene
from src.config.settings import CLAUDE_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

STYLE_PREFIX = (
    "Korean webtoon illustration style, clean line art, "
    "soft pastel colors, expressive characters, "
    "vertical 9:16 composition, no text or speech bubbles, "
    "detailed background, high quality digital art"
)

EMOTION_STYLE = {
    "funny": "bright cheerful colors, comedic exaggerated expressions, lighthearted mood",
    "touching": "warm soft tones, emotional gentle expressions, heartwarming atmosphere",
    "angry": "intense dramatic lighting, frustrated expressions, tense atmosphere",
    "relatable": "everyday realistic setting, natural expressions, slice of life mood",
}


class PromptBuildError(Exception):
    """Raised when prompt generation fails."""


def build_image_prompts(script: ShortsScript) -> list[dict]:
    """Generate image prompts for each scene using Claude Code.

    Returns list of {scene_id, prompt, scene_type} dicts.
    """
    emotion = script.metadata.emotion_type
    emotion_style = EMOTION_STYLE.get(emotion, EMOTION_STYLE["relatable"])

    scenes_text = "\n".join(
        f"- 씬 {s.id} ({s.type}): {s.text}"
        for s in script.scenes
    )

    claude_prompt = f"""다음 블라인드 쇼츠 영상의 각 씬에 대해 만화/웹툰 스타일 이미지 생성 프롬프트를 만들어주세요.

## 영상 정보
제목: {script.metadata.title}
감정: {emotion} ({emotion_style})

## 씬 목록
{scenes_text}

## 규칙
1. 각 씬의 상황을 시각적으로 묘사하는 영어 프롬프트를 작성하세요
2. 한국 직장인 문화, 일상 상황을 구체적으로 묘사하세요
3. 인물의 표정, 행동, 배경을 상세히 포함하세요
4. 텍스트나 말풍선은 포함하지 마세요 (no text, no speech bubbles)
5. 세로 구도(9:16)에 맞게 구성하세요

## 출력 형식 (JSON 배열만 출력)
```json
[
  {{"scene_id": 1, "prompt": "영어 이미지 프롬프트"}},
  {{"scene_id": 2, "prompt": "영어 이미지 프롬프트"}}
]
```

JSON만 출력하세요."""

    logger.info("씬별 이미지 프롬프트 생성 중 (%d씬)...", len(script.scenes))

    try:
        result = subprocess.run(
            ["claude", "-p", claude_prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise PromptBuildError("Claude Code가 설치되지 않았습니다.")
    except subprocess.TimeoutExpired:
        raise PromptBuildError("Claude Code 응답 시간 초과")

    if result.returncode != 0:
        raise PromptBuildError(f"Claude Code 실패: {result.stderr[:200]}")

    prompts = _parse_prompts(result.stdout)

    # Prepend style prefix to each prompt
    for p in prompts:
        p["prompt"] = f"{STYLE_PREFIX}, {emotion_style}, {p['prompt']}"

    return prompts


def build_image_prompts_simple(script: ShortsScript) -> list[dict]:
    """Generate image prompts without Claude Code (fallback).

    Uses simple rule-based prompt generation.
    """
    emotion = script.metadata.emotion_type
    emotion_style = EMOTION_STYLE.get(emotion, EMOTION_STYLE["relatable"])
    prompts = []

    for scene in script.scenes:
        if scene.type == "title":
            prompt = f"dramatic title card scene, {scene.text} theme"
        elif scene.type == "comment":
            prompt = "person reading phone comments, reaction shot, social media"
        else:
            prompt = f"scene depicting: {scene.voice_text[:100]}"

        prompts.append({
            "scene_id": scene.id,
            "prompt": f"{STYLE_PREFIX}, {emotion_style}, {prompt}",
        })

    return prompts


def _parse_prompts(raw: str) -> list[dict]:
    """Parse Claude's response into prompt list."""
    # Direct JSON array
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "result" in data:
            inner = data["result"]
            if isinstance(inner, str):
                return _parse_prompts(inner)
            if isinstance(inner, list):
                return inner
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, KeyError):
        pass

    # JSON in code block
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Find array in text
    arr_match = re.search(r"\[[\s\S]*\]", raw)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    raise PromptBuildError(f"프롬프트 파싱 실패: {raw[:200]}")
