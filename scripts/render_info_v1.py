"""정보쇼츠 V1.0 — 판화 일러스트 지식 스토리텔링 제작 스크립트 (045, 설정 JSON 기반).

벤치마크: 인스타 @hamster.743606 (공개 12편 실측, `reports/hamster743606 인스타 계정 분석.md`).
크림 캔버스 + 빈티지 판화 일러스트 8장(커버 1 + 챕터 7) + 여성 TTS 약 2분 + BGM 없음 + CTA 없음.

**독립 포맷이다** (사용자 지시 2026-10-14): V4.0(`render_news_v4`)·V3.0·`political_*` 와
039/040/044 정치 게이트를 import 하지 않는다. 재사용은 바닥 모듈뿐 —
Gemini TTS(`Kore`, 편 전체 1회 호출) · `silence_align` · `ShortsScript`.
렌더는 `BlindShorts` 가 아니라 전용 Remotion 컴포지션 `InfoShorts`.

CLI:
  PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py <config.json> validate
  PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py <config.json> prompts
  PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py <config.json> images
  PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py <config.json> sheet
  PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py <config.json> thumbnail
  PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py <config.json> render [--reuse-tts]

config 스키마: scripts/info_v1_configs/README.md
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.info_v1_timeline import (
    DEFAULT_TTS_SPEED,
    MAX_FINAL_SEC,
    caption_cues,
    estimate_sec,
    flatten_sentences,
    image_slots,
    length_problems,
    scale_timings,
    wrap_lines,
)
from src.analyzer.script_models import (
    AudioConfig, BackgroundConfig, Metadata, Scene, ShortsScript,
)
from src.config.settings import DATA_DIR

FORMAT = "info_v1"
TOPIC_TYPES = ("paper", "story")
MIN_CHAPTERS, MAX_CHAPTERS = 3, 12
BENCH_CHAPTERS = range(7, 10)          # 실측 7~9장
TITLE_LINE_CHARS = 11                  # Black Han Sans 84px, 폭 900px
CANVAS_COLOR = "#F6EFE1"
DEFAULT_WATERMARK = "made by 호기심 도감"   # 채널명 확정 2026-10-15
TTS_VOICE = "Kore"
TTS_STYLE_PROMPT = (
    "Read in Korean as a friendly, witty science storyteller: lively and brisk, "
    "about 8 syllables per second, natural pauses only at sentence ends."
)
CTA_WORDS = ("팔로우", "구독", "좋아요", "댓글")
YT_TITLE_MAX = 100
_SLUG_RE = re.compile(r"^[a-z0-9_]+$")

STYLE = (
    "Fine engraving-style cross-hatching and stipple shading, slightly grainy risograph "
    "texture, limited palette of deep prussian navy, mustard ochre, burnt orange, olive "
    "green and warm cream, small red accents only for emphasis."
)
NO_TEXT = "No text, no letters, no numbers, no watermark, no frame border."
COVER_TEMPLATE = (
    "Single {subject} isolated on a plain warm cream background (#F5EEE0), no scenery, "
    "vintage engraving / risograph print illustration, centered, full body. {style} {no_text} "
    "Square 1:1 image."
)
SCENE_TEMPLATE = (
    "Vintage mid-century print illustration of {subject}. {style} Composition centered, the "
    "scene forms an organic irregular vignette whose edges dissolve into a plain warm cream "
    "background (#F5EEE0), generous empty margin. {no_text} Square 1:1 image."
)


# ── config ─────────────────────────────────────────────────────
def load_config(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def work_dir(cfg: dict) -> Path:
    return DATA_DIR / "info_v1" / cfg["slug"]


def _speed(cfg: dict) -> float:
    return float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))


def validate_config(cfg: dict) -> None:
    """차단 검증 — 실패 시 ValueError. TTS(하루 10회) 전에 막는다."""
    if cfg.get("format") != FORMAT:
        raise ValueError(f"format 은 '{FORMAT}' 이어야 합니다 (현재: {cfg.get('format')!r})")
    if not _SLUG_RE.match(cfg.get("slug") or ""):
        raise ValueError("slug 는 영문 소문자·숫자·_ 만 허용됩니다")
    if not (cfg.get("title") or "").strip():
        raise ValueError("title(상단 고정 제목) 이 비어 있습니다")
    if cfg.get("topic_type", "story") not in TOPIC_TYPES:
        raise ValueError(f"topic_type 은 {TOPIC_TYPES} 중 하나")
    _validate_chapters(cfg.get("chapters") or [])
    _validate_sources(cfg)
    blocked, msgs = length_problems(estimate_sec(cfg["chapters"], _speed(cfg)))
    if blocked:
        raise ValueError(f"추정 {msgs[0]}")


def _validate_chapters(chapters: list) -> None:
    if not MIN_CHAPTERS <= len(chapters) <= MAX_CHAPTERS:
        raise ValueError(f"챕터는 {MIN_CHAPTERS}~{MAX_CHAPTERS}개 (현재 {len(chapters)})")
    for i, ch in enumerate(chapters):
        if not [s for s in ch.get("sentences") or [] if s and s.strip()]:
            raise ValueError(f"챕터 {i} 에 문장이 없습니다")
        if not (ch.get("image_prompt") or ch.get("image")):
            raise ValueError(f"챕터 {i} 에 image_prompt 또는 image 가 필요합니다")


def _validate_sources(cfg: dict) -> None:
    sources = cfg.get("fact_sources") or []
    if any("namu.wiki" in (s.get("url") or "") for s in sources):
        raise ValueError("나무위키는 출처로 쓸 수 없습니다 (CC BY-NC-SA)")
    if cfg.get("topic_type") == "paper" and not sources:
        raise ValueError("topic_type=paper 는 fact_sources(논문 출처)가 필수입니다")


def config_warnings(cfg: dict) -> list[str]:
    """경고(차단 아님) — 벤치마크 실측에서 벗어난 지점."""
    chapters = cfg["chapters"]
    warns: list[str] = []
    if len(chapters) not in BENCH_CHAPTERS:
        warns.append(f"챕터 {len(chapters)}개 — 벤치마크는 7~9개(커버 포함 8 표준)")
    _, length_msgs = length_problems(estimate_sec(chapters, _speed(cfg)))
    warns.extend(f"추정 {m}" for m in length_msgs)
    refs = flatten_sentences(chapters)
    if refs and refs[0].text.endswith("?"):
        warns.append("훅이 질문형 — 벤치마크 상위 편은 사건·숫자·역설 단정문으로 연다")
    if any(w in r.text for r in refs for w in CTA_WORDS):
        warns.append("CTA 문구 감지 — 벤치마크 12편 모두 CTA 없이 펀치라인으로 끝난다")
    if len(wrap_lines(cfg["title"], TITLE_LINE_CHARS)) > 2:
        warns.append(f"제목이 3줄 이상 — 줄당 {TITLE_LINE_CHARS}자 기준 2줄 이내로")
    if not (cfg.get("description") or cfg.get("caption")):
        warns.append("description(업로드 설명) 없음")
    if len(cfg.get("yt_title") or "") > YT_TITLE_MAX:
        warns.append(f"yt_title {len(cfg['yt_title'])}자 — 유튜브 제목은 {YT_TITLE_MAX}자까지")
    if any(not t.startswith("#") for t in cfg.get("hashtags") or []):
        warns.append("해시태그는 '#' 으로 시작해야 합니다")
    return warns


# ── 일러스트 ────────────────────────────────────────────────────
def image_path(cfg: dict, ci: int) -> Path:
    custom = cfg["chapters"][ci].get("image")
    return Path(custom) if custom else work_dir(cfg) / "images" / f"chapter_{ci:02d}.png"


def missing_images(cfg: dict) -> list[int]:
    return [i for i in range(len(cfg["chapters"])) if not image_path(cfg, i).exists()]


def image_prompt(cfg: dict, ci: int) -> str:
    """판화 화풍 템플릿 + 장면. `image_mood`(예: 귀여움)가 있으면 화풍 앞에 붙인다."""
    subject = cfg["chapters"][ci].get("image_prompt", "")
    template = COVER_TEMPLATE if ci == 0 else SCENE_TEMPLATE
    mood = (cfg.get("image_mood") or "").strip()
    style = f"Character look: {mood}. {STYLE}" if mood else STYLE
    return template.format(subject=subject, style=style, no_text=NO_TEXT)


# ── 스크립트·props ───────────────────────────────────────────────
def build_script(cfg: dict) -> ShortsScript:
    """문장 1개 = 씬 1개 — 씬은 TTS 타이밍 단위일 뿐, 화면은 InfoShorts 가 그린다."""
    refs = flatten_sentences(cfg["chapters"])
    scenes = tuple(
        Scene(id=i, timestamp=float(i), duration=1.0, type="body",
              text=r.text, voice_text=r.text)
        for i, r in enumerate(refs)
    )
    return ShortsScript(
        metadata=Metadata(title=cfg["title"], emotion_type="relatable",
                          duration=estimate_sec(cfg["chapters"], _speed(cfg)),
                          source_type=FORMAT),
        scenes=scenes,
        audio=AudioConfig(tts_script=" ".join(r.text for r in refs)),
        background=BackgroundConfig(type="solid", colors=(CANVAS_COLOR,)),
    )


def _sentence_timings(timings: list[dict]) -> list[tuple[int, int]]:
    main = sorted((t for t in timings if t["scene_id"] != -1), key=lambda t: t["scene_id"])
    return [(int(t["start_ms"]), int(t["end_ms"])) for t in main]


def build_props(cfg: dict, timings: list[dict]) -> dict:
    """TTS 타이밍 → InfoShorts 프롭 (camelCase, 이미지 경로는 렌더러가 public 으로 옮긴다)."""
    spans = _sentence_timings(timings)
    refs = flatten_sentences(cfg["chapters"])
    slots = image_slots(cfg["chapters"], spans)
    captions = [
        {"lines": list(c.lines), "startMs": c.start_ms, "endMs": c.end_ms}
        for r, (s, e) in zip(refs, spans)
        for c in caption_cues(r.text, s, e)
    ]
    return {
        "titleLines": list(wrap_lines(cfg["title"], TITLE_LINE_CHARS)),
        "watermark": cfg.get("watermark") or DEFAULT_WATERMARK,
        "canvasColor": CANVAS_COLOR,
        "images": [
            {"path": str(image_path(cfg, s.chapter)), "startMs": s.start_ms,
             "endMs": s.end_ms, "zoomStartMs": s.zoom_start_ms}
            for s in slots
        ],
        "captions": captions,
        "durationMs": spans[-1][1],
    }


def _source_lines(cfg: dict) -> list[str]:
    return [f"출처 : {s.get('label', '')}" for s in cfg.get("fact_sources") or [] if s.get("label")]


def _hashtag_line(cfg: dict) -> str:
    return " ".join(cfg.get("hashtags") or [])


def _description(cfg: dict) -> str:
    """플랫폼 공통 본문. 없으면 caption 에서 제목·출처 줄을 뺀 나머지."""
    if cfg.get("description"):
        return cfg["description"].strip()
    lines = (cfg.get("caption") or "").splitlines()
    body = [ln for ln in lines if ln.strip() and ln.strip() != cfg["title"] and not ln.startswith("출처")]
    return "\n".join(body)


def _join(*parts: str) -> str:
    return "\n\n".join(p for p in parts if p)


def chat_block(cfg: dict) -> str:
    """완료 블록 — 플랫폼별 제목·설명. 채팅엔 이 블록을 그대로 인용한다 (직접 재작성 금지)."""
    title, body = cfg["title"], _description(cfg)
    sources, tags = "\n".join(_source_lines(cfg)), _hashtag_line(cfg)
    youtube = _join(f"제목: {cfg.get('yt_title') or title}", body, sources, tags)
    instagram = _join(title, body, sources, tags)
    tiktok = _join(f"{cfg.get('yt_title') or title} {tags}".strip())
    return "\n".join([
        "━━━━ 정보쇼츠 V1.0 업로드 세트 ━━━━",
        "[유튜브]", youtube, "",
        "[인스타그램]", instagram, "",
        "[틱톡]", tiktok,
    ])


# ── CLI ────────────────────────────────────────────────────────
def _require_images(cfg: dict) -> None:
    missing = missing_images(cfg)
    if missing:
        paths = ", ".join(str(image_path(cfg, i)) for i in missing)
        raise FileNotFoundError(f"일러스트 없음 (챕터 {missing}) — {paths}")


def cmd_validate(cfg: dict) -> int:
    sec = estimate_sec(cfg["chapters"], _speed(cfg))
    print(f"✅ 검증 통과 — 챕터 {len(cfg['chapters'])}개, 추정 {sec:.1f}초 (상한 {MAX_FINAL_SEC:.0f})")
    return 0


def cmd_prompts(cfg: dict) -> int:
    for i in range(len(cfg["chapters"])):
        mark = "✅" if image_path(cfg, i).exists() else "⬜"
        print(f"\n{mark} [챕터 {i}] → {image_path(cfg, i)}\n{image_prompt(cfg, i)}")
    return 0


def cmd_images(cfg: dict) -> int:
    """빠진 일러스트만 chatgpt.com 자동화로 만든다. 실패한 장은 프롬프트를 출력한다."""
    from src.illustrator.chatgpt_web_image_gen import generate_images_sync
    todo = missing_images(cfg)
    if not todo:
        print("✅ 일러스트 전부 있음")
        return 0
    jobs = [{"key": i, "prompt": image_prompt(cfg, i), "out": image_path(cfg, i)} for i in todo]
    done = {r["key"] for r in generate_images_sync(jobs)}
    failed = [j for j in jobs if j["key"] not in done]
    for j in failed:
        print(f"\n❌ [챕터 {j['key']}] 수동 생성 후 저장 → {j['out']}\n{j['prompt']}")
    print(f"\n🖼️ 생성 {len(done)}/{len(jobs)}장")
    return 1 if failed else 0


def cmd_sheet(cfg: dict) -> int:
    """컷 미리보기 타일 — 글자 수 추정 타이밍(±15%)으로 장별 노출 구간을 함께 적는다."""
    from scripts.info_v1_sheet import write_sheet
    _require_images(cfg)
    out = write_sheet(cfg, work_dir(cfg) / "_verify" / "sheet.jpg")
    print(f"🔎 {out}")
    return 0


def cmd_thumbnail(cfg: dict) -> int:
    """썸네일 PNG — 제목 + 커버 일러스트 + 워터마크 (TTS 불필요)."""
    from src.video.info_renderer import render_thumbnail
    if not image_path(cfg, 0).exists():  # 썸네일은 커버(챕터 0)만 있으면 된다
        raise FileNotFoundError(f"커버 일러스트 없음 — {image_path(cfg, 0)}")
    props = {"titleLines": list(wrap_lines(cfg["title"], TITLE_LINE_CHARS)),
             "watermark": cfg.get("watermark") or DEFAULT_WATERMARK, "canvasColor": CANVAS_COLOR,
             "images": [{"path": str(image_path(cfg, 0)), "startMs": 0, "endMs": 1000,
                         "zoomStartMs": None}], "captions": [], "durationMs": 1000}
    out = render_thumbnail(props, output_path=work_dir(cfg) / f"{cfg['slug']}_thumbnail.png")
    print(f"🖼️ 썸네일: {out}")
    return 0


def _tts(cfg: dict, script: ShortsScript, wd: Path, reuse: bool) -> tuple[Path, list[dict]]:
    """Gemini Kore 1회 호출 → 무음 정렬. reuse: 같은 문구로 화면만 고칠 때(문구 바꿨으면 금지)."""
    raw_mp3, raw_json = wd / "tts_raw.mp3", wd / "tts_raw.json"
    if reuse and raw_mp3.exists() and raw_json.exists():
        print("♻️ TTS 재사용 (Gemini 호출 없음)", flush=True)
        timings = json.loads(raw_json.read_text(encoding="utf-8"))
    else:
        print(f"🎙️ Gemini {TTS_VOICE} TTS 합성 중...", flush=True)
        from src.tts.gemini_tts_generator import generate_voice_with_timing_gemini
        audio, timings = generate_voice_with_timing_gemini(
            script, output_dir=wd, voice_name=TTS_VOICE,
            style_prompt=TTS_STYLE_PROMPT, temperature=0.5, include_outro=False,
        )
        shutil.copy2(audio, raw_mp3)
        raw_json.write_text(json.dumps(timings, ensure_ascii=False), encoding="utf-8")
    from src.tts.silence_align import align_timings_to_silence
    audio, timings = align_timings_to_silence(raw_mp3, timings, out_dir=wd)
    speed = _speed(cfg)
    if abs(speed - 1.0) < 1e-3:
        return audio, timings
    sped = wd / f"{audio.stem}_x{speed:.2f}.mp3"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(audio),
                    "-filter:a", f"atempo={speed}", "-c:a", "libmp3lame", "-q:a", "2",
                    str(sped)], check=True)
    print(f"⏩ TTS {speed:.2f}배속", flush=True)
    return sped, scale_timings(timings, speed)


def cmd_render(cfg: dict, reuse_tts: bool = False) -> int:
    _require_images(cfg)
    wd = work_dir(cfg)
    wd.mkdir(parents=True, exist_ok=True)
    audio, timings = _tts(cfg, build_script(cfg), wd, reuse_tts)
    props = build_props(cfg, timings)
    sec = props["durationMs"] / 1000
    blocked, msgs = length_problems(sec)
    for m in msgs:
        print(f"{'❌' if blocked else '⚠️'} 실측 {m}", flush=True)
    if blocked:
        return 1
    print(f"✅ 나레이션 {sec:.1f}초 · 일러스트 {len(props['images'])}장 · 자막 {len(props['captions'])}큐")
    from src.video.info_renderer import render_info_shorts
    mp4 = render_info_shorts(props, audio_path=audio, output_path=wd / f"{cfg['slug']}.mp4")
    print(f"\n📁 출력: {mp4} ({mp4.stat().st_size / 1024 / 1024:.1f}MB)")
    cmd_thumbnail(cfg)
    print(f"\n{chat_block(cfg)}\n")
    return 0


COMMANDS = {"validate": cmd_validate, "prompts": cmd_prompts,
            "images": cmd_images, "sheet": cmd_sheet, "thumbnail": cmd_thumbnail}


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[2] not in (*COMMANDS, "render"):
        print(__doc__)
        return 2
    cfg = load_config(Path(argv[1]))
    validate_config(cfg)
    for w in config_warnings(cfg):
        print(f"⚠️ {w}", flush=True)
    if argv[2] == "render":
        return cmd_render(cfg, reuse_tts="--reuse-tts" in argv[3:])
    return COMMANDS[argv[2]](cfg)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
