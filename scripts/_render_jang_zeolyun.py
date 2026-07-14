"""장동혁 '절윤 거부 → 제명 위기' — 정치쇼츠 V2 (리더십 옹호 앵글) 렌더.

서사 아크: 2월 절연 거부(원칙) → 소장파 공격 → 7월 조경태 제명·출당 요구
        → "흔들린 건 리더가 아니라 당" (역공·옹호).

기획안을 ShortsScript로 직접 구성(자동 planner 미사용)
→ Gemini Charon 뉴스캐스터 TTS(씬별 타이밍) + 무음 정렬
→ 인물별 실영상(장동혁 YTN / 조경태 MBN 현장영상 / 윤석열 KBS 선고)을 씬별 9:16 컷
→ Remotion 렌더(political 포맷, outro 억제, SFX/트랜지션 OFF).

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_jang_zeolyun.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260709_jang_zeolyun")

# 인물별 소스 영상 (프레임 육안 검증 완료).
SRC = {
    "jang": WORK_DIR / "src_jang.mp4",   # YTN 장동혁 '무죄추정' 발언 (연단 밴드 0.44~0.55)
    "jokt": WORK_DIR / "src_jokt.mp4",   # MBN 조경태 제명·출당 요구 [현장영상]
    "yoon": WORK_DIR / "src_yoon.mp4",   # KBS 윤석열 1심 무기징역 선고 (법정)
}
# 씬별 (인물키, 시작 위치 비율) — 장동혁은 연단 밴드 0.44~0.55만 사용.
SCENE_SOURCE = [
    ("jang", 0.45),   # 0 HOOK: 장동혁 연단 와이드('윤 어게인 선언')
    ("yoon", 0.35),   # 1 S1: 윤석열 무기징역 선고 법정
    ("jang", 0.50),   # 2 S2: 장동혁 클로즈업 + 절연 인용
    ("jokt", 0.32),   # 3 S3: 조경태 제명 요구
    ("jang", 0.47),   # 4 S4: 장동혁 연단
    ("jang", 0.485),  # 5 S5: 장동혁 연단
    ("jang", 0.455),  # 6 CTA: 장동혁 연단
]
FALLBACK_KEY = "jang"


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


# ── 씬 정의 (리더십 옹호 앵글, V2 자막색) ─────────────────────────────
# color: white=기본 / blue=인용 / red=충돌·비판 / yellow=훅·논평강조
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="당 지키려던 대표\n되레 '제명 위기'",
        voice="당을 지키려던 대표가, 되레 제명 위기에 몰렸습니다.",
        hl=("제명 위기",),
    ),
    dict(
        type="body", color="white", emph=False,
        text="2월, 윤 전 대통령\n1심 무기징역",
        voice="지난 2월, 윤 전 대통령이 1심에서 무기징역. "
              "모두가 절연을 외쳤습니다.",
        hl=("무기징역", "절연"),
    ),
    dict(
        type="comment", color="blue", emph=False,
        text="\"절연할 대상은\n갈라치기 세력\"",
        voice="하지만 장동혁은 달랐습니다. 단호하게 절연할 대상은, "
              "오히려 당을 갈라치기하는 세력이라고 맞섰습니다.",
        hl=("장동혁", "갈라치기"),
    ),
    dict(
        type="comment", color="red", emph=True,
        text="7월, 조경태\n\"제명·출당하라\"",
        voice="그리고 7월, 조경태 의원이 칼을 빼들었습니다. "
              "사법부를 부정한 해당행위라며, 대표 제명과 출당을 요구했습니다.",
        hl=("조경태", "제명", "출당"),
    ),
    dict(
        type="comment", color="white", emph=False,
        text="원칙의 대가가\n제명이라면",
        voice="하지만 원칙을 지킨 대가가 제명이라면, "
              "흔들린 건 리더가 아니라 당 그 자체입니다.",
        hl=("원칙", "제명"),
    ),
    dict(
        type="comment", color="yellow", emph=True,
        text="무죄추정, 그리고 단합",
        voice="1심은 끝이 아닙니다. 무죄추정, 그리고 단합. "
              "장동혁이 지키려 한 건 결국 그거였습니다.",
        hl=("무죄추정", "단합"),
    ),
    dict(
        type="comment", color="yellow", emph=True,
        text="원칙인가, 아집인가?\n댓글로 👇",
        voice="원칙인가, 아집인가. 여러분 생각은 댓글로 남겨주세요.",
        hl=("원칙", "아집"),
    ),
]


def build_script() -> ShortsScript:
    scenes = []
    tts_parts = []
    for i, s in enumerate(SCENES):
        scenes.append(Scene(
            id=i,
            timestamp=float(i),
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
            title="당 지키려던 장동혁, 되레 '제명 위기' — 절윤 거부의 부메랑",
            emotion_type="angry",
            duration=40.0,
            source_url="",
            source_type="political_pro",
            source_channel="YTN·MBN·KBS",
            source_title="장동혁 '무죄추정' 발언 / 조경태 제명요구 / 윤석열 선고",
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
            colors=("#1e3a8a", "#0f172a", "#000000"),
        ),
    )


def main() -> int:
    for k, p in SRC.items():
        assert p.exists(), f"소스 없음: {p}"
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
    dur_cache = {k: (_probe_dur(p) if p.exists() else 0.0) for k, p in SRC.items()}
    ts = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        key, frac = SCENE_SOURCE[sid]
        if not SRC[key].exists():
            key = FALLBACK_KEY
        src_path = SRC[key]
        src_dur = dur_cache[key]
        seg_len = (t["end_ms"] - t["start_ms"]) / 1000.0 + 0.6
        seg_len = min(seg_len, 55.0)
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
