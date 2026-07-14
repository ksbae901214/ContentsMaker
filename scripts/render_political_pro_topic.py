"""토픽 모드 정치쇼츠 V2 렌더 (기획안 → 스크립트 → TTS → 뉴스클립 검색 → Remotion).

웹 `/api/generate` (mode=political_pro, topic) 흐름을 CLI로 재현한다.

사용법:
    python3 scripts/render_political_pro_topic.py <plans.json> <plan_idx>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from src.analyzer.political_plan_models import ShortsPlan
from src.analyzer.political_planner import plan_to_script
from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_DIR
from src.scraper.youtube_news_searcher import (
    cut_scene_clip,
    get_video_duration_sec,
    search_and_download_news_clips,
)
from src.tts.gemini_tts_generator import (
    GeminiTTSError,
    generate_voice_with_timing_gemini,
)
from src.tts.silence_align import align_timings_to_silence
from src.video.renderer import render_video


def main() -> int:
    plans_path = Path(sys.argv[1])
    plan_idx = int(sys.argv[2])
    data = json.loads(plans_path.read_text(encoding="utf-8"))
    plans = data["plans"]
    plan = ShortsPlan.from_dict(plans[plan_idx])
    out_dir = plans_path.parent

    print(f"▶ Plan {plan_idx + 1} 선택: {plan.topic}", file=sys.stderr)

    # 1) plan → script
    script = plan_to_script(
        plan,
        video_title=plan.topic,
        video_duration_sec=60.0,
        youtube_url="",
        source_channel="",
        source_title=plan.topic,
        output_dir=out_dir,
    )
    print(f"✅ 스크립트 {len(script.scenes)}씬, {script.metadata.duration:.1f}s", file=sys.stderr)

    # 2) Gemini TTS Charon
    print("🎙️ Gemini TTS(Charon) 합성 중...", file=sys.stderr)
    try:
        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            voice_name="Charon",
            style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
            temperature=0.5,
            include_outro=False,
        )
    except GeminiTTSError as e:
        print(f"❌ TTS 실패: {e}", file=sys.stderr)
        return 6

    # 3) 실측 무음 정렬
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=out_dir)
    print("✅ 무음 정렬 완료", file=sys.stderr)

    # 4) 뉴스클립 자동 검색·다운로드·씬별 cut (topic 모드)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 7
    scene_durations = [max(0.5, (t["end_ms"] - t["start_ms"]) / 1000.0) for t in main_timings]
    n_scenes = len(scene_durations)

    # 넓은·안정적 뉴스 검색어 풀 — 너무 구체적이면 ytsearch 0건이 되므로 폭넓게.
    kw_pool = [
        "소비자물가 상승 뉴스",
        "6월 소비자물가 뉴스",
        "물가 상승 서민 부담 뉴스",
        "장바구니 물가 뉴스",
        "채소값 폭등 뉴스",
        "기름값 상승 주유소 뉴스",
        "정부 물가 대책 뉴스",
        "생활물가 상승 뉴스",
    ]

    work_dir = DATA_DIR / "political_pro" / f"topic_{int(time.time())}_clips"
    sources_dir = work_dir / "sources"
    scenes_dir = work_dir / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    print(f"⬇️ 뉴스 원본 검색·다운로드 ({len(kw_pool)}개 키워드)...", file=sys.stderr)
    downloaded = search_and_download_news_clips(kw_pool, out_dir=sources_dir)
    sources = [p for p in downloaded if p is not None and p.exists()]
    print(f"✅ 원본 {len(sources)}/{len(kw_pool)}개 확보", file=sys.stderr)
    if not sources:
        print("⚠️ 원본 0개 — 전 씬 그라데이션 배경으로 렌더", file=sys.stderr)

    # 성공 소스를 12씬에 순환 배분 (같은 소스는 구간 offset을 달리해 다양성 확보).
    print(f"✂️ 씬별 9:16 cut ({n_scenes}씬)...", file=sys.stderr)
    scene_videos = []
    for i, t in enumerate(main_timings):
        if not sources:
            break
        src = sources[i % len(sources)]
        total = get_video_duration_sec(src)
        dur = scene_durations[i]
        # 같은 소스 재사용 시 회차(i//len)마다 다른 구간을 잡아 겹침 방지
        cycle = i // len(sources)
        base = total * 0.12 + cycle * (dur + 2.0)
        offset = min(max(0.0, base), max(0.0, total - dur - 0.5))
        out_path = scenes_dir / f"s{i:02d}.mp4"
        try:
            cut_scene_clip(src, output=out_path, start_sec=offset, duration_sec=dur, crop_mode="crop")
            scene_videos.append({"scene_id": t["scene_id"], "video_path": str(out_path)})
        except Exception as e:  # noqa: BLE001 — cut 실패 씬은 그라데이션 폴백
            print(f"  씬 #{i} cut 실패: {e}", file=sys.stderr)
    print(f"✅ 씬 클립 {len(scene_videos)}/{n_scenes}개 확보", file=sys.stderr)

    # 5) Remotion 렌더
    print("🎬 Remotion 렌더 중...", file=sys.stderr)
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos or None,
        use_bgm=True,
        scene_timings=timings,
        enable_transitions=False,
        enable_sfx=False,
    )
    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB)", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
