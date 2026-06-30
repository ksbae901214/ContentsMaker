"""Re-render a political_pro short from an existing run dir WITHOUT regenerating
plans (deterministic). Reuses the saved plan + source clip; regenerates only TTS
(identical narration text) → scene cuts → Remotion render with the current layout.

Usage:
    python3 -m scripts.rerender_political_pro <run_dir> [plan_idx]
"""
import json
import sys
import time
from pathlib import Path

from src.analyzer.political_plan_models import ShortsPlan
from src.analyzer.political_planner import plan_to_script
from src.dem_shorts.editor.segment_cutter import cut_segment
from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
from src.tts.silence_align import align_timings_to_silence
from src.video.renderer import render_video


def main() -> int:
    run_dir = Path(sys.argv[1])
    plan_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    data = json.loads((run_dir / "plans.json").read_text(encoding="utf-8"))
    plan = ShortsPlan.from_dict(data["plans"][plan_idx])
    url = data["youtube_url"]
    yt_title = data["video_title"]
    yt_channel = data.get("video_channel", "")
    duration_sec = float(data["video_duration_sec"])
    vp = Path(data["video_path"])
    if not vp.exists():
        # fallback to source mp4 inside run_dir
        cands = list(run_dir.glob("*.mp4"))
        cands = [c for c in cands if not c.name.startswith("scene_")]
        vp = cands[0]

    print(f"plan {plan_idx}: angle={plan.angle} topic={plan.topic}", file=sys.stderr)
    print(f"source video: {vp} ({duration_sec:.1f}s)", file=sys.stderr)

    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel=yt_channel,
        source_title=yt_title,
        youtube_url=url,
    )
    print(f"script: {len(script.scenes)} scenes, {script.metadata.duration}s", file=sys.stderr)

    import os
    reuse = os.environ.get("REUSE_AUDIO", "").strip()
    if reuse:
        # 기존 음성 재사용 (Gemini 비결정성·할당량 회피). 타이밍은 글자수 기준으로
        # 임시 생성 후 silence_align이 실측 보정한다.
        from src.tts.gemini_tts_generator import compute_scene_timings
        from src.tts.silence_align import probe_duration
        audio_path = Path(reuse)
        total_ms = int(probe_duration(audio_path) * 1000)
        timings = compute_scene_timings(script.scenes, total_ms, outro_duration_ms=0)
        print(f"reusing audio: {audio_path}", file=sys.stderr)
    else:
        print("Gemini TTS Charon...", file=sys.stderr)
        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            voice_name="Charon",
            style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
            temperature=0.5,
            include_outro=False,
        )

    # 실측 무음 정렬: 앞뒤 무음 트림 + 씬 경계를 실제 무음에 스냅 (자막-음성 동기화)
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=run_dir)
    print(f"aligned: speech-only audio, {len(timings)} scene timings", file=sys.stderr)

    print("cutting 9:16 scene clips...", file=sys.stderr)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = plan.clip_end_sec - plan.clip_start_sec
    ts2 = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        ns = plan.clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = plan.clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = run_dir / f"scene_{ts2}_{sid:02d}.mp4"
        cut_segment(input_path=vp, output_path=out_file, start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})

    print("Remotion render...", file=sys.stderr)
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        use_bgm=True,
        scene_timings=timings,
        enable_transitions=False,
        enable_sfx=False,
    )
    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\nOUTPUT: {mp4} ({size_mb:.1f}MB)", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
