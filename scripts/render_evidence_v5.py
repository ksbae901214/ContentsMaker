"""쇼츠 V5.0 증거 삽입형 TTS 논평 제작 스크립트 (043, 설정 JSON 기반).

벤치마크: 틱톡 @lkbhop(폴리버스) 504편 전수 + 현 포맷기 상위 10편·중앙 3편 정밀 분석.
흥행작의 공통점은 차트가 아니라 **"증거 한 컷 + 여성 TTS 조롱 논평 + 반전 한 방"** 이다.
TTS 가 논평의 75~100% 를 끌고, 원본 육성·캡처·날짜를 **증거로 끼워 모순을 터뜨린다.**

**V2.2 엔진의 재배합이다.** clip/tts 씬 혼합·타임라인 조립·씬 컷은 전부
`render_political_v2_2.py` 를 import 해 쓴다(그 파일은 수정하지 않는다). 다른 점:
  1. 육성 비율이 뒤집힌다 — V2.2 는 클립 65%+, V5 는 클립 10~25% (증거 자리에만).
     첫 씬 clip 강제가 없다(상위 10편 다수가 TTS 훅).
  2. **여성 TTS** (사용자 확정 2026-10-01) — 벤치마크 13편 중 11편이 여성 나레이터.
  3. **한쪽 진영 공격 허용** — 040 대칭 게이트가 포맷 규칙으로 침묵한다. 그 대가로
     `fact_sources` 없이는 렌더를 시작하지 않는다(041 과 같은 법적 방어선).
  4. **화면 레이어** — 2줄 투톤 헤드라인·주황 중앙 자막·강조어 팝업·증거 카드·반전 플래시
     (Remotion EvidenceLayer, 옵트인). 효과음은 없다(029 전역 OFF 유지, 사용자 확정).
  5. 길이 캡 70초 (권장 60~66초) — 다른 포맷의 035 캡은 그대로.
  6. CTA 는 채널 지침 그대로 — 질문 + 선택지 + "댓글로 알려주세요", 마지막 씬.

2단계 CLI:
  PYTHONPATH=. .venv311/bin/python scripts/render_evidence_v5.py <config.json> download [--force]
  PYTHONPATH=. .venv311/bin/python scripts/render_evidence_v5.py <config.json> render [--reuse-tts]
  (--reuse-tts: 나레이션 문구는 그대로이고 화면만 고칠 때 — 직전 TTS 재사용, Gemini 호출 0)

config 스키마: scripts/political_v2_configs/README.md 의 "043 V5.0" 절 참고.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.evidence_v5_timeline import headline_lines, validate_framing, validate_marks
from scripts.render_political_v2_2 import (
    CLIP_MIN_SEC, clip_max_sec, first_clip_index, scene_mode,
)
from scripts.shorts_domain import resolve_bg_colors, resolve_emotion_type
from scripts.shorts_format import EVIDENCE_V5, resolve_config_format
from src.analyzer.script_models import (
    AudioConfig, BackgroundConfig, Metadata, Scene, ShortsScript,
)

COLORS = {"white", "blue", "red", "yellow"}
# Gemini TTS 여성 보이스 — 벤치마크의 단호한 여성 나레이터에 가장 가까운 'Firm' 톤.
VOICE_NAME = "Kore"
# 낭독 속도는 V2.1/V2.2 와 같은 문구 (Gemini TTS 는 이 문구로 실제 속도가 달라진다).
TTS_STYLE_PROMPT = "Read in a fast, clear newscaster tone with sharp, confident delivery:"
DEFAULT_TTS_SPEED = 1.1
HEADLINE_MAX_LINE = 14          # 벤치마크 실측 행당 12~14자 (도현체 ≈80px)
TARGET_MIN_FINAL_SEC = 55.0     # 이보다 짧으면 권장 구간(60~66초) 안내
FACT_GATE_KEY = "fact_gate"
GATE_OFF = "off"
BANNED_FACT_HOSTS = ("namu.wiki", "namuwiki")


# ── 설정 로드 & 검증 ────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    from scripts.political_cta import apply_cta
    cfg = apply_cta(json.loads(path.read_text(encoding="utf-8")))
    validate_config(cfg)
    for w in config_warnings(cfg):
        print(f"⚠️ {w}", flush=True)
    return cfg


def validate_config(cfg: dict) -> None:
    if resolve_config_format(cfg) != EVIDENCE_V5:
        raise ValueError(
            f"이 스크립트는 format={EVIDENCE_V5!r} 전용입니다 — 다른 버전은 각자의 "
            "render_*.py 로 렌더하세요")
    for key in ("slug", "title", "sources", "scenes"):
        if key not in cfg or not cfg[key]:
            raise ValueError(f"config에 '{key}' 누락")
    hook_idx = first_clip_index(cfg)
    for i, sc in enumerate(cfg["scenes"]):
        _validate_scene(cfg, i, sc, hook_idx)
    _gate_fact_sources(cfg)
    # 034/036 공통 게이트 — 보도체 제목 + 카테고리 오타 + 도메인 금지어
    from scripts.political_upload_package import gate_yt_title
    from scripts.shorts_category import resolve_config_category
    from scripts.shorts_domain import gate_domain_words
    gate_yt_title(cfg)
    resolve_config_category(cfg)
    gate_domain_words(cfg)


def _validate_scene(cfg: dict, i: int, sc: dict, hook_idx: int) -> None:
    mode = scene_mode(sc)
    if mode not in ("clip", "tts"):
        raise ValueError(f"scene[{i}] mode 잘못됨: {mode} (허용: clip/tts)")
    if sc.get("source") not in cfg["sources"]:
        raise ValueError(f"scene[{i}] source '{sc.get('source')}' 가 sources에 없음")
    if sc.get("color", "white") not in COLORS:
        raise ValueError(f"scene[{i}] color 잘못됨: {sc.get('color')} (허용: {COLORS})")
    if mode == "clip":
        dur = float(sc.get("duration", 3.0))
        max_sec = clip_max_sec(i, hook_idx)
        if not (CLIP_MIN_SEC <= dur <= max_sec):
            raise ValueError(
                f"scene[{i}] duration {dur}s 범위 밖 "
                f"(허용 {CLIP_MIN_SEC}~{max_sec}s — 발언 문장 완결 단위, 037)")
        if not sc.get("text"):
            raise ValueError(f"scene[{i}] clip 씬 text(발언 요지 자막) 누락")
    elif not sc.get("voice"):
        raise ValueError(f"scene[{i}] voice(나레이션) 비어있음")
    try:
        validate_framing(sc)
    except ValueError as e:
        raise ValueError(f"scene[{i}] {e}") from e
    ev = sc.get("evidence")
    if ev:
        if not ev.get("image"):
            raise ValueError(f"scene[{i}] evidence.image 누락")
        validate_marks(list(ev.get("marks") or []))


def _gate_fact_sources(cfg: dict) -> None:
    """한쪽 공격을 허용한 대가 — 사실 근거 없이는 렌더하지 않는다 (043 §3).

    V2.2 는 화면 육성이 인용이라 방패가 되지만, V5 는 논평 75% 이상이 채널 자신의
    서술이다. 041 V3.0 과 같은 방어선이고 나무위키 금지도 같은 이유다.
    """
    if cfg.get(FACT_GATE_KEY) == GATE_OFF:
        return
    sources = cfg.get("fact_sources") or []
    if not sources:
        raise ValueError(
            "fact_sources 누락 — V5.0 은 한쪽 진영 공격을 허용하는 대신 모든 사실 주장"
            "(금액·날짜·판결)에 실제 기사 근거가 있어야 합니다. "
            f"우회: \"{FACT_GATE_KEY}\": \"{GATE_OFF}\" (법적 위험은 본인 부담)")
    for s in sources:
        url = (s.get("url") if isinstance(s, dict) else str(s)) or ""
        if any(h in url for h in BANNED_FACT_HOSTS):
            raise ValueError(
                f"나무위키를 팩트 소스로 쓸 수 없습니다 ({url}) — CC BY-NC-SA 라 "
                "업로드용 콘텐츠의 근거로 못 씁니다. 실제 기사·공식 자료를 쓰세요")


# ── 경고 ───────────────────────────────────────────────────────────
def evidence_count(cfg: dict) -> int:
    """증거 개수 = 육성 클립 씬 + 증거 카드."""
    return sum(1 for sc in cfg.get("scenes") or []
               if scene_mode(sc) == "clip" or (sc.get("evidence") or {}).get("image"))


def config_warnings(cfg: dict) -> list[str]:
    """품질 경고 — V2.1 공통 게이트(길이·CTA·039·040 편성) + V5 고유 검사."""
    from scripts.political_length import estimate_total_sec, final_video_sec
    from scripts.render_political_v2_1 import config_warnings as v2_warnings
    warnings = list(v2_warnings(cfg))
    if evidence_count(cfg) == 0:
        warnings.append(
            "증거가 없습니다 — 원본 육성 클립(mode: clip) 또는 캡처 증거 카드(evidence)를 "
            "최소 1개 넣으세요. 인신 조롱만 있는 편은 중앙값에 머뭅니다 "
            "(043 실측: 상위 10편 10/10 증거·이해관계 vs 중앙 3편 0/3)")
    warnings.extend(_headline_warnings(cfg))
    final = final_video_sec(estimate_total_sec(cfg))
    if final < TARGET_MIN_FINAL_SEC:
        warnings.append(
            f"예상 최종 길이 {final:.0f}초 — V5.0 권장 60~66초 (벤치마크 주력 구간). "
            "사실·증거 단계를 보강하세요")
    if not (cfg.get("yt_title_alt") or "").strip():
        warnings.append("yt_title_alt 누락 — 완료 블록에 자극적 제목 B안이 빠집니다")
    if not cfg.get("hashtags"):
        warnings.append("hashtags 누락 — 3~4개를 적으세요 (완료 블록 해시태그)")
    if not source_label(cfg):
        warnings.append(
            "영상 출처가 없습니다 — sources[*].channel 또는 source_label 을 채우세요 "
            "(우상단 '영상출처' 라벨은 저작권 방어선입니다)")
    return warnings


def _headline_warnings(cfg: dict) -> list[str]:
    lines = headline_lines(cfg)
    warnings = []
    if len(lines) != 2:
        warnings.append(
            f"헤드라인이 {len(lines)}줄 — V5.0 은 **2줄 투톤**(1줄 사실·2줄 질문/폭로)입니다")
    for i, line in enumerate(lines):
        if len(line) > HEADLINE_MAX_LINE:
            warnings.append(
                f"헤드라인 {i + 1}줄이 {len(line)}자 — {HEADLINE_MAX_LINE}자 이내로 "
                "줄이세요 (넘치면 자동 축소돼 피드에서 안 읽힙니다)")
    return warnings


# ── 라벨 / 완료 블록 ───────────────────────────────────────────────
def source_label(cfg: dict) -> str:
    """우상단 출처 라벨 — 명시값 우선, 없으면 클립 채널명을 모은다."""
    explicit = (cfg.get("source_label") or "").strip()
    if explicit:
        return explicit
    seen: list[str] = []
    channels = [(cfg.get("source_channel") or "").strip()] + [
        (spec.get("channel") or "").strip()
        for key, spec in (cfg.get("sources") or {}).items()
        if not key.startswith("_") and isinstance(spec, dict)
    ]
    for ch in channels:
        if ch and ch not in seen:
            seen.append(ch)
    return f"영상출처: {', '.join(seen)}" if seen else ""


def with_scene_text(cfg: dict) -> dict:
    """TTS 씬의 빈 `text` 를 나레이션으로 채운 **새 cfg** — 업로드 패키지·3줄요약용.

    V5 는 화면 자막을 나레이션에서 자동 분할하므로 TTS 씬의 `text` 가 선택이다.
    038 의 3줄요약은 `text` 만 보므로 그대로 넘기면 육성 클립 자막만 돌려 써서
    2·3줄이 같아진다 (043 파일럿 1호에서 실측).
    """
    scenes = [
        sc if sc.get("text") or scene_mode(sc) == "clip" else {**sc, "text": sc.get("voice", "")}
        for sc in cfg.get("scenes") or []
    ]
    return {**cfg, "scenes": scenes}


def chat_block(cfg: dict) -> str:
    """완료 블록 — 자극적 제목 A/B + 3줄요약 + 해시태그 (042 V4.0 규격 재사용)."""
    from scripts.render_news_v4 import news_v4_chat_block
    return news_v4_chat_block(with_scene_text(cfg))


# ── 스크립트 구성 ──────────────────────────────────────────────────
def _scene(cfg: dict, i: int, sc: dict, dur: float, hook_idx: int) -> Scene:
    is_clip = scene_mode(sc) == "clip"
    emph = bool(sc.get("emph", False))
    return Scene(
        id=i, timestamp=float(i), duration=dur if is_clip else 1.0,
        type="title" if i == hook_idx and is_clip else "body",
        text=sc.get("text") or sc.get("voice", ""),
        voice_text="" if is_clip else sc["voice"],
        emphasis="high" if (is_clip or emph) else "medium",
        highlight_words=tuple(sc.get("hl", ())),
        visual_type="video",
        subtitle_color=sc.get("color", "white"),
        subtitle_emphasis=emph,
        hook=(i == hook_idx and is_clip),
        highlight_category=sc.get("highlight_category", "neutral"),
    )


def build_script(cfg: dict, clip_durs: dict[int, float]) -> ShortsScript:
    """clip_durs: 클립 씬 index → 실측 컷 길이(초). 자막은 EvidenceLayer 가 그린다."""
    hook_idx = first_clip_index(cfg)
    scenes = tuple(_scene(cfg, i, sc, clip_durs.get(i, 3.0), hook_idx)
                   for i, sc in enumerate(cfg["scenes"]))
    voices = [sc["voice"] for sc in cfg["scenes"] if scene_mode(sc) != "clip"]
    return ShortsScript(
        metadata=Metadata(
            title=cfg["title"],
            emotion_type=resolve_emotion_type(cfg),
            duration=float(cfg.get("duration", 62.0)),
            source_url=cfg.get("youtube_url", ""),
            # political_pro = 정치 어두운 BGM 고정 경로 + 검정 캔버스 (기존 규칙 그대로)
            source_type="political_pro",
            source_channel=cfg.get("source_channel", ""),
            source_title=cfg.get("source_title", ""),
            format_type=cfg.get("format_type", "B"),
        ),
        scenes=scenes,
        audio=AudioConfig(
            tts_script=" ".join(voices), voice="ko-KR-SunHiNeural",
            rate=cfg.get("rate", "+0%"), pitch="+0Hz",
        ),
        background=BackgroundConfig(type="gradient", colors=resolve_bg_colors(cfg)),
    )


# ── 1단계: 다운로드 ────────────────────────────────────────────────
def cmd_download(cfg: dict, force: bool) -> int:
    """V2.2 다운로드 그대로 — 소스 수집 + 검증 프레임 + 육성 클립 프리뷰."""
    from scripts.render_political_v2_2 import cmd_download as v22_cmd_download
    rc = v22_cmd_download(cfg, force)
    missing = [sc["evidence"]["image"] for sc in cfg["scenes"]
               if (sc.get("evidence") or {}).get("image")
               and not Path(sc["evidence"]["image"]).exists()]
    if missing:
        print(f"⚠️ 증거 캡처 파일 없음: {', '.join(missing)} — render 전에 준비하세요",
              flush=True)
    return rc


# ── 2단계: 렌더 ────────────────────────────────────────────────────
def find_reusable_tts(wd: Path, tts_ids: set[int]) -> tuple[Path, list[dict]] | None:
    """작업 폴더의 가장 최근 TTS 원본(mp3 + timing.json) 중 씬 구성이 같은 것.

    화면 레이어만 고쳐 재렌더할 때 Gemini TTS(무료 일 10회)를 다시 쓰지 않으려는
    용도다 (`render --reuse-tts`). 나레이션 문구를 바꿨다면 쓰지 말 것 — 씬 id 만
    비교하므로 문구 변경은 감지하지 못한다.
    """
    for tj in sorted(wd.glob("*.timing.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        mp3 = tj.with_name(tj.name.removesuffix(".timing.json") + ".mp3")
        if not mp3.exists():
            continue
        timings = json.loads(tj.read_text(encoding="utf-8"))
        if {t["scene_id"] for t in timings if t["scene_id"] != -1} == tts_ids:
            return mp3, timings
    return None


def _tts_raw(script: ShortsScript, wd: Path, reuse: bool) -> tuple[Path, list[dict]]:
    if reuse:
        ids = {sc.id for sc in script.scenes if sc.voice_text}
        found = find_reusable_tts(wd, ids)
        if found:
            print(f"♻️ TTS 재사용: {found[0].name} (Gemini 호출 없음)", flush=True)
            return found
        print("⚠️ 재사용할 TTS 없음 — 새로 합성합니다", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    print(f"🎙️ Gemini {VOICE_NAME} TTS 합성 중 (여성 나레이터, tts 씬만)...", flush=True)
    return generate_voice_with_timing_gemini(
        script, output_dir=wd, voice_name=VOICE_NAME,
        style_prompt=TTS_STYLE_PROMPT, temperature=0.5, include_outro=False,
    )


def _synthesize(cfg: dict, script: ShortsScript, wd: Path,
                reuse: bool = False) -> tuple[Path, list[dict]]:
    from scripts.render_political_v2_1 import _speed_audio, scale_timings
    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = _tts_raw(script, wd, reuse)
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=wd)
    speed = float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))
    if abs(speed - 1.0) > 1e-3:
        audio_path = _speed_audio(audio_path, speed, wd / f"{audio_path.stem}_x{speed:.2f}.mp3")
        timings = scale_timings(timings, speed)
        print(f"⏩ TTS {speed:.2f}x 가속 (육성 제외)", flush=True)
    return audio_path, timings


def cmd_render(cfg: dict, reuse_tts: bool = False) -> int:
    from scripts.evidence_v5_timeline import build_layer
    from scripts.political_length import enforce_length
    from scripts.render_political_v2_1 import work_dir
    from scripts.render_political_v2_2 import (
        _assemble_audio, _cut_scene_videos, _resolve_clip_cuts, build_timeline,
        clip_audio_ratio,
    )
    wd = work_dir(cfg)
    clip_cuts = _resolve_clip_cuts(cfg, wd)
    script = build_script(cfg, {i: dur for i, (_, dur) in clip_cuts.items()})
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬 (육성 증거 {len(clip_cuts)} + "
          f"TTS {len(script.scenes) - len(clip_cuts)})", flush=True)

    audio_path, timings = _synthesize(cfg, script, wd, reuse=reuse_tts)
    specs = [{"scene_id": i, "mode": scene_mode(sc),
              **({"duration_ms": int(round(clip_cuts[i][1] * 1000))}
                 if scene_mode(sc) == "clip" else {})}
             for i, sc in enumerate(cfg["scenes"])]
    global_timings, placements = build_timeline(specs, timings)
    total_ms = max(t["end_ms"] for t in global_timings)
    enforce_length(total_ms / 1000.0, cfg)   # V5 캡 70초 — Remotion 전에 fail-fast
    audio_path = _assemble_audio(audio_path, placements, total_ms,
                                 wd / f"{audio_path.stem}_v5mix.mp3")
    ratio = clip_audio_ratio(global_timings, set(clip_cuts))
    print(f"✅ 타임라인 조립: {total_ms / 1000:.1f}s, 육성 비중 {ratio:.0%} "
          "(V5 권장 10~25%)", flush=True)

    print("✂️ 씬 클립 9:16 컷 (육성 mute=False / TTS B-roll mute=True)...", flush=True)
    scene_videos = _cut_scene_videos(cfg, wd, clip_cuts, global_timings)
    layer = build_layer({**cfg, "source_label": source_label(cfg)}, global_timings)

    print("🎬 Remotion 렌더 중 (EvidenceLayer)...", flush=True)
    from src.video.renderer import render_video
    mp4 = render_video(
        script, audio_path=audio_path, scene_videos=scene_videos,
        scene_timings=global_timings, use_bgm=True, use_intro_bgm=False,
        enable_transitions=False, enable_sfx=False, output_dir=wd,
        evidence_layer=layer,
    )
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size / 1024 / 1024:.1f}MB)", flush=True)

    from scripts.political_upload_package import generate_upload_package
    pkg = generate_upload_package(with_scene_text(cfg), video_path=mp4, out_dir=wd)
    print(f"📦 업로드 패키지: {pkg}", flush=True)
    print(f"\n{chat_block(cfg)}\n", flush=True)
    print(str(mp4))
    return 0


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[2] not in ("download", "render"):
        print(__doc__)
        return 2
    cfg = load_config(Path(sys.argv[1]))
    if sys.argv[2] == "download":
        return cmd_download(cfg, force=("--force" in sys.argv))
    return cmd_render(cfg, reuse_tts=("--reuse-tts" in sys.argv))


if __name__ == "__main__":
    raise SystemExit(main())
