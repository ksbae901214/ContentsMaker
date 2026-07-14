"""장윤기 사건 — '경찰이 살인 덮었는데, 그 경찰에 수사권을 몰아주나' 반문 앵글 (정치쇼츠 V2).

⚠️ 법적 프레이밍: 경찰 은폐는 '의혹/혐의', 팀장 '증거인멸 혐의로 구속'·지휘부 '대기발령'은
   보도된 사실. 아버지 증거물 폐기는 '정황'으로 귀속. 반문(제정신인가)은 공적 입법정책에
   대한 논평(의견). 장윤기는 살해범(구속 기소)이지만 경찰 '공범'은 '분노/의혹'으로 귀속.

핵심 팩트(교차검증):
  - 담당 강력팀장 '증거인멸 혐의' 구속, 서장 등 지휘부 6명 대기발령 (서울신문 07/07·07/09)
  - 범인 아버지 현직 경찰, 원룸 증거물(리얼돌·휴대전화) 폐기 정황 (서울신문 07/01)
  - 與 민주당, '장윤기 사건에도' 검찰 보완수사권 폐지 발의 (파이낸셜뉴스 07/09)
  - 김민석 국무총리 "보완수사권 폐지=정부 기본 입장" (06/25), 10월 공소청·중수청 출범 전 수사 경찰 일원화
  - 법조계·사법부·대한변협 "부실·유착 수사 거를 마지막 장치" 우려 (헤럴드경제 등)

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_jang_police_power.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260713_jang_police_power")

# 인물별 소스 영상 (없으면 종합 뉴스 클립으로 폴백).
SRC = {
    "jang": WORK_DIR / "src_jang.mp4",     # 장윤기 사건 뉴스 (광주 여고생 살해·경찰)
    "father": WORK_DIR / "src_father.mp4",  # 아버지 현직경찰 증거인멸/폐기 보도
    "dp": WORK_DIR / "src_dp.mp4",          # 민주당 보완수사권 폐지 (국회/의총/원내대표)
    "kms": WORK_DIR / "src_kms.mp4",        # 김민석 국무총리
    "law": WORK_DIR / "src_law.mp4",        # 법조계/대한변협 우려
    "news": WORK_DIR / "src_news.mp4",      # 종합 폴백
}

# 씬별 (인물키, 시작 위치 비율) — TTS에서 언급되는 인물의 영상으로 매핑.
# 같은 소스를 여러 씬이 쓰면 offset을 달리해 동일 프레임 반복 방지.
SCENE_SOURCE = [
    ("jang", 0.15),    # S0 훅
    ("jang", 0.42),    # S1 사건 팩트
    ("father", 0.30),  # S2 아버지 현직경찰 (폴백 jang)
    ("dp", 0.30),      # S3 與 보완수사권 폐지 발의
    ("kms", 0.30),     # S4 김민석 총리
    ("law", 0.30),     # S5 법조계·변협 경고 (폴백 news)
    ("jang", 0.62),    # S6 CTA 반문
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


# ── 씬 정의 (반문 앵글, V2 자막색) ──────────────────────────────────
# color: white=기본 / blue=인용 / red=충돌·비판 / yellow=훅·논평강조
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="여고생 살인 덮은 경찰\n그 경찰에 수사권 몰아준다?",
        voice="여고생 살인을 덮은 경찰. 그런데 정부는, 바로 그 경찰에게 "
              "수사권을 몰아주려 합니다.",
        hl=("살인 덮은 경찰", "수사권"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="장윤기 사건\n강력팀장 '증거인멸' 구속",
        voice="광주 여고생 살해범 장윤기 사건. 담당 강력팀장이 증거를 인멸한 "
              "혐의로 구속됐고, 서장 등 지휘부 여섯 명이 대기발령됐습니다.",
        hl=("장윤기", "증거인멸", "구속"),
    ),
    dict(
        type="body", color="red", emph=True,
        text="범인 아버지가 현직 경찰\n증거물 빼돌린 정황",
        voice="범인의 아버지는 현직 경찰이었습니다. 아들 방의 증거물을 챙겨 "
              "버린 정황까지 드러나, 경찰이 공범이냐는 분노가 터졌습니다.",
        hl=("현직 경찰", "공범"),
    ),
    dict(
        type="body", color="red", emph=True,
        text="바로 그때, 與 '보완수사권 폐지' 발의",
        voice="그런데 바로 이 시점에, 여당은 검찰의 보완수사권을 없애는 법안을 "
              "발의했습니다. 경찰의 부실 수사를 검찰이 다시 걸러내던, 마지막 장치입니다.",
        hl=("보완수사권 폐지", "마지막 장치"),
    ),
    dict(
        type="body", color="red", emph=False,
        text="김민석 총리 \"폐지가 정부 입장\"\n10월, 수사권 경찰로 일원화",
        voice="김민석 국무총리는 보완수사권 폐지가 정부의 기본 입장이라고 "
              "못박았습니다. 오는 시월, 수사권을 경찰로 일원화하겠다는 겁니다.",
        hl=("김민석", "정부 입장", "일원화"),
    ),
    dict(
        type="body", color="blue", emph=False,
        text="법조계·사법부·변협 경고\n\"부실수사 거를 장치 사라진다\"",
        voice="법조계도, 사법부도, 대한변협도 경고합니다. 이 장치가 사라지면, "
              "장윤기 사건 같은 부실 수사를 걸러낼 방법이 없어진다고.",
        hl=("법조계", "변협", "사라진다"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="살인 덮은 경찰에\n수사권을 몰아준다? 👇",
        voice="살인을 덮은 경찰에게, 오히려 수사권을 몰아준다. 이게 정상입니까? "
              "여러분 생각을 댓글로 남겨주세요.",
        hl=("몰아준다", "정상입니까"),
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
            title="여고생 살인 덮은 경찰… 정부는 그 경찰에 수사권을 몰아준다?",
            emotion_type="angry",
            duration=44.0,
            source_url="",
            source_type="political_pro",
            source_channel="종합 뉴스",
            source_title="장윤기 사건 경찰 은폐 논란 속 보완수사권 폐지",
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
    assert SRC["news"].exists() or SRC["jang"].exists(), "폴백 소스 없음"
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
        from src.tts.silence_align import align_timings_to_silence
        audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=WORK_DIR)
        print("   → Charon 합성·정렬 완료", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠️ Charon 실패({e}) → edge-tts 폴백", flush=True)
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
            key = "news" if SRC["news"].exists() else "jang"   # 폴백
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
