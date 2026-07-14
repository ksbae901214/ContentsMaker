"""장윤기 편 재렌더 — 기존 Charon 오디오·타이밍·씬클립 재사용 (Best Comment 라벨 제거만 반영).

TTS 재합성 없이(GEMINI 쿼터 절약) build_script(type=body) + 기존 자산으로 render_video만 재실행.
usage: PYTHONPATH=. .venv311/bin/python scripts/_rerender_jang_reuse.py
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

from scripts._render_jang_police_power import WORK_DIR, build_script


def main() -> int:
    script = build_script()
    audio_path = Path(sorted(glob.glob(str(WORK_DIR / "*_aligned.mp3")))[-1])
    timing_path = Path(sorted(glob.glob(str(WORK_DIR / "*.timing.json")))[-1])
    timings = json.loads(timing_path.read_text())

    # 기존 씬 클립 재사용 (가장 최근 타임스탬프 세트)
    clips = sorted(glob.glob(str(WORK_DIR / "scene_*_0*.mp4")))
    ts_prefix = Path(clips[-1]).name.rsplit("_", 1)[0]  # scene_<ts>
    scene_videos = []
    for t in [x for x in timings if x["scene_id"] != -1]:
        sid = t["scene_id"]
        p = WORK_DIR / f"{ts_prefix}_{sid:02d}.mp4"
        assert p.exists(), f"씬 클립 없음: {p}"
        scene_videos.append({"scene_id": sid, "video_path": str(p)})

    print(f"✅ 재사용: audio={audio_path.name}, timings={len(timings)}, clips={len(scene_videos)}", flush=True)
    print("🎬 Remotion 재렌더 중 (Best Comment 제거)...", flush=True)

    from src.video.renderer import render_video
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        scene_timings=timings,
        use_bgm=True,
        enable_transitions=False,
        enable_sfx=False,
        output_dir=WORK_DIR,
    )
    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB)", flush=True)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
