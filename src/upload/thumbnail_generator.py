"""YouTube thumbnail auto-generator (MID-05).

Captures a hook-scene frame from the rendered video and overlays a
Pretendard ExtraBold title with red/yellow highlight — the political-YouTube
standard look (frame close-up + bold 2-line title on upper third).

Pipeline:
    generate_thumbnail_from_script(script, video_path, output_dir)
      -> capture_hook_frame (ffmpeg subprocess)
      -> compose_thumbnail  (PIL: crop + overlay)
      -> {output_dir}/{stem}.thumb.png (1280x720)
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from src.analyzer.script_models import ShortsScript


THUMB_WIDTH = 1280
THUMB_HEIGHT = 720

# Title sits in the lower half so it clears the YouTube Shorts navigation bar
# (back button + search icon overlay the top ~10–15% of the display).
TEXT_TOP_PERCENT = 0.50
TEXT_Y_OFFSET = 20

# Political-YouTube palette.
COLOR_CONTEXT = "#DC143C"   # crimson red — context words
COLOR_HIGHLIGHT = "#FFD93D"  # bright yellow — highlight words
COLOR_STROKE = "#000000"
STROKE_WIDTH = 10

# Font hunt order: project-local asset → system Pretendard → PIL default.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
FONT_CANDIDATES = (
    _PROJECT_ROOT / "assets" / "fonts" / "Pretendard-ExtraBold.otf",
    _PROJECT_ROOT / "assets" / "fonts" / "Pretendard-Bold.otf",
    Path("/System/Library/Fonts/Supplemental/AppleSDGothicNeo.ttc"),
    Path("/Library/Fonts/NanumSquareB.ttf"),
)
TITLE_FONT_SIZE = 96


def compute_text_position(
    canvas_height: int = THUMB_HEIGHT,
    top_percent: float = TEXT_TOP_PERCENT,
    y_offset: int = TEXT_Y_OFFSET,
) -> int:
    """Return the y-coordinate where thumbnail title text should start."""
    return int(canvas_height * top_percent) + y_offset


def _resolve_font(size: int = TITLE_FONT_SIZE) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load Pretendard ExtraBold if present, else fall back."""
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def capture_hook_frame(
    video_path: Path,
    time_sec: float = 0.8,
    output_path: Path | None = None,
) -> Path:
    """Extract one frame from the video at ``time_sec`` using ffmpeg.

    If the first attempt fails (e.g. hook scene shorter than ``time_sec``),
    retry at ``0.3s``. Raises ``RuntimeError`` if both attempts fail.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_path is None:
        output_path = video_path.with_suffix(".hookframe.png")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fallback_sec = 0.3 if time_sec > 0.3 else 0.0
    attempts: list[float] = [time_sec]
    if fallback_sec != time_sec:
        attempts.append(fallback_sec)

    last_stderr: bytes = b""
    for t in attempts:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{t}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and output_path.exists():
            return output_path
        last_stderr = result.stderr or b""

    raise RuntimeError(
        f"ffmpeg failed to extract frame from {video_path}: "
        f"{last_stderr.decode('utf-8', errors='replace')[:200]}"
    )


def _crop_to_canvas(frame: Image.Image, width: int, height: int) -> Image.Image:
    """Resize & center-crop a frame to the target canvas."""
    target_ratio = width / height
    src_w, src_h = frame.size
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # Frame is wider — scale by height, crop sides.
        new_h = height
        new_w = int(src_ratio * new_h)
    else:
        new_w = width
        new_h = int(new_w / src_ratio)

    resized = frame.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill: str,
    stroke_width: int = STROKE_WIDTH,
) -> None:
    """Draw text with a solid black stroke outline (10px)."""
    try:
        draw.text(
            xy, text, font=font, fill=fill,
            stroke_width=stroke_width, stroke_fill=COLOR_STROKE,
            anchor="mm",
        )
    except TypeError:
        # Very old Pillow without stroke support — fallback emits offset copies.
        x, y = xy
        for dx in range(-stroke_width, stroke_width + 1, 2):
            for dy in range(-stroke_width, stroke_width + 1, 2):
                draw.text((x + dx, y + dy), text, font=font, fill=COLOR_STROKE, anchor="mm")
        draw.text(xy, text, font=font, fill=fill, anchor="mm")


def _split_title(title: str) -> list[str]:
    """Split title into up to 2 lines. Respect existing newlines; else balance."""
    title = (title or "").strip()
    if not title:
        return []
    if "\n" in title:
        return [line.strip() for line in title.split("\n") if line.strip()][:2]
    if len(title) <= 10:
        return [title]
    # Balance on whitespace nearest the middle, else hard split.
    mid = len(title) // 2
    for radius in range(0, len(title) // 2):
        for cand in (mid - radius, mid + radius):
            if 0 < cand < len(title) and title[cand] == " ":
                return [title[:cand].strip(), title[cand + 1:].strip()]
    return [title[:mid], title[mid:]]


def compose_thumbnail(
    frame_path: Path,
    title: str,
    output_path: Path,
    highlight_words: Iterable[str] | None = None,
    width: int = THUMB_WIDTH,
    height: int = THUMB_HEIGHT,
) -> Path:
    """Compose a 1280x720 thumbnail: frame background + bold title overlay."""
    frame_path = Path(frame_path)
    if not frame_path.exists():
        raise FileNotFoundError(f"Frame not found: {frame_path}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(frame_path) as src:
        canvas = _crop_to_canvas(src.convert("RGB"), width, height)

    lines = _split_title(title)
    if lines:
        font = _resolve_font(TITLE_FONT_SIZE)
        draw = ImageDraw.Draw(canvas)
        highlights = {w for w in (highlight_words or ()) if w}

        y_start = compute_text_position(canvas_height=height)
        line_height = int(TITLE_FONT_SIZE * 1.15)
        for i, line in enumerate(lines):
            is_highlight = any(hw in line for hw in highlights)
            fill = COLOR_HIGHLIGHT if is_highlight else COLOR_CONTEXT
            y = y_start + i * line_height
            _draw_outlined_text(draw, (width // 2, y), line, font, fill)

    canvas.save(output_path, "PNG", optimize=True)
    return output_path


def _pick_hook_timestamp(script: ShortsScript) -> float:
    """Return seek time into the video for the representative frame."""
    for scene in script.scenes:
        if getattr(scene, "hook", False) and scene.duration > 0:
            # Mid-scene gives a more expressive frame than the cut-in.
            return max(scene.timestamp + min(scene.duration / 2, 0.8), 0.3)
    return 0.8


def generate_thumbnail_from_script(
    script: ShortsScript,
    video_path: Path,
    output_dir: Path,
) -> Path:
    """Capture hook frame from ``video_path`` and compose a thumbnail.

    Output is saved as ``{output_dir}/{video_stem}.thumb.png``.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = output_dir / f"{video_path.stem}.thumb.png"
    frame_path = output_dir / f"{video_path.stem}.hookframe.png"

    t = _pick_hook_timestamp(script)
    capture_hook_frame(video_path, time_sec=t, output_path=frame_path)

    title = script.metadata.title or ""
    highlights = tuple(
        w
        for scene in script.scenes
        for w in (scene.highlight_words or ())
    )

    compose_thumbnail(
        frame_path=frame_path,
        title=title,
        output_path=thumb_path,
        highlight_words=highlights,
    )

    try:
        frame_path.unlink()
    except OSError:
        pass

    return thumb_path
