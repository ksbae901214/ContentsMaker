"""Tests for src/upload/upload_history.py — 업로드 이력 JSON 기록."""
import json
from pathlib import Path

from src.upload.upload_history import record_upload


def test_record_success_creates_file(tmp_path: Path):
    history = tmp_path / "upload_history.json"

    entry = record_upload(
        platform="youtube",
        video_path=Path("/tmp/v.mp4"),
        title="테스트 영상",
        status="success",
        result="https://youtube.com/shorts/abc",
        history_path=history,
    )

    assert history.exists()
    saved = json.loads(history.read_text())
    assert len(saved) == 1
    assert saved[0]["platform"] == "youtube"
    assert saved[0]["status"] == "success"
    assert saved[0]["result"] == "https://youtube.com/shorts/abc"
    assert saved[0]["title"] == "테스트 영상"
    assert "timestamp" in saved[0]
    assert entry["platform"] == "youtube"


def test_record_failure_with_error(tmp_path: Path):
    history = tmp_path / "upload_history.json"

    record_upload(
        platform="tiktok",
        video_path=Path("/tmp/v.mp4"),
        title="t",
        status="failed",
        error="network down",
        history_path=history,
    )

    saved = json.loads(history.read_text())
    assert saved[0]["status"] == "failed"
    assert saved[0]["error"] == "network down"
    assert saved[0]["result"] is None


def test_entries_accumulate(tmp_path: Path):
    history = tmp_path / "upload_history.json"
    for i in range(3):
        record_upload(
            platform="youtube",
            video_path=Path(f"/tmp/{i}.mp4"),
            title=f"v{i}",
            status="success",
            result=f"url{i}",
            history_path=history,
        )

    saved = json.loads(history.read_text())
    assert [e["title"] for e in saved] == ["v0", "v1", "v2"]


def test_corrupt_history_file_recovers(tmp_path: Path):
    history = tmp_path / "upload_history.json"
    history.write_text("{not valid json")

    record_upload(
        platform="youtube",
        video_path=Path("/tmp/v.mp4"),
        title="t",
        status="success",
        result="url",
        history_path=history,
    )

    saved = json.loads(history.read_text())
    assert len(saved) == 1
