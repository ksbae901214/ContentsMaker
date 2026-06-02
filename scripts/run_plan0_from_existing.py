"""One-off bridge: existing plans.json + Plan 0 → TTS + 단일 연속 클립 + Remotion render.

기존 political-pro CLI는 plans를 항상 재생성해서 비결정적 + 느림.
이 스크립트는 data/political_pro/20260601_171644_cli/plans.json 의 Plan 0 으로
바로 영상까지 만든다. 본 사용자 세션 한정.

2026-06-01: 씬별 클립을 자르지 않고 [clip_start, clip_start + tts_total] 단일 연속
클립을 background_video로 전달해 영상이 끊김 없이 쭉 재생되도록 함.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.analyzer.political_plan_models import ThreePlansResult
from src.analyzer.political_planner import plan_to_script
from src.tts.gemini_tts_generator import (
    GeminiTTSError,
    generate_voice_with_timing_gemini,
)
from src.dem_shorts.editor.segment_cutter import cut_segment
from src.video.renderer import render_video


def main() -> int:
    out_dir = Path("data/political_pro/20260601_171644_cli").resolve()
    plans_path = out_dir / "plans.json"
    if not plans_path.exists():
        print(f"❌ plans.json 없음: {plans_path}", file=sys.stderr)
        return 1

    data = json.loads(plans_path.read_text(encoding="utf-8"))
    result = ThreePlansResult.from_dict(data)
    plan = result.plans[0]  # Plan 0 (title_anchor)
    print(f"✅ Plan 0 로드: {plan.topic}", file=sys.stderr)

    vp = Path(result.video_path).resolve()
    if not vp.exists():
        print(f"❌ 원본 영상 없음: {vp}", file=sys.stderr)
        return 1

    script = plan_to_script(
        plan,
        video_title=result.video_title,
        video_duration_sec=result.video_duration_sec,
        source_channel=result.video_channel,
        source_title=result.video_title,
        youtube_url=result.youtube_url,
    )
    print(
        f"✅ 스크립트 변환 완료 ({len(script.scenes)}씬, {script.metadata.duration}초)",
        file=sys.stderr,
    )

    print("🎙️ Gemini TTS Charon 합성 중...", file=sys.stderr)
    try:
        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            voice_name="Charon",
            style_prompt=(
                "Read in a fast, clear newscaster tone with neutral political delivery:"
            ),
            temperature=0.5,
            include_outro=False,
        )
    except GeminiTTSError as e:
        print(f"❌ Gemini TTS 실패: {e}", file=sys.stderr)
        return 2
    print(f"✅ 음성 합성 완료: {audio_path}", file=sys.stderr)

    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 3

    # 단일 연속 클립을 잘라낸다. 길이는 본 콘텐츠 TTS 총 길이 + 약간의 여유.
    # video_duration_sec를 초과하지 않게 cap.
    tts_total_sec = max(t["end_ms"] for t in main_timings) / 1000.0
    tail_pad = 0.5  # 끝부분 컷 잘림 방지용 여유
    cut_start = max(0.0, plan.clip_start_sec)
    cut_end = min(result.video_duration_sec, cut_start + tts_total_sec + tail_pad)
    bg_clip = out_dir / "bg_continuous.mp4"
    print(
        f"✂️ 단일 연속 클립 cut: [{cut_start:.2f}s ~ {cut_end:.2f}s, "
        f"길이 {cut_end - cut_start:.2f}s], TTS 총 {tts_total_sec:.2f}s",
        file=sys.stderr,
    )
    cut_segment(input_path=vp, output_path=bg_clip, start_sec=cut_start, end_sec=cut_end, mute=True)
    print(f"✅ 연속 클립 생성: {bg_clip}", file=sys.stderr)

    print("🎬 Remotion 렌더 중...", file=sys.stderr)
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=None,  # 씬별 클립 사용 안 함 — background_video로 대체
        background_video=bg_clip,
        use_bgm=True,
        scene_timings=timings,
        enable_transitions=False,  # 정치 모드 락인: 전환 OFF
        enable_sfx=False,  # 정치 모드 락인: SFX OFF
    )

    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(
        f"\n📁 출력: {mp4} ({size_mb:.1f}MB, {script.metadata.duration:.0f}s)",
        file=sys.stderr,
    )
    print("⚠️  주의: 출력은 자동 생성 결과입니다. 게시 전 반드시 검수가 필요합니다.", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
