"""국민의힘 '장동혁 거취' 내전 — 정치쇼츠 V2 (지도부 심판 앵글) 렌더.

6·3 지방선거 참패 → 유의동·오세훈의 장동혁 대표 거취 직격 → 지도부 버티기.
기획안을 ShortsScript로 직접 구성(자동 planner 미사용) → Gemini Charon 뉴스캐스터 TTS
→ 인물별 실영상(장동혁 수락연설 / 소장파 사퇴요구 기자회견 / 유의동 라디오 / 오세훈 참전)
을 씬별 9:16 컷(proportional, 프리즈 방지) → Remotion 렌더. outro(scene_id -1) 억제.

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_gukhim_naebun.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260708_gukhim_naebun")
SOURCE_CHANNEL = "연합뉴스TV / MBC 시선집중 / 중앙 신통방통"
SOURCE_TITLE = "6·3 지방선거 참패 후 '장동혁 거취' 내전"

# 인물별 소스 영상 (프레임 육안 검증 완료).
SRC = {
    "jang_face": WORK_DIR / "src_jang3.mp4",  # 장동혁 신임 당대표 수락연설 (본인 얼굴)
    "jang_out": WORK_DIR / "src_jang.mp4",    # 소장파 "장동혁 사퇴하라" 기자회견 (심판 b-roll)
    "yu": WORK_DIR / "src_yu.mp4",            # 유의동 평택을 당선인 라디오 인터뷰
    "oh": WORK_DIR / "src_oh.mp4",            # 오세훈 "장동혁 물러나라" 참전
}
# 씬별 (인물키, 시작 위치 비율) — TTS에서 언급되는 인물의 영상으로 매핑.
# 같은 소스를 여러 씬이 쓰면 offset 비율을 달리해 동일 프레임 반복 방지.
SCENE_SOURCE = [
    ("jang_face", 0.35),  # S0 훅: 당대표는 안 내려온다 (장동혁)
    ("jang_face", 0.62),  # S1 참패 (장동혁)
    ("yu", 0.45),         # S2 유의동 직격
    ("oh", 0.45),         # S3 오세훈 가세
    ("jang_out", 0.30),   # S4 지도부 버티기 (소장파 사퇴요구)
    ("jang_out", 0.62),   # S5 심판 논평 (소장파 사퇴요구)
    ("jang_face", 0.82),  # S6 CTA (장동혁)
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

# ── 씬 정의 (지도부 심판 앵글, V2 자막색) ─────────────────────────────
# color: white=기본 / blue=인용 / red=충돌·비판 / yellow=훅·논평강조
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="지방선거 참패\n당대표는 안 내려온다",
        voice="지방선거 참패. 그런데 국민의힘 당대표는, 내려올 생각이 없습니다.",
        hl=("참패", "당대표"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="6·3 지방선거\n국민의힘 완패",
        voice="6월 3일 지방선거에서 국민의힘은 완패했습니다. "
              "민심은 사실상 지도부를 심판한 겁니다.",
        hl=("지방선거", "완패", "심판"),
    ),
    dict(
        type="body", color="red", emph=True,
        text="유의동 직격\n\"장동혁, 거취부터 결단하라\"",
        voice="평택을 재선거를 뚫고 당선된 유의동. 곧장 장동혁 대표를 겨냥해, "
              "거취부터 결단하라고 직격했습니다.",
        hl=("유의동", "장동혁", "거취"),
    ),
    dict(
        type="body", color="red", emph=False,
        text="오세훈도 가세\n\"장동혁은 짐이다\"",
        voice="오세훈도 가세했습니다. 장 대표가 후보들에게 짐이 되고 있다며, "
              "선거 내내 동행유세를 거부했습니다.",
        hl=("오세훈", "짐", "동행유세"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="지도부는 버티기\n\"대안도 없이 흔든다\" 반격",
        voice="하지만 지도부는 사퇴 대신 버티기. 대안도 없이 흔든다며 맞받았고, "
              "당내에선 찌질이라는 막말까지 터졌습니다.",
        hl=("버티기", "찌질이"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="민심은 심판했는데\n지도부만 모른다",
        voice="국민은 이미 심판했는데, 정작 지도부만 그걸 모르는 걸까요. "
              "책임은 사라지고, 내분만 남았습니다.",
        hl=("심판", "지도부", "내분"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="장동혁, 물러나야 할까?\n댓글로 👇",
        voice="장동혁 대표, 지금이라도 물러나야 할까요? "
              "여러분 생각을 댓글로 남겨주세요.",
        hl=("장동혁",),
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
            title="참패에도 안 내려온다…국힘 '장동혁 거취' 내전",
            emotion_type="angry",
            duration=40.0,
            source_url="",
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
    for k, p in SRC.items():
        assert p.exists(), f"소스 없음: {k} -> {p}"
    script = build_script()
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬", flush=True)

    print("🎙️ Gemini Charon TTS 합성 중 (뉴스캐스터 톤)...", flush=True)
    try:
        from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            output_dir=WORK_DIR,
            voice_name="Charon",
            style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
            temperature=0.5,
            include_outro=False,
        )
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Gemini TTS 실패({e}) → edge-tts 폴백", flush=True)
        from src.tts.tts_generator import generate_voice_with_timing
        audio_path, timings = generate_voice_with_timing(
            script, output_dir=WORK_DIR, include_outro=False,
        )

    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=WORK_DIR)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    print(f"✅ 합성·정렬 완료: {tts_total_ms/1000:.1f}s, {len(main_timings)}씬", flush=True)

    print("✂️ 씬 클립 9:16 컷 (인물별 소스)...", flush=True)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    dur_cache = {k: _probe_dur(p) for k, p in SRC.items()}
    ts = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        key, frac = SCENE_SOURCE[sid]
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
