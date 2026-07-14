"""조국 '일베 감별법' 논란 — 정치쇼츠 V2 (조국 비판 앵글) 렌더.

기획안을 ShortsScript로 직접 구성(자동 planner 미사용) → edge-tts 씬별 타이밍 합성
→ 단일 소스 뉴스클립(채널A)을 씬별로 9:16 컷(proportional, 프리즈 방지)
→ Remotion 렌더. political 포맷에 맞춰 outro(scene_id -1) 억제.

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_josguk_ilbe.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260707_josguk_ilbe")
YT_URL = "https://www.youtube.com/watch?v=VSAn-JTZsFA"
SOURCE_CHANNEL = "채널A 김진의돌직구쇼"
SOURCE_TITLE = "'무섭노' 사투리에 때아닌 '일베' 논란"

# 인물별 소스 영상 (없으면 채널A 종합 클립으로 폴백).
SRC = {
    "rescene": WORK_DIR / "src_rescene.mp4",
    "joguk": WORK_DIR / "src_joguk.mp4",
    "leejs": WORK_DIR / "src_leejs.mp4",
    "nkw": WORK_DIR / "src_nkw.mp4",
    "chA": WORK_DIR / "source_chA.mp4",
}
# 씬별 (인물키, 시작 위치 비율) — TTS에서 언급되는 인물의 영상으로 교체.
# 같은 소스를 여러 씬이 쓰면 offset 비율을 달리해 동일 프레임 반복 방지.
SCENE_SOURCE = [
    ("rescene", 0.30),   # S0 훅: '무섭노' (리센느)
    ("rescene", 0.55),   # S1 발단: 거제 아이돌 (리센느)
    ("joguk", 0.40),     # S2 조국 등판
    ("leejs", 0.40),     # S3 이준석 직격
    ("nkw", 0.40),       # S4 나경원 (+조국 맞불)
    ("chA", 0.35),       # S5 논평 (종합)
    ("rescene", 0.75),   # S6 CTA (리센느)
]


def _probe_dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0

# ── 씬 정의 (조국 비판 앵글, V2 자막색) ─────────────────────────────
# color: white=기본 / blue=인용 / red=충돌·비판 / yellow=훅·논평강조
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="'무섭노' 한마디\n조국이 '일베'로 몰았다",
        voice="거제 걸그룹의 무섭노 한마디를, 조국이 일베로 몰았습니다.",
        hl=("무섭노", "일베"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="거제 22살 아이돌\n'무섭노'에 사상검증",
        voice="경남 거제 출신 스물두 살 아이돌. 고향 말로 무섭노라 했다가, "
              "일베 말투냐는 사상검증이 시작됐습니다.",
        hl=("거제", "사상검증"),
    ),
    dict(
        type="comment", color="blue", emph=False,
        text="조국 등판\n\"일베는 기계적으로 '노'\"",
        voice="그러자 조국 전 대표가 등판했습니다. 일베는 표준말 뒤에 기계적으로 노를 붙인다며, "
              "이른바 일베 감별법까지 꺼냈습니다.",
        hl=("조국", "일베 감별법"),
    ),
    dict(
        type="comment", color="red", emph=True,
        text="이준석 직격\n\"죽창 들자던 사람이 사상검증?\"",
        voice="역풍이 터졌습니다. 이준석은, 2019년 죽창 들자던 사람이 "
              "이젠 말끝 하나로 사상을 검증하냐고 직격했습니다.",
        hl=("이준석", "죽창", "사상"),
    ),
    dict(
        type="comment", color="red", emph=False,
        text="나경원 \"검열사회\"\n조국 \"'노'는 혐오표현\" 맞불",
        voice="나경원도 사투리까지 재단하는 검열사회라 비판했지만, "
              "조국은 노는 혐오표현이라며 물러서지 않았습니다.",
        hl=("나경원", "검열사회", "혐오표현"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="재단당한 건 사투리\n표현의 자유 vs 사상검증",
        voice="정작 재단당한 건 평범한 경상도 사투리. "
              "표현의 자유냐, 말끝까지 감별하는 사상검증이냐.",
        hl=("사투리", "표현의 자유", "사상검증"),
    ),
    dict(
        type="comment", color="yellow", emph=True,
        text="당신의 '무섭노'는?\n댓글로 👇",
        voice="당신의 무섭노는 사투리인가요? 댓글로 남겨주세요.",
        hl=("무섭노",),
    ),
]


def build_script() -> ShortsScript:
    scenes = []
    tts_parts = []
    for i, s in enumerate(SCENES):
        scenes.append(Scene(
            id=i,
            timestamp=float(i),   # 명목값; 실제 타이밍은 scene_timings가 구동
            duration=1.0,
            type=s["type"],
            text=s["text"],
            voice_text=s["voice"],
            emphasis="high" if s["emph"] else "medium",
            highlight_words=tuple(s["hl"]),
            visual_type="video",
            subtitle_color=s["color"],
            subtitle_emphasis=s["emph"],
            hook=(i == 0),
        ))
        tts_parts.append(s["voice"])

    return ShortsScript(
        metadata=Metadata(
            title="죽창 들자던 조국, 이젠 말끝으로 '사상검증'",
            emotion_type="angry",
            duration=40.0,
            source_url=YT_URL,
            source_type="political_pro",
            source_channel=SOURCE_CHANNEL,
            source_title=SOURCE_TITLE,
            format_type="B",
        ),
        scenes=tuple(scenes),
        audio=AudioConfig(
            tts_script=" ".join(tts_parts),
            voice="ko-KR-SunHiNeural",
            rate="+15%",
            pitch="+0Hz",
        ),
        background=BackgroundConfig(
            type="gradient",
            colors=("#7f1d1d", "#450a0a", "#000000"),
        ),
    )


def main() -> int:
    assert SRC["chA"].exists(), f"폴백 소스 없음: {SRC['chA']}"
    script = build_script()
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬", flush=True)

    print("🎙️ Gemini Charon TTS 합성 중 (뉴스캐스터 톤)...", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    audio_path, timings = generate_voice_with_timing_gemini(
        script,
        output_dir=WORK_DIR,
        voice_name="Charon",
        style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
        temperature=0.5,
        include_outro=False,
    )
    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=WORK_DIR)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    print(f"✅ 합성·정렬 완료: {tts_total_ms/1000:.1f}s, {len(main_timings)}씬", flush=True)

    print("✂️ 씬 클립 9:16 컷 (인물별 소스)...", flush=True)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    # 소스별 길이 캐시 (폴백: 파일 없으면 채널A 종합 클립)
    dur_cache: dict[str, float] = {}
    for k, p in SRC.items():
        dur_cache[k] = _probe_dur(p) if p.exists() else 0.0
    ts = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        key, frac = SCENE_SOURCE[sid]
        if not SRC[key].exists():
            key = "chA"   # 인물 클립 없으면 종합 클립 폴백
        src_path = SRC[key]
        src_dur = dur_cache[key]
        seg_len = (t["end_ms"] - t["start_ms"]) / 1000.0 + 0.6
        seg_len = min(seg_len, 55.0)                       # 60s 상한(FR-018)
        start = max(0.0, min(src_dur * frac, src_dur - seg_len - 0.2))
        end = min(start + seg_len, src_dur)
        out_file = WORK_DIR / f"scene_{ts}_{sid:02d}.mp4"
        cut_segment(input_path=src_path, output_path=out_file,
                    start_sec=start, end_sec=end, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
        print(f"   S{sid} ← {key} [{start:.1f}~{end:.1f}]", flush=True)
    print(f"✅ 씬 클립 {len(scene_videos)}개 컷 완료", flush=True)

    print("🎬 Remotion 렌더 중...", flush=True)
    from src.video.renderer import render_video
    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        scene_timings=timings,
        use_bgm=True,
        enable_transitions=False,
        enable_sfx=False,
        output_dir=WORK_DIR,
    )
    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB)", flush=True)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
