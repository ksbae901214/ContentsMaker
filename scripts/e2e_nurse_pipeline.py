"""End-to-end pipeline for the '내 환자가 죽었는데' Blind post.

11 scenes (each ≤5s, touching emotion).

Steps:
1. Generate 11 photorealistic Korean drama style images (Nano Banana Pro)
2. Generate 11 Kling 2.5 image-to-video clips (720p, Start image, Unlimited)
3. Generate TTS audio with per-scene timings
4. Render final shorts via Remotion (Kling clips + subs + BGM)

All Freepik calls go through cost guard (allow_paid=False) — 0 credits.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

from src.analyzer.script_models import ShortsScript
from src.illustrator.freepik_image_gen import FreepikImageGenerator
from src.illustrator.image_constants import (
    PHOTO_STYLE_FOOTER as PHOTO_FOOTER,
    PHOTO_STYLE_PREFIX as PHOTO_STYLE,
)
from src.tts.edge_tts_generator import generate_voice_with_timing
from src.video.renderer import render_video
from src.video_gen.freepik_gen import FreepikBrowserGenerator
from src.video_gen.motion_prompt_builder import build_motion_prompt


SCRIPT_FILE = Path("data/scripts/20260408_e2e_nurse.json")
# Use dedicated subfolder so cache lookup doesn't pull in stale files from
# other tests (e.g. site's manga-mode batch from earlier)
IMAGES_DIR = Path("data/images/nurse")
VIDEOS_DIR = Path("data/videos/nurse_scenes")
FINAL_DIR = Path("data/outputs")

# Per-scene image prompts (realistic Korean drama photography style).
# Each prompt enforces anatomy + photo (not illustration).
SCENE_IMAGE_PROMPTS = [
    {
        "scene_id": 1,
        "prompt": (
            PHOTO_STYLE +
            "Tight portrait of a Korean nurse in her 30s wearing a plain solid navy blue scrub uniform "
            "with NO patches, NO name tag, NO logos. Standing in a softly lit hospital corridor "
            "at golden hour, her face showing a thoughtful melancholy expression, "
            "warm window light from the side, blurred plain wall behind her with NO signs and NO doors visible, "
            "anatomically correct, exactly two hands with five fingers each, "
            "her hands clasped together at her chest, holding nothing, "
            "shallow depth of field, focus on her face."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 2,
        "prompt": (
            PHOTO_STYLE +
            "Close-up of a Korean female nurse in plain solid scrubs (no labels) gently holding the hand of "
            "an elderly Korean patient lying in a hospital bed. Focus on the joined hands with the patient's "
            "face slightly visible. Soft warm afternoon light from a window, plain blurred wall behind, "
            "compassionate atmosphere, "
            "anatomically correct, exactly two hands with five fingers each, "
            "both nurse's hands gently cupping the patient's hand. "
            "NO medical equipment with displays in frame, NO IV bags, NO monitors, plain bedding only."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 3,
        "prompt": (
            PHOTO_STYLE +
            "A middle-aged Korean man in his 50s wearing a sharp dark gray business suit, "
            "standing in profile against a plain blurred warm beige wall, "
            "looking serious with a slight frown. NO accessories, NO ties with patterns, plain solid suit. "
            "Soft side lighting, professional cinematic atmosphere, "
            "anatomically correct, exactly two hands with five fingers each, "
            "both hands at his sides, body facing the camera 3/4 view. "
            "NO background details, NO furniture, NO doors, NO signs — just a clean simple wall behind him."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 4,
        "prompt": (
            PHOTO_STYLE +
            "Wide cinematic shot of a luxurious VIP private hospital room. An elderly wealthy Korean man "
            "in his 70s lying alone in a hospital bed, his blanket pulled up to his chest, "
            "head turned slightly toward the window with a quiet sad expression on his face — "
            "a man who has everything but nobody by his side. "
            "Elegant warm decor — wood panel walls, a vase of flowers on a side table, "
            "soft golden window light bathing his face. Deeply lonely melancholy atmosphere. "
            "Anatomically correct, exactly two hands with five fingers each, "
            "his hands resting on top of the blanket. The patient is CLEARLY VISIBLE from the start, "
            "no obstruction, no occlusion, fully solid body — not transparent, not ghostly. "
            "NO other people in frame (he is alone). "
            "NO monitors, NO IV bags, NO medical equipment, NO signs, NO papers — "
            "just the patient, the bed, the side table, and warm soft light. "
            "Deep depth of field, cinematic color grading."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 5,
        "prompt": (
            PHOTO_STYLE +
            "Wide cinematic shot of a dim hospital VIP suite. In the foreground a frail elderly Korean man "
            "lying clearly visible in a hospital bed, eyes closed peacefully, his blanket pulled up to his chest. "
            "Behind him, sitting in a chair beside the bed, a young Korean man in a plain dark business suit "
            "(the secretary, mid-30s) hunched over scrolling on a smartphone with a bored disengaged expression. "
            "The secretary is NOT looking at the patient. Cold blue sterile lighting from the side, "
            "lonely contrast atmosphere — patient alone with a stranger. "
            "Both subjects are CLEARLY VISIBLE FROM THE START in the same frame, no obstruction, no occlusion. "
            "Anatomically correct, exactly two hands with five fingers each. "
            "The patient's hands rest on the blanket. The secretary holds the phone with both hands. "
            "Static composition, no dramatic angles, eye-level camera. "
            "NO medical equipment with text, NO IV bags, NO monitors with displays, NO signs, plain room."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 6,
        "prompt": (
            PHOTO_STYLE +
            "A Korean woman in her 30s sitting in a chair beside her elderly mother's hospital bed, "
            "facing her mother with deep love and worry on her face. The mother is partially visible "
            "lying in the bed. Golden hour warm sunlight through a plain window in the background, "
            "intimate warm atmosphere. Plain solid clothing on both, no patterns, no labels. "
            "Anatomically correct, exactly two hands with five fingers each, "
            "both daughter's hands gently holding her mother's hand on the bed sheets. "
            "Shallow depth of field, focus on the daughter. "
            "NO medical equipment in frame, NO IV bags, NO monitors, plain sheets only."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 7,
        "prompt": (
            PHOTO_STYLE +
            "Macro close-up of two Korean female hands gently patting an elderly Korean woman's wrinkled hand "
            "on a plain white hospital bed sheet. Warm sunlight catching on the skin texture, tender moment. "
            "Anatomically correct hands, two younger hands and one elderly hand all with five fingers each, "
            "all visible clearly in frame. Soft bokeh blurred plain background — just the sheets and warm light. "
            "NO medical equipment in frame, NO IV tubes, NO monitors, NO labels, just hands and sheets."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 8,
        "prompt": (
            PHOTO_STYLE +
            "A Korean woman in her 30s wrapping her arms around her elderly mother in a hospital bed, "
            "embracing her gently with care, both faces visible side by side with peaceful expressions, "
            "the daughter's cheek touching her mother's hair. Warm afternoon window light, "
            "profound tenderness and love. Plain solid clothing, no labels. "
            "Anatomically correct, exactly two hands with five fingers each, "
            "the daughter's both arms wrapped around her mother's shoulders. "
            "NO medical equipment, NO monitors, NO IV bags, plain bedding only."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 9,
        "prompt": (
            PHOTO_STYLE +
            "Close-up portrait of an elderly Korean woman lying peacefully in a hospital bed at dawn, "
            "her face serene and beautiful, eyes gently closed as if sleeping, soft morning blue-gold light "
            "from a plain window. Her gray hair neatly framing her face. Plain white sheets pulled up to her chin. "
            "Anatomically correct, peaceful tranquility, "
            "NO visible hands (covered by blanket), NO medical equipment, NO tubes, NO monitors, "
            "NO IV lines, NO labels, just her face and the soft morning light."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 10,
        "prompt": (
            PHOTO_STYLE +
            "A Korean daughter in her 30s sitting beside a hospital bed, holding her late mother's hand "
            "with both of her hands. Tears streaming down her face but a peaceful smile of acceptance, "
            "looking down at her mother's hand with reverence. Warm dawn light filling the room from a plain window. "
            "Plain solid clothing. Anatomically correct, exactly two hands with five fingers each, "
            "both daughter's hands cradling her mother's hand on plain white sheets. "
            "NO medical equipment, NO IV, NO monitors, NO papers, NO signs, NO furniture details, "
            "warm sacred atmosphere, focus on her face and the joined hands."
            + PHOTO_FOOTER
        ),
    },
    {
        "scene_id": 11,
        "prompt": (
            PHOTO_STYLE +
            "A Korean woman in her 30s standing silhouetted by a large plain window at golden hour, "
            "looking out with a contemplative peaceful expression, warm sunlight bathing her face. "
            "Plain solid sweater, no patterns no labels. Soft introspective mood. "
            "Anatomically correct, exactly two hands with five fingers each, "
            "her right hand resting gently on the window glass, her left hand at her side. "
            "NO buildings with signs visible through the window — just warm sky and soft sunlight. "
            "NO furniture in frame, NO art, hopeful peaceful atmosphere."
            + PHOTO_FOOTER
        ),
    },
]


def _find_cached_nurse_image(scene_id: int) -> str | None:
    """Look for a nurse-pipeline image for this scene_id in the dedicated
    nurse subfolder. This ensures we don't accidentally pick up stale files
    from other tests (e.g. site's manga batch).
    """
    if not IMAGES_DIR.exists():
        return None
    candidates = sorted(
        IMAGES_DIR.glob(f"*_scene_{scene_id:02d}.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return str(candidates[0])
    return None


async def step1_generate_images() -> dict[int, str]:
    """Generate 11 images via Freepik (cost guard ON), with on-disk cache.

    For each scene, if data/images/ already has a file matching the scene_id
    pattern dated today, reuse it. Otherwise generate fresh.
    """
    print("=" * 70)
    print("  Step 1/4: Nano Banana Pro로 11장 실사 이미지 생성 (cost guard ON)")
    print("=" * 70)

    # Resolve cache and figure out which scenes still need generation
    cached: dict[int, str] = {}
    missing_prompts: list[dict] = []
    for prompt_data in SCENE_IMAGE_PROMPTS:
        sid = prompt_data["scene_id"]
        cached_path = _find_cached_nurse_image(sid)
        if cached_path:
            print(f"   ✅ 씬 {sid:2d} 캐시됨 → {Path(cached_path).name}")
            cached[sid] = cached_path
        else:
            missing_prompts.append(prompt_data)

    if not missing_prompts:
        print("   모든 씬 캐시됨, 생성 스킵")
        return cached

    print(f"   생성 필요: {len(missing_prompts)} 씬")

    gen = FreepikImageGenerator()
    results = await gen.generate_scene_images(
        prompts=missing_prompts,
        output_dir=IMAGES_DIR,
    )
    for r in results:
        cached[r["scene_id"]] = r["image_path"]
    return cached


async def step2_generate_videos(
    script: ShortsScript, scene_images: dict[int, str]
) -> dict[int, Path]:
    """Generate 11 Kling 2.5 image-to-video clips (cost guard ON)."""
    print()
    print("=" * 70)
    print("  Step 2/4: Kling 2.5 + 720p + Start image로 11개 영상 생성")
    print("=" * 70)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    gen = FreepikBrowserGenerator()
    out: dict[int, Path] = {}

    for scene in script.scenes:
        scene_id = scene.id
        image_path = scene_images.get(scene_id)
        if not image_path or not Path(image_path).exists():
            logger.error("씬 %d: 이미지 없음", scene_id)
            continue

        out_path = VIDEOS_DIR / f"scene_{scene_id:02d}.mp4"
        if out_path.exists() and out_path.stat().st_size > 100000:
            logger.info("✅ 씬 %d 캐시됨 (스킵)", scene_id)
            out[scene_id] = out_path
            continue

        logger.info("씬 %d/%d: Kling 2.5 영상 생성 중", scene_id, len(script.scenes))
        try:
            result = await gen.generate_and_wait(
                prompt=build_motion_prompt(scene),
                duration=5.0,
                resolution="720p",
                source_image=str(Path(image_path).resolve()),
                output_path=str(out_path),
                max_wait=600.0,
            )
            logger.info("  ✅ 씬 %d 완료: %s", scene_id, result.path)
            out[scene_id] = out_path
        except Exception as exc:
            logger.error("  ❌ 씬 %d 실패: %s", scene_id, exc)

    return out


def step3_generate_tts(script: ShortsScript):
    """Generate edge-tts audio + per-scene timings."""
    print()
    print("=" * 70)
    print("  Step 3/4: edge-tts 음성 + 타이밍")
    print("=" * 70)
    audio_path, scene_timings = generate_voice_with_timing(script)
    print(f"   audio: {audio_path.name}")
    print(f"   timings: {len(scene_timings)} scenes")
    return audio_path, scene_timings


def step4_render(script, audio_path, scene_videos, scene_timings):
    print()
    print("=" * 70)
    print("  Step 4/4: Remotion 최종 렌더")
    print("=" * 70)
    return render_video(
        script=script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        use_bgm=True,
        scene_timings=scene_timings,
        output_dir=FINAL_DIR,
    )


def main() -> int:
    print("=" * 70)
    print("  Nurse 11-scene Pipeline (Premium+ unlimited)")
    print("=" * 70)

    print("\n📄 ShortsScript 로드...")
    script = ShortsScript.load(SCRIPT_FILE)
    print(f"   타이틀: {script.metadata.title!r}")
    print(f"   씬: {len(script.scenes)}개 | 감정: {script.metadata.emotion_type}")

    # Step 1: Images
    scene_images = asyncio.run(step1_generate_images())
    print(f"\n   ✅ 이미지 {len(scene_images)}장 생성")

    if len(scene_images) < 11:
        print(f"\n❌ 이미지 누락: {set(range(1, 12)) - set(scene_images.keys())}")
        return 1

    # Step 2: Videos
    new_clips = asyncio.run(step2_generate_videos(script, scene_images))
    print(f"\n   ✅ 영상 {len(new_clips)}개 생성")

    if len(new_clips) < 11:
        print(f"\n❌ 영상 누락: {set(range(1, 12)) - set(new_clips.keys())}")
        return 1

    # Step 3: TTS
    audio_path, scene_timings = step3_generate_tts(script)

    # Step 4: Render
    scene_videos = [
        {"scene_id": sid, "video_path": str(path)}
        for sid, path in sorted(new_clips.items())
    ]
    output_path = step4_render(script, audio_path, scene_videos, scene_timings)
    size_mb = output_path.stat().st_size / 1024 / 1024

    print()
    print("=" * 70)
    print("  ✅ 완료!")
    print("=" * 70)
    print(f"   영상: {output_path}")
    print(f"   크기: {size_mb:.2f} MB")
    print(f"   씬: {len(script.scenes)}개")
    print(f"   비용: $0 (Premium+ 무제한, cost guard 보장)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
