"""정치쇼츠 V2.1 범용 제작 스크립트 (설정 JSON 기반).

V2(render_political_v2.py)의 구조를 유지하되 조회수 개선(prompt_plan 031)을 반영한
신규 버전. V2 파일은 수정하지 않는다.

V2 대비 변경점:
  1. **훅 씬 원본 육성** — config `hook` 섹션 지정 시 scene 0은 TTS 낭독 대신
     인물의 실제 발언 오디오(mute=False + loudnorm)를 0초에 배치하고
     `yt_title`을 노란 자막으로 오버레이. TTS는 scene 1부터.
     (TTS mp3 앞에 훅 길이만큼 무음 패딩 + 타이밍 시프트 → Remotion 무수정)
  2. **업로드 패키지 자동 생성** — 렌더 완료 시 upload_package.md
     (제목 A/B·설명·해시태그·고정댓글·권장 업로드 시각·썸네일 후보 3장).
  3. scene `type` 기본값 body, `comment` 입력은 body로 강제
     (Blind 잔여물 "Best Comment" 라벨 방지).

2단계 CLI:
  # 1) 인물 클립 다운로드 + 검증 프레임 추출 (렌더 전 프레임 육안 확인용)
  PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_1.py <config.json> download [--force]
  # 2) Gemini Charon TTS → 훅 원본 컷 → 인물별 씬 컷 → Remotion 렌더 → 업로드 패키지
  PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_1.py <config.json> render

config.json 스키마: scripts/political_v2_configs/README.md 의 "V2.1 확장" 섹션 참고.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from scripts.shorts_domain import resolve_bg_colors, resolve_emotion_type
from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

CUT_MAX_SEC = 55.0        # cut_segment 60s 상한(FR-018) 여유
HOOK_MIN_SEC = 1.0        # 훅 원본 클립 최소 길이
# 훅은 실촬영 클립이라 AI 생성 5s 제한(MAX_SCENE_DURATION)이 무관하고,
# 발언이 문장 끝까지 완결되어야 하므로 10s까지 허용 (사용자 피드백 2026-07-14).
HOOK_MAX_SEC = 10.0
COLORS = {"white", "blue", "red", "yellow"}
PY = sys.executable       # .venv311/bin/python 로 실행됨


# ── 설정 로드 & 검증 ────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    from scripts.political_cta import apply_cta
    # 035: cta 블록이 있으면 40% 지점에 tts 씬으로 삽입한 뒤 검증한다
    cfg = apply_cta(json.loads(path.read_text(encoding="utf-8")))
    validate_config(cfg)
    for w in config_warnings(cfg):
        print(f"⚠️ {w}", flush=True)
    return cfg


def config_warnings(cfg: dict) -> list[str]:
    """035 품질 경고 — 길이 캡·CTA 형식·말미 CTA 잔존 (하드 오류 아님).

    V2.2(render_political_v2_2.py)도 이 함수를 재사용한다.
    """
    from scripts.political_cta import lint_cta, trailing_cta_warnings
    from scripts.political_length import length_warnings
    from scripts.shorts_category import resolve_config_category
    from scripts.shorts_domain import domain_warnings
    warnings = list(length_warnings(cfg))
    if cfg.get("cta"):
        warnings.extend(lint_cta(cfg["cta"], resolve_config_category(cfg)))
    warnings.extend(trailing_cta_warnings(cfg))
    warnings.extend(domain_warnings(cfg))     # 036: 도메인 주의어·출처 표기
    return warnings


def validate_config(cfg: dict) -> None:
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
    hook = cfg.get("hook")
    if hook:
        if hook.get("source") not in cfg["sources"]:
            raise ValueError(f"hook.source '{hook.get('source')}' 가 sources에 없음")
        dur = float(hook.get("duration", 3.0))
        if not (HOOK_MIN_SEC <= dur <= HOOK_MAX_SEC):
            raise ValueError(
                f"hook.duration {dur}s 범위 밖 (허용 {HOOK_MIN_SEC}~{HOOK_MAX_SEC}s)")
    # 034: 보도체·해시태그 제목은 렌더 전에 차단 (yt_title_lint: "off" 로 우회)
    from scripts.political_upload_package import gate_yt_title
    gate_yt_title(cfg)
    # 036: category 오타 + 도메인 금지어(경제 투자권유)를 렌더 전에 차단
    from scripts.shorts_category import resolve_config_category
    from scripts.shorts_domain import gate_domain_words
    resolve_config_category(cfg)
    gate_domain_words(cfg)


def scene_type(sc: dict) -> str:
    """comment 는 body 로 강제 — SceneText 의 'Best Comment' 라벨(Blind 잔여물) 방지."""
    t = sc.get("type", "body")
    return "body" if t == "comment" else t


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


# ── 1단계: 다운로드 + 검증 프레임 (V2와 동일) ──────────────────────
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
    if cfg.get("hook"):
        print("🔊 hook 소스는 발언 육성 구간인지 소리도 함께 확인하세요 "
              "(ffplay 또는 QuickTime).", flush=True)
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


# ── 훅/타이밍 헬퍼 (V2.1 신규) ──────────────────────────────────────
def shift_timings(timings: list[dict], offset_ms: int) -> list[dict]:
    """모든 씬 타이밍을 offset_ms 만큼 뒤로 민다 (훅 원본 구간 확보)."""
    return [
        {**t, "start_ms": t["start_ms"] + offset_ms, "end_ms": t["end_ms"] + offset_ms}
        for t in timings
    ]


def scale_timings(timings: list[dict], speed: float) -> list[dict]:
    """모든 씬 타이밍을 1/speed 로 압축 (TTS 가속과 동기). speed=1.2 → 1.2배 빠름."""
    return [
        {**t, "start_ms": int(round(t["start_ms"] / speed)),
              "end_ms": int(round(t["end_ms"] / speed))}
        for t in timings
    ]


def resolve_hook_cut(hook: dict, source_dur: float) -> tuple[float, float]:
    """훅 클립의 (start_sec, duration) 계산. 소스가 짧으면 클램프."""
    dur = min(float(hook.get("duration", 3.0)), HOOK_MAX_SEC)
    if "start_sec" in hook:
        start = float(hook["start_sec"])
    else:
        start = source_dur * float(hook.get("frac", 0.4))
    start = max(0.0, min(start, max(0.0, source_dur - dur - 0.2)))
    dur = min(dur, max(HOOK_MIN_SEC, source_dur - start))
    return start, dur


def _pad_audio_front(audio: Path, pad_ms: int, out: Path) -> Path:
    """TTS mp3 앞에 무음 pad_ms 삽입 — 훅 원본 음성 구간 동안 TTS 침묵."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(audio),
         "-af", f"adelay={pad_ms}:all=1",
         "-codec:a", "libmp3lame", "-q:a", "2", str(out)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"TTS 무음 패딩 실패: {r.stderr[:300]}")
    return out


def _speed_audio(audio: Path, speed: float, out: Path) -> Path:
    """TTS mp3 를 speed 배로 가속 (atempo, 피치 유지). 훅 육성엔 미적용."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(audio),
         "-filter:a", f"atempo={speed:.4f}",
         "-codec:a", "libmp3lame", "-q:a", "2", str(out)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"TTS 속도 조절 실패: {r.stderr[:300]}")
    return out


def _loudnorm_clip_audio(clip: Path) -> None:
    """훅 클립 오디오 라우드니스 정규화 (영상 스트림은 copy)."""
    tmp = clip.with_name(clip.stem + "_norm.mp4")
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(clip),
         "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "aac", "-b:a", "128k", str(tmp)],
        capture_output=True, text=True,
    )
    if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(clip)
    else:
        print(f"⚠️ loudnorm 실패 — 원본 오디오 유지: {r.stderr[:200]}", flush=True)
        tmp.unlink(missing_ok=True)


# ── 스크립트 구성 ──────────────────────────────────────────────────
def build_script(cfg: dict, hook_dur: float = 0.0) -> ShortsScript:
    """hook_dur > 0 이면 scene 0 = 원본 육성 훅 (voice_text="")."""
    scenes, parts = [], []
    offset = 0
    if hook_dur > 0:
        hook = cfg["hook"]
        scenes.append(Scene(
            id=0, timestamp=0.0, duration=hook_dur,
            type="title",
            text=hook.get("text") or cfg.get("yt_title") or cfg["title"],
            voice_text="",  # TTS 없음 — 원본 발언 음성 재생
            emphasis="high",
            highlight_words=tuple(hook.get("hl", ())),
            visual_type="video",
            subtitle_color="yellow",
            subtitle_emphasis=True,
            hook=True,
            # 훅 원본 육성 씬은 자막이 인물을 가리지 않도록 영상 아래 배치 (기본 bottom)
            subtitle_position=hook.get("subtitle_position", "bottom"),
        ))
        offset = 1
    for i, sc in enumerate(cfg["scenes"]):
        sid = i + offset
        emph = bool(sc.get("emph", False))
        scenes.append(Scene(
            id=sid, timestamp=float(sid), duration=1.0,
            type=scene_type(sc),
            text=sc["text"], voice_text=sc["voice"],
            emphasis="high" if emph else "medium",
            highlight_words=tuple(sc.get("hl", ())),
            visual_type="video",
            subtitle_color=sc.get("color", "white"),
            subtitle_emphasis=emph,
            hook=(sid == 0),
            # 방송 번인 자막(로어서드)과 겹칠 때 "bottom" 으로 레터박스 아래 배치.
            # 미지정("")이면 기존 동작(position_y 0.652) 유지.
            subtitle_position=sc.get("subtitle_position", ""),
        ))
        parts.append(sc["voice"])
    return ShortsScript(
        metadata=Metadata(
            title=cfg["title"],
            emotion_type=resolve_emotion_type(cfg),          # 036: 카테고리별 기본값
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
            colors=resolve_bg_colors(cfg),                   # 036: 카테고리별 기본값
        ),
    )


# ── 2단계: TTS → 훅/씬 컷 → 렌더 → 업로드 패키지 ──────────────────
def _prepare_hook(cfg: dict, wd: Path) -> tuple[float, float]:
    """훅 소스 확인 + (start_sec, duration) 계산. 사용 불가면 (0, 0)."""
    hook = cfg.get("hook")
    if not hook:
        return 0.0, 0.0
    src = src_path(wd, hook["source"])
    if not src.exists():
        print(f"⚠️ hook 소스 '{hook['source']}' 파일 없음 — V2 방식(TTS 훅)으로 폴백", flush=True)
        return 0.0, 0.0
    start, dur = resolve_hook_cut(hook, _probe_dur(src))
    return start, dur


def cmd_render(cfg: dict) -> int:
    wd = work_dir(cfg)
    fallback = cfg.get("fallback_source") or next(
        (k for k, s in cfg["sources"].items() if s.get("url")), None
    )
    hook_start, hook_dur = _prepare_hook(cfg, wd)
    script = build_script(cfg, hook_dur=hook_dur)
    mode = f"훅 원본 육성 {hook_dur:.1f}s" if hook_dur > 0 else "TTS 훅 (V2 방식)"
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬 ({mode})", flush=True)

    print("🎙️ Gemini Charon TTS 합성 중 (뉴스캐스터 톤)...", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    audio_path, timings = generate_voice_with_timing_gemini(
        script, output_dir=wd, voice_name="Charon",
        style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
        temperature=0.5, include_outro=False,
    )
    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=wd)

    speed = float(cfg.get("tts_speed", 1.1))  # V2.1 기본값 1.1배 (사용자 확정)
    if abs(speed - 1.0) > 1e-3:
        sped = wd / f"{audio_path.stem}_x{speed:.2f}.mp3"
        audio_path = _speed_audio(audio_path, speed, sped)
        timings = scale_timings(timings, speed)
        print(f"⏩ TTS {speed:.2f}x 가속 (atempo + 타이밍 스케일, 훅 제외)", flush=True)

    if hook_dur > 0:
        hook_ms = int(round(hook_dur * 1000))
        padded = wd / f"{audio_path.stem}_hookpad.mp3"
        audio_path = _pad_audio_front(audio_path, hook_ms, padded)
        timings = shift_timings(timings, hook_ms)
        print(f"✅ TTS 앞 무음 {hook_ms}ms 패딩 + 타이밍 시프트", flush=True)

    main = [t for t in timings if t["scene_id"] != -1]
    total_ms = max(t["end_ms"] for t in main)
    print(f"✅ 합성·정렬 완료: {total_ms/1000:.1f}s (훅 포함), {len(main)}씬", flush=True)
    # 035 완주율 게이트 — 실측 길이로 하드 차단 (Remotion 렌더 전에 fail-fast)
    from scripts.political_length import enforce_length
    enforce_length(total_ms / 1000.0, cfg)

    print("✂️ 씬 클립 9:16 컷 (인물별 소스)...", flush=True)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    dur_cache = {k: (_probe_dur(src_path(wd, k)) if src_path(wd, k).exists() else 0.0)
                 for k in cfg["sources"]}
    ts = int(time.time())
    scene_videos = []
    scene_offset = 1 if hook_dur > 0 else 0

    if hook_dur > 0:
        hook_src = src_path(wd, cfg["hook"]["source"])
        hook_out = wd / f"scene_{ts}_00.mp4"
        cut_segment(input_path=hook_src, output_path=hook_out,
                    start_sec=hook_start, end_sec=hook_start + hook_dur, mute=False)
        _loudnorm_clip_audio(hook_out)
        scene_videos.append({"scene_id": 0, "video_path": str(hook_out)})
        print(f"   S0(훅·육성) ← {cfg['hook']['source']} "
              f"[{hook_start:.1f}~{hook_start + hook_dur:.1f}]", flush=True)

    for t in main:
        sid = t["scene_id"]
        sc = cfg["scenes"][sid - scene_offset]
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
        use_intro_bgm=False,  # 훅 원본 육성 보호 — 인트로 BGM(0.35) 미사용
        enable_transitions=False, enable_sfx=False, output_dir=wd,
    )
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size/1024/1024:.1f}MB)", flush=True)

    from scripts.political_upload_package import generate_upload_package
    pkg = generate_upload_package(cfg, video_path=mp4, out_dir=wd)
    print(f"📦 업로드 패키지: {pkg}", flush=True)
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
