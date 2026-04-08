"""Final shorts composition: Kling 2.5 clips + TTS voice + subtitles + BGM.

Takes the 6 Kling 2.5 image-to-video clips (v2), the existing edge-tts
audio with per-scene timings, and wraps them in the Remotion composition
that overlays subtitles (with emotion highlight colors) and BGM.

Reuses src.video.renderer.render_video() — the same path the web UI uses
for the video visual mode — so no new rendering logic is introduced.

Run:
    python3 scripts/e2e_anklet_final.py
"""
from __future__ import annotations

import json
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
from src.video.renderer import render_video


SCRIPT_FILE = Path("data/scripts/20260408_e2e_anklet.json")
AUDIO_FILE = Path(
    "data/audio/20260408_141241_블라인드_인기글안방_화장실에서_모르는_여자_발찌.mp3"
)
TIMING_FILE = Path(
    "data/audio/20260408_141241_블라인드_인기글안방_화장실에서_모르는_여자_발찌.timing.json"
)
SCENE_VIDEOS = [
    {"scene_id": 1, "video_path": "data/videos/anklet_scenes_v2/scene_01.mp4"},
    {"scene_id": 2, "video_path": "data/videos/anklet_scenes_v2/scene_02.mp4"},
    {"scene_id": 3, "video_path": "data/videos/anklet_scenes_v2/scene_03.mp4"},
    {"scene_id": 4, "video_path": "data/videos/anklet_scenes_v2/scene_04.mp4"},
    {"scene_id": 5, "video_path": "data/videos/anklet_scenes_v2/scene_05.mp4"},
    {"scene_id": 6, "video_path": "data/videos/anklet_scenes_v2/scene_06.mp4"},
]


def main() -> int:
    print("=" * 70)
    print("  Final Shorts: Kling 2.5 clips + TTS + Subtitles + BGM")
    print("=" * 70)

    # 1. Load script
    print("\n📄 1/3: ShortsScript 로드...")
    script = ShortsScript.load(SCRIPT_FILE)
    print(f"   타이틀: {script.metadata.title!r}")
    print(f"   씬: {len(script.scenes)}개 | 감정: {script.metadata.emotion_type}")

    # 2. Load pre-generated TTS timings
    print("\n🎙️ 2/3: 기존 edge-tts 음성 + 타이밍 로드...")
    if not AUDIO_FILE.exists():
        print(f"   ❌ 음성 파일 없음: {AUDIO_FILE}")
        return 1
    if not TIMING_FILE.exists():
        print(f"   ❌ 타이밍 파일 없음: {TIMING_FILE}")
        return 1
    scene_timings = json.loads(TIMING_FILE.read_text(encoding="utf-8"))
    print(f"   오디오: {AUDIO_FILE.name}")
    print(f"   타이밍: {len(scene_timings)}개 씬")

    # Verify all scene video files exist
    missing = [v["video_path"] for v in SCENE_VIDEOS if not Path(v["video_path"]).exists()]
    if missing:
        print(f"\n❌ 씬 비디오 누락: {missing}")
        return 1

    # 3. Render via Remotion
    print("\n🎬 3/3: Remotion 렌더링...")
    print("   (Kling 2.5 비디오 배경 + 자막 + TTS 음성 + BGM)")
    output_path = render_video(
        script=script,
        audio_path=AUDIO_FILE,
        scene_videos=SCENE_VIDEOS,
        use_bgm=True,
        scene_timings=scene_timings,
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print()
    print("=" * 70)
    print("  ✅ 최종 쇼츠 완성!")
    print("=" * 70)
    print(f"   영상: {output_path}")
    print(f"   크기: {size_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
