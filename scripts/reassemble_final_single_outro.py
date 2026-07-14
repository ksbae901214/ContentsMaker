"""Reassemble FINAL video with:
    - V2 main body trimmed to 24.77s (drops the auto source-label outro)
    - Spokesperson clip with UPDATED subtitle text
    - Subscribe outro at the very end (with source attribution baked in)
"""
from __future__ import annotations

import subprocess as _sub
import sys
import time as _time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/kyusik/ContentsMaker")
OUT_DIR = ROOT / "data/political_pro/20260615_193552_cli"

V2_MIX = OUT_DIR / "20260616_070742_민주당_지지율_하락_읽고_던진_국민의힘의_전면_재선거.mp4"
SRC_OBS = OUT_DIR / "_hUJOG82az0.mp4"
TTS_CONTENT_END_S = 24.77  # last main-scene TTS end (timing.json scene 7 end_ms)

WIDTH, HEIGHT = 1080, 1920
FPS = 30
KOREAN_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def _run(cmd: list[str]) -> None:
    print("$", " ".join(cmd[:4]), "...", file=sys.stderr)
    res = _sub.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:3])}")


def render_subtitle_png(
    *,
    text_lines: list[str],
    out_path: Path,
    font_size: int = 60,
    y_offset_frac: float = 0.74,
    bottom_label: str = "",
) -> None:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(KOREAN_FONT, font_size, index=1)
    label_font = ImageFont.truetype(KOREAN_FONT, 38, index=1)
    line_gap = int(font_size * 0.35)
    line_h = [
        draw.textbbox((0, 0), line, font=font)[3]
        - draw.textbbox((0, 0), line, font=font)[1]
        for line in text_lines
    ]
    total_h = sum(line_h) + line_gap * (len(text_lines) - 1)
    y = int(HEIGHT * y_offset_frac) - total_h // 2
    for line in text_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (WIDTH - w) // 2 - bbox[0]
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 230))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += h + line_gap

    if bottom_label:
        bbox = draw.textbbox((0, 0), bottom_label, font=label_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2 - bbox[0]
        ly = y + 30
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                draw.text((x + dx, ly + dy), bottom_label,
                          font=label_font, fill=(0, 0, 0, 230))
        draw.text((x, ly), bottom_label, font=label_font, fill=(255, 230, 80, 255))
    img.save(out_path, "PNG")


def cut_clip_with_subtitle(
    *, src: Path, start: float, end: float,
    subtitle_png: Path, out: Path,
) -> None:
    dur = end - start
    vf = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.3f}", "-i", str(src),
        "-i", str(subtitle_png),
        "-t", f"{dur:.3f}",
        "-filter_complex",
        f"[0:v]{vf}[v0];[v0][1:v]overlay=0:0:format=auto[vout]",
        "-map", "[vout]", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def trim_video(*, src: Path, end_sec: float, out: Path) -> None:
    """Trim src to [0, end_sec], re-encoding for safe concat compatibility."""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-t", f"{end_sec:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def build_subscribe_outro(out: Path, *, duration: float = 4.0) -> None:
    """End card: 그라데이션 + 구독·좋아요 + 작은 출처 라벨 (단일 outro)."""
    bg = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(bg)
    top, bot = (180, 30, 30), (15, 15, 15)
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = (
            int(top[0] * (1 - t) + bot[0] * t),
            int(top[1] * (1 - t) + bot[1] * t),
            int(top[2] * (1 - t) + bot[2] * t),
        )
        draw.line([(0, y), (WIDTH, y)], fill=c)

    big = ImageFont.truetype(KOREAN_FONT, 100, index=1)
    small = ImageFont.truetype(KOREAN_FONT, 56, index=1)
    tiny = ImageFont.truetype(KOREAN_FONT, 32, index=0)  # regular weight

    def _draw(d, txt, font, y, fill, outline=(0, 0, 0)):
        bbox = d.textbbox((0, 0), txt, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2 - bbox[0]
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                d.text((x + dx, y + dy), txt, font=font, fill=outline)
        d.text((x, y), txt, font=font, fill=fill)

    _draw(draw, "구독·좋아요", big, 700, fill=(255, 255, 255))
    _draw(draw, "부탁드립니다 🔔", big, 850, fill=(255, 230, 80))
    _draw(draw, "정치 분석 매일 업로드", small, 1080, fill=(220, 220, 220))
    # 출처 라벨 (V2 자동 outro를 잘라낸 보상 — 본 영상에 단일 source line으로 통합)
    _draw(draw, "출처: OBS뉴스, Channel A 기자회견", tiny, 1820, fill=(180, 180, 180))

    png = OUT_DIR / "outro_subscribe_with_source.png"
    bg.save(png, "PNG")

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-t", f"{duration:.2f}", "-i", str(png),
        "-f", "lavfi", "-t", f"{duration:.2f}", "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-shortest", str(out),
    ]
    _run(cmd)


def concat_videos(parts: list[Path], out: Path) -> None:
    inputs = []
    for p in parts:
        inputs += ["-i", str(p)]
    fc = (
        "".join(f"[{i}:v:0][{i}:a:0]" for i in range(len(parts)))
        + f"concat=n={len(parts)}:v=1:a=1[vout][aout]"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs, "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def main() -> int:
    ts = int(_time.time())

    # 1) 자막 PNG 새로 생성 (3줄 — '재선거에 대해 / 의견은 조금씩 달랐지만 / 결론에는 모두 동의했습니다')
    spokes_png = OUT_DIR / "spokesperson_subtitle_v2.png"
    print("🖼️ 새 자막 PNG 생성 (3줄)", file=sys.stderr)
    render_subtitle_png(
        text_lines=[
            "재선거에 대해",
            "의견은 조금씩 달랐지만",
            "결론에는 모두 동의했습니다",
        ],
        out_path=spokes_png,
        font_size=60,
        y_offset_frac=0.72,
        bottom_label="— 국민의힘 대변인 (OBS뉴스)",
    )

    # 2) 대변인 클립 새로 컷 (자막만 교체)
    spokes_clip = OUT_DIR / f"spokesperson_clip_v2_{ts}.mp4"
    print("✂️ 대변인 클립 88.5~100.5s 컷 + 새 자막 overlay", file=sys.stderr)
    cut_clip_with_subtitle(
        src=SRC_OBS, start=88.5, end=100.5,
        subtitle_png=spokes_png, out=spokes_clip,
    )

    # 3) V2 본편 24.77s까지 잘라내 자동 outro 제거
    v2_trimmed = OUT_DIR / f"v2_trimmed_{ts}.mp4"
    print(f"✂️ V2 → {TTS_CONTENT_END_S}s 까지만 trim (자동 outro 제거)", file=sys.stderr)
    trim_video(src=V2_MIX, end_sec=TTS_CONTENT_END_S, out=v2_trimmed)

    # 4) 구독·좋아요 outro (출처 라벨 포함) — 단일 종료 카드
    outro_mp4 = OUT_DIR / f"outro_subscribe_v2_{ts}.mp4"
    print("🎨 구독·좋아요 outro (출처 라벨 포함) 생성", file=sys.stderr)
    build_subscribe_outro(outro_mp4, duration=4.0)

    # 5) 최종 concat — V2(trim) + 대변인 + outro
    final = OUT_DIR / f"FINAL_single_outro_{ts}.mp4"
    print(f"🎬 concat → {final.name}", file=sys.stderr)
    concat_videos([v2_trimmed, spokes_clip, outro_mp4], final)
    print(f"✅ FINAL: {final}", file=sys.stderr)
    print(str(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
