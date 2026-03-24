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
    "Beautiful Korean webtoon romance style illustration, "
    "attractive good-looking characters with 8-head body proportions, "
    "pretty women and handsome men with detailed beautiful faces, "
    "clean line art with soft pastel coloring and gentle shading, "
    "expressive beautiful eyes and natural hair, "
    "modern Korean everyday backgrounds (office, cafe, home, street), "
    "vertical 9:16 composition, "
    "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, NO watermarks anywhere in the image, "
    "pure visual storytelling only, "
    "high quality digital art, trending on webtoon"
)

EMOTION_STYLE = {
    "funny": "bright cheerful pastel colors, characters with cute surprised or laughing expressions, lighthearted playful mood",
    "touching": "warm golden soft lighting, characters with gentle emotional expressions, heartwarming romantic atmosphere",
    "angry": "cool dramatic lighting, characters with sharp frustrated expressions, intense confrontational atmosphere",
    "relatable": "soft natural everyday lighting, characters with natural thoughtful expressions, cozy slice-of-life atmosphere",
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

    claude_prompt = f"""다음 블라인드 쇼츠 영상의 각 씬에 대해 "사회만화 Socialtoon" 유튜브 채널 스타일의 이미지 생성 프롬프트를 만들어주세요.

## 참고 스타일 (사회만화 Socialtoon)
- 한국 사회/직장 이슈를 다루는 심플한 웹툰 스타일
- 약간 리얼한 신체 비율 (치비가 아님, 머리:몸 = 1:4~5)
- 깔끔한 아웃라인 + 플랫 컬러링
- 과장된 표정으로 감정 전달 (핵심)
- 한국 일상 배경 (사무실, 카페, 집, 식당, 거리)
- 글씨/텍스트/숫자 절대 없음

## 영상 정보
제목: {script.metadata.title}
감정: {emotion} ({emotion_style})

## 씬 목록
{scenes_text}

## 프롬프트 작성 규칙
1. 영어로 작성하세요
2. 각 씬의 상황을 구체적인 장면으로 묘사하세요
3. 캐릭터의 외모, 옷차림, 표정, 포즈를 상세히 묘사하세요
4. 한국 문화에 맞는 배경을 구체적으로 지정하세요 (Korean apartment, Korean office, Korean wedding hall 등)
5. 반드시 포함: "absolutely no text, no letters, no numbers, no words, no speech bubbles anywhere in the image"
6. 인물 수와 관계를 명확히 (예: a young Korean woman and her boyfriend, Korean parents at a dinner table)
7. 표정 묘사가 가장 중요 (frustrated, embarrassed, angry, shocked, sad 등)

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
            prompt = (
                "a young Korean person standing in a dramatic pose, "
                "looking at the viewer with an expressive face, "
                "modern Korean city background, "
                "absolutely no text, no letters, no numbers, no words, no speech bubbles anywhere in the image"
            )
        elif scene.type == "comment":
            prompt = (
                "a person looking at their smartphone with a surprised or amused reaction, "
                "Korean cafe or room setting, "
                "absolutely no text, no letters, no numbers, no words, no speech bubbles anywhere in the image"
            )
        else:
            prompt = (
                f"scene showing: {scene.voice_text[:80]}, "
                "Korean everyday setting, expressive character faces, "
                "absolutely no text, no letters, no numbers, no words, no speech bubbles anywhere in the image"
            )

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
