"""정치쇼츠 V2 범용 제작 스크립트 (설정 JSON 기반).

지침(memory: political-shorts-v2-production-structure)을 코드로 고정한 재사용 템플릿.
주제·씬·인물 쿼리만 config.json으로 바꾸면 동일 구조로 제작한다.

2단계 CLI:
  # 1) 인물 클립 다운로드 + 검증 프레임 추출 (렌더 전 프레임 육안 확인용)
  PYTHONPATH=. .venv311/bin/python scripts/render_political_v2.py <config.json> download [--force]
  # 2) Gemini Charon TTS → 인물별 씬 컷 → Remotion 렌더
  PYTHONPATH=. .venv311/bin/python scripts/render_political_v2.py <config.json> render

config.json 스키마: scripts/political_v2_configs/README 및 josguk_ilbe.json 예시 참고.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

CUT_MAX_SEC = 55.0        # cut_segment 60s 상한(FR-018) 여유
COLORS = {"white", "blue", "red", "yellow"}
PY = sys.executable       # .venv311/bin/python 로 실행됨


# ── 설정 로드 & 검증 ────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ("slug", "title", "sources", "scenes"):
        if key not in cfg:
            raise ValueError(f"config에 '{key}' 누락")
    for i, sc in enumerate(cfg["scenes"]):
        if sc.get("color", "white") not in COLORS:
            raise ValueError(f"scene[{i}] color 잘못됨: {sc.get('color')} (허용: {COLORS})")
        if sc["source"] not in cfg["sources"]:
            raise ValueError(f"scene[{i}] source '{sc['source']}' 가 sources에 없음")
        if not sc.get("voice"):
            raise ValueError(f"scene[{i}] voice(나레이션) 비어있음")
    return cfg


def work_dir(cfg: dict) -> Path:
    d = Path("data/political_pro") / cfg["slug"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def src_path(wd: Path, key: str) -> Path:
    return wd / f"src_{key}.mp4"


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


# ── 1단계: 다운로드 + 검증 프레임 ──────────────────────────────────
def cmd_download(cfg: dict, force: bool) -> int:
    wd = work_dir(cfg)
    verify_dir = wd / "_verify"
    verify_dir.mkdir(exist_ok=True)
    for key, spec in cfg["sources"].items():
        out = src_path(wd, key)
        if out.exists() and not force:
            print(f"⏭️  {key}: 이미 있음 (--force 로 재다운로드)", flush=True)
        else:
            _download_source(key, spec, out)
        if out.exists():
            dur = _probe_dur(out)
            frac = spec.get("verify_frac", 0.4)
            frame = verify_dir / f"{key}.png"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", str(max(1.0, dur * frac)),
                 "-i", str(out), "-frames:v", "1", str(frame)],
                check=False,
            )
            print(f"✅ {key}: {dur:.0f}s → 검증 프레임 {frame}", flush=True)
    print(f"\n🔎 렌더 전 {verify_dir}/ 의 프레임으로 인물이 맞는지 확인하세요.", flush=True)
    return 0


def _download_source(key: str, spec: dict, out: Path) -> None:
    # 기존 파일/파편 제거 → --force-overwrites 만으로는 skip 될 수 있음
    for p in out.parent.glob(f"{out.stem}.*"):
        p.unlink(missing_ok=True)
    if spec.get("url"):
        target = spec["url"]
    else:
        n = spec.get("search_n", 6)
        target = f"ytsearch{n}:{spec['query']}"
    dmax = spec.get("dur_max", 900)
    dmin = spec.get("dur_min", 20)
    print(f"⬇️  {key}: {target}", flush=True)
    subprocess.run(
        [PY, "-m", "yt_dlp", target,
         "--match-filter", f"duration<{dmax} & duration>{dmin}",
         "--max-downloads", "1", "--force-overwrites", "--no-playlist-reverse",
         "-f", "bv*[height<=720]+ba/b[height<=720]", "--merge-output-format", "mp4",
         "--print-to-file", "%(title)s", str(out.with_suffix(".title.txt")),
         "-o", str(out.with_suffix(".%(ext)s"))],
        check=False,
    )
    title_f = out.with_suffix(".title.txt")
    if title_f.exists():
        print(f"    제목: {title_f.read_text(encoding='utf-8').strip()}", flush=True)


# ── 스크립트 구성 ──────────────────────────────────────────────────
def build_script(cfg: dict) -> ShortsScript:
    scenes, parts = [], []
    for i, sc in enumerate(cfg["scenes"]):
        emph = bool(sc.get("emph", False))
        scenes.append(Scene(
            id=i, timestamp=float(i), duration=1.0,
            type=sc.get("type", "comment"),
            text=sc["text"], voice_text=sc["voice"],
            emphasis="high" if emph else "medium",
            highlight_words=tuple(sc.get("hl", ())),
            visual_type="video",
            subtitle_color=sc.get("color", "white"),
            subtitle_emphasis=emph,
            hook=(i == 0),
        ))
        parts.append(sc["voice"])
    return ShortsScript(
        metadata=Metadata(
            title=cfg["title"],
            emotion_type=cfg.get("emotion_type", "angry"),
            duration=float(cfg.get("duration", 40.0)),
            source_url=cfg.get("youtube_url", ""),
            source_type="political_pro",
            source_channel=cfg.get("source_channel", ""),
            source_title=cfg.get("source_title", ""),
            format_type=cfg.get("format_type", "B"),
        ),
        scenes=tuple(scenes),
        audio=AudioConfig(
            tts_script=" ".join(parts),
            voice="ko-KR-SunHiNeural",
            rate=cfg.get("rate", "+0%"),
            pitch="+0Hz",
        ),
        background=BackgroundConfig(
            type="gradient",
            colors=tuple(cfg.get("bg_colors", ("#7f1d1d", "#450a0a", "#000000"))),
        ),
    )


# ── 2단계: TTS → 컷 → 렌더 ─────────────────────────────────────────
def cmd_render(cfg: dict) -> int:
    wd = work_dir(cfg)
    fallback = cfg.get("fallback_source") or next(
        (k for k, s in cfg["sources"].items() if s.get("url")), None
    )
    script = build_script(cfg)
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬", flush=True)

    print("🎙️ Gemini Charon TTS 합성 중 (뉴스캐스터 톤)...", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    audio_path, timings = generate_voice_with_timing_gemini(
        script, output_dir=wd, voice_name="Charon",
        style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
        temperature=0.5, include_outro=False,
    )
    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=wd)
    main = [t for t in timings if t["scene_id"] != -1]
    total_ms = max(t["end_ms"] for t in main)
    print(f"✅ 합성·정렬 완료: {total_ms/1000:.1f}s, {len(main)}씬", flush=True)

    print("✂️ 씬 클립 9:16 컷 (인물별 소스)...", flush=True)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    dur_cache = {k: (_probe_dur(src_path(wd, k)) if src_path(wd, k).exists() else 0.0)
                 for k in cfg["sources"]}
    ts = int(time.time())
    scene_videos = []
    for t in main:
        sid = t["scene_id"]
        sc = cfg["scenes"][sid]
        key = sc["source"]
        if not src_path(wd, key).exists():
            key = fallback
            if key is None or not src_path(wd, key).exists():
                raise FileNotFoundError(f"scene {sid} 소스 없음, 폴백도 없음")
        seg_len = min((t["end_ms"] - t["start_ms"]) / 1000.0 + 0.6, CUT_MAX_SEC)
        d = dur_cache[key]
        start = max(0.0, min(d * sc.get("frac", 0.4), d - seg_len - 0.2))
        out_file = wd / f"scene_{ts}_{sid:02d}.mp4"
        cut_segment(input_path=src_path(wd, key), output_path=out_file,
                    start_sec=start, end_sec=min(start + seg_len, d), mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
        print(f"   S{sid} ← {key} [{start:.1f}~{min(start+seg_len, d):.1f}]", flush=True)

    print("🎬 Remotion 렌더 중...", flush=True)
    from src.video.renderer import render_video
    mp4 = render_video(
        script, audio_path=audio_path, scene_videos=scene_videos,
        scene_timings=timings, use_bgm=True,
        enable_transitions=False, enable_sfx=False, output_dir=wd,
    )
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size/1024/1024:.1f}MB)", flush=True)
    print(str(mp4))
    return 0


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[2] not in ("download", "render"):
        print(__doc__)
        return 2
    cfg = load_config(Path(sys.argv[1]))
    if sys.argv[2] == "download":
        return cmd_download(cfg, force=("--force" in sys.argv))
    return cmd_render(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
