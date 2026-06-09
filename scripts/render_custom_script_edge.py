"""Render a pre-built ShortsScript JSON for a political_pro source clip.

Sibling to ``render_existing_plan_edge.py``. Use this when you already have a
hand-tuned ``script_*.json`` (e.g. ``script_plan_C_comparison.json``) and just
want to (re)render it with the locked-in Edge TTS format
(``ko-KR-InJoonNeural`` +22%) against an existing political_pro out_dir.

Usage:
    python3 scripts/render_custom_script_edge.py \
        <out_dir> <script_filename> <clip_start_sec> <clip_end_sec>

Example:
    python3 scripts/render_custom_script_edge.py \
        data/political_pro/20260602_112955_cli \
        script_plan_C_comparison.json 21.96 91.38
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1]).resolve()
    script_filename = sys.argv[2]
    clip_start_sec = float(sys.argv[3])
    clip_end_sec = float(sys.argv[4])

    if clip_end_sec <= clip_start_sec:
        print(f"❌ clip_end_sec ({clip_end_sec}) must be > clip_start_sec "
              f"({clip_start_sec})", file=sys.stderr)
        return 3

    script_path = out_dir / script_filename
    if not script_path.exists():
        print(f"❌ script not found: {script_path}", file=sys.stderr)
        return 4

    plans_path = out_dir / "plans.json"
    plans_data = json.loads(plans_path.read_text(encoding="utf-8"))
    video_path = Path(plans_data["video_path"])
    if not video_path.exists():
        print(f"❌ source video not found: {video_path}", file=sys.stderr)
        return 5

    from src.analyzer.script_models import AudioConfig, ShortsScript

    script = ShortsScript.load(script_path)
    print(f"✅ 스크립트 로드: {script_path.name} "
          f"({len(script.scenes)}씬, {script.metadata.duration}초)",
          file=sys.stderr)

    # 락인 포맷: InJoonNeural +22% (박근혜·추김토론 영상에서 검증)
    script = ShortsScript(
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
    print(f"   voice={script.audio.voice} rate={script.audio.rate}",
          file=sys.stderr)

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
    print(f"📊 오디오 길이: {audio_dur:.1f}s "
          f"(목표 ~{script.metadata.duration}s)", file=sys.stderr)

    # Scene clip cut (linear map of TTS timeline → source clip range)
    print(f"✂️ 씬 클립 분할 ({clip_start_sec:.2f}s–{clip_end_sec:.2f}s, 9:16)...",
          file=sys.stderr)
    from src.dem_shorts.editor.segment_cutter import cut_segment

    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 7
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = clip_end_sec - clip_start_sec
    ts2 = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        ns = clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = out_dir / f"scene_custom_{ts2}_{sid:02d}.mp4"
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
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, "
          f"{script.metadata.duration:.0f}s)", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
