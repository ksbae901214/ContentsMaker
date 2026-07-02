"""V3 하이브리드 정치쇼츠 렌더러.

각 HybridBeat을 한 개의 mp4 청크로 변환하고, 마지막에 ffmpeg concat 재인코딩으로
합친다. 자막은 Pillow PNG overlay (Remotion `SceneText.tsx`의 Noto Sans KR과 동일
폰트로 시각적 통일).

TTS 비트 — 사전 합성된 Charon mp3에서 [start, end] 구간을 추출 + 배경 영상(mute) +
   자막 PNG overlay
원본 비트 — 소스 영상 [start, end] 컷 + 원본 음성 유지 + 자막 PNG overlay
공통 — 1080×1920, h264 yuv420p, AAC 48kHz, 30fps, loudnorm 정규화
"""
from __future__ import annotations

import subprocess as _sub
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.analyzer.hybrid_plan_models import HybridBeat, HybridShortsPlan

# ─── 캔버스 / 코덱 상수 ─────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1080, 1920
FPS = 30
AUDIO_RATE = 48000
AUDIO_CH = 2

# ─── 폰트 (Remotion SceneText와 통일) ─────────────────────────────────────────
NOTO_BLACK = Path.home() / "Library/Fonts/NotoSansCJKkr-Black.otf"
NOTO_MEDIUM = Path.home() / "Library/Fonts/NotoSansCJKkr-Medium.otf"
NOTO_LIGHT = Path.home() / "Library/Fonts/NotoSansCJKkr-Light.otf"


SUBTITLE_COLORS = {
    "white": (255, 255, 255),
    "red": (255, 90, 90),
    "yellow": (255, 230, 80),
    "blue": (130, 200, 255),
}


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    path = {
        "black": NOTO_BLACK, "medium": NOTO_MEDIUM, "light": NOTO_LIGHT,
    }[weight]
    return ImageFont.truetype(str(path), size)


# ─── ffmpeg 실행기 ────────────────────────────────────────────────────────────
def _run(cmd: list[str]) -> None:
    print("$", " ".join(cmd[:4]), "...", file=sys.stderr)
    res = _sub.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:3])}")


# ─── 자막 PNG 렌더 (Noto Sans KR) ─────────────────────────────────────────────
@dataclass(frozen=True)
class SubtitleStyle:
    lines: tuple[str, ...]
    color_name: str = "white"        # white/red/yellow/blue
    emphasis: bool = False           # True → Black weight + larger
    y_center_frac: float = 0.74      # 화면 세로 위치 (0=top, 1=bottom)
    bottom_label: str = ""           # e.g. "— 대변인 (OBS뉴스)"


def render_title_banner_png(
    *,
    text: str,
    out_path: Path,
    font_size: int = 80,
    y_top: int = 130,
) -> None:
    """상단 제목 띠 PNG — outro 제외 모든 비트에 overlay 되는 영구 자막.

    노란색 굵은 글씨 + 반투명 검은 배경 박스로 가독성 확보.
    Remotion `SceneText.tsx`와 동일한 Noto Sans KR Black 사용.
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font("black", font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x, pad_y = 40, 26
    band_w = text_w + pad_x * 2
    band_h = text_h + pad_y * 2
    band_left = (WIDTH - band_w) // 2
    band_top = y_top

    # 반투명 검은 배경 박스
    band = Image.new("RGBA", (band_w, band_h), (0, 0, 0, 180))
    img.paste(band, (band_left, band_top))

    # 텍스트 (검정 외곽선 + 노란색)
    tx = band_left + pad_x - bbox[0]
    ty = band_top + pad_y
    for dx in (-3, -2, 0, 2, 3):
        for dy in (-3, -2, 0, 2, 3):
            draw.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 235))
    draw.text((tx, ty), text, font=font, fill=(255, 230, 80, 255))

    img.save(out_path, "PNG")


def render_subtitle_png(*, style: SubtitleStyle, out_path: Path) -> None:
    """1080×1920 투명 PNG에 다줄 자막 + 선택적 하단 라벨을 그린다.

    글자: Noto Sans CJK KR Black(강조) 또는 Medium(기본). 검정 외곽선으로 가독성 확보.
    하단 라벨: Light weight + 노란색 (인용 출처 강조).
    """
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    fg = SUBTITLE_COLORS.get(style.color_name, SUBTITLE_COLORS["white"])
    # 폰트 통일 (2026-06-16) — 원본 비트·TTS 비트 모두 Noto Sans CJK KR Black 사용.
    # emphasis 차이는 크기에만 반영 (4px 차이) → 시각적 통일감 확보.
    size = 80 if style.emphasis else 76
    main_font = _font("black", size)
    label_font = _font("black", 36)

    # 줄 높이 계산
    line_h: list[int] = []
    for ln in style.lines:
        bbox = draw.textbbox((0, 0), ln, font=main_font)
        line_h.append(bbox[3] - bbox[1])
    line_gap = int(size * 0.32)
    block_h = sum(line_h) + line_gap * (len(style.lines) - 1)
    y = int(HEIGHT * style.y_center_frac) - block_h // 2

    for ln in style.lines:
        bbox = draw.textbbox((0, 0), ln, font=main_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (WIDTH - w) // 2 - bbox[0]
        # 검정 외곽선 (가독성)
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                draw.text((x + dx, y + dy), ln, font=main_font, fill=(0, 0, 0, 235))
        draw.text((x, y), ln, font=main_font, fill=(*fg, 255))
        y += h + line_gap

    if style.bottom_label:
        bbox = draw.textbbox((0, 0), style.bottom_label, font=label_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2 - bbox[0]
        ly = y + 24
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                draw.text((x + dx, ly + dy), style.bottom_label,
                          font=label_font, fill=(0, 0, 0, 230))
        draw.text((x, ly), style.bottom_label, font=label_font,
                  fill=(255, 230, 80, 255))

    img.save(out_path, "PNG")


# ─── 청크 빌더 ────────────────────────────────────────────────────────────────
def build_tts_beat(
    *,
    beat: HybridBeat,
    background_clip: Path,
    background_offset_sec: float,
    tts_audio_full: Path,
    tts_start_sec: float,
    tts_end_sec: float,
    subtitle_png: Path,
    out: Path,
    title_banner_png: Path | None = None,
    speed: float = 1.0,
) -> None:
    """TTS 비트 청크 생성.

    background_clip[offset, offset+dur]를 mute로 깔고, tts_audio_full[start, end]를
    오디오 트랙으로 입힌 뒤 자막 PNG를 overlay한다. dur는 TTS 음성 길이 기준.

    speed: 1.0이면 원본 속도, 1.2이면 음성/영상 모두 1.2배 빠르게 (출력 길이 단축).
    title_banner_png: 지정 시 상단 제목 띠를 추가 overlay (outro 제외 비트에 영구 표시).
    """
    dur = tts_end_sec - tts_start_sec
    out_dur = dur / speed
    vf = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )
    if speed != 1.0:
        vf += f",setpts=PTS/{speed}"

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        # bg video — 입력 단에서 dur초로 잘라야 setpts 적용 후 정확히 out_dur 출력됨
        "-ss", f"{background_offset_sec:.3f}", "-t", f"{dur:.3f}",
        "-i", str(background_clip),
        # tts audio segment
        "-ss", f"{tts_start_sec:.3f}", "-t", f"{dur:.3f}",
        "-i", str(tts_audio_full),
        # subtitle png (loop)
        "-loop", "1", "-t", f"{out_dur:.3f}", "-i", str(subtitle_png),
    ]
    if title_banner_png:
        cmd += ["-loop", "1", "-t", f"{out_dur:.3f}", "-i", str(title_banner_png)]

    # filter chain
    chain = f"[0:v]{vf}[v0];[v0][2:v]overlay=0:0:format=auto[v1]"
    if title_banner_png:
        chain += ";[v1][3:v]overlay=0:0:format=auto[vout]"
        v_label = "vout"
    else:
        v_label = "v1"

    if speed != 1.0:
        chain += (
            f";[1:a]aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo,"
            f"atempo={speed},loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )
    else:
        chain += (
            f";[1:a]aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )

    cmd += [
        "-filter_complex", chain,
        "-map", f"[{v_label}]", "-map", "[aout]",
        "-t", f"{out_dur:.3f}",
        "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CH), "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def build_original_beat(
    *,
    beat: HybridBeat,
    source_clip: Path,
    subtitle_png: Path,
    out: Path,
    title_banner_png: Path | None = None,
) -> None:
    """원본 비트 청크 생성.

    소스 영상의 [clip_start_sec, clip_end_sec]를 잘라서 letterbox로 9:16 캔버스에
    배치, 원본 음성 유지, 자막 PNG overlay. loudnorm으로 TTS와 음량 정합.
    title_banner_png: 지정 시 상단 제목 띠를 추가 overlay (지속 표시).
    """
    dur = beat.clip_end_sec - beat.clip_start_sec
    vf = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{beat.clip_start_sec:.3f}", "-i", str(source_clip),
        "-i", str(subtitle_png),
    ]
    if title_banner_png:
        cmd += ["-i", str(title_banner_png)]

    chain = f"[0:v]{vf}[v0];[v0][1:v]overlay=0:0:format=auto[v1]"
    if title_banner_png:
        chain += ";[v1][2:v]overlay=0:0:format=auto[vout]"
        v_label = "vout"
    else:
        v_label = "v1"
    chain += (
        f";[0:a]aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )

    cmd += [
        "-t", f"{dur:.3f}",
        "-filter_complex", chain,
        "-map", f"[{v_label}]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CH), "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def build_original_beat_timed_subs(
    *,
    beat: HybridBeat,
    source_clip: Path,
    timed_subs: list[tuple[float, float, Path]],
    out: Path,
) -> None:
    """원본 비트 청크 생성 — 시간 따라 자막이 교체되는 버전.

    추출 구간 안에서 화자가 말하는 내용 전체가 자막으로 다 나오도록, 여러 자막 PNG를
    `enable='between(t,a,b)'`로 순차 overlay 한다.

    Args:
        timed_subs: [(rel_start_sec, rel_end_sec, png_path), ...]
            클립 시작 기준 상대 시간. 인접 자막 간 갭은 비워두어도 무방
            (그 시간엔 자막 없음).
    """
    dur = beat.clip_end_sec - beat.clip_start_sec
    vf = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS}"
    )
    inputs: list[str] = [
        "-ss", f"{beat.clip_start_sec:.3f}", "-i", str(source_clip),
    ]
    for _, _, png in timed_subs:
        inputs += ["-i", str(png)]

    # overlay 체인 구성. v0 = letterbox된 비디오. 각 자막은 enable로 표시 구간 제한.
    chain = f"[0:v]{vf}[v0]"
    prev_label = "v0"
    for i, (s, e, _) in enumerate(timed_subs):
        next_label = f"v{i + 1}"
        chain += (
            f";[{prev_label}][{i + 1}:v]"
            f"overlay=0:0:enable='between(t,{s:.3f},{e:.3f})':format=auto"
            f"[{next_label}]"
        )
        prev_label = next_label
    chain += (
        f";[0:a]aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-t", f"{dur:.3f}",
        "-filter_complex", chain,
        "-map", f"[{prev_label}]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CH), "-b:a", "192k",
        str(out),
    ]
    _run(cmd)


def build_subscribe_outro(*, out: Path, source_label: str, duration: float = 4.0) -> None:
    """단일 종료 카드 (구독·좋아요 + 출처 라벨 통합)."""
    bg = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    d = ImageDraw.Draw(bg)
    top, bot = (180, 30, 30), (15, 15, 15)
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = (
            int(top[0] * (1 - t) + bot[0] * t),
            int(top[1] * (1 - t) + bot[1] * t),
            int(top[2] * (1 - t) + bot[2] * t),
        )
        d.line([(0, y), (WIDTH, y)], fill=c)

    big = _font("black", 110)
    mid = _font("medium", 60)
    tiny = _font("light", 30)

    def _draw(d, txt, font, y, fill):
        bbox = d.textbbox((0, 0), txt, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2 - bbox[0]
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                d.text((x + dx, y + dy), txt, font=font, fill=(0, 0, 0))
        d.text((x, y), txt, font=font, fill=fill)

    _draw(d, "구독·좋아요", big, 700, (255, 255, 255))
    _draw(d, "부탁드립니다 🔔", big, 850, (255, 230, 80))
    _draw(d, "정치 분석 매일 업로드", mid, 1080, (220, 220, 220))
    if source_label:
        _draw(d, source_label, tiny, 1820, (180, 180, 180))

    png = out.with_suffix(".png")
    bg.save(png, "PNG")

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-t", f"{duration:.2f}", "-i", str(png),
        "-f", "lavfi", "-t", f"{duration:.2f}", "-i",
        f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_RATE}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CH), "-b:a", "192k",
        "-shortest", str(out),
    ]
    _run(cmd)


def build_outro_from_image(
    *,
    image_path: Path,
    out: Path,
    duration: float = 4.0,
    source_label: str = "",
) -> None:
    """기존 outro 이미지(예: public/outro.png) 사용 + 선택적 하단 출처 라벨 오버레이.

    이미지가 1080×1920이 아니면 letterbox로 맞춤. source_label 있으면 PIL로 라벨 PNG를
    그려서 overlay 한다.
    """
    label_png: Path | None = None
    if source_label:
        lbl = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        d = ImageDraw.Draw(lbl)
        font = _font("light", 28)
        bbox = d.textbbox((0, 0), source_label, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2 - bbox[0]
        y = HEIGHT - 60
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                d.text((x + dx, y + dy), source_label,
                       font=font, fill=(0, 0, 0, 230))
        d.text((x, y), source_label, font=font, fill=(200, 200, 200, 255))
        label_png = out.with_name(out.stem + "_label.png")
        lbl.save(label_png, "PNG")

    vf_scale = (
        f"scale=w={WIDTH}:h={HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-t", f"{duration:.2f}", "-i", str(image_path),
    ]
    if label_png:
        cmd += ["-loop", "1", "-t", f"{duration:.2f}", "-i", str(label_png)]
    cmd += [
        "-f", "lavfi", "-t", f"{duration:.2f}", "-i",
        f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_RATE}",
    ]
    if label_png:
        fc = (
            f"[0:v]{vf_scale}[v0];"
            f"[v0][1:v]overlay=0:0:format=auto[vout]"
        )
        cmd += [
            "-filter_complex", fc,
            "-map", "[vout]", "-map", "2:a",
        ]
    else:
        cmd += [
            "-vf", vf_scale,
            "-map", "0:v", "-map", "1:a",
        ]
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CH), "-b:a", "192k",
        "-shortest", str(out),
    ]
    _run(cmd)


def concat_chunks(parts: list[Path], out: Path) -> None:
    """모든 청크를 재인코딩 concat (codec 통일 + PTS 안정성)."""
    inputs: list[str] = []
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
        "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-ar", str(AUDIO_RATE), "-ac", str(AUDIO_CH), "-b:a", "192k",
        str(out),
    ]
    _run(cmd)
