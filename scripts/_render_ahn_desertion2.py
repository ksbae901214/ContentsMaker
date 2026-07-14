"""안규백 국방장관 '탈영 의혹' 2탄 — 후속(탄핵청원 30만·병적기록 미공개) 비판 앵글.

⚠️ 법적 프레이밍: 수사 중 '의혹'이며 본인 부인. 전 문장 의혹/주장/촉구/해명으로
귀속. 본인 반론(S4) 필수 포함. '탈영병 단정' 금지.

1탄(20260709_ahn_desertion) 검증 완료 클립 재활용:
  ahn   = src_ahn2 (안규백 국방위 인사청문회 모두발언) ✅
  handh = src_handh (한동훈, 병적기록 공개 촉구) ✅
  news  = src_news (채널A — 국방부 대변인 브리핑 포함) ✅
신규: protest = src_protest (탄핵청원/사관학교 총궐기 등 압박 실감용, 폴백=news)

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_ahn_desertion2.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260709_ahn_desertion")   # 1탄과 자산 공유

SRC = {
    "ahn": WORK_DIR / "src_ahn2.mp4",
    "handh": WORK_DIR / "src_handh.mp4",
    "news": WORK_DIR / "src_news.mp4",
    "protest": WORK_DIR / "src_protest.mp4",
}

# 씬별 (인물키, 시작 위치 비율). ahn offset은 본인 발화 구간 0.30~0.58로 한정.
SCENE_SOURCE = [
    ("ahn", 0.30),      # S0 훅: 그 후, 탄핵청원 30만
    ("ahn", 0.42),      # S1 재점화 브릿지
    ("handh", 0.30),    # S2 국민의힘/한동훈 사퇴·공개 촉구
    ("news", 0.30),     # S3 국방부 대변인 원론 반복·미공개
    ("ahn", 0.52),      # S4 본인 해명 (피해자)
    ("protest", 0.40),  # S5 겹악재(탄핵청원·통폐합) — 없으면 news 폴백
    ("ahn", 0.58),      # S6 CTA
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


# color: white=기본 / blue=해명 / red=의혹·충돌 / yellow=훅·CTA
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="탈영 의혹 그 후\n탄핵청원 30만 돌파",
        voice="안규백 국방장관 탈영 의혹, 그 후. 사퇴를 요구하는 탄핵 청원이 "
              "삼십만을 넘어섰습니다.",
        hl=("탈영 의혹", "탄핵청원 30만"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="방위병 22개월\n'7개월 군무이탈' 의혹 재점화",
        voice="방위병 스물두 달 복무 기록. 약 일곱 달을 무단으로 이탈했다는 의혹이 "
              "다시 불붙었습니다.",
        hl=("22개월", "군무이탈"),
    ),
    dict(
        type="comment", color="red", emph=True,
        text="국민의힘 \"공개하면 끝날 일\n즉각 사퇴하라\"",
        voice="국민의힘은 병적기록부만 공개하면 끝날 일이라며, 안 장관의 즉각 사퇴를 "
              "촉구했습니다.",
        hl=("국민의힘", "사퇴"),
    ),
    dict(
        type="comment", color="red", emph=False,
        text="국방부는 \"정상 복무\"만 반복\n병적기록은 미공개",
        voice="그런데 국방부는 정상적으로 복무를 마쳤다는 말만 반복할 뿐, 정작 "
              "병적기록은 공개하지 않고 있습니다.",
        hl=("국방부", "병적기록", "미공개"),
    ),
    dict(
        type="comment", color="blue", emph=False,
        text="安 \"군무이탈 없다\n나는 병무 행정 피해자\"",
        voice="안 장관은 군무이탈 사실은 없다며, 자신은 오히려 병무 행정의 피해자라는 "
              "해명을 고수하고 있습니다.",
        hl=("군무이탈 없다", "피해자"),
    ),
    dict(
        type="comment", color="red", emph=True,
        text="탄핵청원 30만\n사관학교 통폐합까지 겹악재",
        voice="탄핵 청원 삼십만에, 사관학교 통폐합 논란까지. 안 장관을 향한 압박이 "
              "겹겹이 쌓이고 있습니다.",
        hl=("탄핵청원 30만", "겹악재"),
    ),
    dict(
        type="comment", color="yellow", emph=True,
        text="공개하면 끝날 일\n왜 안 열까? 👇",
        voice="공개하면 끝날 일, 왜 열지 않을까요? 여러분 생각을 댓글로 남겨주세요.",
        hl=("공개", "왜"),
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
            title="안규백 탈영 의혹 그 후, 탄핵청원 30만 돌파",
            emotion_type="angry",
            duration=43.0,
            source_url="",
            source_type="political_pro",
            source_channel="종합 뉴스",
            source_title="안규백 국방장관 탈영 의혹 후속",
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
    assert SRC["ahn"].exists(), f"안규백 소스 없음: {SRC['ahn']}"
    script = build_script()
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬", flush=True)

    print("🎙️ edge-tts 합성 중 (SunHiNeural, 씬별 타이밍)...", flush=True)
    from src.tts.edge_tts_generator import generate_voice_with_timing
    audio_path, timings = generate_voice_with_timing(script, output_dir=WORK_DIR)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    print(f"✅ 합성 완료: {tts_total_ms/1000:.1f}s, {len(main_timings)}씬", flush=True)

    print("✂️ 씬 클립 9:16 컷 (인물별 소스)...", flush=True)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    dur_cache: dict[str, float] = {}
    for k, p in SRC.items():
        dur_cache[k] = _probe_dur(p) if p.exists() else 0.0
    ts = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        key, frac = SCENE_SOURCE[sid]
        if not SRC[key].exists():
            key = "news"   # 폴백
        src_path = SRC[key]
        src_dur = dur_cache[key]
        seg_len = (t["end_ms"] - t["start_ms"]) / 1000.0 + 0.6
        seg_len = min(seg_len, 55.0)
        start = max(0.0, min(src_dur * frac, src_dur - seg_len - 0.2))
        end = min(start + seg_len, src_dur)
        out_file = WORK_DIR / f"s2_scene_{ts}_{sid:02d}.mp4"
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
