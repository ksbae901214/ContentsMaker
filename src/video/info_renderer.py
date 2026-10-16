"""정보쇼츠 V1.0 Remotion 렌더러 — `InfoShorts` 컴포지션 전용 (045).

`renderer.render_video`(BlindShorts) 를 거치지 않는다 — 그쪽은 BGM·아웃트로·SFX·
정치 오버레이 분기가 얽혀 있고, 이 포맷은 그중 아무것도 쓰지 않는다.
dem_shorts 처럼 컴포지션을 따로 두고 props JSON 을 넘긴다.
"""
from __future__ import annotations

import json
import logging
import math
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

FPS = 30
TAIL_FRAMES = FPS // 2           # 마지막 펀치라인 뒤 0.5초 여운 (벤치마크 끝 무음 0.75초)
COMPOSITION_ID = "InfoShorts"
REMOTION_ROOT = PROJECT_ROOT / "src" / "video" / "remotion"
REMOTION_PUBLIC = REMOTION_ROOT / "public"
FONTS_DIR = REMOTION_ROOT / "fonts"
RENDER_TIMEOUT_SEC = 1800


class InfoRenderError(Exception):
    """InfoShorts 렌더 실패."""


def duration_frames(duration_ms: int) -> int:
    return math.ceil(duration_ms * FPS / 1000) + TAIL_FRAMES


def _copy(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def stage_assets(props: dict, audio_path: Path | None, public_dir: Path, *, tag: str,
                 fonts_dir: Path = FONTS_DIR) -> tuple[dict, list[Path]]:
    """자산을 public/ 으로 복사하고 경로를 staticFile 이름으로 바꾼 새 props 를 만든다.

    Returns: (새 props, 렌더 후 지울 임시 파일들). 폰트는 다음 렌더도 쓰므로 남긴다.
    """
    staged: list[Path] = []
    images = []
    for i, img in enumerate(props["images"]):
        src = Path(img["path"])
        name = f"info_{tag}_img_{i:02d}{src.suffix.lower()}"
        staged.append(_copy(src, public_dir / name))
        images.append({k: v for k, v in img.items() if k != "path"} | {"file": name})
    audio_name = ""
    if audio_path is not None:
        audio_name = f"info_{tag}_audio{audio_path.suffix}"
        staged.append(_copy(audio_path, public_dir / audio_name))
    for font in sorted(fonts_dir.glob("*.[ot]tf")):
        target = public_dir / "fonts" / font.name
        if not target.exists():
            _copy(font, target)
    return {**props, "images": images, "audioFile": audio_name}, staged


def _run_remotion(props_path: Path, output_path: Path, frames: int) -> None:
    npx = shutil.which("npx")
    if not npx:
        raise InfoRenderError("npx 를 찾을 수 없습니다 — Node.js 가 필요합니다")
    cmd = [npx, "remotion", "render", "src/index.ts", COMPOSITION_ID, str(output_path),
           "--props", str(props_path), "--frames", f"0-{frames - 1}", "--codec", "h264"]
    try:
        result = subprocess.run(cmd, cwd=REMOTION_ROOT, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=RENDER_TIMEOUT_SEC)
    except subprocess.TimeoutExpired as exc:
        raise InfoRenderError(f"렌더 시간 초과 ({RENDER_TIMEOUT_SEC}초)") from exc
    if result.returncode != 0:
        tail = (result.stderr or result.stdout)[-800:]
        raise InfoRenderError(f"Remotion 렌더 실패 (exit {result.returncode}):\n{tail}")


def thumbnail_props(props: dict) -> dict:
    """썸네일용 props — 제목 + 커버 일러스트 + 워터마크만 (자막·줌 없음)."""
    cover = {**props["images"][0], "startMs": 0, "endMs": 1000, "zoomStartMs": None}
    return {**props, "images": [cover], "captions": [], "durationMs": 1000}


def render_thumbnail(props: dict, *, output_path: Path) -> Path:
    """첫 프레임 PNG (1080×1920). 업로드 시 커버로 쓴다."""
    tag = datetime.now().strftime("%Y%m%d_%H%M%S") + "_thumb"
    staged_props, staged = stage_assets(thumbnail_props(props), None, REMOTION_PUBLIC, tag=tag)
    props_path = output_path.with_suffix(".props.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    props_path.write_text(json.dumps(staged_props, ensure_ascii=False), encoding="utf-8")
    npx = shutil.which("npx")
    if not npx:
        raise InfoRenderError("npx 를 찾을 수 없습니다 — Node.js 가 필요합니다")
    cmd = [npx, "remotion", "still", "src/index.ts", COMPOSITION_ID, str(output_path.resolve()),
           "--props", str(props_path.resolve()), "--frame", "0"]
    try:
        result = subprocess.run(cmd, cwd=REMOTION_ROOT, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=300)
    finally:
        for f in staged:
            f.unlink(missing_ok=True)
        props_path.unlink(missing_ok=True)
    if result.returncode != 0 or not output_path.exists():
        raise InfoRenderError(f"썸네일 렌더 실패:\n{(result.stderr or result.stdout)[-800:]}")
    return output_path


def render_info_shorts(props: dict, *, audio_path: Path, output_path: Path) -> Path:
    """props(경로 포함) + 나레이션 → MP4. 임시 자산은 성공·실패와 무관하게 지운다."""
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    staged_props, staged = stage_assets(props, audio_path, REMOTION_PUBLIC, tag=tag)
    frames = duration_frames(props["durationMs"])
    props_path = output_path.with_suffix(".props.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    props_path.write_text(json.dumps(staged_props, ensure_ascii=False), encoding="utf-8")
    logger.info("InfoShorts 렌더 시작: %d프레임 (%.1f초)", frames, frames / FPS)
    try:
        _run_remotion(props_path, output_path.resolve(), frames)
    finally:
        for f in staged:
            f.unlink(missing_ok=True)
    if not output_path.exists():
        raise InfoRenderError(f"렌더 완료됐지만 출력 파일이 없습니다: {output_path}")
    return output_path
