"""T023 [US1]: Remotion V3 렌더러 — subprocess로 npx remotion render 호출.

자산 격리: remotion_v3/public/ 에 audio/clips/cards 복사 후 렌더.
효과음·전환 효과 0 락인 (FR-034/035) — Remotion 컴포넌트 측에서 보장.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.jpolitics.models.script import JpoliticsScript
    from src.jpolitics.tts.voice import SceneTiming

from src.jpolitics.constants import REMOTION_V3_DIR, REMOTION_V3_PUBLIC_DIR
from src.jpolitics.logger import get_logger

logger = get_logger("video.renderer")


def _convert_to_camel_case(snake_dict: dict) -> dict:
    """snake_case → camelCase 재귀 변환 (Remotion props 호환)."""
    if not isinstance(snake_dict, dict):
        if isinstance(snake_dict, list):
            return [_convert_to_camel_case(x) for x in snake_dict]  # type: ignore[return-value]
        return snake_dict
    out = {}
    for k, v in snake_dict.items():
        parts = k.split("_")
        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
        out[camel] = _convert_to_camel_case(v) if isinstance(v, (dict, list)) else v
    return out


def _copy_assets(
    script: "JpoliticsScript", audio_path: Path
) -> None:
    """audio.mp3 + 씬별 clips + 카드 사진을 remotion_v3/public/ 으로 복사."""
    pub = REMOTION_V3_PUBLIC_DIR
    pub.mkdir(parents=True, exist_ok=True)
    (pub / "clips").mkdir(exist_ok=True)
    (pub / "cards").mkdir(exist_ok=True)

    # Audio
    if audio_path.exists():
        shutil.copy2(audio_path, pub / "audio.mp3")

    # Clips
    for scene in script.scenes:
        if scene.clip_path and Path(scene.clip_path).exists():
            dest = pub / "clips" / f"clip_{scene.id}.mp4"
            shutil.copy2(scene.clip_path, dest)

    # Cards
    for scene in script.scenes:
        if not scene.comparison_cards:
            continue
        for card in scene.comparison_cards:
            if card.photo_path and Path(card.photo_path).exists():
                dest = pub / "cards" / f"{card.name}.jpg"
                if not dest.exists():
                    shutil.copy2(card.photo_path, dest)


def _build_props(
    script: "JpoliticsScript",
    scene_timings: list["SceneTiming"],
) -> dict:
    """script + timings → Remotion JpoliticsComposition props (camelCase)."""
    script_dict = script.to_dict()
    # Audio.audio_path를 public/ 상대경로로
    script_dict["audio"]["audio_path"] = "audio.mp3"
    # Clips
    for scene_dict in script_dict["scenes"]:
        if scene_dict.get("clip_path"):
            scene_dict["clip_path"] = f"clips/clip_{scene_dict['id']}.mp4"
        if scene_dict.get("comparison_cards"):
            for card_dict in scene_dict["comparison_cards"]:
                if card_dict.get("photo_path"):
                    card_dict["photo_path"] = f"cards/{card_dict['name']}.jpg"
    # Timings
    script_dict["audio"]["scene_timings"] = [
        {"scene_id": t.scene_id, "start_ms": t.start_ms, "end_ms": t.end_ms}
        for t in scene_timings
    ]
    return _convert_to_camel_case(script_dict)


def render(
    *,
    script: "JpoliticsScript",
    audio_path: Path,
    scene_timings: list["SceneTiming"],
    output_path: Path,
) -> Path:
    """JpoliticsShorts composition → MP4 렌더.

    Returns:
        output_path (실제 생성된 mp4 경로)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _copy_assets(script, audio_path)
    props = _build_props(script, scene_timings)
    props_json = json.dumps(props, ensure_ascii=False)

    cmd = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "JpoliticsShorts",
        str(output_path.absolute()),
        f"--props={props_json}",
        "--codec=h264",
    ]
    logger.info(
        "Remotion V3 render → %s (cwd=%s)", output_path, REMOTION_V3_DIR
    )
    result = subprocess.run(
        cmd,
        cwd=str(REMOTION_V3_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(
            "Remotion render failed:\nstdout: %s\nstderr: %s",
            result.stdout,
            result.stderr,
        )
        raise RuntimeError(f"Remotion render failed (exit {result.returncode})")
    return output_path
