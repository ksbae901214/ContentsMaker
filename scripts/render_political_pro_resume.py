"""Resume political_pro rendering from cached plans.json + Edge TTS audio.

이 스크립트는 Gemini TTS quota 초과 시 폴백 경로용:
plans.json + Edge TTS audio + timing.json → scene_videos cut → Remotion render.

[[feedback-political-shorts-lockin]] 적용: InJoonNeural+22% 음성.
[[feedback-political-pro-format]] 락인 유지: enable_sfx/transitions=False.
"""
from __future__ import annotations

import json
import sys
import time as _time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzer.political_planner import plan_to_script  # noqa: E402
from src.analyzer.political_planner import ShortsPlan  # noqa: E402
from src.dem_shorts.editor.segment_cutter import cut_segment  # noqa: E402
from src.video.renderer import render_video  # noqa: E402


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: render_political_pro_resume.py <plans.json> <plan_idx> "
            "<audio.mp3> [timing.json]",
            file=sys.stderr,
        )
        return 2

    plans_path = Path(sys.argv[1])
    plan_idx = int(sys.argv[2])
    audio_path = Path(sys.argv[3])
    timing_path = (
        Path(sys.argv[4]) if len(sys.argv) > 4 else audio_path.with_suffix(".timing.json")
    )

    data = json.loads(plans_path.read_text(encoding="utf-8"))
    plan_dict = data["plans"][plan_idx]
    plan = ShortsPlan.from_dict(plan_dict)
    video_path = Path(data["video_path"])
    yt_title = data["video_title"]
    yt_channel = data["video_channel"]
    duration_sec = data["video_duration_sec"]
    youtube_url = data["youtube_url"]

    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel=yt_channel,
        source_title=yt_title,
        youtube_url=youtube_url,
    )
    print(f"✅ 스크립트 변환 완료 ({len(script.scenes)}씬, {script.metadata.duration}초)", file=sys.stderr)

    timings = json.loads(timing_path.read_text(encoding="utf-8"))
    print(f"✅ Edge TTS timing 로드: {len(timings)}개 (audio={audio_path.name})", file=sys.stderr)

    print("✂️ 씬 클립 분할 (9:16)...", file=sys.stderr)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 7
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = plan.clip_end_sec - plan.clip_start_sec
    ts2 = int(_time.time())
    scene_videos = []
    out_dir = plans_path.parent
    for t in main_timings:
        sid = t["scene_id"]
        ns = plan.clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = plan.clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = out_dir / f"scene_{ts2}_{sid:02d}.mp4"
        cut_segment(input_path=video_path, output_path=out_file, start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    print(f"✅ 씬 클립 {len(scene_videos)}개 분할 완료", file=sys.stderr)

    print("🎬 Remotion 렌더 중...", file=sys.stderr)
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        use_bgm=True,  # default
        scene_timings=timings,
        enable_transitions=False,  # political_pro 락인
        enable_sfx=False,  # political_pro 락인
    )
    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, {script.metadata.duration:.0f}s)", file=sys.stderr)
    print("⚠️  주의: 출력은 자동 생성 결과. 게시 전 반드시 사용자 검수 필요.", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
