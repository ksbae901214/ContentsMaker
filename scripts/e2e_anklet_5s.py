"""E2E pipeline for the 5-second-per-scene version of the anklet short.

- Script: data/scripts/20260408_e2e_anklet_5s.json (11 scenes, each ≤5s)
- Reuses existing v2 Kling clips for scenes 1, 2, 4, 6, 8, 10 (first halves).
- Generates new Kling clips for scenes 3, 5, 7, 9, 11 (continuation scenes)
  using the 5 new source images produced separately.
- Regenerates TTS audio from the new script (11 scene timings).
- Calls Remotion renderer with all 11 clips + audio + BGM + subtitles.

Run:
    python3 scripts/e2e_anklet_5s.py
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
from src.tts.edge_tts_generator import generate_voice_with_timing
from src.video.renderer import render_video
from src.video_gen.freepik_gen import FreepikBrowserGenerator


SCRIPT_FILE = Path("data/scripts/20260408_e2e_anklet_5s.json")
OUTPUT_DIR = Path("data/videos/anklet_scenes_5s")
FINAL_DIR = Path("data/outputs")

# Scene → asset mapping.
# REUSED clips from v2 (existing, no generation needed):
REUSED_CLIPS = {
    1: "data/videos/anklet_scenes_v2/scene_01.mp4",   # old 1 whole
    2: "data/videos/anklet_scenes_v2/scene_02.mp4",   # old 2 first half
    4: "data/videos/anklet_scenes_v2/scene_03.mp4",   # old 3 first half
    6: "data/videos/anklet_scenes_v2/scene_04.mp4",   # old 4 first half
    8: "data/videos/anklet_scenes_v2/scene_05.mp4",   # old 5 first half
    10: "data/videos/anklet_scenes_v2/scene_06.mp4",  # old 6 first half
}

# NEW clips to generate (scene → new source image):
NEW_CLIPS = {
    3: "data/images/20260408_162417_scene_03.png",
    5: "data/images/20260408_162532_scene_05.png",
    7: "data/images/20260408_162638_scene_07.png",
    9: "data/images/20260408_162808_scene_09.png",
    11: "data/images/20260408_162848_scene_11.png",
}


def build_motion_prompt(scene) -> str:
    base = (
        "Slow cinematic camera movement, subtle natural motion. "
        "The subject's facial expression and body language subtly animates. "
        "Preserve anatomical correctness — exactly two hands, no extra limbs, "
        "no duplicated body parts, hands remain in their original positions. "
        "Gentle push-in. "
    )
    return base + scene.voice_text[:80]


async def generate_new_clips(script: ShortsScript) -> dict[int, Path]:
    """Generate the 5 new Kling 2.5 clips for continuation scenes."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gen = FreepikBrowserGenerator()
    scene_by_id = {s.id: s for s in script.scenes}
    out: dict[int, Path] = {}

    for scene_id, source_img in NEW_CLIPS.items():
        scene = scene_by_id[scene_id]
        out_path = OUTPUT_DIR / f"scene_{scene_id:02d}.mp4"

        if out_path.exists() and out_path.stat().st_size > 100000:
            logger.info("✅ 씬 %d 캐시됨 (%.1f MB), 스킵",
                        scene_id, out_path.stat().st_size / 1024 / 1024)
            out[scene_id] = out_path
            continue

        logger.info(
            "씬 %d: Kling 2.5 영상 생성 (source=%s)",
            scene_id, Path(source_img).name,
        )
        try:
            result = await gen.generate_and_wait(
                prompt=build_motion_prompt(scene),
                duration=5.0,
                resolution="720p",
                source_image=str(Path(source_img).resolve()),
                output_path=str(out_path),
                max_wait=300.0,
            )
            logger.info("  ✅ 씬 %d 완료: %s", scene_id, result.path)
            out[scene_id] = out_path
        except Exception as exc:
            logger.error("  ❌ 씬 %d 실패: %s", scene_id, exc)

    return out


def assemble_scene_videos(new_clips: dict[int, Path]) -> list[dict]:
    """Merge reused v2 clips + new clips into the scene_videos list."""
    scene_videos = []
    for sid in sorted({**REUSED_CLIPS, **{k: str(v) for k, v in new_clips.items()}}.keys()):
        if sid in new_clips:
            path = str(new_clips[sid])
        elif sid in REUSED_CLIPS:
            path = REUSED_CLIPS[sid]
        else:
            continue
        scene_videos.append({"scene_id": sid, "video_path": path})
    return scene_videos


def main() -> int:
    print("=" * 70)
    print("  Anklet 5s-per-scene pipeline (11 scenes)")
    print("=" * 70)

    # 1. Load script
    print("\n📄 1/4: 11씬 스크립트 로드...")
    script = ShortsScript.load(SCRIPT_FILE)
    print(f"   타이틀: {script.metadata.title!r}")
    print(f"   씬: {len(script.scenes)}개")
    for s in script.scenes:
        print(f"     씬 {s.id:2d} ({s.duration:.1f}s, {s.type}): {s.voice_text[:45]}")

    # 2. Generate missing Kling clips
    print("\n🎥 2/4: 신규 Kling 2.5 클립 5개 생성...")
    new_clips = asyncio.run(generate_new_clips(script))
    if len(new_clips) < len(NEW_CLIPS):
        missing = set(NEW_CLIPS) - set(new_clips)
        print(f"   ❌ 누락: {missing}")
        return 1

    # 3. Regenerate TTS from new script
    print("\n🎙️ 3/4: 새 TTS 음성 생성 (11씬)...")
    audio_path, scene_timings = generate_voice_with_timing(script)
    print(f"   오디오: {audio_path.name}")
    print(f"   타이밍: {len(scene_timings)}개")
    for t in scene_timings:
        print(f"     씬 {t['scene_id']:2d}: {t['start_ms']/1000:.2f}s → {t['end_ms']/1000:.2f}s")

    # 4. Final render
    print("\n🎬 4/4: Remotion 렌더링 (Kling x11 + TTS + 자막 + BGM)...")
    scene_videos = assemble_scene_videos(new_clips)
    assert len(scene_videos) == 11, f"Expected 11 scene videos, got {len(scene_videos)}"

    output_path = render_video(
        script=script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        use_bgm=True,
        scene_timings=scene_timings,
        output_dir=FINAL_DIR,
    )
    size_mb = output_path.stat().st_size / 1024 / 1024

    print()
    print("=" * 70)
    print("  ✅ 완료!")
    print("=" * 70)
    print(f"   최종 영상: {output_path}")
    print(f"   크기: {size_mb:.2f} MB")
    print(f"   씬: 11개 (각 ≤5s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
