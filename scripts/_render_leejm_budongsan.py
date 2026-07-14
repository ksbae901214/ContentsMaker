"""이재명 정부 부동산 '규제의 역설' — 정치쇼츠 V2 (비판 앵글) 렌더.

A(규제의 역설: 집값 오히려 폭등) + B(여론조사 수치) 축.
기획안을 ShortsScript로 직접 구성 → Gemini Charon 뉴스캐스터 TTS(씬별 타이밍)
→ 인물별 실영상 9:16 컷(proportional, 프리즈 방지) → Remotion 렌더.
political 포맷: outro(scene_id -1) 억제, SFX/트랜지션 OFF.

usage: PYTHONPATH=. .venv311/bin/python scripts/_render_leejm_budongsan.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

WORK_DIR = Path("data/political_pro/20260714_leejm_budongsan")
YT_URL = "https://www.youtube.com/watch?v=zIQwcS8REjo"
SOURCE_CHANNEL = "춘천MBC NEWS"
SOURCE_TITLE = "이재명 대통령, 부동산 정책 국무회의 발언 / 서울 아파트값 상승 (KBS)"

# 인물/자료 소스. leejm=이재명 국무회의(검증완료), apt=서울 아파트값 뉴스.
SRC = {
    "leejm": WORK_DIR / "src_leejm.mp4",   # 이재명 대통령 (검증: 15/30/60/90s 본인)
    "apt": WORK_DIR / "src_apt.mp4",       # 서울 아파트값 상승 KBS 뉴스
}
# 씬별 (소스키, 시작 위치 비율). leejm 재사용 씬은 offset을 벌려 프레임 반복 방지.
SCENE_SOURCE = [
    ("leejm", 0.05),   # S0 훅: 집값 잡겠다더니
    ("leejm", 0.11),   # S1 규제 폭탄
    ("apt",   0.10),   # S2 규제의 역설(집값 폭등) — 아파트 뉴스
    ("apt",   0.50),   # S3 부작용(매물잠김·양극화) — 아파트 뉴스
    ("leejm", 0.17),   # S4 여론조사(잘못 46%)
    ("leejm", 0.23),   # S5 국민 55% "더 오른다"
    ("leejm", 0.29),   # S6 CTA
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


# ── 씬 정의 (비판 앵글, V2 자막색) ──────────────────────────────────
# color: white=기본 / blue=인용·수치 / red=충돌·비판 / yellow=훅·논평강조
# ⚠️ type은 title/body만 사용 (comment는 "Best Comment" 라벨 렌더됨)
SCENES = [
    dict(
        type="title", color="yellow", emph=True,
        text="집값 잡겠다더니\n서울 10% 폭등",
        voice="집값을 잡겠다던 이재명 정부. 1년 만에 서울 아파트값이 10퍼센트 넘게 뛰었습니다.",
        hl=("집값", "10% 폭등"),
    ),
    dict(
        type="body", color="white", emph=False,
        text="대출 6억 제한\n서울 전역 규제지역",
        voice="대출은 6억으로 묶고, 서울 전역을 규제지역으로 지정했죠. "
              "규제 폭탄을 쏟아부었습니다.",
        hl=("대출 6억", "규제지역"),
    ),
    dict(
        type="body", color="red", emph=True,
        text="규제의 역설\n집값은 더 올랐다",
        voice="그런데 결과는 정반대. 서울 아파트값은 10.47퍼센트 올라, "
              "직전 1년보다 더 가파르게 뛰었습니다.",
        hl=("규제의 역설", "더"),
    ),
    dict(
        type="body", color="red", emph=False,
        text="매물 잠김·양극화\n부작용만 남았다",
        voice="대출을 막고 실거주까지 강제하자, 매물은 잠기고 지역 양극화만 커졌습니다.",
        hl=("매물 잠김", "양극화"),
    ),
    dict(
        type="body", color="blue", emph=False,
        text="갤럽 조사\n잘못한다 46% vs 잘한다 26%",
        voice="국민 평가는 냉정했습니다. 갤럽 조사에서 잘못한다 46퍼센트, "
              "잘한다는 26퍼센트에 그쳤습니다.",
        hl=("46%", "26%"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="국민 55%\n\"집값 더 오른다\"",
        voice="게다가 국민 55퍼센트는 앞으로 집값이 더 오를 거라 답했습니다. "
              "정책을 못 믿는다는 뜻이죠.",
        hl=("55%", "더 오른다"),
    ),
    dict(
        type="body", color="yellow", emph=True,
        text="규제만 쏟고\n집값은 못 잡았다\n댓글로 👇",
        voice="규제만 쏟아내고 집값은 못 잡은 1년. 여러분 생각은 어떤가요? "
              "댓글로 남겨주세요.",
        hl=("규제만", "못 잡았다"),
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
            title="집값 잡겠다더니 서울 10% 폭등…국민 46% '낙제점'",
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
    assert SRC["leejm"].exists(), f"소스 없음: {SRC['leejm']}"
    assert SRC["apt"].exists(), f"소스 없음: {SRC['apt']}"
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
    dur_cache: dict[str, float] = {k: _probe_dur(p) for k, p in SRC.items()}
    ts = int(time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        key, frac = SCENE_SOURCE[sid]
        if not SRC[key].exists():
            key = "leejm"
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
