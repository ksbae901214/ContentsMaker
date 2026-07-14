"""AI 인플루언서 스타일 비교용 샘플 이미지 생성 (1회성 스크립트).

스타일 A: ayla.rae 스타일 — 매력 어필 + 피트니스 (글래머러스, SFW)
스타일 B: 라이프스타일 버추얼 인플루언서 — 일상/패션 중심 (Rozy 스타일)
"""
import asyncio
import logging
from pathlib import Path

from src.config.settings import PROJECT_ROOT
from src.illustrator.freepik_image_gen import FreepikImageGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

OUTPUT_DIR = PROJECT_ROOT / "data" / "images" / "influencer_samples"

PROMPTS = [
    {
        "scene_id": 1,
        "prompt": (
            "Photorealistic Instagram photo of a stunningly beautiful Korean "
            "female fitness influencer in her mid-20s, athletic hourglass "
            "figure, wearing a stylish coral sports bra and black high-waist "
            "leggings, standing in a bright modern gym, confident smile, "
            "golden hour window light, shot on 85mm f/1.8, shallow depth of "
            "field, influencer aesthetic, glamorous but tasteful, SFW"
        ),
    },
    {
        "scene_id": 2,
        "prompt": (
            "Photorealistic Instagram photo of the same beautiful Korean "
            "female fitness influencer, mid-20s, athletic figure, doing a "
            "dumbbell shoulder press, fitted white crop top and grey leggings, "
            "premium gym interior, dynamic pose, sweat glow, cinematic "
            "lighting, magazine quality, glamorous fitness model aesthetic, SFW"
        ),
    },
    {
        "scene_id": 3,
        "prompt": (
            "Photorealistic lifestyle Instagram photo of a friendly Korean "
            "female virtual influencer in her mid-20s, natural beauty, wearing "
            "casual athleisure (oversized hoodie and leggings), holding a "
            "green smoothie at a sunny cafe terrace after workout, relaxed "
            "candid vibe, soft daylight, warm tones, approachable everyday "
            "lifestyle aesthetic, SFW"
        ),
    },
    {
        "scene_id": 4,
        "prompt": (
            "Photorealistic lifestyle Instagram photo of the same friendly "
            "Korean female virtual influencer, mid-20s, stretching on a yoga "
            "mat in a cozy minimal home living room with plants, comfortable "
            "loungewear, morning sunlight through window, wholesome wellness "
            "routine aesthetic, candid documentary style, SFW"
        ),
    },
]


async def main() -> None:
    gen = FreepikImageGenerator()
    results = await gen.generate_scene_images(
        prompts=PROMPTS,
        output_dir=OUTPUT_DIR,
        aspect_ratio="9:16",
    )
    for r in results:
        print(r["image_path"])


if __name__ == "__main__":
    asyncio.run(main())
