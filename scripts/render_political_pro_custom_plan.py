"""Render a political_pro V2 video from a HAND-CRAFTED ShortsPlan.

Use case: user wants a different angle/tone than what the LLM-generated plans.json
offers, but wants to reuse the cached video + clip window. Mirrors the same
TTS → ffmpeg cut → Remotion render pipeline used by `cmd_political_pro`.

Usage:
    PYTHONPATH=. python3 scripts/render_political_pro_custom_plan.py <plans_dir>

The plan body is hard-coded below — edit and re-run.
"""
from __future__ import annotations

import json as _json
import sys
import time as _time
from pathlib import Path

from src.analyzer.political_plan_models import (
    Narration,
    ShortsPlan,
    ThreePlansResult,
)
from src.analyzer.political_planner import plan_to_script
from src.dem_shorts.editor.segment_cutter import cut_segment
from src.tts.gemini_tts_generator import (
    GeminiTTSError,
    generate_voice_with_timing_gemini,
)
from src.video.renderer import render_video


def build_plan() -> ShortsPlan:
    """기획안: 민주당 지지율 하락을 간파한 국민의힘이 재선거 카드로 반격 —
    '영리한 판단이었다'는 호평/전략 분석 톤.

    소스 클립: 13.7~47.3초 (재선거 발표 + 6개 지역 + 서울 포함 언급 구간).
    """
    narrations = (
        Narration(
            start_sec=0.0,
            end_sec=4.5,
            text="민주당 지지율 슬그머니 하락",
            subtitle_color="red",
            subtitle_emphasis=True,
            tts_text="민주당 지지율이 슬그머니 빠지기 시작했습니다",
        ),
        Narration(
            start_sec=4.5,
            end_sec=9.0,
            text="그 신호를 정확히 읽어낸 국민의힘",
            subtitle_color="yellow",
            subtitle_emphasis=True,
            tts_text="국민의힘이 이 흐름을 정확히 포착했습니다",
        ),
        Narration(
            start_sec=9.0,
            end_sec=13.5,
            text="꺼낸 카드, 전면 재선거",
            subtitle_color="yellow",
            subtitle_emphasis=True,
            tts_text="꺼낸 카드는 전면 재선거 강수였습니다",
        ),
        Narration(
            start_sec=13.5,
            end_sec=18.0,
            text="서울·인천·경기 6곳 한 번에",
            subtitle_color="white",
            subtitle_emphasis=False,
            tts_text="서울 인천 경기 등 6곳을 한 번에 묶었습니다",
        ),
        Narration(
            start_sec=18.0,
            end_sec=22.5,
            text="항의 아닌 정국 주도권 탈환",
            subtitle_color="blue",
            subtitle_emphasis=False,
            tts_text="항의가 아니라 정국 주도권 탈환입니다",
        ),
        Narration(
            start_sec=22.5,
            end_sec=27.0,
            text="결단력 평가, 한 방에 뒤집었다",
            subtitle_color="red",
            subtitle_emphasis=True,
            tts_text="결단력 부족 평가를 단숨에 뒤집은 영리한 판단이었습니다",
        ),
    )

    return ShortsPlan(
        topic="민주당 지지율 하락 읽고 던진 국민의힘의 전면 재선거 — 신의 한 수?",
        hook="민주당 지지율 빠졌다, 국민의힘 신의 한 수",
        clip_start_sec=13.7,
        clip_end_sec=47.3,
        clip_reason=(
            "전면 재선거 발표 + 6개 지역(서울 포함) 언급이 한 화면에 집약된 구간. "
            "호평 톤의 평론 나레이션 위에 발표 장면이 시각적 근거로 깔리도록 재활용."
        ),
        flow_intro="민주당 지지율 미세 하락이라는 정치적 환경 변화에서 시작",
        flow_middle="국민의힘이 그 흐름을 포착해 전면 재선거 강수를 던진 의사결정 과정 묘사",
        flow_climax=(
            "단순 항의가 아니라 정국 주도권 탈환을 노린 전략적 한 수였다는 "
            "호평으로 마무리 — 결단력 없다던 평가를 뒤집은 판단"
        ),
        narrations=narrations,
        cta="이번 결단, 신의 한 수 같으신가요?",
        angle="title_anchor",
        format_type="A",
        format_reason="평론·전략 분석 톤 (논평형 인터뷰 구조에 가까움)",
        visual_directives=(
            "0~5초: '지지율 하락' 키워드 빨간색 자막 강조",
            "5~10초: '정확히 읽어냈다' 키워드 노란색 강조",
            "10~15초: '전면 재선거 강수' 키워드 노란색 + 발표 장면 클로즈업",
            "20~25초: '정국 주도권' 파란색 — 톤 다운된 분석체",
            "25~30초: '영리한 판단' 빨간색 강조로 호평 클라이맥스",
        ),
        source_type="youtube",
    )


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: render_political_pro_custom_plan.py <plans_dir>",
              file=sys.stderr)
        return 2

    out_dir = Path(sys.argv[1]).resolve()
    plans_json = out_dir / "plans.json"
    if not plans_json.exists():
        print(f"❌ plans.json not found at {plans_json}", file=sys.stderr)
        return 2

    raw = _json.loads(plans_json.read_text(encoding="utf-8"))
    existing = ThreePlansResult.from_dict(raw)
    vp = Path(existing.video_path)
    yt_title = existing.video_title
    yt_channel = existing.video_channel
    duration_sec = existing.video_duration_sec
    url = existing.youtube_url

    plan = build_plan()
    print(f"✅ 커스텀 plan 빌드 — {plan.topic}", file=sys.stderr)

    # 커스텀 plan을 같은 디렉터리에 별도 저장 (디버깅·이력용)
    (out_dir / "plan_custom_supportive.json").write_text(
        _json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

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
        out_file = out_dir / f"scene_custom_{ts2}_{sid:02d}.mp4"
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
