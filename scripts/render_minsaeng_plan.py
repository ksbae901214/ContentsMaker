#!/usr/bin/env python3
"""topic 기반 ShortsPlan(민생 심판) → MP4 렌더링.

호출 순서는 src/main.py:584-654 (political_pro CLI)를 따르되,
원본 YouTube 클립이 없는 topic 모드이므로 cut_segment 단계는 생략한다.
TTS는 Gemini Charon을 우선 시도하고, 실패 시 edge-tts로 폴백한다.
"""
import json
from pathlib import Path

from src.analyzer.political_plan_models import ShortsPlan
from src.analyzer.political_planner import plan_to_script
from src.video.renderer import render_video

PLAN_PATH = Path("data/political_pro/20260701_민생심판/plan.json")
OUT_DIR = Path("data/political_pro/20260701_민생심판")


def build_tts(script):
    """Charon TTS 우선, 실패 시 edge-tts 폴백. (audio_path, timings) 반환."""
    try:
        from src.tts.gemini_tts_generator import (
            GeminiTTSError,
            generate_voice_with_timing_gemini,
        )
        from src.tts.silence_align import align_timings_to_silence

        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            output_dir=OUT_DIR,
            voice_name="Charon",
            style_prompt=(
                "Read in a fast, clear newscaster tone with neutral political delivery:"
            ),
            temperature=0.5,
            include_outro=False,
        )
        audio_path, timings = align_timings_to_silence(
            audio_path, timings, out_dir=OUT_DIR
        )
        print(f"[TTS] Gemini Charon OK -> {audio_path}")
        return audio_path, timings
    except Exception as exc:  # noqa: BLE001 - 폴백 목적
        print(f"[TTS] Gemini 실패({type(exc).__name__}: {exc}) -> edge-tts 폴백")
        from src.tts.edge_tts_generator import generate_voice_with_timing

        audio_path, timings = generate_voice_with_timing(script, output_dir=OUT_DIR)
        print(f"[TTS] edge-tts OK -> {audio_path}")
        return audio_path, timings


def main() -> None:
    plan_dict = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    plan = ShortsPlan.from_dict(plan_dict)
    print(f"[1/4] Plan 로드: {plan.topic}")

    script = plan_to_script(
        plan,
        video_title=plan.topic,
        video_duration_sec=60.0,  # topic 모드에서는 무시됨
        youtube_url="",
        source_channel="",
        source_title=plan.topic,
        output_dir=OUT_DIR,
    )
    print(f"[2/4] Script 변환 완료: {len(script.scenes)}개 씬")

    audio_path, timings = build_tts(script)
    print(f"[3/4] TTS 완료: {len(timings)}개 타이밍")

    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=None,   # topic 모드 — 원본 클립 없음 (그라데이션 배경)
        scene_images=None,
        scene_timings=timings,
        output_dir=OUT_DIR,
        use_bgm=True,
        enable_transitions=False,
        enable_sfx=False,
    )
    print(f"[4/4] ✅ 렌더 완료: {mp4}")


if __name__ == "__main__":
    main()
