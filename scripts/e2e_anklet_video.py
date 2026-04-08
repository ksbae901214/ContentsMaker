"""Image-to-video E2E pipeline: realistic images → Kling 2.5 clips → concat.

Takes the 6 Nano Banana Pro realistic scene images from the previous test run
and converts each into a 5-second video clip via Kling 2.5 (unlimited on
Premium+). Concatenates all clips into one full video using ffmpeg.

Run:
    python3 scripts/e2e_anklet_video.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path

# Make this script runnable standalone
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

from src.analyzer.script_models import ShortsScript
from src.video_gen.freepik_gen import FreepikBrowserGenerator


SCRIPT_FILE = Path("data/scripts/20260408_e2e_anklet.json")
# Pre-generated realistic images from the previous E2E test
SCENE_IMAGES = [
    (1, "data/images/20260408_140718_scene_01.png"),
    (2, "data/images/20260408_140800_scene_02.png"),
    (3, "data/images/20260408_140848_scene_03.png"),
    (4, "data/images/20260408_141005_scene_04.png"),
    (5, "data/images/20260408_141052_scene_05.png"),
    (6, "data/images/20260408_141240_scene_06.png"),
]
OUTPUT_DIR = Path("data/videos/anklet_scenes")
FINAL_OUTPUT = Path(
    "data/outputs/20260408_anklet_kling25_fullvideo.mp4"
)


async def generate_all_clips(script: ShortsScript) -> list[Path]:
    """Generate 5s video clip per scene using Kling 2.5 + the scene's image."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    gen = FreepikBrowserGenerator()

    clip_paths: list[Path] = []
    for scene_id, image_path in SCENE_IMAGES:
        scene = next((s for s in script.scenes if s.id == scene_id), None)
        if not scene:
            logger.warning("씬 %d 없음, 스킵", scene_id)
            continue

        # Motion prompt — describe subtle camera/subject motion based on the scene
        motion_prompt = _build_motion_prompt(scene.voice_text, scene.type)
        out_path = OUTPUT_DIR / f"scene_{scene_id:02d}.mp4"

        if out_path.exists() and out_path.stat().st_size > 100000:
            logger.info("✅ 씬 %d 캐시됨 (%.1f MB), 스킵", scene_id, out_path.stat().st_size / 1024 / 1024)
            clip_paths.append(out_path)
            continue

        logger.info(
            "씬 %d/%d: Kling 2.5 영상 생성 중... (source=%s)",
            scene_id, len(SCENE_IMAGES), Path(image_path).name,
        )
        logger.info("  motion prompt: %s", motion_prompt)

        try:
            result = await gen.generate_and_wait(
                prompt=motion_prompt,
                duration=5.0,
                resolution="720p",
                source_image=str(Path(image_path).resolve()),
                output_path=str(out_path),
                max_wait=300.0,
            )
            logger.info("  ✅ 씬 %d 완료: %s", scene_id, result.path)
            clip_paths.append(out_path)
        except Exception as exc:
            logger.error("  ❌ 씬 %d 실패: %s", scene_id, exc)

    return clip_paths


def _build_motion_prompt(voice_text: str, scene_type: str) -> str:
    """Heuristic motion prompt — subtle camera moves + subject action."""
    # Keep it simple: slow cinematic camera move + subject emotion
    base = (
        "Slow cinematic camera movement, subtle natural motion. "
        "The subject's facial expression and body language subtly animates. "
    )
    if scene_type == "title":
        return base + "Gentle push-in on subject. " + voice_text[:80]
    if scene_type == "comment":
        return base + "Soft parallax. " + voice_text[:80]
    return base + "Slow pan, subtle sway. " + voice_text[:80]


def concat_clips_with_ffmpeg(clips: list[Path], output: Path) -> Path:
    """Concatenate MP4 clips losslessly using ffmpeg concat demuxer.

    Requires all clips to share the same codec/resolution/fps. Kling 2.5
    outputs are all 720p h.264 at ~24fps, so concat demuxer works without
    re-encoding (very fast).

    Fallback: re-encode via concat protocol if demuxer fails.
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    # Build a temp file list for ffmpeg concat demuxer
    list_file = output.parent / f"{output.stem}_concat.txt"
    list_content = "\n".join(
        f"file '{clip.resolve()}'" for clip in clips
    )
    list_file.write_text(list_content, encoding="utf-8")
    logger.info("concat 리스트: %s", list_file)

    # Try lossless concat first (fastest)
    logger.info("ffmpeg concat 시도 (lossless)...")
    proc = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        logger.warning("lossless concat 실패 → 재인코딩 시도: %s", proc.stderr[-300:])
        proc = subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "fast",
                "-c:a", "aac",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 재인코딩도 실패: {proc.stderr[-500:]}")

    list_file.unlink(missing_ok=True)
    return output


def main() -> int:
    print("=" * 70)
    print("  Image → Video (Kling 2.5) E2E Pipeline")
    print("=" * 70)

    # 1. Load script
    print("\n📄 1/3: ShortsScript 로드...")
    script = ShortsScript.load(SCRIPT_FILE)
    print(f"   씬: {len(script.scenes)}개 | 감정: {script.metadata.emotion_type}")

    # Verify images exist
    missing = [p for _, p in SCENE_IMAGES if not Path(p).exists()]
    if missing:
        print(f"\n❌ 이미지 누락: {missing}")
        return 1

    # 2. Generate video clips
    print("\n🎥 2/3: Kling 2.5로 씬별 5초 영상 생성...")
    print("   (무제한 모델, 변동비 $0)")
    clips = asyncio.run(generate_all_clips(script))
    print(f"\n   생성된 클립: {len(clips)}개")
    for clip in clips:
        size_mb = clip.stat().st_size / 1024 / 1024
        print(f"     {clip.name}: {size_mb:.1f} MB")

    if not clips:
        print("\n❌ 클립 생성 실패")
        return 1

    # 3. Concat via ffmpeg
    print("\n🎬 3/3: ffmpeg로 클립 concat...")
    final = concat_clips_with_ffmpeg(clips, FINAL_OUTPUT)
    size_mb = final.stat().st_size / 1024 / 1024

    # Get duration via ffprobe
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(final),
        ],
        capture_output=True,
        text=True,
    )
    duration = float(probe.stdout.strip()) if probe.returncode == 0 else 0

    print()
    print("=" * 70)
    print("  ✅ 완료!")
    print("=" * 70)
    print(f"   풀 영상: {final}")
    print(f"   크기: {size_mb:.2f} MB")
    print(f"   길이: {duration:.1f}초")
    print(f"   씬 클립: {len(clips)}개 (data/videos/anklet_scenes/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
