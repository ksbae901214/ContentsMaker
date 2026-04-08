"""End-to-end pipeline test: Blind post → Freepik images → TTS → Remotion video.

Uses the new FreepikImageGenerator (unlimited on Premium+) instead of GPT Image API.
Applies custom title override after analysis.

Run:
    python3 scripts/e2e_anklet.py
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import replace
from pathlib import Path

# Allow running as a standalone script: add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

from src.analyzer.script_models import ShortsScript
from src.illustrator.image_generator import generate_scene_images
from src.tts.edge_tts_generator import generate_voice_with_timing
from src.video.renderer import render_video


# Pre-built script (skipping Claude analyzer — we have the scenes ready).
SCRIPT_FILE = Path("data/scripts/20260408_e2e_anklet.json")


def main() -> int:
    # ─── 1 & 2. Load pre-built ShortsScript ───
    print("📄 1/3: ShortsScript 로드...")
    script = ShortsScript.load(SCRIPT_FILE)
    print(f"   타이틀: {script.metadata.title!r}")
    print(f"   감정: {script.metadata.emotion_type}")
    print(f"   씬: {len(script.scenes)}개 | 길이: {script.metadata.duration}초")

    # ─── 2. Freepik image generation (6 scenes) ───
    print("🎨 2/4: Freepik Nano Banana Pro 이미지 생성 (무제한)...")
    scene_images = generate_scene_images(
        script=script,
        provider="freepik",
        image_style="realistic",
    )
    print(f"   생성: {len(scene_images)}장")
    for img in scene_images:
        print(f"     씬 {img['scene_id']}: {Path(img['image_path']).name}")

    # ─── 3. TTS voice generation with timing ───
    print("🎙️ 3/4: edge-tts 음성 생성 중...")
    audio_path, scene_timings = generate_voice_with_timing(script)
    print(f"   오디오: {audio_path}")
    print(f"   씬 타이밍: {len(scene_timings)}개")

    # ─── 4. Remotion render ───
    print("🎬 4/4: Remotion 영상 렌더링 중...")
    output_path = render_video(
        script=script,
        audio_path=audio_path,
        scene_images=scene_images,
        use_bgm=True,
        scene_timings=scene_timings,
    )
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print()
    print("✅ 완료!")
    print(f"   영상: {output_path}")
    print(f"   크기: {size_mb:.2f} MB")
    print(f"   타이틀: {script.metadata.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
