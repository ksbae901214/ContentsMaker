"""T070: BGM manifest 로드/검증 + 등록 (R-11, FR-035).

쇼츠 렌더링 시 BGM은 반드시 manifest에 등록된 파일만 사용 가능.
저작권 확인된 파일만 등록.

Manifest 스키마:
{
  "tracks": [
    {"filename": "calm_01.mp3", "mood": "calm", "license": "CC0 / Artist"}
  ]
}
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.dem_shorts.utils.paths import BGM_DIR, BGM_MANIFEST

logger = logging.getLogger(__name__)


class BgmManifestError(Exception):
    """Raised when BGM manifest operation fails."""


def load_manifest(path: Path = BGM_MANIFEST) -> dict:
    """Manifest 로드. 파일 없으면 빈 구조 반환."""
    if not path.exists():
        return {"tracks": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BgmManifestError(f"manifest JSON 파싱 실패: {exc}") from exc
    if "tracks" not in data or not isinstance(data["tracks"], list):
        raise BgmManifestError(f"manifest 'tracks' 필드 누락 또는 타입 오류")
    return data


def save_manifest(data: dict, path: Path = BGM_MANIFEST) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_registered(filename: str | None, path: Path = BGM_MANIFEST) -> bool:
    """None은 등록된 것으로 간주 (BGM 미사용 허용)."""
    if filename is None:
        return True
    data = load_manifest(path)
    return any(t.get("filename") == filename for t in data["tracks"])


def validate_bgm_filename(filename: str | None, path: Path = BGM_MANIFEST) -> None:
    """FR-035: 미등록 파일 거부."""
    if filename is None:
        return
    if not is_registered(filename, path):
        raise BgmManifestError(
            f"BGM '{filename}' is not registered in manifest {path}. "
            "Use `bgm-register` CLI to add it after verifying license."
        )


def register_bgm(
    manifest_path: Path,
    *,
    filename: str,
    mood: str,
    license_text: str,
    audio_path: Path,
) -> None:
    """저작권 확인된 BGM 파일을 manifest에 등록.

    Validations:
    - license_text 필수 (빈 문자열 금지)
    - audio_path 존재 및 비어있지 않음
    - filename 중복 시 덮어쓰기 없이 스킵
    """
    if not license_text or not license_text.strip():
        raise BgmManifestError("license_text required (CC0, CC-BY, or paid license ID)")

    if not audio_path.exists():
        raise BgmManifestError(f"audio file not found: {audio_path}")
    if audio_path.stat().st_size == 0:
        raise BgmManifestError(f"audio file is empty: {audio_path}")

    data = load_manifest(manifest_path)
    if any(t.get("filename") == filename for t in data["tracks"]):
        logger.info("bgm '%s' already registered, skipping", filename)
        return

    data["tracks"].append({
        "filename": filename,
        "mood": mood,
        "license": license_text.strip(),
        "size_bytes": audio_path.stat().st_size,
    })
    save_manifest(data, manifest_path)
    logger.info("bgm registered: %s (mood=%s)", filename, mood)


def get_bgm_path(filename: str) -> Path:
    """Manifest 등록된 파일의 실제 디스크 경로 반환."""
    validate_bgm_filename(filename)
    return BGM_DIR / filename
