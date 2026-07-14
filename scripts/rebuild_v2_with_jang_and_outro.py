"""Rebuild the political_pro V2 video with:
    - Scenes 0–5 background = 장동혁 기자회견 clip (Channel A press conference)
    - Scenes 6–7 background = 기존 OBS 대변인 발표 clip (climax + CTA)
    - Reuses cached Charon TTS audio + timings (avoids Charon speed variance)
Then append:
    - 대변인 인터뷰 클립 (원본 음성, 자막 overlay)
    - 구독·좋아요 마무리 outro (자체 제작, 4초)
"""
from __future__ import annotations

import json as _json
import subprocess as _sub
import sys
import time as _time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/Users/kyusik/ContentsMaker")
sys.path.insert(0, str(ROOT))

from src.analyzer.political_plan_models import ThreePlansResult  # noqa: E402
from src.analyzer.political_planner import plan_to_script  # noqa: E402
from src.dem_shorts.editor.segment_cutter import cut_segment  # noqa: E402
from src.video.renderer import render_video  # noqa: E402

# Reuse build_plan() from sibling script
from scripts.render_political_pro_custom_plan import build_plan  # noqa: E402

OUT_DIR = ROOT / "data/political_pro/20260615_193552_cli"
SRC_OBS = OUT_DIR / "_hUJOG82az0.mp4"
SRC_JANG = OUT_DIR / "jang_dong_hyuk_xMZuzO3gXs4.mp4"
CACHED_AUDIO = (
    ROOT / "data/audio/20260615_195349_민주당_지지율_하락_읽고_던진_국민의힘의_전면_재선거.mp3"
)
CACHED_TIMING = (
    ROOT
    / "data/audio/20260615_195349_민주당_지지율_하락_읽고_던진_국민의힘의_전면_재선거.timing.json"
)

WIDTH, HEIGHT = 1080, 1920
FPS = 30
KOREAN_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


# ───────────────────────────── helpers (ffmpeg + PIL) ─────────────────────────────


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
    font_size: int = 64,
    y_offset_frac: float = 0.74,
    bottom_label: str = "",
) -> None:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(KOREAN_FONT, font_size, index=1)
    label_font = ImageFont.truetype(KOREAN_FONT, 38, index=1)

    line_gap = int(font_size * 0.35)
    line_h = []
    for line in text_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_h.append(bbox[3] - bbox[1])
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


def cut_segment_with_audio_letterbox(
    *, src: Path, start: float, end: float, out: Path,
    subtitle_png: Path | None = None,
) -> None:
    """Cut [start, end] from src, scale+letterbox to 1080x1920, keep audio.
    Optional subtitle overlay PNG. Re-encode to match Remotion output codec.
    """
    dur = end - start
    vf = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )
    cmd: list[str] = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.3f}", "-i", str(src),
    ]
    if subtitle_png:
        cmd += ["-i", str(subtitle_png)]
    cmd += ["-t", f"{dur:.3f}"]
    if subtitle_png:
        cmd += [
            "-filter_complex",
            f"[0:v]{vf}[v0];[v0][1:v]overlay=0:0:format=auto[vout]",
            "-map", "[vout]", "-map", "0:a?",
        ]
    else:
        cmd += ["-vf", vf, "-map", "0:v", "-map", "0:a?"]
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def concat_videos(parts: list[Path], out: Path) -> None:
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]
    filter_parts = []
    for i in range(len(parts)):
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")
    fc = "".join(filter_parts) + f"concat=n={len(parts)}:v=1:a=1[vout][aout]"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


# ───────────────────────────── outro builder ─────────────────────────────


def build_subscribe_outro(out: Path, *, duration: float = 4.0) -> None:
    """1080×1920 gradient bg + '구독·좋아요 부탁드립니다 🔔' centered. Silent audio."""
    # 1) gradient bg PNG (red→dark) — fits 보수 정치 톤
    bg = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    top = (180, 30, 30)
    bot = (15, 15, 15)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        for x in range(WIDTH):
            bg.putpixel((x, y), (r, g, b))
    # faster: use ImageDraw.line
    bg2 = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(bg2)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # 2) text
    big = ImageFont.truetype(KOREAN_FONT, 100, index=1)
    small = ImageFont.truetype(KOREAN_FONT, 56, index=1)

    line1 = "구독·좋아요"
    line2 = "부탁드립니다 🔔"
    line3 = "정치 분석 매일 업로드"

    def _draw_centered(draw, txt, font, y, fill, outline=(0, 0, 0)):
        bbox = draw.textbbox((0, 0), txt, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2 - bbox[0]
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                draw.text((x + dx, y + dy), txt, font=font, fill=outline)
        draw.text((x, y), txt, font=font, fill=fill)

    d = ImageDraw.Draw(bg2)
    _draw_centered(d, line1, big, 700, fill=(255, 255, 255))
    _draw_centered(d, line2, big, 850, fill=(255, 230, 80))
    _draw_centered(d, line3, small, 1080, fill=(220, 220, 220))

    png = OUT_DIR / "outro_subscribe.png"
    bg2.save(png, "PNG")

    # 3) ffmpeg: still PNG → video + silent audio for `duration` sec
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


# ───────────────────────────── main ─────────────────────────────


def main() -> int:
    plans_json = OUT_DIR / "plans.json"
    existing = ThreePlansResult.from_dict(_json.loads(plans_json.read_text(encoding="utf-8")))
    yt_title = existing.video_title
    yt_channel = existing.video_channel
    duration_sec = existing.video_duration_sec
    url = existing.youtube_url

    plan = build_plan()
    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel=yt_channel,
        source_title=yt_title,
        youtube_url=url,
    )
    print(f"✅ script ready — {len(script.scenes)}씬, {script.metadata.duration}초",
          file=sys.stderr)

    # Reuse cached TTS audio + timings (Charon variance avoidance)
    timings = _json.loads(CACHED_TIMING.read_text(encoding="utf-8"))
    audio_path = CACHED_AUDIO
    print(f"✅ cached audio: {audio_path.name}", file=sys.stderr)

    # Build mixed scene_videos
    main_timings = sorted(
        [t for t in timings if t["scene_id"] != -1], key=lambda x: x["scene_id"]
    )

    # Jang clip cover scenes 0–5 starting at 60s
    JANG_START = 60.0
    # OBS clip cover scenes 6–7 starting at 38s (climactic 결국 6.3 지선...)
    OBS_START = 38.0

    ts = int(_time.time())
    scene_videos: list[dict] = []
    jang_cursor = JANG_START
    obs_cursor = OBS_START

    for t in main_timings:
        sid = t["scene_id"]
        scene_dur = (t["end_ms"] - t["start_ms"]) / 1000.0
        if sid <= 5:
            ns = jang_cursor
            ne = jang_cursor + scene_dur
            src = SRC_JANG
            jang_cursor = ne
        else:
            ns = obs_cursor
            ne = obs_cursor + scene_dur
            src = SRC_OBS
            obs_cursor = ne
        out_file = OUT_DIR / f"scene_jangmix_{ts}_{sid:02d}.mp4"
        cut_segment(input_path=src, output_path=out_file,
                    start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    print(f"✅ mixed scene_videos: {len(scene_videos)} (0–5=jang, 6–7=obs)",
          file=sys.stderr)

    print("🎬 Remotion 렌더 중...", file=sys.stderr)
    v2_mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        scene_timings=timings,
        output_dir=OUT_DIR,
        use_bgm=True,
        enable_transitions=False,
        enable_sfx=False,
    )
    print(f"✅ V2 (jang mix): {v2_mp4}", file=sys.stderr)

    # 대변인 인터뷰 클립 (재사용 가능하면 재생성)
    spokes_sub_png = OUT_DIR / "spokesperson_subtitle.png"
    if not spokes_sub_png.exists():
        render_subtitle_png(
            text_lines=["의견은 조금씩 달랐지만", "결론에는 모두 동의했습니다"],
            out_path=spokes_sub_png,
            font_size=68,
            bottom_label="— 국민의힘 대변인 (OBS뉴스)",
        )
    spokes_clip = OUT_DIR / f"spokesperson_clip_{ts}.mp4"
    cut_segment_with_audio_letterbox(
        src=SRC_OBS, start=88.5, end=100.5,
        out=spokes_clip, subtitle_png=spokes_sub_png,
    )
    print(f"✅ 대변인 클립: {spokes_clip}", file=sys.stderr)

    # 구독·좋아요 outro
    outro_mp4 = OUT_DIR / f"outro_subscribe_{ts}.mp4"
    build_subscribe_outro(outro_mp4, duration=4.0)
    print(f"✅ outro: {outro_mp4}", file=sys.stderr)

    # Final concat
    final = OUT_DIR / f"FINAL_jang_mix_{ts}.mp4"
    print(f"🎬 concat → {final.name}", file=sys.stderr)
    concat_videos([v2_mp4, spokes_clip, outro_mp4], final)
    print(f"✅ FINAL: {final}", file=sys.stderr)
    print(str(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
