"""Render an existing political_pro plan using Edge TTS (InJoonNeural+22%).

Fallback path when Gemini Charon TTS is unstable. Uses the verified general
political-shorts lock-in: ko-KR-InJoonNeural at +22% rate.

Usage:
    python3 scripts/render_existing_plan_edge.py <out_dir> <plan_idx>
"""
from __future__ import annotations

import json
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
    data = json.loads(plans_path.read_text(encoding="utf-8"))

    from src.analyzer.political_plan_models import ShortsPlan
    from src.analyzer.political_planner import plan_to_script
    from src.analyzer.script_models import AudioConfig

    plans = [ShortsPlan.from_dict(p) for p in data["plans"]]
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

    # 락인 포맷: InJoonNeural +22% (박근혜·추김토론 영상에서 검증)
    script = script.__class__(
        metadata=script.metadata,
        scenes=script.scenes,
        audio=AudioConfig(
            tts_script=script.audio.tts_script,
            voice="ko-KR-InJoonNeural",
            rate="+22%",
            pitch=script.audio.pitch,
        ),
        background=script.background,
    )
    print(f"✅ 스크립트 변환 완료 ({len(script.scenes)}씬, {script.metadata.duration}초) "
          f"voice={script.audio.voice} rate={script.audio.rate}", file=sys.stderr)

    script_path = out_dir / f"script_plan{plan_idx + 1}_edge.json"
    script_path.write_text(
        json.dumps(script.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Edge TTS
    print(f"🎙️ Edge TTS (InJoonNeural +22%) 합성 중...", file=sys.stderr)
    from src.tts.edge_tts_generator import generate_voice_with_timing
    audio_path, timings = generate_voice_with_timing(script)
    print(f"✅ 음성 합성 완료: {audio_path}", file=sys.stderr)

    # Sanity check
    import subprocess
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(audio_path)],
        capture_output=True, text=True,
    )
    audio_dur = float(probe.stdout.strip())
    print(f"📊 오디오 길이: {audio_dur:.1f}s (목표 ~{script.metadata.duration}s)",
          file=sys.stderr)

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
        out_file = out_dir / f"scene_edge_{ts2}_{sid:02d}.mp4"
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
