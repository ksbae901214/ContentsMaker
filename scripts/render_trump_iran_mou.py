"""트럼프-이란 MOU 정치쇼츠 V2 렌더 실행 스크립트.

미리 자른 씬별 클립 + edge-tts 음성 + scene_timings 사용해
Remotion 렌더만 수행. SFX/transition 모두 OFF (정치쇼츠 V2 락인).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video

PROJ_DIR = Path("data/jpolitics/20260615_170407_trump_iran_mou_signing")
SCRIPT_PATH = PROJ_DIR / "script.json"
AUDIO_PATH = Path("data/audio/20260615_171056_트럼프_이란과_합의_마무리_615_전자서명.mp3")
TIMINGS_PATH = Path("data/audio/20260615_171056_트럼프_이란과_합의_마무리_615_전자서명.timing.json")
CLIPS_DIR = PROJ_DIR / "clips"


def main() -> int:
    with SCRIPT_PATH.open() as f:
        script = ShortsScript.from_dict(json.load(f))

    with TIMINGS_PATH.open() as f:
        scene_timings = json.load(f)

    scene_videos = []
    for sc in script.scenes:
        clip = CLIPS_DIR / f"scene_{sc.id}.mp4"
        if not clip.exists():
            print(f"❌ 클립 없음: {clip}", file=sys.stderr)
            return 1
        scene_videos.append({"scene_id": sc.id, "video_path": str(clip)})

    print(f"📋 씬 {len(scene_videos)}개, 클립 {len(scene_videos)}개, 타이밍 {len(scene_timings)}개", file=sys.stderr)
    print(f"🎬 Remotion 렌더 시작...", file=sys.stderr)

    mp4 = render_video(
        script,
        audio_path=AUDIO_PATH,
        scene_videos=scene_videos,
        scene_timings=scene_timings,
        use_bgm=False,
        enable_sfx=False,
        enable_transitions=False,
    )

    print(f"\n✅ 렌더 완료: {mp4}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
