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
from src.illustrator.image_constants import (
    ANATOMY_GUARD,
    NO_TEXT_GUARD,
    PHOTO_STYLE_FOOTER,
    PHOTO_STYLE_PREFIX,
)
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
    # CRITICAL: the word "illustration" is FORBIDDEN here — it triggers
    # stylized output on Nano Banana / GPT Image. We want camera photography.
    # The NO_TEXT_GUARD, PHOTO_STYLE_PREFIX, PHOTO_STYLE_FOOTER, and
    # ANATOMY_GUARD constants are the shared source of truth
    # (see src/illustrator/image_constants.py) so e2e scripts and the
    # web UI produce identical quality.
    "realistic": (
        PHOTO_STYLE_PREFIX
        + "shallow depth of field, natural daylight with soft window light or golden hour, "
        "true-to-life skin texture with visible pores and micro-details, "
        "attractive Korean adults in their 20s-30s in modern Korean settings, "
        "cinematic color grading (Sony Venice / ARRI Alexa look), "
        "high dynamic range, sharp focus on subject, tasteful bokeh background, "
        + ANATOMY_GUARD
        + ", natural realistic hand positioning and proportions, "
        "hands and fingers in clear well-defined positions (not overlapping or merged)"
        + PHOTO_STYLE_FOOTER
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

# Style-specific instructions for the Claude scene-description generator.
# These replace the hard-coded "한국 웹툰 스타일" prompt when non-webtoon style.
STYLE_INSTRUCTIONS_FOR_CLAUDE = {
    "webtoon": {
        "style_name": "한국 웹툰 (Korean webtoon)",
        "requirements": (
            "- 한국 웹툰 스타일: 굵은 블랙 아웃라인 + 플랫 컬러링 (그라디언트 최소화)\n"
            "- 캐릭터: 매우 예쁜 한국 여성 / 매우 잘생긴 한국 남성 (8등신 비율)\n"
            "- 얼굴: 크고 아름다운 눈, 섬세한 이목구비, 감정이 풍부한 표정\n"
            "- 배경: 한국 일상 (현대 사무실, 아파트, 카페, 거리 등)\n"
            "- 텍스트 금지: 이미지 어디에도 글자/숫자/텍스트/말풍선 절대 없음"
        ),
    },
    "realistic": {
        "style_name": "사진 실사 (Photorealistic DSLR photography)",
        "requirements": (
            "- ⚠️ CRITICAL: 이것은 실제 사진입니다. 일러스트/그림/웹툰/애니메이션 절대 아님\n"
            "- DSLR 카메라로 찍은 사진 느낌: 85mm prime lens, f/1.8, shallow depth of field\n"
            "- 한국 드라마 시네마토그래피 스타일\n"
            "- 자연스러운 피부 텍스처 (모공까지 보이는 디테일)\n"
            "- 매력적인 한국인 20-30대 (사실적 외모)\n"
            "- 자연광 또는 골든아워, 부드러운 조명\n"
            "- 한국 현대 배경 (아파트, 오피스, 카페 등)\n"
            "- ⚠️ ANATOMY CRITICAL: 정확히 손 2개, 손가락 5개씩, 팔 2개, 다리 2개\n"
            "  - 절대 금지: 손이 3개, 왼손이 2개, 손가락 6개, 팔 3개, 신체 부위 중복, 기형 손\n"
            "  - 손의 위치를 명확히 묘사 (예: 'left hand covering mouth, right hand resting on table')\n"
            "  - 손이 보이지 않을 경우 'hands not visible' 또는 'hidden behind back'으로 명시\n"
            "- 절대 포함 금지 단어: 'illustration', 'drawing', 'cartoon', 'anime', 'webtoon', 'painting'\n"
            "- 반드시 포함 단어: 'photograph', 'photorealistic', 'DSLR', 'shot on', 'bokeh', 'anatomically correct'\n"
            "- ⚠️ 텍스트 금지 (CRITICAL): 이미지 어디에도 글자 절대 없음 — "
            "표지판, 이름표, 명찰, 간판, 메뉴판, 포스터, 문서, 클립보드, 책 표지, 제품 라벨, "
            "약병 라벨, 모니터 화면 텍스트, 폰/태블릿/TV 화면 텍스트, 화이트보드, 차트, "
            "한국어/영어/중국어/일본어 등 모든 언어의 읽을 수 있는 문자 일절 금지. "
            "프롬프트에 반드시 '배경의 벽/가구/물건에는 텍스트 없음, 단색/무지 표면으로 유지'를 명시"
        ),
    },
    "3d_pixar": {
        "style_name": "3D Pixar 애니메이션",
        "requirements": (
            "- Pixar/Disney 3D 렌더 스타일\n"
            "- 부드러운 피부 텍스처, 큰 표정있는 눈, 둥글고 친근한 얼굴\n"
            "- 컬러풀한 채도 높은 팔레트, 부드러운 조명\n"
            "- 현대 한국 배경\n"
            "- 텍스트 금지"
        ),
    },
    "anime": {
        "style_name": "일본 애니메이션",
        "requirements": (
            "- Japanese anime 스타일, 크고 표정 있는 눈\n"
            "- 활기찬 컬러, 섬세한 머리 쉐이딩\n"
            "- 깨끗한 라인아트\n"
            "- 한국 배경\n"
            "- 텍스트 금지"
        ),
    },
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

    # Style-specific instruction block (was hardcoded to webtoon before)
    style_info = STYLE_INSTRUCTIONS_FOR_CLAUDE.get(
        image_style, STYLE_INSTRUCTIONS_FOR_CLAUDE["webtoon"]
    )
    style_name = style_info["style_name"]
    style_requirements = style_info["requirements"]

    # Extra rule-6 content varies by style (photo vs illustration)
    if image_style == "realistic":
        rule_6 = (
            "6. 캐릭터 묘사는 실제 사진 찍는 것처럼: 'a Korean woman in her 20s with shoulder-length "
            "black hair, wearing a beige cardigan, looking shocked', 'captured in natural window light' 등\n"
            "   ⚠️ ANATOMY (CRITICAL): 손/팔/다리의 위치를 명확히 묘사. "
            "예: 'her left hand covering her mouth, her right hand resting at her side', "
            "'both hands holding a smartphone', 'hands clasped together in front of chest'. "
            "손이 보이지 않을 경우 'hands hidden behind back' 또는 'hands out of frame'. "
            "반드시 'anatomically correct, exactly two hands with five fingers each' 포함.\n"
            "   ⚠️ 절대 사용 금지 단어: illustration, drawing, cartoon, anime, manga, webtoon, painting, artwork\n"
            "   ✅ 반드시 사용: photograph, photo, photorealistic, shot on DSLR, 85mm lens, bokeh, cinematic, anatomically correct"
        )
    else:
        rule_6 = (
            "6. 캐릭터 외모(매력적인 얼굴), 옷차림, 표정, 포즈를 구체적으로 묘사하세요"
        )

    claude_prompt = f"""다음 블라인드 쇼츠 영상의 각 씬에 대해 {style_name} 스타일의 이미지 생성 프롬프트를 만들어주세요.

## 그림 스타일 요구사항
{style_requirements}

## 영상 정보
제목: {script.metadata.title}
감정: {emotion} ({emotion_style})

## 씬 목록
{scenes_text}

## 프롬프트 작성 규칙
1. 영어로 작성하세요
2. 각 씬 상황을 구체적 장면으로 묘사하세요
3. 한국 문화 맞는 배경 지정 (Korean apartment interior, Korean company office 등)
4. 반드시 포함: "absolutely NO text, NO letters, NO numbers, NO words, NO speech bubbles, NO captions, NO signs with writing, NO titles, NO labels anywhere in the image, the image must contain ZERO written characters of any language"
5. 인물 수와 관계 명확히 (a Korean woman in her 20s, a Korean man in his 30s 등)
{rule_6}
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
