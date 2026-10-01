"""쇼츠 V3.0 인물 프로필 다큐멘터리 제작 스크립트 (041, 설정 JSON 기반).

**V2.1 의 확장이다.** 훅 육성 1컷 + 이후 무음 B-roll + 전체 TTS 구조가
`render_political_v2_1.py` 와 동일해서 오디오 조립 코드는 그대로 재사용한다.
V2.1/V2.2 파일은 수정하지 않는다.

⚠️ **이름 충돌 주의**: 이 레포에는 이미 "V3"가 둘 있다 —
`src/jpolitics/`(027 모먼트 직캠), `src/analyzer/hybrid_*`(030 하이브리드).
이 포맷은 코드·문서에서 항상 **profile_v3** 로 부른다.

V2.1 대비 달라지는 것:
  1. **인물 1명이 소재 단위** — 사건이 아니라 한 사람의 이력·행보를 소개한다.
     `sources` 는 그 인물이 등장하는 여러 영상(인터뷰/연설/기자회견/근황)이고,
     씬은 선언 순서대로 **순환 배치**된다(`source` 를 씬마다 쓸 필요가 없다).
  2. **매 순환마다 오프셋을 민다** — `plan[(slot + pass) % n]`. 안 그러면
     v1→v2→v3 순서가 눈에 띄게 반복된다.
  3. **팩트 소스 강제** — 나레이션의 65%+ 가 채널 자신의 발언이라 V2.2 의
     '육성 인용'이라는 방패가 없다. `fact_sources` 없이는 렌더를 시작하지 않는다.
     **나무위키는 쓸 수 없다** (CC BY-NC-SA — celebrity 모드가 업로드를 코드로
     막아 둔 이유. V3.0 은 업로드가 목적이다).
  4. **궁서 2줄 투톤 헤드라인 + 인물 배지** (Remotion 옵트인 프롭).
  5. **CTA 는 구독·댓글 유도형** (사용자 확정 2026-09-14, `cta_style` 기본값이
     포맷에서 `subscribe` 로 잡힌다).

2단계 CLI:
  PYTHONPATH=. .venv311/bin/python scripts/render_profile_v3.py <config.json> download [--force]
  PYTHONPATH=. .venv311/bin/python scripts/render_profile_v3.py <config.json> render

config 스키마: scripts/political_v2_configs/README.md 의 "041 V3.0" 절 참고.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from scripts.render_political_v2_1 import (
    HOOK_MAX_SEC,
    HOOK_MIN_SEC,
    YTDLP_CHALLENGE_ARGS,
    _loudnorm_clip_audio,
    _pad_audio_front,
    _probe_dur,
    _speed_audio,
    resolve_hook_cut,
    scale_timings,
    shift_timings,
    src_path,
    work_dir,
)
from scripts.shorts_domain import resolve_emotion_type
from scripts.shorts_format import PROFILE_V3, resolve_config_format
from src.analyzer.script_models import (
    AudioConfig, BackgroundConfig, Metadata, Scene, ShortsScript,
)

CUT_MAX_SEC = 55.0
COLORS = {"white", "blue", "red", "yellow"}
PY = sys.executable

# 인물 B-roll 은 비평 대상이 그 영상 자체가 아니라서 인용 목적성이 V2.2 보다
# 약하다. 클립당 길이를 짧게 유지하는 것이 유일한 방어선이다.
CLIP_MAX_SEC = 6.0
# 궁서 100px 기준 한 줄 상한. 넘으면 TitleBar 가 자동 축소하는데, 계속 길면
# 72px 하한에 걸려 줄이 접히고 3줄이 되어 인물 배지를 덮는다 (2026-09-14 실측).
HEADLINE_MAX_LINE = 12
HEADLINE_QUESTION_MARKS = ("?", "？")

FACT_GATE_KEY = "fact_gate"
GATE_OFF = "off"
BANNED_FACT_HOSTS = ("namu.wiki", "namuwiki")

# 041 V3.0 기본 배속 — 지침·V2.1 과 동일(1.1배). 대본 220~320자 기준 34~40초.
DEFAULT_TTS_SPEED = 1.1
# 낭독 톤·속도는 V2.1/V2.2 와 같은 문구를 쓴다 (사용자 지시 2026-09-14).
# Gemini TTS 는 이 문구로 실제 낭독 속도가 달라지므로 배속만 맞춰선 안 된다.
V2_1_TTS_STYLE_PROMPT = (
    "Read in a fast, clear newscaster tone with neutral political delivery:")
HEADLINE_FONT = "GungSeo"          # macOS 기본 설치 궁서체 (Regular 단일 웨이트)
HEADLINE_LETTER_SPACING = -4       # 지침 §3-1 — 궁서 기본 자간이 넓어 좁힌다
# 지침 §4-1 의 캔버스 색. political_pro 기본값(검정)을 옵트인으로 덮어쓴다.
DEFAULT_BG_COLORS = ("#F5F5F5", "#F5F5F5")
# 지침 §3-1 투톤 — 1열 딥 차콜 / 2열 비비드 레드(TitleBar 가 2열에 고정 적용).
# 흰 캔버스에서 흰 글자는 박스 없이는 안 보인다 (사용자 지시 2026-09-14).
HEADLINE_COLOR = "#111111"
# 제목·인물 배지의 반투명 검정 박스 — 밝은 캔버스에서 회색으로 보여 끈다.
OVERLAY_BOXES = False
# **BGM 없음 — V3.0 고정 규격** (사용자 지시 2026-09-14). config 로 켤 수 없다.
# 인물 프로필은 나레이션이 전부라 BGM 이 낭독을 가린다. 036 의 emotion_type
# BGM 스위치는 V3.0 에 적용되지 않는다(emotion_type 은 자막·배경색에만 남는다).
USE_BGM = False


# ── 설정 로드 & 검증 ────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    from scripts.political_cta import apply_cta
    cfg = apply_cta(json.loads(path.read_text(encoding="utf-8")))
    validate_config(cfg)
    for w in config_warnings(cfg):
        print(f"⚠️ {w}", flush=True)
    return cfg


def _fact_gate_disabled(cfg: dict) -> bool:
    return cfg.get(FACT_GATE_KEY) == GATE_OFF


def validate_config(cfg: dict) -> None:
    if resolve_config_format(cfg) != PROFILE_V3:
        raise ValueError(
            f"이 스크립트는 format={PROFILE_V3!r} 전용입니다 — "
            "V2.1/V2.2 config 는 render_political_v2_1.py / _v2_2.py 로 렌더하세요")
    for key in ("slug", "person", "sources", "scenes"):
        if key not in cfg or not cfg[key]:
            raise ValueError(f"config에 '{key}' 누락")
    for i, sc in enumerate(cfg["scenes"]):
        if sc.get("color", "white") not in COLORS:
            raise ValueError(f"scene[{i}] color 잘못됨: {sc.get('color')} (허용: {COLORS})")
        if not sc.get("voice"):
            raise ValueError(f"scene[{i}] voice(나레이션) 비어있음")
        src = sc.get("source")
        if src and src not in cfg["sources"]:
            raise ValueError(f"scene[{i}] source '{src}' 가 sources에 없음")
    hook = cfg.get("hook")
    if hook:
        if hook.get("source") not in cfg["sources"]:
            raise ValueError(f"hook.source '{hook.get('source')}' 가 sources에 없음")
        dur = float(hook.get("duration", 3.0))
        if not (HOOK_MIN_SEC <= dur <= HOOK_MAX_SEC):
            raise ValueError(
                f"hook.duration {dur}s 범위 밖 (허용 {HOOK_MIN_SEC}~{HOOK_MAX_SEC}s)")
    _gate_fact_sources(cfg)
    # 034/036 공통 게이트 — 보도체 제목 + 카테고리 오타 + 도메인 금지어
    from scripts.political_upload_package import gate_yt_title
    from scripts.shorts_category import resolve_config_category
    from scripts.shorts_domain import gate_domain_words
    gate_yt_title(cfg)
    resolve_config_category(cfg)
    gate_domain_words(cfg)


def _gate_fact_sources(cfg: dict) -> None:
    """팩트 소스 없이는 렌더를 시작하지 않는다 (지침 §2, 이 레포에선 법적 요건).

    V2.2 는 화면에 나오는 육성이 인용이라 방패가 되지만, V3.0 은 나레이션 전체가
    채널 자신의 서술이다. 소스가 없으면 그 서술을 방어할 근거가 없다.
    """
    if _fact_gate_disabled(cfg):
        return
    sources = cfg.get("fact_sources") or []
    if not sources:
        raise ValueError(
            "fact_sources 누락 — V3.0 나레이션은 전부 채널 자신의 서술이라 "
            "실제 기사 근거가 없으면 방어가 불가능합니다 (지침 §2). "
            f"우회: \"{FACT_GATE_KEY}\": \"{GATE_OFF}\" (법적 위험은 본인 부담)")
    for s in sources:
        url = (s.get("url") if isinstance(s, dict) else str(s)) or ""
        if any(h in url for h in BANNED_FACT_HOSTS):
            raise ValueError(
                f"나무위키를 팩트 소스로 쓸 수 없습니다 ({url}) — CC BY-NC-SA 라 "
                "업로드용 콘텐츠의 근거로 못 씁니다 (celebrity 모드가 업로드를 "
                "코드로 막아 둔 것과 같은 이유). 실제 기사·공식 프로필을 쓰세요")


def config_warnings(cfg: dict) -> list[str]:
    """품질 경고 모음 — V2.1 게이트 전부 + V3.0 고유 검사. 하드 오류 아님."""
    from scripts.render_political_v2_1 import config_warnings as v2_warnings
    warnings = list(v2_warnings(cfg))
    warnings.extend(headline_warnings(cfg))
    warnings.extend(_clip_length_warnings(cfg))
    if not cfg.get("person_title"):
        warnings.append(
            "person_title 미지정 — 인물 배지가 이름만 나옵니다 (직책을 함께 "
            "보여야 '지금 왜 이 사람인가'가 전달됩니다)")
    if not source_label(cfg):
        warnings.append(
            "사용한 클립의 채널명이 없습니다 — sources[*].channel 을 채우거나 "
            "source_channel 을 지정하세요 (인물 B-roll 의 출처 표기는 저작권 "
            "방어선입니다). download 단계가 채널명을 자동으로 채워 줍니다")
    return warnings


def _clip_length_warnings(cfg: dict) -> list[str]:
    warnings = []
    hook = cfg.get("hook") or {}
    if float(hook.get("duration", 0.0)) > CLIP_MAX_SEC:
        warnings.append(
            f"hook 클립 {hook['duration']}초 — {CLIP_MAX_SEC:.0f}초 이내로 "
            "줄이세요 (저작권: 인물 B-roll 은 비평 대상이 그 영상이 아니라 "
            "인용 목적성이 V2.2 보다 약합니다)")
    return warnings


# ── 헤드라인 / 배지 ────────────────────────────────────────────────
def headline_lines(cfg: dict) -> list[str]:
    """궁서 2줄 헤드라인. 미지정이면 제목 1줄로 폴백."""
    head = cfg.get("headline")
    if isinstance(head, str):
        return [ln for ln in head.split("\n") if ln.strip()]
    if isinstance(head, list) and head:
        return [str(ln) for ln in head if str(ln).strip()]
    return [cfg.get("yt_title") or cfg.get("title") or ""]


def headline_text(cfg: dict) -> str:
    """Remotion TitleBar 가 \\n 으로 2줄 투톤(1열 흰색 / 2열 레드)을 나눈다."""
    return "\n".join(headline_lines(cfg))


def headline_warnings(cfg: dict) -> list[str]:
    lines = headline_lines(cfg)
    warnings = []
    if len(lines) > 2:
        warnings.append(
            f"헤드라인이 {len(lines)}줄 — **2줄**이어야 합니다. 3줄이 되면 "
            "인물 배지를 덮습니다 (2026-09-14 실측)")
    for i, line in enumerate(lines):
        if len(line) > HEADLINE_MAX_LINE:
            warnings.append(
                f"헤드라인 {i + 1}열이 {len(line)}자 — {HEADLINE_MAX_LINE}자 "
                "이내로 줄이세요 (궁서는 자폭이 넓어 길면 자동 축소되고, "
                "계속 길면 줄이 접혀 배지를 덮습니다)")
    if len(lines) >= 2 and not any(m in lines[1] for m in HEADLINE_QUESTION_MARKS):
        warnings.append(
            "헤드라인 2열이 질문형이 아닙니다 — 이력·배경을 파헤쳐보고 싶게 "
            "만드는 질문이어야 합니다 (예: '구글 엔지니어 출신?'). "
            "1.0/2.0 의 스캔들형 '의혹?' 과는 다릅니다")
    return warnings


def person_badge(cfg: dict) -> str:
    """우상단 배지 문구 — '실명 · 직책'."""
    name = (cfg.get("person") or "").strip()
    title = (cfg.get("person_title") or "").strip()
    return f"{name} · {title}" if name and title else name


def source_label(cfg: dict) -> str:
    """하단 출처 표기 — 사용한 모든 클립의 채널명 통합 (지침 §4-5)."""
    explicit = (cfg.get("source_channel") or "").strip()
    if explicit:
        return f"출처: {explicit}"
    seen: list[str] = []
    for spec in clip_sources(cfg).values():
        ch = (spec.get("channel") or "").strip()
        if ch and ch not in seen:
            seen.append(ch)
    return f"출처: {', '.join(seen)}" if seen else ""


# ── 클립 순환 배치 ─────────────────────────────────────────────────
def clip_sources(cfg: dict) -> dict[str, dict]:
    """실제 클립 소스만 — `_` 로 시작하는 설명 키를 제외한다.

    이 레포의 config 템플릿은 객체 안에 `_comment` 를 섞어 쓴다. 걸러내지 않으면
    설명 문자열이 소스로 잡혀 순환 배치와 출처 표기가 깨진다.
    """
    return {
        k: v for k, v in (cfg.get("sources") or {}).items()
        if not k.startswith("_") and isinstance(v, dict)
    }


def rotation_plan(cfg: dict) -> list[str]:
    """씬에 돌려 쓸 소스 키 목록 — config 선언 순서."""
    return list(clip_sources(cfg).keys())


def source_for_scene(cfg: dict, plan: list[str], index: int) -> str:
    """씬 index 에 배정할 소스 키.

    씬이 `source` 를 직접 지정하면 그걸 쓰고, 아니면 순환 배치한다.
    **매 순환(pass)마다 시작 오프셋을 민다** — 안 그러면 나레이션이 길어 여러 번
    돌 때 v1→v2→v3 순서가 그대로 반복돼 눈에 띈다 (지침 §4-3).
    """
    scenes = cfg.get("scenes") or []
    if index < len(scenes):
        explicit = scenes[index].get("source")
        if explicit:
            return explicit
    if not plan:
        return ""
    n = len(plan)
    return plan[(index % n + index // n) % n]


def photo_for_index(photos: list[str], index: int) -> str | None:
    """인물 사진 풀에서 순환 선택 — 같은 사진 반복을 피한다 (지침 §2-6)."""
    if not photos:
        return None
    return photos[index % len(photos)]


# ── 스크립트 구성 ──────────────────────────────────────────────────
def build_script(cfg: dict, hook_dur: float = 0.0) -> ShortsScript:
    """hook_dur > 0 이면 scene 0 = 원본 육성 훅 (voice_text="")."""
    scenes, parts = [], []
    offset = 0
    if hook_dur > 0:
        hook = cfg["hook"]
        scenes.append(Scene(
            id=0, timestamp=0.0, duration=hook_dur, type="title",
            text=hook.get("text") or headline_lines(cfg)[0],
            voice_text="",
            emphasis="high",
            highlight_words=tuple(hook.get("hl", ())),
            visual_type="video",
            subtitle_color="yellow",
            subtitle_emphasis=True,
            hook=True,
            subtitle_position=hook.get("subtitle_position", "bottom"),
        ))
        offset = 1
    for i, sc in enumerate(cfg["scenes"]):
        sid = i + offset
        emph = bool(sc.get("emph", False))
        scenes.append(Scene(
            id=sid, timestamp=float(sid), duration=1.0,
            type="body",
            text=sc.get("text", ""), voice_text=sc["voice"],
            emphasis="high" if emph else "medium",
            highlight_words=tuple(sc.get("hl", ())),
            visual_type="video",
            subtitle_color=sc.get("color", "white"),
            subtitle_emphasis=emph,
            hook=(sid == 0),
            subtitle_position=sc.get("subtitle_position", ""),
        ))
        parts.append(sc["voice"])
    return ShortsScript(
        metadata=Metadata(
            title=headline_text(cfg),
            emotion_type=resolve_emotion_type(cfg),
            duration=float(cfg.get("duration", 45.0)),
            source_url=cfg.get("youtube_url", ""),
            source_type="political_pro",
            source_channel=cfg.get("source_channel", ""),
            source_title=cfg.get("source_title", ""),
            source_label=source_label(cfg),
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
            # 카테고리 기본값(정치=진한 빨강)이 아니라 V3.0 캔버스가 기본이다.
            type="gradient",
            colors=tuple(cfg.get("bg_colors") or DEFAULT_BG_COLORS),
        ),
    )


# ── 1단계: 다운로드 ────────────────────────────────────────────────
def cmd_download(cfg: dict, force: bool) -> int:
    wd = work_dir(cfg)
    verify_dir = wd / "_verify"
    verify_dir.mkdir(exist_ok=True)
    person = cfg["person"]
    for key, spec in clip_sources(cfg).items():
        out = src_path(wd, key)
        if out.exists() and not force:
            print(f"⏭️  {key}: 이미 있음 (--force 로 재다운로드)", flush=True)
        else:
            _download_source(key, spec, out)
        if not out.exists():
            continue
        dur = _probe_dur(out)
        frac = spec.get("verify_frac", 0.4)
        frame = verify_dir / f"{key}.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", str(max(1.0, dur * frac)),
             "-i", str(out), "-frames:v", "1", str(frame)],
            check=False,
        )
        title = _read_side_file(out, "title")
        channel = _read_side_file(out, "channel")
        flag = "" if not title or person in title else "  ⚠️ 제목에 인물 실명 없음"
        print(f"✅ {key}: {dur:.0f}s / {channel or '채널 미상'} → {frame}{flag}",
              flush=True)
    print(f"\n🔎 렌더 전 {verify_dir}/ 의 프레임으로 **그 인물 본인이 맞는지** "
          "확인하세요 — 기자회견·위원회 영상은 사회자·다른 발언자가 잡힙니다.",
          flush=True)
    if cfg.get("hook"):
        print("🔊 hook 소스는 발언 육성 구간인지 소리도 함께 확인하세요.", flush=True)
    missing = [k for k in clip_sources(cfg) if not src_path(wd, k).exists()]
    if missing:
        print(f"⚠️ 내려받지 못한 소스: {', '.join(missing)} — 해당 씬은 "
              "인물 사진으로 대체됩니다 (person_photos).", flush=True)
    return 0


def _read_side_file(out: Path, kind: str) -> str:
    f = out.with_suffix(f".{kind}.txt")
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def _download_source(key: str, spec: dict, out: Path) -> None:
    for p in out.parent.glob(f"{out.stem}.*"):
        p.unlink(missing_ok=True)
    target = spec["url"] if spec.get("url") else \
        f"ytsearch{spec.get('search_n', 6)}:{spec['query']}"
    dmax, dmin = spec.get("dur_max", 900), spec.get("dur_min", 20)
    print(f"⬇️  {key}: {target}", flush=True)
    subprocess.run(
        [PY, "-m", "yt_dlp", target,
         *YTDLP_CHALLENGE_ARGS,
         "--match-filter", f"duration<{dmax} & duration>{dmin}",
         "--max-downloads", "1", "--force-overwrites", "--no-playlist-reverse",
         "-f", "bv*[height<=720]+ba/b[height<=720]", "--merge-output-format", "mp4",
         "--print-to-file", "%(title)s", str(out.with_suffix(".title.txt")),
         # 출처 표기(지침 §4-5)용 — V2.1 은 채널명을 저장하지 않는다
         "--print-to-file", "%(channel)s", str(out.with_suffix(".channel.txt")),
         "-o", str(out.with_suffix(".%(ext)s"))],
        check=False,
    )


# ── 2단계: 렌더 ────────────────────────────────────────────────────
def _prepare_hook(cfg: dict, wd: Path) -> tuple[float, float]:
    hook = cfg.get("hook")
    if not hook:
        return 0.0, 0.0
    src = src_path(wd, hook["source"])
    if not src.exists():
        print(f"⚠️ hook 소스 '{hook['source']}' 파일 없음 — TTS 훅으로 폴백", flush=True)
        return 0.0, 0.0
    return resolve_hook_cut(hook, _probe_dur(src))


def cmd_render(cfg: dict) -> int:
    wd = work_dir(cfg)
    hook_start, hook_dur = _prepare_hook(cfg, wd)
    script = build_script(cfg, hook_dur=hook_dur)
    mode = f"훅 원본 육성 {hook_dur:.1f}s" if hook_dur > 0 else "TTS 훅"
    print(f"✅ 스크립트 구성: {len(script.scenes)}씬 ({mode})", flush=True)

    print("🎙️ Gemini Charon TTS 합성 중 (V2.1과 동일한 뉴스캐스터 톤)...", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    audio_path, timings = generate_voice_with_timing_gemini(
        script, output_dir=wd, voice_name="Charon",
        # 사용자 지시 2026-09-14 — V2.1 과 같은 낭독 속도로 통일.
        # **배속(tts_speed)은 원래부터 V2.1 과 같은 1.1이었다.** 체감 속도를
        # 가르던 건 이 style_prompt 다: 'calm documentary narration' 으로 주면
        # Gemini 가 눈에 띄게 느리게 읽는다. 지침의 다큐멘터리 톤보다 채널
        # 일관성을 택했다.
        style_prompt=V2_1_TTS_STYLE_PROMPT,
        temperature=0.5, include_outro=False,
    )
    from src.tts.silence_align import align_timings_to_silence
    audio_path, timings = align_timings_to_silence(audio_path, timings, out_dir=wd)

    speed = float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))
    if abs(speed - 1.0) > 1e-3:
        sped = wd / f"{audio_path.stem}_x{speed:.2f}.mp3"
        audio_path = _speed_audio(audio_path, speed, sped)
        timings = scale_timings(timings, speed)
        print(f"⏩ TTS {speed:.2f}x 가속 (훅 제외)", flush=True)

    if hook_dur > 0:
        hook_ms = int(round(hook_dur * 1000))
        audio_path = _pad_audio_front(
            audio_path, hook_ms, wd / f"{audio_path.stem}_hookpad.mp3")
        timings = shift_timings(timings, hook_ms)
        print(f"✅ TTS 앞 무음 {hook_ms}ms 패딩 + 타이밍 시프트", flush=True)

    main = [t for t in timings if t["scene_id"] != -1]
    total_ms = max(t["end_ms"] for t in main)
    print(f"✅ 합성·정렬 완료: {total_ms/1000:.1f}s (훅 포함), {len(main)}씬", flush=True)
    from scripts.political_length import enforce_length
    enforce_length(total_ms / 1000.0, cfg)

    scene_videos, scene_images = _cut_scenes(cfg, wd, main, hook_start, hook_dur)

    print("🎬 Remotion 렌더 중...", flush=True)
    from src.video.renderer import render_video
    mp4 = render_video(
        script, audio_path=audio_path,
        scene_videos=scene_videos, scene_images=scene_images,
        scene_timings=timings, use_bgm=USE_BGM, use_intro_bgm=False,
        enable_transitions=False, enable_sfx=False, output_dir=wd,
        headline_font=HEADLINE_FONT,
        headline_letter_spacing=HEADLINE_LETTER_SPACING,
        person_badge=person_badge(cfg),
        # 지침 §4-1 흰 캔버스 — political_pro 의 검정 강제를 푼다 (사용자 지시)
        respect_background_colors=True,
        headline_color=HEADLINE_COLOR,
        overlay_boxes=OVERLAY_BOXES,
    )
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size/1024/1024:.1f}MB)", flush=True)

    from scripts.political_upload_package import (
        build_chat_ready_block, generate_upload_package,
    )
    pkg = generate_upload_package(cfg, video_path=mp4, out_dir=wd)
    print(f"📦 업로드 패키지: {pkg}", flush=True)
    print(f"\n{build_chat_ready_block(cfg)}\n", flush=True)
    print(str(mp4))
    return 0


def _cut_scenes(cfg: dict, wd: Path, main: list[dict],
                hook_start: float, hook_dur: float) -> tuple[list[dict], list[dict]]:
    """씬별 클립 컷. 폴백 체인: 배정 영상 → 인물 사진 풀 → 초반 오프셋 영상."""
    from src.dem_shorts.editor.segment_cutter import cut_segment
    # 9:16 패딩 색을 캔버스와 맞춘다 — 클립 파일에 색이 **구워지므로**, 검정으로
    # 두면 흰 캔버스 위에 검은 띠가 그대로 남는다 (2026-09-14 실측).
    pad = (cfg.get("bg_colors") or DEFAULT_BG_COLORS)[0]
    print(f"✂️ 씬 클립 9:16 컷 (인물 소스 순환 배치, 패딩 {pad})...", flush=True)
    plan = rotation_plan(cfg)
    photos = [p for p in (cfg.get("person_photos") or []) if Path(p).exists()]
    dur_cache = {k: (_probe_dur(src_path(wd, k)) if src_path(wd, k).exists() else 0.0)
                 for k in clip_sources(cfg)}
    ts = int(time.time())
    scene_videos: list[dict] = []
    scene_images: list[dict] = []
    scene_offset = 1 if hook_dur > 0 else 0

    if hook_dur > 0:
        hook_out = wd / f"scene_{ts}_00.mp4"
        cut_segment(input_path=src_path(wd, cfg["hook"]["source"]),
                    output_path=hook_out, start_sec=hook_start,
                    end_sec=hook_start + hook_dur, mute=False, pad_color=pad)
        _loudnorm_clip_audio(hook_out)
        scene_videos.append({"scene_id": 0, "video_path": str(hook_out)})
        print(f"   S0(훅·육성) ← {cfg['hook']['source']} "
              f"[{hook_start:.1f}~{hook_start + hook_dur:.1f}]", flush=True)

    photo_slot = 0
    for t in main:
        sid = t["scene_id"]
        idx = sid - scene_offset
        sc = cfg["scenes"][idx]
        seg_len = min((t["end_ms"] - t["start_ms"]) / 1000.0 + 0.6, CUT_MAX_SEC)
        key = source_for_scene(cfg, plan, idx)
        use_photo = bool(sc.get("use_photo"))
        available = key and src_path(wd, key).exists()

        if (use_photo or not available) and photos:
            photo = photo_for_index(photos, photo_slot)
            photo_slot += 1
            scene_images.append({"scene_id": sid, "image_path": photo})
            why = "지정" if use_photo else "소스 없음"
            print(f"   S{sid} ← 인물 사진({why}) {Path(photo).name}", flush=True)
            continue
        if not available:
            raise FileNotFoundError(
                f"scene {sid}: 소스 '{key}' 파일이 없고 person_photos 도 비어 "
                "있습니다 — download 를 먼저 돌리거나 인물 사진을 넣으세요")

        d = dur_cache[key]
        start = max(0.0, min(d * sc.get("frac", 0.4), d - seg_len - 0.2))
        out_file = wd / f"scene_{ts}_{sid:02d}.mp4"
        cut_segment(input_path=src_path(wd, key), output_path=out_file,
                    start_sec=start, end_sec=min(start + seg_len, d), mute=True,
                    pad_color=pad)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
        print(f"   S{sid} ← {key} [{start:.1f}~{min(start+seg_len, d):.1f}] (음소거)",
              flush=True)
    return scene_videos, scene_images


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
