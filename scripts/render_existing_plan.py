"""Re-render an existing political_pro plan without re-downloading the video.

Loads plans.json from a previous political-pro --plans-only run, picks a plan
by index, then runs the remaining pipeline:
  plan_to_script → Gemini TTS Charon → scene clip cut → Remotion render.

Usage:
    python3 scripts/render_existing_plan.py <out_dir> <plan_idx>

Example:
    python3 scripts/render_existing_plan.py \
        data/political_pro/20260602_112955_cli 1
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1]).resolve()
    plan_idx = int(sys.argv[2])

    plans_path = out_dir / "plans.json"
    if not plans_path.exists():
        print(f"❌ plans.json not found: {plans_path}", file=sys.stderr)
        return 2

    data = json.loads(plans_path.read_text(encoding="utf-8"))

    # Reconstruct ShortsPlan from dict
    from src.analyzer.political_plan_models import ShortsPlan
    from src.analyzer.political_planner import plan_to_script

    plans = [ShortsPlan.from_dict(p) for p in data["plans"]]
    if plan_idx not in (0, 1, 2):
        print(f"❌ plan_idx must be 0/1/2, got {plan_idx}", file=sys.stderr)
        return 2
    plan = plans[plan_idx]
    print(f"✅ Plan {plan_idx + 1} ({plan.angle}) — {plan.topic}", file=sys.stderr)

    yt_title = data["video_title"]
    yt_url = data["youtube_url"]
    video_path = Path(data["video_path"])
    duration_sec = data["video_duration_sec"]

    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel="MBC 뉴스데스크",
        source_title=yt_title,
        youtube_url=yt_url,
    )
    print(f"✅ 스크립트 변환 완료 ({len(script.scenes)}씬, {script.metadata.duration}초)",
          file=sys.stderr)

    # Save script for review
    script_path = out_dir / f"script_plan{plan_idx + 1}.json"
    script_path.write_text(
        json.dumps(script.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"📄 스크립트 저장: {script_path}", file=sys.stderr)

    # Gemini TTS Charon
    print(f"🎙️ Gemini TTS Charon 합성 중...", file=sys.stderr)
    from src.tts.gemini_tts_generator import (
        GeminiTTSError,
        generate_voice_with_timing_gemini,
    )
    try:
        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            voice_name="Charon",
            style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
            temperature=0.5,
            include_outro=False,
        )
    except GeminiTTSError as e:
        print(f"❌ Gemini TTS 실패: {e}", file=sys.stderr)
        return 6
    print(f"✅ 음성 합성 완료: {audio_path}", file=sys.stderr)

    # Scene clip cut
    print(f"✂️ 씬 클립 분할 (9:16)...", file=sys.stderr)
    from src.dem_shorts.editor.segment_cutter import cut_segment

    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 7
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = plan.clip_end_sec - plan.clip_start_sec
    ts2 = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        ns = plan.clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = plan.clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = out_dir / f"scene_{ts2}_{sid:02d}.mp4"
        cut_segment(input_path=video_path, output_path=out_file,
                    start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    print(f"✅ 씬 클립 {len(scene_videos)}개 분할 완료", file=sys.stderr)

    # Remotion render
    print(f"🎬 Remotion 렌더 중...", file=sys.stderr)
    from src.video.renderer import render_video
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        use_bgm=False,
        scene_timings=timings,
        enable_transitions=False,
        enable_sfx=False,
    )

    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, {script.metadata.duration:.0f}s)",
          file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
