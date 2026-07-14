"""Render political_pro V2 video from an already-generated plans.json.

Skips download/transcript/plans generation (uses cached artifacts) and runs
plan_to_script → Gemini TTS Charon → ffmpeg scene cut → Remotion render.

Mirrors the post-plan-selection branch of `src/main.py::cmd_political_pro`.
"""
from __future__ import annotations

import json as _json
import sys
import time as _time
from pathlib import Path

from src.analyzer.political_plan_models import ThreePlansResult
from src.analyzer.political_planner import plan_to_script
from src.dem_shorts.editor.segment_cutter import cut_segment
from src.tts.gemini_tts_generator import (
    GeminiTTSError,
    generate_voice_with_timing_gemini,
)
from src.video.renderer import render_video


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: render_political_pro_from_plans.py <plans_dir> <plan_idx>",
              file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1]).resolve()
    plan_idx = int(sys.argv[2])

    plans_json = out_dir / "plans.json"
    if not plans_json.exists():
        print(f"❌ plans.json not found at {plans_json}", file=sys.stderr)
        return 2

    raw = _json.loads(plans_json.read_text(encoding="utf-8"))
    result = ThreePlansResult.from_dict(raw)
    if plan_idx not in (0, 1, 2):
        print(f"❌ plan-idx 0/1/2 (got {plan_idx})", file=sys.stderr)
        return 2

    plan = result.plans[plan_idx]
    vp = Path(result.video_path)
    yt_title = result.video_title
    yt_channel = result.video_channel
    duration_sec = result.video_duration_sec
    url = result.youtube_url

    print(f"✅ Plan {plan_idx + 1} 선택됨 — {plan.topic}", file=sys.stderr)

    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel=yt_channel,
        source_title=yt_title,
        youtube_url=url,
    )
    print(f"✅ 스크립트 변환 완료 ({len(script.scenes)}씬, {script.metadata.duration}초)",
          file=sys.stderr)

    print("🎙️ Gemini TTS Charon 합성 중...", file=sys.stderr)
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
    print("✅ 음성 합성 완료", file=sys.stderr)

    print("✂️ 씬 클립 분할 (9:16)...", file=sys.stderr)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 7
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = plan.clip_end_sec - plan.clip_start_sec
    ts2 = int(_time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        ns = plan.clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = plan.clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = out_dir / f"scene_{ts2}_{sid:02d}.mp4"
        cut_segment(input_path=vp, output_path=out_file,
                    start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    print(f"✅ 씬 클립 {len(scene_videos)}개 분할 완료", file=sys.stderr)

    print("🎬 Remotion 렌더 중...", file=sys.stderr)
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        scene_timings=timings,
        output_dir=out_dir,
        use_bgm=True,
        enable_transitions=False,
        enable_sfx=False,
    )
    print(f"✅ 영상 렌더 완료: {mp4}", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
