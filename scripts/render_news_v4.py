"""쇼츠 V4.0 사진 슬라이드 뉴스 카드 제작 스크립트 (042, 설정 JSON 기반).

벤치마크: @gokorea012(김정치입니다) 틱톡 "영화 암살자들 한동훈 직격탄" (29.3초).
**영상 클립 0개** — 보도사진·SNS 캡처를 3.4초 고정 타이머로 넘기며 줌을 걸고,
전 구간 TTS 나레이션을 까는 BGM 없는 뉴스 카드.

**V3.0(profile_v3)의 확장이다.** 흰 캔버스·2줄 투톤 제목·BGM 없음·Charon 낭독
톤·업로드 패키지는 그대로 가져오고, 새로 붙는 건 두 가지뿐이다:
  1. 자막과 독립된 **사진 트랙** (`news_v4_timeline.photo_schedule`)
  2. **호흡 단위 자막** (`news_v4_timeline.caption_chunks_for_scene`)
육성 훅·클립 컷·yt-dlp 가 없어서 V3.0 보다 단순하다.

⚠️ 같은 채널을 025(2026-06)에 벤치마크한 `src/jpolitics/` 와는 무관하다 — 그때는
노란 헤드라인 + 원본 클립 포맷이었다.

범위: **정치만** (사용자 확정 2026-09-30).

CLI:
  PYTHONPATH=. .venv311/bin/python scripts/render_news_v4.py <config.json> validate
  PYTHONPATH=. .venv311/bin/python scripts/render_news_v4.py <config.json> photos-sheet
  PYTHONPATH=. .venv311/bin/python scripts/render_news_v4.py <config.json> render

config 스키마: scripts/political_v2_configs/README.md 의 "042 V4.0" 절.
"""
from __future__ import annotations

import json
from pathlib import Path

import sys

from scripts.news_v4_timeline import (
    FITS,
    caption_chunks_for_scene,
    photo_schedule,
    schedule_warnings,
)
from scripts.render_political_v2_1 import (
    _speed_audio,
    scale_timings,
    work_dir,
)
from scripts.render_profile_v3 import (
    COLORS,
    DEFAULT_BG_COLORS,
    DEFAULT_TTS_SPEED,
    HEADLINE_COLOR,
    HEADLINE_MAX_LINE,
    V2_1_TTS_STYLE_PROMPT,
    _gate_fact_sources,
    headline_lines,
    headline_text,
)
from scripts.shorts_domain import resolve_emotion_type
from scripts.shorts_format import NEWS_V4, resolve_config_format, rules_for_format
from src.analyzer.script_models import (
    AudioConfig, BackgroundConfig, Metadata, Scene, ShortsScript,
)

POLITICAL = "political"
# 벤치마크는 6장(합성 1 + 캡처 1 + 사진 4). 4장 미만이면 3.4초 타이머가 같은
# 사진을 금방 다시 꺼내 슬라이드가 짧아 보인다.
MIN_PHOTOS = 4
# 완료 블록 = 자극적 제목 A/B + 3줄요약 + 해시태그 (사용자 지시 2026-09-30).
# hashtags 미지정이면 persons 로 1~2개만 붙어 검색 노출이 약하다.
MIN_HASHTAGS = 3
CREDIT_PREFIX = "출처 : "
CREDIT_SEP = " · "
# **BGM 없음 — V4.0 고정 규격**. 벤치마크 문장 사이 무음 -66.8dB (디지털 무음).
# V3.0 과 같은 이유로 config 로 켤 수 없다.
USE_BGM = False
SHEET_CELL = 360

__all__ = [
    "MIN_HASHTAGS", "MIN_PHOTOS", "USE_BGM", "news_v4_chat_block", "build_news_card", "build_script", "config_warnings",
    "estimated_timings", "headline_text", "load_config", "missing_photos",
    "photo_credit_label", "tag_badge", "validate_config", "with_caption_text",
]


# ── 설정 로드 & 검증 ────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    from scripts.political_cta import apply_cta
    cfg = with_caption_text(apply_cta(json.loads(path.read_text(encoding="utf-8"))))
    validate_config(cfg)
    for w in config_warnings(cfg):
        print(f"⚠️ {w}", flush=True)
    return cfg


def with_caption_text(cfg: dict) -> dict:
    """`text` 없는 씬에 나레이션을 채운 **새 cfg** — V4 화면 자막 = 낭독 원문.

    업로드 패키지 3줄요약(038)은 `text` 를 읽는다. 비워 두면 요약이 제목으로
    폴백해 한 줄짜리가 된다.
    """
    scenes = [
        sc if sc.get("text") else {**sc, "text": sc.get("voice", "")}
        for sc in cfg.get("scenes") or []
    ]
    return {**cfg, "scenes": scenes}


def validate_config(cfg: dict) -> None:
    if resolve_config_format(cfg) != NEWS_V4:
        raise ValueError(
            f"이 스크립트는 format={NEWS_V4!r} 전용입니다 — V2.1/V2.2/V3.0 config 는 "
            "각자의 render_*.py 로 렌더하세요")
    for key in ("slug", "photos", "scenes"):
        if not cfg.get(key):
            raise ValueError(f"config에 '{key}' 누락")
    if (cfg.get("category") or POLITICAL) != POLITICAL:
        raise ValueError(
            f"V4.0 은 정치 전용입니다 (category={cfg['category']!r}) — "
            "사용자 확정 2026-09-30")
    _validate_photos(cfg["photos"])
    for i, sc in enumerate(cfg["scenes"]):
        if not sc.get("voice"):
            raise ValueError(f"scene[{i}] voice(나레이션) 비어있음")
        if sc.get("color", "white") not in COLORS:
            raise ValueError(f"scene[{i}] color 잘못됨: {sc.get('color')} (허용: {COLORS})")
    _gate_fact_sources(cfg)
    # 034/036 공통 게이트 — 보도체 제목 + 카테고리 오타 + 도메인 금지어
    from scripts.political_upload_package import gate_yt_title
    from scripts.shorts_category import resolve_config_category
    from scripts.shorts_domain import gate_domain_words
    gate_yt_title(cfg)
    resolve_config_category(cfg)
    gate_domain_words(cfg)


def _validate_photos(photos: list) -> None:
    """credit 은 차단 — 하단 출처 줄이 여기서 조립되는 저작권 방어선이다."""
    for i, p in enumerate(photos):
        if not isinstance(p, dict) or not p.get("path"):
            raise ValueError(f"photos[{i}] path 누락")
        if not (p.get("credit") or "").strip():
            raise ValueError(
                f"photos[{i}] credit(출처) 누락 — '{p['path']}' 의 언론사·게시자를 "
                "적으세요. 하단 출처 줄이 이 값으로 조립됩니다")
        if p.get("fit", "cover") not in FITS:
            raise ValueError(f"photos[{i}] fit 잘못됨: {p.get('fit')} (허용: {FITS})")


def config_warnings(cfg: dict) -> list[str]:
    """품질 경고 — V2.1 공통 게이트(035~040) + V4 고유 검사. 하드 오류 아님."""
    from scripts.render_political_v2_1 import config_warnings as v2_warnings
    warnings = list(v2_warnings(cfg))
    warnings.extend(_headline_warnings(cfg))
    if len(cfg.get("photos") or []) < MIN_PHOTOS:
        warnings.append(
            f"사진 {len(cfg.get('photos') or [])}장 — {MIN_PHOTOS}장 이상 권장 "
            "(벤치마크 6장). 적으면 3.4초 타이머가 같은 사진을 금방 다시 꺼냅니다")
    warnings.extend(_packaging_warnings(cfg))
    if not tag_badge(cfg):
        warnings.append(
            "tag 미지정 — 우상단 배지가 빠집니다. 출처 유형+앵글 한 줄 "
            "(예: '페이스북 직격 비판')")
    return warnings


def _packaging_warnings(cfg: dict) -> list[str]:
    """V4.0 완료 블록 규격 — 자극적 제목 A/B + 해시태그 3개 이상."""
    from scripts.political_upload_package import build_hashtags
    warnings = []
    if not (cfg.get("yt_title_alt") or "").strip():
        warnings.append(
            "yt_title_alt 미지정 — V4.0 완료 블록은 자극적 제목 A/B 두 안을 낸다 "
            "(공포·충격·호기심 톤, 명사로 닫기 — 034 보도체 게이트는 그대로)")
    tags = build_hashtags(cfg)
    if len(tags) < MIN_HASHTAGS:
        warnings.append(
            f"해시태그 {len(tags)}개 — {MIN_HASHTAGS}~4개를 config `hashtags` 에 "
            "직접 적으세요 (인물 + 사건 키워드, 예: #김여정 #DMZ지뢰 #유엔사)")
    return warnings


def _headline_warnings(cfg: dict) -> list[str]:
    """V3.0 의 줄 수·줄 길이 검사만 — '2열 질문형'은 인물 프로필 전용 규칙."""
    lines = headline_lines(cfg)
    warnings = []
    if len(lines) > 2:
        warnings.append(f"헤드라인이 {len(lines)}줄 — 2줄이어야 합니다")
    for i, line in enumerate(lines):
        if len(line) > HEADLINE_MAX_LINE:
            warnings.append(
                f"헤드라인 {i + 1}열이 {len(line)}자 — {HEADLINE_MAX_LINE}자 이내로 "
                "줄이세요 (넘치면 자동 축소돼 피드에서 안 읽힙니다)")
    return warnings


# ── 화면 라벨 ──────────────────────────────────────────────────────
def photo_credit_label(cfg: dict) -> str:
    """하단 출처 한 줄 — 사진 credit 등장 순 중복 제거 (벤치마크 형식)."""
    explicit = (cfg.get("source_channel") or "").strip()
    if explicit:
        return f"{CREDIT_PREFIX}{explicit}"
    seen: list[str] = []
    for p in cfg.get("photos") or []:
        credit = (p.get("credit") or "").strip()
        if credit and credit not in seen:
            seen.append(credit)
    return f"{CREDIT_PREFIX}{CREDIT_SEP.join(seen)}" if seen else ""


def tag_badge(cfg: dict) -> str:
    """우상단 검정 배지 문구 — 출처 유형+앵글 (예: '페이스북 직격 비판')."""
    return (cfg.get("tag") or "").strip()


# ── 스크립트·카드 조립 (순수) ──────────────────────────────────────
def build_script(cfg: dict) -> ShortsScript:
    """문장 1개 = 씬 1개. 육성 훅이 없어 씬 0 도 나레이션 씬이다.

    화면 비주얼은 씬이 아니라 news_card 가 그린다 — 씬은 TTS 타이밍 단위다.
    """
    scenes = tuple(
        Scene(
            id=i, timestamp=float(i), duration=1.0, type="body",
            text=sc.get("text") or sc["voice"], voice_text=sc["voice"],
            emphasis="medium", highlight_words=tuple(sc.get("hl", ())),
            subtitle_color=sc.get("color", "white"),
        )
        for i, sc in enumerate(cfg["scenes"])
    )
    return ShortsScript(
        metadata=Metadata(
            title=headline_text(cfg),
            emotion_type=resolve_emotion_type(cfg),
            duration=float(cfg.get("duration", 30.0)),
            source_url="",
            source_type="political_pro",
            source_label=photo_credit_label(cfg),
        ),
        scenes=scenes,
        audio=AudioConfig(
            tts_script=" ".join(sc["voice"] for sc in cfg["scenes"]),
            voice="ko-KR-SunHiNeural", rate="+0%", pitch="+0Hz",
        ),
        background=BackgroundConfig(
            type="gradient", colors=tuple(cfg.get("bg_colors") or DEFAULT_BG_COLORS)),
    )


def _content(timings: list[dict]) -> list[dict]:
    return sorted((t for t in timings if t["scene_id"] != -1), key=lambda t: t["scene_id"])


def build_news_card(cfg: dict, timings: list[dict]) -> dict:
    """TTS 타이밍 → 사진 컷 배치 + 호흡 자막 + 출처 줄 (renderer.news_card 형식)."""
    main = _content(timings)
    total_ms = max(t["end_ms"] for t in main)
    slots = photo_schedule(cfg["photos"], main[0]["end_ms"], total_ms)
    captions = [
        c for t in main
        for c in caption_chunks_for_scene(cfg["scenes"][t["scene_id"]],
                                          t["start_ms"], t["end_ms"])
    ]
    # 출처 줄은 **화면에 실제로 나온 사진**만 — TTS 가 추정보다 짧으면 뒤쪽 사진은
    # 컷을 못 받는데, 그 출처까지 적으면 출처 표기가 틀린다 (2026-09-30 실측).
    on_screen = {s.path for s in slots}
    shown = {**cfg, "photos": [p for p in cfg["photos"] if p["path"] in on_screen]}
    return {
        "photos": [{"path": s.path, "fit": s.fit, "start_ms": s.start_ms,
                    "end_ms": s.end_ms} for s in slots],
        "captions": [{"text": c.text, "start_ms": c.start_ms, "end_ms": c.end_ms,
                      "hl": list(c.hl), "color": c.color} for c in captions],
        "credit_line": photo_credit_label(shown),
        "font_family": rules_for_format(NEWS_V4).headline_font,
    }


def missing_photos(cfg: dict) -> list[str]:
    return [p["path"] for p in cfg.get("photos") or [] if not Path(p["path"]).exists()]


def estimated_timings(cfg: dict) -> list[dict]:
    """TTS 없이 글자 수로 추정한 씬 타이밍 — photos-sheet 미리보기용 (±15%)."""
    from scripts.political_length import estimate_tts_sec
    speed = float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))
    out, t = [], 0
    for i, sc in enumerate(cfg["scenes"]):
        dur = int(round(estimate_tts_sec(len(sc["voice"]), speed) * 1000))
        out.append({"scene_id": i, "start_ms": t, "end_ms": t + dur})
        t += dur
    return out


# ── CLI ────────────────────────────────────────────────────────────
def _require_photos(cfg: dict) -> None:
    """TTS 전에 막는다 — Gemini TTS 는 하루 10회라 사진 누락으로 날리면 안 된다."""
    missing = missing_photos(cfg)
    if missing:
        raise FileNotFoundError("사진 파일 없음 — " + ", ".join(missing))


def cmd_photos_sheet(cfg: dict) -> int:
    """컷 배치 미리보기 타일 — 렌더 전 인물·내용을 눈으로 확인한다."""
    from PIL import Image, ImageDraw, ImageFont
    _require_photos(cfg)
    card = build_news_card(cfg, estimated_timings(cfg))
    cols = 4
    rows = (len(card["photos"]) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * SHEET_CELL, rows * SHEET_CELL), "#F5F5F5")
    try:
        font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
    except OSError:
        font = ImageFont.load_default()
    credits = {p["path"]: p["credit"] for p in cfg["photos"]}
    for i, p in enumerate(card["photos"]):
        img = Image.open(p["path"]).convert("RGB")
        img.thumbnail((SHEET_CELL, SHEET_CELL))
        x, y = (i % cols) * SHEET_CELL, (i // cols) * SHEET_CELL
        sheet.paste(img, (x + (SHEET_CELL - img.width) // 2, y + (SHEET_CELL - img.height) // 2))
        label = f"{i + 1}. {p['start_ms'] / 1000:.1f}s {credits[p['path']]}"
        ImageDraw.Draw(sheet).text((x + 8, y + 8), label, fill="#E50914", font=font)
        print(f"  {label}  [{p['fit']}]  {p['path']}", flush=True)
    out = work_dir(cfg) / "_verify" / "photos_sheet.jpg"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out, quality=85)
    for w in schedule_warnings(cfg["photos"], tuple(card["photos"])):
        print(f"⚠️ {w}", flush=True)
    print(f"🔎 {out} — 타이밍은 글자 수 추정(±15%)", flush=True)
    return 0


def _synthesize(cfg: dict, script: ShortsScript, wd: Path) -> tuple[Path, list[dict]]:
    print("🎙️ Gemini Charon TTS 합성 중 (V2.1 과 같은 뉴스캐스터 톤)...", flush=True)
    from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
    from src.tts.silence_align import align_timings_to_silence
    audio, timings = generate_voice_with_timing_gemini(
        script, output_dir=wd, voice_name="Charon",
        style_prompt=V2_1_TTS_STYLE_PROMPT, temperature=0.5, include_outro=False,
    )
    audio, timings = align_timings_to_silence(audio, timings, out_dir=wd)
    speed = float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))
    if abs(speed - 1.0) > 1e-3:
        audio = _speed_audio(audio, speed, wd / f"{audio.stem}_x{speed:.2f}.mp3")
        timings = scale_timings(timings, speed)
        print(f"⏩ TTS {speed:.2f}x 가속", flush=True)
    return audio, timings


def cmd_render(cfg: dict) -> int:
    _require_photos(cfg)
    wd = work_dir(cfg)
    script = build_script(cfg)
    audio, timings = _synthesize(cfg, script, wd)
    total_ms = max(t["end_ms"] for t in _content(timings))
    print(f"✅ 합성·정렬 완료: {total_ms / 1000:.1f}s, {len(script.scenes)}문장", flush=True)
    from scripts.political_length import enforce_length
    enforce_length(total_ms / 1000.0, cfg)

    card = build_news_card(cfg, timings)
    print(f"🖼️ 사진 컷 {len(card['photos'])}개 · 자막 {len(card['captions'])}조각", flush=True)
    for w in schedule_warnings(cfg["photos"], tuple(card["photos"])):
        print(f"⚠️ {w}", flush=True)

    print("🎬 Remotion 렌더 중...", flush=True)
    from src.video.renderer import render_video
    mp4 = render_video(
        script, audio_path=audio, scene_timings=timings,
        use_bgm=USE_BGM, use_intro_bgm=False,
        enable_transitions=False, enable_sfx=False, output_dir=wd,
        headline_font=rules_for_format(NEWS_V4).headline_font,
        person_badge=tag_badge(cfg),
        respect_background_colors=True,
        headline_color=HEADLINE_COLOR,
        overlay_boxes=False, headline_plain=True, badge_boxed=True,
        news_card=card,
    )
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size / 1024 / 1024:.1f}MB)", flush=True)

    from scripts.political_upload_package import generate_upload_package
    pkg = generate_upload_package(cfg, video_path=mp4, out_dir=wd)
    print(f"📦 업로드 패키지: {pkg}", flush=True)
    print(f"\n{news_v4_chat_block(cfg)}\n", flush=True)
    print(str(mp4))
    return 0


def news_v4_chat_block(cfg: dict) -> str:
    """렌더 완료 블록 — **자극적 제목 A/B + 3줄요약 + 해시태그** (V4.0 규격).

    038 의 build_chat_ready_block 은 제목을 한 안만 낸다. V4.0 은 두 안을 함께
    내라는 사용자 지시(2026-09-30)라 제목 줄만 A/B 로 바꾼다. 채팅 완료 메시지는
    이 블록을 그대로 인용한다(038 — 손으로 다시 쓰지 않는다).
    """
    from scripts.political_upload_package import (
        build_chat_ready_block, sanitize_yt_title,
    )
    block = build_chat_ready_block(cfg)
    alt = (cfg.get("yt_title_alt") or "").strip()
    if not alt:
        return block
    first, rest = block.split("\n", 1)
    alt_title, _ = sanitize_yt_title(alt)
    return f"{first.replace('제목: ', '제목 A: ', 1)}\n제목 B: {alt_title}\n{rest}"


COMMANDS = {"validate": lambda cfg: 0, "photos-sheet": cmd_photos_sheet,
            "render": cmd_render}


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[2] not in COMMANDS:
        print(f"사용법: render_news_v4.py <config.json> {{{'|'.join(COMMANDS)}}}")
        return 2
    cfg = load_config(Path(sys.argv[1]))
    return COMMANDS[sys.argv[2]](cfg)


if __name__ == "__main__":
    sys.exit(main())
