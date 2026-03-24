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
) -> list[dict]:
    """Generate manga-style images for each scene.

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

    target_dir = output_dir or DATA_IMAGES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client = OpenAI(api_key=api_key)
    results = []

    for i, prompt_data in enumerate(prompts):
        scene_id = prompt_data["scene_id"]
        prompt = prompt_data["prompt"]

        logger.info(
            "이미지 생성 %d/%d (씬 %d): %s...",
            i + 1, len(prompts), scene_id, prompt[:60],
        )

        try:
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
