"""한동훈 제명 → 10만 규탄집회 → 7월 친한계 무더기 징계 — 정치쇼츠 V2 (장동혁 징계정치 비판).

통합 서사: 1월 윤리위 제명 → 1/31 여의도 10만 규탄집회 → 장동혁 버티기
→ 7월 친한계 60건+ 징계·복당 영구금지. 대립 서사체·탈보도체, 지도부 심판 앵글.
ShortsScript 직접 구성 → Gemini Charon 뉴스캐스터 TTS
→ 인물별 실영상(한동훈 / 규탄집회 / 장동혁 수락연설 / 소장파 사퇴요구)을
씬별 9:16 컷(proportional, 프리즈 방지) → Remotion 렌더. outro(scene_id -1) 억제.

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_hanjm_jemyeong.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260708_hanjm_jemyeong")
SOURCE_CHANNEL = "KBS / YTN / 부산일보TV / 연합뉴스TV"
SOURCE_TITLE = "한동훈 제명·10만 규탄집회 → 7월 친한계 무더기 징계"

# 인물별 소스 영상 (프레임 육안 검증 완료).
SRC = {
    "han": WORK_DIR / "src_han.mp4",            # 한동훈 전 대표 (부산일보TV, 본인 얼굴)
    "rally": WORK_DIR / "src_rally.mp4",        # 제명 규탄 집회 (KBS, "제명 철회하라" 피켓)
    "jang_face": WORK_DIR / "src_jang_face.mp4",  # 장동혁 신임 당대표 수락연설 (본인)
    "jang_out": WORK_DIR / "src_jang_out.mp4",  # 소장파 "장동혁 사퇴하라" 기자회견 (내분 b-roll)
}
# 씬별 (인물키, 시작 위치 비율) — TTS에서 언급되는 인물/현장 영상으로 매핑.
SCENE_SOURCE = [
    ("han", 0.40),        # S0 훅: 제명당한 한동훈
    ("jang_face", 0.35),  # S1 제명 확정 (지도부)
    ("rally", 0.50),      # S2 10만 규탄집회
    ("jang_face", 0.60),  # S3 장동혁 버티기
    ("jang_face", 0.80),  # S4 7월 친한계 징계 (장동혁 발언)
    ("jang_out", 0.45),   # S5 논평: 숙청·계파전쟁 (사퇴요구 현장)
    ("han", 0.70),        # S6 CTA: 한동훈
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

# ── 씬 정의 (장동혁 징계정치 비판 앵글, V2 자막색) ─────────────────────
# color: white=기본 / blue=인용 / red=충돌·비판 / yellow=훅·논평강조
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="제명당한 한동훈\n10만이 들고일어났다",
        voice="제명당한 한동훈. 10만 지지자가 거리로 쏟아졌습니다.",
        hl=("제명", "10만"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="1월, 윤리위가\n한동훈 '제명' 확정",
        voice="지난 1월, 국민의힘 윤리위가 한동훈 전 대표를 제명했습니다. "
              "가족 당원게시판 사건이 명분이었습니다.",
        hl=("윤리위", "제명"),
    ),
    dict(
        type="body", color="red", emph=True,
        text="여의도 10만 집결\n\"제명 철회하라\"",
        voice="1월 31일, 여의도공원에 10만 인파가 모였습니다. "
              "제명을 철회하라는 함성이 터졌습니다.",
        hl=("여의도", "10만", "철회"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="그래도 장동혁은\n\"사퇴 없다\"",
        voice="하지만 장동혁 대표는 꿈쩍하지 않았습니다. 사퇴는 없다며, "
              "오히려 징계의 칼을 다시 잡았습니다.",
        hl=("장동혁", "사퇴", "징계"),
    ),
    dict(
        type="body", color="red", emph=True,
        text="7월, 친한계 무더기 징계\n\"복당 영구금지\"",
        voice="그리고 7월, 친한동훈계 예순여 건이 징계 심의에 올랐습니다. "
              "장 대표는 당헌을 고쳐서라도 복당을 영구 금지하겠다고 했습니다.",
        hl=("친한동훈계", "징계", "영구 금지"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="제명·징계로 지운 자리\n남은 건 계파 전쟁",
        voice="반대파를 제명하고 징계로 지워도, 남는 건 갈라진 당. "
              "심판이라 쓰고, 숙청이라 읽힙니다.",
        hl=("제명", "징계", "숙청"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="한동훈 제명, 정당했나?\n댓글로 👇",
        voice="한동훈 제명, 과연 정당했을까요? "
              "여러분 생각을 댓글로 남겨주세요.",
        hl=("한동훈", "제명"),
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
            title="10만이 들고일어났다…한동훈 제명·장동혁의 '징계정치'",
            emotion_type="angry",
            duration=42.0,
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
