"""plans.json에서 특정 angle의 ShortsPlan을 골라 political_pro V2 렌더 경로
(plan_to_script → Gemini TTS → 씬 컷 → Remotion)를 그대로 실행한다.
자동 생성 플랜을 '있는 그대로' 사용하므로 tts_text(보도체 낭독)가 유지돼 풀 길이로 나온다.

usage: PYTHONPATH=. python scripts/_render_plan_by_angle.py <plans.json> <angle>
(main.py cmd_political_pro L674-744 미러)
"""
from __future__ import annotations

import sys
import time
import json
from pathlib import Path

from src.analyzer.political_plan_models import ThreePlansResult
from src.analyzer.political_planner import plan_to_script


def main() -> int:
    plans_path = sys.argv[1]
    want_angle = sys.argv[2]

    result = ThreePlansResult.from_dict(json.load(open(plans_path, encoding="utf-8")))
    plan = next((p for p in result.plans if p.angle == want_angle), None)
    if plan is None:
        print(f"❌ angle={want_angle} 플랜 없음 (있는 angle: {[p.angle for p in result.plans]})",
              file=sys.stderr)
        return 2

    vp = Path(result.video_path)
    out_dir = vp.parent
    url = result.youtube_url
    yt_title = result.video_title
    yt_channel = result.video_channel
    duration_sec = result.video_duration_sec

    # 클립 구간 override (optional argv[3]=start, argv[4]=end).
    # OffthreadVideo는 루프하지 않으므로, clip_duration이 TTS 총길이보다 짧으면
    # 각 씬 영상 조각이 짧아 프리즈된다. 소스를 넓게 써서 연속 재생을 보장한다.
    from dataclasses import replace as _replace
    if len(sys.argv) >= 5:
        cs, ce = float(sys.argv[3]), float(sys.argv[4])
        plan = _replace(plan, clip_start_sec=cs, clip_end_sec=ce)
        print(f"🔧 클립 구간 override → {cs}~{ce}", file=sys.stderr)

    print(f"✅ 선택: angle={plan.angle} | {plan.yt_title or plan.topic}", file=sys.stderr)
    print(f"   clip {plan.clip_start_sec}~{plan.clip_end_sec} (source {duration_sec:.1f}s)",
          file=sys.stderr)

    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel=yt_channel,
        source_title=yt_title,
        youtube_url=url,
    )
    print(f"✅ 스크립트 변환 ({len(script.scenes)}씬, {script.metadata.duration}초)", file=sys.stderr)

    print("🎙️ Gemini TTS Charon 합성 중...", file=sys.stderr)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    audio_path, timings = generate_voice_with_timing_gemini(
        script,
        voice_name="Charon",
        style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
        temperature=0.5,
        include_outro=False,
    )
    print("✅ 음성 합성 완료", file=sys.stderr)

    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=out_dir)
    print("✅ 무음 정렬 완료", file=sys.stderr)

    print("✂️ 씬 클립 분할 (9:16)...", file=sys.stderr)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    main_timings = [t for t in timings if t["scene_id"] != -1]
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = plan.clip_end_sec - plan.clip_start_sec
    ts2 = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        ns = plan.clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = plan.clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = out_dir / f"scene3_{ts2}_{sid:02d}.mp4"
        cut_segment(input_path=vp, output_path=out_file, start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    print(f"✅ 씬 클립 {len(scene_videos)}개 분할 완료", file=sys.stderr)

    print("🎬 Remotion 렌더 중...", file=sys.stderr)
    from src.video.renderer import render_video
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
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, {script.metadata.duration:.0f}s)", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
