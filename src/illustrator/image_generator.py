"""GPT Image Mini API — generates manga-style illustrations.

Constitution Principle I: $0.005/image, minimal cost.
Constitution Principle III: Images support text-first video as backgrounds.
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import datetime
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.config.settings import PROJECT_ROOT
from src.illustrator.prompt_builder import (
    PromptBuildError,
    build_image_prompts,
    build_image_prompts_simple,
)
from src.illustrator.reference_manager import (
    is_available as refs_available,
    select_references,
)

logger = logging.getLogger(__name__)

DATA_IMAGES_DIR = PROJECT_ROOT / "data" / "images"

# GPT Image model config
IMAGE_MODEL = "gpt-image-1"
IMAGE_SIZE = "1024x1536"  # Vertical 2:3 (closest to 9:16)
IMAGE_QUALITY = "low"  # $0.005/image


class ImageGenerateError(Exception):
    """Raised when image generation fails."""


def generate_scene_images(
    script: ShortsScript,
    output_dir: Path | None = None,
    use_simple_prompts: bool = False,
    use_references: bool = True,
) -> list[dict]:
    """Generate manga-style images for each scene.

    When reference images are available and use_references=True,
    uses images.edit() API to maintain consistent art style and characters.
    Falls back to images.generate() when no references exist.

    Returns list of {scene_id, image_path, prompt} dicts.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImageGenerateError(
            "openai 패키지가 필요합니다: pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ImageGenerateError(
            "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "export OPENAI_API_KEY='sk-...' 로 설정해주세요."
        )

    # Build prompts
    try:
        if use_simple_prompts:
            prompts = build_image_prompts_simple(script)
        else:
            prompts = build_image_prompts(script)
    except PromptBuildError as e:
        logger.warning("Claude 프롬프트 생성 실패, 단순 모드로 전환: %s", e)
        prompts = build_image_prompts_simple(script)

    # Check reference availability
    has_refs = use_references and refs_available()
    if has_refs:
        logger.info("레퍼런스 이미지 모드: images.edit() API 사용")
    else:
        logger.info("기본 모드: images.generate() API 사용")

    target_dir = output_dir or DATA_IMAGES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client = OpenAI(api_key=api_key)
    results = []

    # Collect scene texts for reference matching
    scene_texts = {s.id: s.text for s in script.scenes}

    for i, prompt_data in enumerate(prompts):
        scene_id = prompt_data["scene_id"]
        prompt = prompt_data["prompt"]

        logger.info(
            "이미지 생성 %d/%d (씬 %d): %s...",
            i + 1, len(prompts), scene_id, prompt[:60],
        )

        try:
            if has_refs:
                response = _generate_with_references(
                    client, prompt, scene_texts.get(scene_id, ""),
                )
            else:
                response = client.images.generate(
                    model=IMAGE_MODEL,
                    prompt=prompt,
                    n=1,
                    size=IMAGE_SIZE,
                    quality=IMAGE_QUALITY,
                )

            # Save image
            image_data = response.data[0]
            filename = f"{timestamp}_scene_{scene_id:02d}.png"
            image_path = target_dir / filename

            if hasattr(image_data, "b64_json") and image_data.b64_json:
                img_bytes = base64.b64decode(image_data.b64_json)
                image_path.write_bytes(img_bytes)
            elif hasattr(image_data, "url") and image_data.url:
                import urllib.request
                urllib.request.urlretrieve(image_data.url, str(image_path))
            else:
                logger.warning("씬 %d: 이미지 데이터 없음, 스킵", scene_id)
                continue

            results.append({
                "scene_id": scene_id,
                "image_path": str(image_path),
                "prompt": prompt,
            })
            logger.info("  저장: %s (%.1f KB)", image_path.name, image_path.stat().st_size / 1024)

        except Exception as e:
            logger.warning("씬 %d 이미지 생성 실패: %s (스킵)", scene_id, e)
            continue

    if not results:
        raise ImageGenerateError("모든 씬의 이미지 생성에 실패했습니다")

    cost = len(results) * 0.005
    logger.info("이미지 생성 완료: %d/%d장 ($%.3f)", len(results), len(prompts), cost)

    return results


def _generate_with_references(client, prompt: str, scene_text: str):
    """Generate image using images.edit() with reference images.

    Selects appropriate reference images based on scene context
    and passes them alongside the prompt for style consistency.
    """
    ref_set = select_references(scene_text)

    if not ref_set.has_references:
        return client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            n=1,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
        )

    ref_files = []
    try:
        for ref_path in ref_set.all_paths:
            ref_files.append(open(ref_path, "rb"))

        return client.images.edit(
            model=IMAGE_MODEL,
            image=ref_files if len(ref_files) > 1 else ref_files[0],
            prompt=prompt,
            n=1,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
        )
    finally:
        for f in ref_files:
            f.close()
