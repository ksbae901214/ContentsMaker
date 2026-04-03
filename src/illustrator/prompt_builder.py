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
from src.illustrator.reference_manager import is_available as refs_available

logger = logging.getLogger(__name__)

STYLE_PREFIX = (
    "Korean webtoon style illustration, "
    "simple clean flat coloring with bold black outlines, "
    "realistic body proportions (not chibi), natural Korean adult characters, "
    "very attractive pretty Korean women and very handsome Korean men, "
    "detailed expressive faces with large beautiful eyes, "
    "slightly simplified but realistic facial features, "
    "flat color fills with minimal shading (socialtoon style), "
    "Korean everyday settings (modern office, apartment, cafe, street), "
    "vertical 9:16 composition suitable for YouTube Shorts, "
    "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, NO watermarks, NO subtitles, NO UI elements, NO titles, NO labels, NO signs with writing anywhere in the image, "
    "the image must contain ZERO written characters of any language, "
    "pure illustrated scene only, "
    "high quality Korean webtoon digital art"
)

# When reference images are provided, this REPLACES STYLE_PREFIX entirely.
# Describes the EXACT visual characteristics of the reference images
# so GPT Image replicates the style even when the scene is emotional/dark.
REFERENCE_STYLE_PREFIX = (
    "CRITICAL — You MUST draw in the EXACT same art style as the reference images provided. "
    "The reference style has these MANDATORY visual characteristics that you must replicate exactly: "
    # --- EYES (highest priority) ---
    "EYES: large round anime-style eyes, black pupils with light amber/golden-brown iris, "
    "two small white highlight reflection dots in each eye (standard anime eye highlights), "
    "thin clean upper eyelashes, NO realistic eye rendering, NO small/narrow eyes, "
    "eyes must be big relative to the face (anime proportions). "
    # --- EXPRESSIONS (only use reference expressions) ---
    "EXPRESSIONS — ONLY use these 3 expression types from the reference sheets: "
    "(1) SURPRISED: wide open O-shaped mouth, raised eyebrows, small sweat drop, "
    "(2) ANGRY: V-shaped furrowed eyebrows, wide open shouting mouth, red anger mark on forehead, "
    "(3) SAD: downturned eyebrows, small closed mouth, tear drops on cheeks. "
    "Do NOT invent other expression styles. Pick the closest match from these 3. "
    # --- FACE & BODY ---
    "cute pretty female faces and handsome boyish male faces (young Korean office workers in 20s-30s), "
    "warm healthy skin tones (NOT pale or grey), soft brown hair with warm highlights, "
    # --- STYLE ---
    "BRIGHT warm natural lighting with soft warm tones, "
    "clean soft anime-style shading with gentle gradients (NOT heavy shadows), "
    "clean thin line art (NOT thick dark outlines), "
    "bright cheerful color palette even for serious scenes, "
    "modern Korean office/apartment/cafe setting with natural daylight, "
    "characters wearing white dress shirts and business casual, "
    "soft pastel-toned backgrounds with warm lighting. "
    # --- FORBIDDEN ---
    "FORBIDDEN — NEVER use: dark moody atmosphere, heavy shadows, noir aesthetic, "
    "dark color palette, dramatic red/black skies, thriller/horror style, "
    "harsh lighting, dark skin tones, heavy muscular builds, intimidating expressions, "
    "realistic eyes, small narrow eyes, Western cartoon eyes. "
    "Even if the scene describes anger or sadness, keep the art style BRIGHT and SOFT like the references. "
    # --- COMPOSITION ---
    "vertical 9:16 composition, "
    "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, "
    "NO signs with writing, NO titles, NO labels anywhere in the image, "
    "the image must contain ZERO written characters of any language"
)

# Legacy suffix kept for backward compatibility
REFERENCE_STYLE_SUFFIX = REFERENCE_STYLE_PREFIX

IMAGE_STYLE_PRESETS = {
    "webtoon": STYLE_PREFIX,
    "3d_pixar": (
        "3D Pixar-style rendered character, soft diffused lighting, cute proportions, "
        "highly detailed 3D render, Pixar/Disney animation quality, "
        "smooth skin textures, expressive cartoon eyes with thick eyelashes, "
        "round friendly faces, colorful saturated palette, "
        "vertical 9:16 composition suitable for YouTube Shorts, "
        "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, "
        "NO watermarks, NO subtitles, NO UI elements, NO titles, NO labels, NO signs with writing, "
        "the image must contain ZERO written characters of any language, "
        "high quality 3D animated render"
    ),
    "realistic": (
        "Photorealistic digital illustration, natural soft lighting, "
        "detailed skin texture, cinematic composition, "
        "Korean drama style photography aesthetic, "
        "attractive Korean adults in modern settings, "
        "warm natural color grading, shallow depth of field, "
        "vertical 9:16 composition suitable for YouTube Shorts, "
        "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, "
        "NO watermarks, NO subtitles, NO UI elements, NO titles, NO labels, NO signs with writing, "
        "the image must contain ZERO written characters of any language, "
        "high quality photorealistic digital art"
    ),
    "anime": (
        "Japanese anime style illustration, large expressive eyes, "
        "vibrant colors, detailed hair shading, "
        "anime-style character design with clean line art, "
        "bright color palette, dynamic poses, "
        "modern Japanese animation quality, "
        "vertical 9:16 composition suitable for YouTube Shorts, "
        "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, "
        "NO watermarks, NO subtitles, NO UI elements, NO titles, NO labels, NO signs with writing, "
        "the image must contain ZERO written characters of any language, "
        "high quality anime digital art"
    ),
}

# Emotion modifiers — kept SOFT to not override the bright reference style
EMOTION_STYLE = {
    "funny": "characters with cute surprised or laughing expressions, lighthearted playful mood, bright warm colors",
    "touching": "characters with gentle emotional expressions, soft warm golden tones, heartwarming atmosphere",
    "angry": "characters with frustrated pouting expressions, furrowed brows, bright warm office setting, keep colors warm and bright",
    "relatable": "characters with thoughtful or tired expressions, cozy everyday setting, soft natural warm lighting",
}


class PromptBuildError(Exception):
    """Raised when prompt generation fails."""


def build_image_prompts(script: ShortsScript, image_style: str = "webtoon") -> list[dict]:
    """Generate image prompts for each scene using Claude Code.

    Returns list of {scene_id, prompt, scene_type} dicts.
    """
    emotion = script.metadata.emotion_type
    emotion_style = EMOTION_STYLE.get(emotion, EMOTION_STYLE["relatable"])

    scenes_text = "\n".join(
        f"- 씬 {s.id} ({s.type}): {s.text}"
        for s in script.scenes
    )

    claude_prompt = f"""다음 블라인드 쇼츠 영상의 각 씬에 대해 한국 웹툰 스타일의 이미지 생성 프롬프트를 만들어주세요.

## 그림 스타일 요구사항
- 한국 웹툰 스타일: 굵은 블랙 아웃라인 + 플랫 컬러링 (그라디언트 최소화)
- 캐릭터: 매우 예쁜 한국 여성 / 매우 잘생긴 한국 남성 (8등신 비율)
- 얼굴: 크고 아름다운 눈, 섬세한 이목구비, 감정이 풍부한 표정
- 배경: 한국 일상 (현대 사무실, 아파트, 카페, 거리 등)
- 텍스트 금지: 이미지 어디에도 글자/숫자/텍스트/말풍선 절대 없음

## 영상 정보
제목: {script.metadata.title}
감정: {emotion} ({emotion_style})

## 씬 목록
{scenes_text}

## 프롬프트 작성 규칙
1. 영어로 작성하세요
2. 각 씬 상황을 구체적 장면으로 묘사하세요
3. 캐릭터 외모(매력적인 얼굴), 옷차림, 표정, 포즈를 구체적으로 묘사하세요
4. 한국 문화 맞는 배경 지정 (Korean apartment interior, Korean company office 등)
5. 반드시 포함: "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, NO signs with writing, NO titles, NO labels anywhere in the image, the image must contain ZERO written characters of any language"
6. 인물 수와 관계 명확히 (a beautiful Korean woman in her 20s, a handsome Korean man in his 30s 등)
7. 표정이 핵심 (deeply frustrated, embarrassed, shocked, tearful, overjoyed 등)
8. 감정에 맞는 조명/분위기도 포함 (warm lighting, dramatic shadows 등)

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

    # Build final prompts: reference style only for webtoon
    style_prefix = IMAGE_STYLE_PRESETS.get(image_style, IMAGE_STYLE_PRESETS["webtoon"])
    use_refs = refs_available() and image_style == "webtoon"
    for p in prompts:
        scene_desc = f"{emotion_style}, {p['prompt']}"
        if use_refs:
            base = f"{REFERENCE_STYLE_PREFIX}, {scene_desc}"
        else:
            base = f"{style_prefix}, {scene_desc}"
        p["prompt"] = base

    return prompts


def build_image_prompts_simple(script: ShortsScript, image_style: str = "webtoon") -> list[dict]:
    """Generate image prompts without Claude Code (fallback).

    Uses simple rule-based prompt generation.
    """
    emotion = script.metadata.emotion_type
    emotion_style = EMOTION_STYLE.get(emotion, EMOTION_STYLE["relatable"])
    style_prefix = IMAGE_STYLE_PRESETS.get(image_style, IMAGE_STYLE_PRESETS["webtoon"])
    use_refs = refs_available() and image_style == "webtoon"
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

        if use_refs:
            base = f"{REFERENCE_STYLE_PREFIX}, {emotion_style}, {prompt}"
        else:
            base = f"{style_prefix}, {emotion_style}, {prompt}"
        prompts.append({
            "scene_id": scene.id,
            "prompt": base,
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
