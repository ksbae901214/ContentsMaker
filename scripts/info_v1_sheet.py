"""정보쇼츠 V1.0 컷 미리보기 타일 — 렌더(TTS 1회) 전에 일러스트 순서·노출 구간을 눈으로 본다."""
from __future__ import annotations

from pathlib import Path

from scripts.info_v1_timeline import (
    DEFAULT_TTS_SPEED,
    KORE_SYLLABLES_PER_SEC,
    flatten_sentences,
    image_slots,
)

CELL = 360
COLS = 4
LABEL_COLOR = "#B5341C"
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def estimated_spans(chapters: list[dict], speed: float = DEFAULT_TTS_SPEED) -> list[tuple[int, int]]:
    """글자 수 추정 문장 구간(±15%). 문장 사이 0.4초 무음을 넣는다."""
    spans, t = [], 0
    for r in flatten_sentences(chapters):
        dur = int(len(r.text.replace(" ", "")) / KORE_SYLLABLES_PER_SEC / speed * 1000)
        spans.append((t, t + dur))
        t += dur + 400
    return spans


def write_sheet(cfg: dict, out: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    from scripts.render_info_v1 import image_path

    chapters = cfg["chapters"]
    slots = image_slots(chapters, estimated_spans(chapters, float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))))
    rows = (len(slots) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL, rows * CELL), "#F6EFE1")
    try:
        font = ImageFont.truetype(FONT_PATH, 24)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(sheet)
    for i, s in enumerate(slots):
        img = Image.open(image_path(cfg, s.chapter)).convert("RGB")
        img.thumbnail((CELL, CELL))
        x, y = (i % COLS) * CELL, (i // COLS) * CELL
        sheet.paste(img, (x + (CELL - img.width) // 2, y + (CELL - img.height) // 2))
        zoom = "" if s.zoom_start_ms is None else f" 줌@{s.zoom_start_ms / 1000:.1f}"
        label = f"{s.chapter}. {s.start_ms / 1000:.1f}~{s.end_ms / 1000:.1f}s{zoom}"
        draw.text((x + 8, y + 8), label, fill=LABEL_COLOR, font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)
    return out
