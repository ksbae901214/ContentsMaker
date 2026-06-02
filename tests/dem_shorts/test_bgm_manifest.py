"""T071: BGM manifest 테스트 — 미등록 파일 거부 (R-11, FR-035).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dem_shorts.editor.bgm_manifest import (
    BgmManifestError,
    is_registered,
    load_manifest,
    register_bgm,
    validate_bgm_filename,
)


@pytest.fixture
def tmp_manifest(tmp_path: Path) -> Path:
    return tmp_path / "bgm_manifest.json"


class TestLoadManifest:
    def test_empty_when_missing(self, tmp_manifest: Path):
        data = load_manifest(tmp_manifest)
        assert data == {"tracks": []}

    def test_loads_existing(self, tmp_manifest: Path):
        tmp_manifest.write_text(
            json.dumps({
                "tracks": [
                    {"filename": "calm_01.mp3", "mood": "calm", "license": "CC0"},
                ]
            })
        )
        data = load_manifest(tmp_manifest)
        assert len(data["tracks"]) == 1
        assert data["tracks"][0]["filename"] == "calm_01.mp3"


class TestIsRegistered:
    def test_registered_filename(self, tmp_manifest: Path):
        tmp_manifest.write_text(
            json.dumps({"tracks": [{"filename": "a.mp3", "mood": "calm", "license": "CC0"}]})
        )
        assert is_registered("a.mp3", tmp_manifest) is True

    def test_unregistered_filename(self, tmp_manifest: Path):
        tmp_manifest.write_text(json.dumps({"tracks": []}))
        assert is_registered("unknown.mp3", tmp_manifest) is False

    def test_none_is_registered(self, tmp_manifest: Path):
        """BGM 미사용은 허용."""
        assert is_registered(None, tmp_manifest) is True


class TestValidateBgmFilename:
    def test_none_accepted(self, tmp_manifest: Path):
        validate_bgm_filename(None, tmp_manifest)  # no exception

    def test_registered_accepted(self, tmp_manifest: Path):
        tmp_manifest.write_text(
            json.dumps({"tracks": [{"filename": "b.mp3", "mood": "dramatic", "license": "CC0"}]})
        )
        validate_bgm_filename("b.mp3", tmp_manifest)

    def test_unregistered_rejected(self, tmp_manifest: Path):
        tmp_manifest.write_text(json.dumps({"tracks": []}))
        with pytest.raises(BgmManifestError) as ei:
            validate_bgm_filename("notregistered.mp3", tmp_manifest)
        assert "not registered" in str(ei.value).lower() or "manifest" in str(ei.value).lower()


class TestRegisterBgm:
    def test_registers_new(self, tmp_manifest: Path, tmp_path: Path):
        # Create fake file
        f = tmp_path / "new.mp3"
        f.write_bytes(b"\x00" * 100)
        register_bgm(
            tmp_manifest,
            filename="new.mp3",
            mood="calm",
            license_text="CC-BY 4.0 / Artist Name",
            audio_path=f,
        )
        data = load_manifest(tmp_manifest)
        assert any(t["filename"] == "new.mp3" for t in data["tracks"])

    def test_idempotent(self, tmp_manifest: Path, tmp_path: Path):
        f = tmp_path / "ok.mp3"
        f.write_bytes(b"\x00" * 50)
        register_bgm(tmp_manifest, filename="ok.mp3", mood="calm", license_text="CC0", audio_path=f)
        register_bgm(tmp_manifest, filename="ok.mp3", mood="calm", license_text="CC0", audio_path=f)
        data = load_manifest(tmp_manifest)
        entries = [t for t in data["tracks"] if t["filename"] == "ok.mp3"]
        assert len(entries) == 1  # dedup by filename

    def test_requires_license_field(self, tmp_manifest: Path, tmp_path: Path):
        f = tmp_path / "x.mp3"
        f.write_bytes(b"\x00")
        with pytest.raises(BgmManifestError):
            register_bgm(tmp_manifest, filename="x.mp3", mood="calm", license_text="", audio_path=f)
