"""정치쇼츠 V2.2 범용 제작 스크립트 — 원본 육성 릴레이 포맷 (설정 JSON 기반).

V2.1(render_political_v2_1.py)의 파이프라인을 유지하되 포맷을 반전(prompt_plan 033):
**육성 클립 3~5개가 영상의 뼈대**, TTS 논평은 기본 1개(최대 2개 권장).
V2.1 파일은 수정하지 않는다 (공용 헬퍼는 import 재사용).

V2.1 대비 변경점:
  1. scene 스키마에 `mode: "clip" | "tts"` (기본 tts) — clip 씬은 인물 실제 발언
     오디오(mute=False + loudnorm) + 발언 요지 노란 자막 하단 배치.
     scene 0은 clip 강제(훅). top-level `hook` 섹션은 없다(씬으로 통일).
  2. 오디오 타임라인 조립 일반화 — TTS는 tts 씬만 합성(voice_text 빈 클립 씬은
     생성기가 자동 제외) 후 씬별 세그먼트로 잘라 클립 길이만큼 무음을 사이사이
     배치(ffmpeg filter_complex adelay+amix) → 전 씬 global 타이밍 재계산.
     V2.1의 "앞 무음 패딩 1회"의 일반형. Remotion 무수정.
  3. 씬별 검증 산출물 — download 시 clip 씬 프리뷰(_verify/clip_NN.mp4, 청음용),
     render 시 씬별 프레임(_verify/scene_NN.png).

2단계 CLI:
  # 1) 소스 다운로드 + 검증 프레임 + clip 씬 프리뷰(소리 확인 필수)
  PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py <config.json> download [--force]
  # 2) Gemini Charon TTS → 타임라인 조립 → 씬 컷 → Remotion 렌더 → 업로드 패키지
  PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py <config.json> render

config.json 스키마: scripts/political_v2_configs/README.md 의 "V2.2 확장" 섹션 참고.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from scripts.render_political_v2_1 import (
    COLORS, HOOK_MAX_SEC, HOOK_MIN_SEC,
    _probe_dur, _speed_audio,
    cmd_download as v21_cmd_download,
    scale_timings, scene_type, src_path, work_dir,
)
from scripts.shorts_domain import resolve_bg_colors, resolve_emotion_type
from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)

CLIP_MIN_SEC = HOOK_MIN_SEC        # 1.0 — 클립 씬도 문장 완결 단위
CLIP_HOOK_MAX_SEC = HOOK_MAX_SEC   # 10.0 — scene 0 훅 (스와이프 방어, V2.1 규칙 유지)
# 본문 클립은 문장 완결 우선 — 대변인 브리핑의 끊어읽기 포즈를 포함하면
# 한 문장이 10s를 넘는 경우가 있어 12s까지 허용 (2026-07-23 오세훈 편 실측).
CLIP_BODY_MAX_SEC = 12.0
CUT_MAX_SEC = 55.0                 # cut_segment 60s 상한(FR-018) 여유
FPS = 30                           # Remotion 컴포지션 프레임레이트
# Remotion(OffthreadVideo) 오디오 추출이 AAC priming(2112샘플)을 스킵하지 않아
# 클립 오디오가 정확히 44ms '지연'(입모양보다 소리가 늦음)되는 것이 실측됨
# (48kHz, 2026-07-23 훅2 립싱크 리포트 — 교차상관 S0/S1 모두 동일, adelay
# 대조실험으로 방향 확정). atrim으로 오디오 앞 44ms를 잘라 상쇄.
# Remotion 버전 업그레이드 시 재실측 필요.
AAC_PRIMING_COMP_MS = 44
MAX_TTS_SCENES_SOFT = 2       # 초과 시 경고 (기본 권장 1개)
CLIP_RATIO_MIN = 0.65         # 클립 오디오 비중 권장 하한 (미달 시 경고)


# ── 설정 로드 & 검증 ────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    import json
    from scripts.political_cta import apply_cta
    from scripts.render_political_v2_1 import config_warnings
    # 035: cta 블록이 있으면 40% 지점에 tts 씬으로 삽입한 뒤 검증한다
    cfg = apply_cta(json.loads(path.read_text(encoding="utf-8")))
    for w in [*validate_config(cfg), *config_warnings(cfg)]:
        print(f"⚠️ {w}", flush=True)
    return cfg


def scene_mode(sc: dict) -> str:
    return sc.get("mode", "tts")


def clip_max_sec(scene_idx: int) -> float:
    return CLIP_HOOK_MAX_SEC if scene_idx == 0 else CLIP_BODY_MAX_SEC


def resolve_clip_cut(sc: dict, source_dur: float,
                     max_sec: float) -> tuple[float, float]:
    """클립 씬의 (start_sec, duration) 계산 — resolve_hook_cut의 상한 가변형.

    duration은 30fps 프레임 격자로 반올림 — 씬 경계가 정수 프레임에
    떨어져야 클립 오디오/비디오가 반프레임(±17ms) 밀리지 않는다
    (2026-07-23 훅2 립싱크 실측).
    """
    dur = min(float(sc.get("duration", 3.0)), max_sec)
    if "start_sec" in sc:
        start = float(sc["start_sec"])
    else:
        start = source_dur * float(sc.get("frac", 0.4))
    start = max(0.0, min(start, max(0.0, source_dur - dur - 0.2)))
    dur = min(dur, max(CLIP_MIN_SEC, source_dur - start))
    dur = round(dur * FPS) / FPS
    return start, dur


def validate_config(cfg: dict) -> list[str]:
    """하드 오류는 ValueError, 권장 위반은 경고 문자열 리스트로 반환."""
    for key in ("slug", "title", "sources", "scenes"):
        if key not in cfg:
            raise ValueError(f"config에 '{key}' 누락")
    n_clip = n_tts = 0
    for i, sc in enumerate(cfg["scenes"]):
        mode = scene_mode(sc)
        if mode not in ("clip", "tts"):
            raise ValueError(f"scene[{i}] mode 잘못됨: {mode} (허용: clip/tts)")
        if sc.get("source") not in cfg["sources"]:
            raise ValueError(f"scene[{i}] source '{sc.get('source')}' 가 sources에 없음")
        if sc.get("color", "yellow" if mode == "clip" else "white") not in COLORS:
            raise ValueError(f"scene[{i}] color 잘못됨: {sc.get('color')} (허용: {COLORS})")
        if mode == "clip":
            n_clip += 1
            dur = float(sc.get("duration", 3.0))
            max_sec = clip_max_sec(i)
            if not (CLIP_MIN_SEC <= dur <= max_sec):
                raise ValueError(
                    f"scene[{i}] duration {dur}s 범위 밖 "
                    f"(허용 {CLIP_MIN_SEC}~{max_sec}s — 발언 문장 완결 단위)")
            if i > 0 and not sc.get("text"):
                raise ValueError(f"scene[{i}] clip 씬 text(발언 요지 자막) 누락")
        else:
            n_tts += 1
            if not sc.get("voice"):
                raise ValueError(f"scene[{i}] voice(나레이션) 비어있음")
    if cfg["scenes"] and scene_mode(cfg["scenes"][0]) != "clip":
        raise ValueError("scene[0]은 clip(원본 육성 훅)이어야 합니다")
    if n_tts == 0:
        raise ValueError("tts 논평 씬이 최소 1개 필요합니다 (채널 아이덴티티 보존)")
    # 034: 보도체·해시태그 제목은 렌더 전에 차단 (yt_title_lint: "off" 로 우회)
    from scripts.political_upload_package import gate_yt_title
    gate_yt_title(cfg)
    # 036: category 오타 + 도메인 금지어(경제 투자권유)를 렌더 전에 차단
    from scripts.shorts_category import resolve_config_category
    from scripts.shorts_domain import gate_domain_words
    resolve_config_category(cfg)
    gate_domain_words(cfg)

    warnings = []
    if n_tts > MAX_TTS_SCENES_SOFT:
        warnings.append(
            f"tts 씬 {n_tts}개 — V2.2 권장은 1개(최대 {MAX_TTS_SCENES_SOFT}개). "
            "클립 릴레이 비중을 늘리세요")
    if n_clip < 2:
        warnings.append(
            f"클립 씬 {n_clip}개 — V2.2는 클립 3~5개 릴레이가 뼈대입니다. "
            "1개뿐이면 V2.1을 쓰세요")
    return warnings


# ── 타임라인 조립 (핵심, 순수 함수) ─────────────────────────────────
def build_timeline(
    scene_specs: list[dict], tts_timings: list[dict],
) -> tuple[list[dict], list[dict]]:
    """전 씬 global 타이밍 + TTS 세그먼트 배치 계산.

    scene_specs: 씬 순서대로 {"scene_id", "mode", ["duration_ms"(clip)]}
    tts_timings: TTS mp3 내부 씬 타이밍 (voice 없는 클립 씬은 미포함, -1=outro)
    반환: (global_timings, placements)
      placements[i] = {"src_start_ms", "src_end_ms", "dst_ms"} — mp3의
      [src_start, src_end) 구간을 최종 오디오의 dst_ms 위치에 배치.
    """
    by_id = {t["scene_id"]: t for t in tts_timings if t["scene_id"] != -1}
    global_timings, placements = [], []
    cursor = 0
    for spec in scene_specs:
        sid = spec["scene_id"]
        if spec["mode"] == "clip":
            dur = int(spec["duration_ms"])
        else:
            t = by_id.get(sid)
            if t is None:
                raise ValueError(f"scene {sid}(tts)의 TTS 타이밍이 없습니다")
            dur = t["end_ms"] - t["start_ms"]
            placements.append({
                "src_start_ms": t["start_ms"],
                "src_end_ms": t["end_ms"],
                "dst_ms": cursor,
            })
        global_timings.append(
            {"scene_id": sid, "start_ms": cursor, "end_ms": cursor + dur})
        cursor += dur
    return global_timings, placements


def clip_audio_ratio(global_timings: list[dict], clip_ids: set[int]) -> float:
    """최종 타임라인에서 클립(원본 육성) 오디오가 차지하는 비중 (0~1)."""
    if not global_timings:
        return 0.0
    total = max(t["end_ms"] for t in global_timings)
    clip_ms = sum(t["end_ms"] - t["start_ms"]
                  for t in global_timings if t["scene_id"] in clip_ids)
    return clip_ms / total if total else 0.0


def build_assemble_filter(placements: list[dict], total_ms: int) -> str:
    """TTS 세그먼트를 클립 사이 무음 위로 배치하는 ffmpeg filter_complex 문자열."""
    parts, labels = [], []
    for i, p in enumerate(placements):
        parts.append(
            f"[0:a]atrim=start={p['src_start_ms'] / 1000:.3f}"
            f":end={p['src_end_ms'] / 1000:.3f},"
            f"asetpts=PTS-STARTPTS,adelay={p['dst_ms']}:all=1[s{i}]")
        labels.append(f"[s{i}]")
    parts.append(
        f"{''.join(labels)}amix=inputs={len(placements)}:normalize=0,"
        f"apad=whole_dur={total_ms / 1000:.3f}[aout]")
    return ";".join(parts)


def _assemble_audio(tts_mp3: Path, placements: list[dict],
                    total_ms: int, out: Path) -> Path:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(tts_mp3),
         "-filter_complex", build_assemble_filter(placements, total_ms),
         "-map", "[aout]", "-codec:a", "libmp3lame", "-q:a", "2", str(out)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"오디오 타임라인 조립 실패: {r.stderr[:300]}")
    return out


def _loudnorm_clip_audio(clip: Path) -> None:
    """클립 오디오 라우드니스 정규화 + 48kHz 강제 (영상 스트림 copy).

    V2.1 대비: ① aresample=48000 (loudnorm의 192kHz 업샘플 → 96kHz AAC 방지)
    ② atrim으로 오디오를 44ms 당겨 AAC priming 지연 상쇄
    (AAC_PRIMING_COMP_MS 참조). V2.1 함수는 수정하지 않는다.
    """
    tmp = clip.with_name(clip.stem + "_norm.mp4")
    comp_sec = AAC_PRIMING_COMP_MS / 1000
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(clip),
         "-c:v", "copy",
         "-af", ("loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
                 f"atrim=start={comp_sec},asetpts=PTS-STARTPTS"),
         "-ar", "48000", "-c:a", "aac", "-b:a", "128k", str(tmp)],
        capture_output=True, text=True,
    )
    if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(clip)
    else:
        print(f"⚠️ loudnorm 실패 — 원본 오디오 유지: {r.stderr[:200]}", flush=True)
        tmp.unlink(missing_ok=True)


# ── 스크립트 구성 ──────────────────────────────────────────────────
def _clip_scene(cfg: dict, i: int, sc: dict, dur: float) -> Scene:
    text = sc.get("text") or cfg.get("yt_title") or cfg["title"]
    if sc.get("speaker"):
        text = f"[{sc['speaker']}]\n{text}"
    return Scene(
        id=i, timestamp=float(i), duration=dur,
        type="title" if i == 0 else "body",
        text=text,
        voice_text="",  # TTS 없음 — 원본 발언 음성 재생
        emphasis="high",
        highlight_words=tuple(sc.get("hl", ())),
        visual_type="video",
        subtitle_color=sc.get("color", "yellow"),
        subtitle_emphasis=True,
        hook=(i == 0),
        # 육성 씬 자막은 인물을 가리지 않도록 영상 아래 배치 (기본 bottom)
        subtitle_position=sc.get("subtitle_position", "bottom"),
    )


def _tts_scene(i: int, sc: dict) -> Scene:
    emph = bool(sc.get("emph", False))
    return Scene(
        id=i, timestamp=float(i), duration=1.0,
        type=scene_type(sc),
        text=sc["text"], voice_text=sc["voice"],
        emphasis="high" if emph else "medium",
        highlight_words=tuple(sc.get("hl", ())),
        visual_type="video",
        subtitle_color=sc.get("color", "white"),
        subtitle_emphasis=emph,
        hook=False,
        # 방송 번인 자막(로어서드)과 겹칠 때 "bottom" 으로 레터박스 아래 배치.
        # 미지정("")이면 기존 동작(position_y 0.652) 유지.
        subtitle_position=sc.get("subtitle_position", ""),
    )


def build_script(cfg: dict, clip_durs: dict[int, float]) -> ShortsScript:
    """clip_durs: 클립 씬 index → 실측 컷 길이(초)."""
    scenes, parts = [], []
    for i, sc in enumerate(cfg["scenes"]):
        if scene_mode(sc) == "clip":
            scenes.append(_clip_scene(cfg, i, sc, clip_durs.get(i, 3.0)))
        else:
            scenes.append(_tts_scene(i, sc))
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


# ── 1단계: 다운로드 + clip 씬 프리뷰 ────────────────────────────────
def cmd_download(cfg: dict, force: bool) -> int:
    rc = v21_cmd_download(cfg, force)
    wd = work_dir(cfg)
    verify_dir = wd / "_verify"
    verify_dir.mkdir(exist_ok=True)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    for i, sc in enumerate(cfg["scenes"]):
        if scene_mode(sc) != "clip":
            continue
        src = src_path(wd, sc["source"])
        if not src.exists():
            print(f"⚠️ clip scene[{i}] 소스 '{sc['source']}' 없음 — 프리뷰 생략", flush=True)
            continue
        start, dur = resolve_clip_cut(sc, _probe_dur(src), clip_max_sec(i))
        preview = verify_dir / f"clip_{i:02d}.mp4"
        cut_segment(input_path=src, output_path=preview,
                    start_sec=start, end_sec=start + dur, mute=False)
        print(f"🔊 clip 프리뷰: {preview} ← {sc['source']} "
              f"[{start:.1f}~{start + dur:.1f}]", flush=True)
    print("\n🔎 렌더 전 _verify/clip_NN.mp4 를 재생해 발언이 문장 단위로 "
          "완결되는지 반드시 청음 확인하세요.", flush=True)
    return rc


# ── 2단계: TTS → 타임라인 조립 → 씬 컷 → 렌더 → 업로드 패키지 ─────
def _resolve_clip_cuts(cfg: dict, wd: Path) -> dict[int, tuple[float, float]]:
    cuts = {}
    for i, sc in enumerate(cfg["scenes"]):
        if scene_mode(sc) != "clip":
            continue
        src = src_path(wd, sc["source"])
        if not src.exists():
            raise FileNotFoundError(
                f"clip scene[{i}] 소스 '{sc['source']}' 없음 — download 먼저 실행")
        cuts[i] = resolve_clip_cut(sc, _probe_dur(src), clip_max_sec(i))
    return cuts


def _extract_scene_frame(video: Path, out_png: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", "0.2", "-i", str(video),
         "-frames:v", "1", str(out_png)],
        check=False,
    )


def _cut_scene_videos(cfg: dict, wd: Path, clip_cuts: dict,
                      global_timings: list[dict]) -> list[dict]:
    from src.dem_shorts.editor.segment_cutter import cut_segment
    verify_dir = wd / "_verify"
    verify_dir.mkdir(exist_ok=True)
    fallback = cfg.get("fallback_source") or next(
        (k for k, s in cfg["sources"].items() if s.get("url")), None
    )
    dur_cache = {k: (_probe_dur(src_path(wd, k)) if src_path(wd, k).exists() else 0.0)
                 for k in cfg["sources"]}
    ts = int(time.time())
    scene_videos = []
    for t in global_timings:
        sid = t["scene_id"]
        sc = cfg["scenes"][sid]
        out_file = wd / f"scene_{ts}_{sid:02d}.mp4"
        if scene_mode(sc) == "clip":
            start, dur = clip_cuts[sid]
            cut_segment(input_path=src_path(wd, sc["source"]), output_path=out_file,
                        start_sec=start, end_sec=start + dur, mute=False)
            _loudnorm_clip_audio(out_file)
            print(f"   S{sid}(육성) ← {sc['source']} [{start:.1f}~{start + dur:.1f}]",
                  flush=True)
        else:
            key = sc["source"]
            if not src_path(wd, key).exists():
                key = fallback
                if key is None or not src_path(wd, key).exists():
                    raise FileNotFoundError(f"scene {sid} 소스 없음, 폴백도 없음")
            seg_len = min((t["end_ms"] - t["start_ms"]) / 1000.0 + 0.6, CUT_MAX_SEC)
            d = dur_cache[key]
            if "start_sec" in sc:
                start = max(0.0, min(float(sc["start_sec"]), d - seg_len - 0.2))
            else:
                start = max(0.0, min(d * sc.get("frac", 0.4), d - seg_len - 0.2))
            if d - start < seg_len:
                print(f"⚠️ S{sid}: 소스 잔여 {d - start:.1f}s < 씬 {seg_len:.1f}s — "
                      "프리즈 위험, 소스/시작점 재검토", flush=True)
            cut_segment(input_path=src_path(wd, key), output_path=out_file,
                        start_sec=start, end_sec=min(start + seg_len, d), mute=True)
            print(f"   S{sid}(TTS) ← {key} [{start:.1f}~{min(start + seg_len, d):.1f}]",
                  flush=True)
        _extract_scene_frame(out_file, verify_dir / f"scene_{sid:02d}.png")
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    return scene_videos


def cmd_render(cfg: dict) -> int:
    wd = work_dir(cfg)
    clip_cuts = _resolve_clip_cuts(cfg, wd)
    script = build_script(cfg, {i: dur for i, (_, dur) in clip_cuts.items()})
    n_clip = len(clip_cuts)
    n_tts = len(cfg["scenes"]) - n_clip
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬 "
          f"(육성 클립 {n_clip} + TTS 논평 {n_tts} — V2.2 릴레이)", flush=True)

    print("🎙️ Gemini Charon TTS 합성 중 (뉴스캐스터 톤, tts 씬만)...", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    audio_path, timings = generate_voice_with_timing_gemini(
        script, output_dir=wd, voice_name="Charon",
        style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
        temperature=0.5, include_outro=False,
    )
    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=wd)

    speed = float(cfg.get("tts_speed", 1.1))  # V2.1 표준 배속 유지 (육성엔 미적용)
    if abs(speed - 1.0) > 1e-3:
        sped = wd / f"{audio_path.stem}_x{speed:.2f}.mp3"
        audio_path = _speed_audio(audio_path, speed, sped)
        timings = scale_timings(timings, speed)
        print(f"⏩ TTS {speed:.2f}x 가속 (atempo + 타이밍 스케일)", flush=True)

    specs = [
        {"scene_id": i, "mode": scene_mode(sc),
         **({"duration_ms": int(round(clip_cuts[i][1] * 1000))}
            if scene_mode(sc) == "clip" else {})}
        for i, sc in enumerate(cfg["scenes"])
    ]
    global_timings, placements = build_timeline(specs, timings)
    total_ms = max(t["end_ms"] for t in global_timings)
    # 035 완주율 게이트 — 실측 길이로 하드 차단 (Remotion 렌더 전에 fail-fast)
    from scripts.political_length import enforce_length
    enforce_length(total_ms / 1000.0, cfg)
    assembled = wd / f"{audio_path.stem}_v22mix.mp3"
    audio_path = _assemble_audio(audio_path, placements, total_ms, assembled)
    ratio = clip_audio_ratio(global_timings, set(clip_cuts))
    print(f"✅ 타임라인 조립: {total_ms / 1000:.1f}s, TTS 세그먼트 {len(placements)}개, "
          f"클립 비중 {ratio:.0%}", flush=True)
    if ratio < CLIP_RATIO_MIN:
        print(f"⚠️ 클립 오디오 비중 {ratio:.0%} < 권장 {CLIP_RATIO_MIN:.0%} — "
              "TTS 논평을 줄이거나 클립을 늘리세요", flush=True)

    print("✂️ 씬 클립 9:16 컷 (육성 mute=False / TTS mute=True)...", flush=True)
    scene_videos = _cut_scene_videos(cfg, wd, clip_cuts, global_timings)

    print("🎬 Remotion 렌더 중...", flush=True)
    from src.video.renderer import render_video
    mp4 = render_video(
        script, audio_path=audio_path, scene_videos=scene_videos,
        scene_timings=global_timings, use_bgm=True,
        use_intro_bgm=False,  # 육성 보호 — 인트로 BGM 미사용
        enable_transitions=False, enable_sfx=False, output_dir=wd,
    )
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size / 1024 / 1024:.1f}MB)", flush=True)

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
