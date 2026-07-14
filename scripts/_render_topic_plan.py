"""임시: topic 모드 political-pro plan → 영상 렌더 (원본 클립 없이 그라데이션 배경).

경제쇼츠 V2 — data/political_pro/<dir>/plans.json 의 plan[idx] 를
plan_to_script → Gemini Charon TTS → 무음정렬 → Remotion 렌더.
scene_videos 없이 렌더하면 economic(relatable) 청록/블루 그라데이션 배경 위에
V2 컬러 자막이 올라간다.

Usage: python -m scripts._render_topic_plan <plans_json_dir> <plan_idx>
"""
import sys
from pathlib import Path

from src.analyzer.political_plan_models import ThreePlansResult
from src.analyzer.political_planner import plan_to_script


def main() -> int:
    plans_dir = Path(sys.argv[1])
    plan_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    import json
    data = json.loads((plans_dir / "plans.json").read_text(encoding="utf-8"))
    result = ThreePlansResult.from_dict(data)
    plan = result.plans[plan_idx]
    print(f"✅ plan[{plan_idx}] angle={plan.angle} — {plan.topic}", file=sys.stderr)

    script = plan_to_script(
        plan,
        video_title=result.video_title or plan.topic,
        video_duration_sec=0.0,
        youtube_url="",
        source_channel="",
        source_title=result.video_title or plan.topic,
        output_dir=plans_dir,
    )
    print(f"✅ 스크립트 변환 ({len(script.scenes)}씬, {script.metadata.duration}초)",
          file=sys.stderr)

    # topic 모드: Gemini TTS+silence-align 조합이 오작동(91.9s 합성→14s 오절단)하여
    # 메인 파이프라인 edge-tts 사용. 씬 그룹별 정확 타이밍 반환, 무음정렬 불필요.
    print("🎙️ edge-tts 합성 중 (씬별 타이밍)...", file=sys.stderr)
    from src.tts.edge_tts_generator import generate_voice_with_timing
    audio_path, timings = generate_voice_with_timing(script, output_dir=plans_dir)
    last = max((t["end_ms"] for t in timings), default=0)
    print(f"✅ 음성 합성 완료 (오디오 {last/1000:.1f}s, {len(timings)}씬)", file=sys.stderr)

    print("🎬 Remotion 렌더 중 (그라데이션 배경, 원본 클립 없음)...", file=sys.stderr)
    from src.video.renderer import render_video
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=None,      # topic 모드: 원본 클립 없음 → 그라데이션 배경
        scene_images=None,
        use_bgm=True,
        scene_timings=timings,
        enable_transitions=False,
        enable_sfx=False,
        output_dir=plans_dir,
    )
    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, {script.metadata.duration:.0f}s)",
          file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
