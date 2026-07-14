"""안규백 국방장관 '탈영 의혹' — 정치쇼츠 V2 (비판 앵글) 렌더.

⚠️ 법적 프레이밍: 본 사안은 **수사 중인 '의혹'**이며 본인이 부인한다. 모든 문장을
'의혹/주장/해명/수사 중'으로 귀속 처리하고, 명예훼손 방어를 위해 본인 반론(S4)을
반드시 포함한다. '탈영병이다'라는 단정은 금지.

기획안을 ShortsScript로 직접 구성(자동 planner 미사용) → Charon 뉴스캐스터 TTS
씬별 타이밍 합성 → 인물별 유튜브 소스를 9:16 컷(proportional, 프리즈 방지)
→ Remotion 렌더. political 포맷에 맞춰 outro(scene_id -1) 억제.

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_ahn_desertion.py

사전 준비(영상 소스 다운로드, 인물별):
  .venv311/bin/python -m yt_dlp "ytsearch1:안규백 국방장관 인사청문회" \
    --match-filter "duration>20 & duration<600" --max-downloads 1 \
    -o "data/political_pro/20260709_ahn_desertion/src_ahn.%(ext)s" --force-overwrites
  # 한기호 기자회견 / 한동훈 발언 / 종합 뉴스 클립도 동일 방식으로.
  # ⚠️ 렌더 전 각 클립에서 프레임 1장 추출해 인물 육안 검증 필수.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260709_ahn_desertion")

# 인물별 소스 영상 (없으면 종합 뉴스 클립 news 로 폴백).
# 프레임 육안 검증 완료(2026-07-10):
#   ahn   = src_ahn2 (안규백 국방위 인사청문회 모두발언, 전주MBC) ✅
#   hankh = src_hankh (국회 회견 현장영상, 의혹 제기측) ✅
#   handh = src_handh (한동훈, THE FACT) ✅
SRC = {
    "ahn": WORK_DIR / "src_ahn2.mp4",      # 안규백 본인 발언 (검증됨)
    "hankh": WORK_DIR / "src_hankh.mp4",   # 의혹 제기측 회견
    "handh": WORK_DIR / "src_handh.mp4",   # 한동훈 (야권 총공세)
    "news": WORK_DIR / "src_news.mp4",     # 채널A 종합 뉴스 (폴백)
}

# 씬별 (인물키, 시작 위치 비율) — TTS에서 언급되는 인물의 영상으로 매핑.
# 같은 소스를 여러 씬이 쓰면 offset 비율을 달리해 동일 프레임 반복 방지.
# ahn offset은 모두발언(본인 발화) 구간 0.30~0.58 내로 한정.
SCENE_SOURCE = [
    ("ahn", 0.30),     # S0 훅: 국방장관 탈영 의혹 (안규백)
    ("ahn", 0.42),     # S1 팩트: 22개월 복무 (안규백)
    ("hankh", 0.35),   # S2 의혹 제기 (한기호·김영수)
    ("hankh", 0.60),   # S3 헌병 구금 의혹 (한기호)
    ("ahn", 0.52),     # S4 본인 해명 (안규백)
    ("handh", 0.30),   # S5 야권 총공세 + 수사 (한동훈)
    ("ahn", 0.58),     # S6 CTA (안규백)
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


# ── 씬 정의 (비판 앵글, 전 문장 '의혹/주장/해명/수사' 귀속) ───────────────
# color: white=기본 / blue=인용·해명 / red=충돌·의혹 / yellow=훅·논평강조
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="국방부 장관이\n'탈영 의혹'?",
        voice="대한민국 국방부 장관이, 정작 본인은 탈영 의혹에 휩싸였습니다.",
        hl=("국방부 장관", "탈영 의혹"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="방위병 평균 14개월인데\n안규백은 22개월 복무",
        voice="1980년대 방위병 평균 복무는 열네 달. 그런데 안규백 장관의 병역 "
              "기록은 스물두 달, 여덟 달이 더 깁니다.",
        hl=("14개월", "22개월"),
    ),
    dict(
        type="comment", color="red", emph=True,
        text="한기호·김영수\n\"7개월 무단이탈\" 주장",
        voice="국민의힘 한기호 의원과 김영수 소장은, 안 장관이 1984년 복무 중 "
              "약 일곱 달을 무단으로 이탈했다고 주장했습니다.",
        hl=("한기호", "무단이탈", "주장"),
    ),
    dict(
        type="comment", color="red", emph=False,
        text="\"헌병에 체포·30일 구금\"\n의혹 제기",
        voice="심지어 헌병에 체포돼 삼십 일간 구금됐다는 의혹까지 제기됐습니다.",
        hl=("헌병", "30일 구금", "의혹"),
    ),
    dict(
        type="comment", color="blue", emph=False,
        text="安 \"병무 행정 착오\"\n\"어머니가 점심 제공한 일\"",
        voice="안 장관은 병무 행정 착오라며, 중대장 요청으로 어머니가 병사들에게 "
              "점심을 제공한 일로 조사받았을 뿐 탈영은 없었다고 해명했습니다.",
        hl=("행정 착오", "해명"),
    ),
    dict(
        type="comment", color="red", emph=True,
        text="한동훈 총공세\n경찰, 위증 혐의 수사 착수",
        voice="한동훈 등 야권은 병적기록을 공개하라 총공세에 나섰고, 경찰은 국회 "
              "위증 혐의로 수사에 착수했습니다.",
        hl=("한동훈", "위증 혐의", "수사"),
    ),
    dict(
        type="comment", color="yellow", emph=True,
        text="행정 착오? 탈영 은폐?\n병적기록이 답한다 👇",
        voice="단순 행정 착오일까요, 감춰진 탈영일까요. 진실은 병적기록 공개에 "
              "달렸습니다. 여러분 생각을 댓글로 남겨주세요.",
        hl=("행정 착오", "탈영", "병적기록"),
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
            title="국방장관 안규백, '탈영 의혹' 22개월의 미스터리",
            emotion_type="angry",
            duration=40.0,
            source_url="",
            source_type="political_pro",
            source_channel="종합 뉴스",
            source_title="안규백 국방장관 탈영 의혹",
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
    assert SRC["news"].exists() or any(SRC[k].exists() for k in SRC), \
        f"소스 영상이 하나도 없음: {WORK_DIR} (yt_dlp로 먼저 다운로드)"
    script = build_script()
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬", flush=True)

    # Charon(Gemini) TTS가 문장 사이 비정상 침묵(214s 중 158s)을 생성해 edge-tts로
    # 전환(2026-07-10). script.audio = ko-KR-SunHiNeural +15%, 씬별 타이밍 정확.
    print("🎙️ edge-tts 합성 중 (SunHiNeural, 씬별 타이밍)...", flush=True)
    from src.tts.edge_tts_generator import generate_voice_with_timing
    audio_path, timings = generate_voice_with_timing(script, output_dir=WORK_DIR)
    main_timings = [t for t in timings if t["scene_id"] != -1]
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    print(f"✅ 합성·정렬 완료: {tts_total_ms/1000:.1f}s, {len(main_timings)}씬", flush=True)

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
            key = "news"   # 인물 클립 없으면 종합 클립 폴백
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
