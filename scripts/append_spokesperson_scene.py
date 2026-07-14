"""Append an original-audio spokesperson clip to an existing political_pro V2 video.

Pipeline:
    1) Render a 1080×1920 subtitle PNG (Pillow) with the spokesperson's quote.
    2) Cut the chosen segment from the source YouTube MP4, scaled+letterboxed
       to 1080×1920, **original audio preserved**, with the subtitle overlaid.
    3) ffmpeg concat-demuxer (re-encoded) the spokesperson clip onto the base
       V2 video so the final MP4 has matching codec params.

Inputs are hard-coded at the bottom — edit and re-run.
"""
from __future__ import annotations

import subprocess as _sub
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/kyusik/ContentsMaker")
WIDTH, HEIGHT = 1080, 1920
FPS = 30
KOREAN_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def render_subtitle_png(
    *,
    text_lines: list[str],
    out_path: Path,
    font_size: int = 64,
    y_offset_frac: float = 0.74,
    bottom_label: str = "",
) -> None:
    """Draw centered Korean subtitle (white + black outline) onto a transparent
    1080×1920 PNG. Optional bottom-label (e.g. '국민의힘 대변인') sits below the
    main subtitle.
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(KOREAN_FONT, font_size, index=1)  # Bold
    label_font = ImageFont.truetype(KOREAN_FONT, 38, index=1)

    line_gap = int(font_size * 0.35)
    total_h = sum(
        (draw.textbbox((0, 0), line, font=font)[3]
         - draw.textbbox((0, 0), line, font=font)[1])
        for line in text_lines
    ) + line_gap * (len(text_lines) - 1)

    y = int(HEIGHT * y_offset_frac) - total_h // 2

    for line in text_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (WIDTH - w) // 2 - bbox[0]
        # outline
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
        draw.text((x, ly), bottom_label, font=label_font,
                  fill=(255, 230, 80, 255))  # yellow for source label

    img.save(out_path, "PNG")


def cut_clip_with_subtitle(
    *,
    src_mp4: Path,
    start_sec: float,
    end_sec: float,
    subtitle_png: Path,
    out_path: Path,
) -> None:
    """Cut src_mp4[start:end], letterbox to 1080×1920, overlay subtitle PNG,
    keep original audio, re-encode to h264+aac matching the V2 video.
    """
    duration = end_sec - start_sec
    # scale to fit within 1080x1920 keeping aspect, then pad with black
    vf = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start_sec:.3f}", "-i", str(src_mp4),
        "-i", str(subtitle_png),
        "-t", f"{duration:.3f}",
        "-filter_complex",
        f"[0:v]{vf}[v0];[v0][1:v]overlay=0:0:format=auto[vout]",
        "-map", "[vout]", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out_path),
    ]
    _run(cmd)


def concat_videos(parts: list[Path], out_path: Path) -> None:
    """Re-encode concat (safer than -c copy when frame timing/PTS differ)."""
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]

    filter_parts = []
    for i in range(len(parts)):
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")
    filter_complex = (
        "".join(filter_parts)
        + f"concat=n={len(parts)}:v=1:a=1[vout][aout]"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out_path),
    ]
    _run(cmd)


def _run(cmd: list[str]) -> None:
    print("$", " ".join(cmd[:4]), "...", file=sys.stderr)
    res = _sub.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:3])}")


def main() -> int:
    out_dir = ROOT / "data/political_pro/20260615_193552_cli"
    src_mp4 = out_dir / "_hUJOG82az0.mp4"
    base_v2 = out_dir / "20260615_195411_민주당_지지율_하락_읽고_던진_국민의힘의_전면_재선거.mp4"

    # 90~100s 구간: 대변인이 "의견은 조금씩 다른 부분이 있었지만 결론에는 모두 동의하셨다"고
    # 답변하는 부분. 호평/전략 분석 톤("신의 한 수")의 근거로 적합.
    seg_start, seg_end = 88.5, 100.5

    # 2단 자막 — 발언 요지 2줄로 분리.
    subtitle_lines = [
        "의견은 조금씩 달랐지만",
        "결론에는 모두 동의했습니다",
    ]
    bottom_label = "— 국민의힘 대변인 (OBS뉴스)"

    subtitle_png = out_dir / "spokesperson_subtitle.png"
    print(f"🖼️ 자막 PNG 생성 → {subtitle_png.name}", file=sys.stderr)
    render_subtitle_png(
        text_lines=subtitle_lines,
        out_path=subtitle_png,
        font_size=68,
        bottom_label=bottom_label,
    )

    spokes_clip = out_dir / "spokesperson_clip.mp4"
    print(f"✂️ {seg_start}~{seg_end}s 컷 + 1080×1920 letterbox + 원본 음성 유지",
          file=sys.stderr)
    cut_clip_with_subtitle(
        src_mp4=src_mp4,
        start_sec=seg_start,
        end_sec=seg_end,
        subtitle_png=subtitle_png,
        out_path=spokes_clip,
    )

    final = out_dir / (
        base_v2.stem + "_with_spokesperson.mp4"
    )
    print(f"🎬 V2 + 대변인 클립 concat → {final.name}", file=sys.stderr)
    concat_videos([base_v2, spokes_clip], final)

    print(f"✅ 완료: {final}", file=sys.stderr)
    print(str(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
