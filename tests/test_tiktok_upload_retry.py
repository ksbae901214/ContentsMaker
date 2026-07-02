"""TikTok upload_video의 재시도 + 이력 기록 통합 테스트 (urlopen mocked)."""
import json
import urllib.error
from pathlib import Path

import pytest

import src.upload.tiktok_uploader as tu
import src.upload.upload_history as uh


class _FakeResp:
    def __init__(self, data: dict):
        self._data = data

    def read(self) -> bytes:
        return json.dumps(self._data).encode()


_INIT_OK = {
    "error": {"code": "ok"},
    "data": {"upload_url": "http://upload.example", "publish_id": "pid-123"},
}


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    history = tmp_path / "hist.json"
    monkeypatch.setattr(uh, "HISTORY_PATH", history)
    monkeypatch.setattr(tu, "_get_access_token", lambda: "tok")
    monkeypatch.setattr("src.upload.retry.time.sleep", lambda _: None)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"vid")
    return history, video


def test_transient_5xx_is_retried_then_succeeds(env, monkeypatch):
    history, video = env
    calls = {"n": 0}

    def fake_urlopen(req):
        calls["n"] += 1
        if calls["n"] == 1:  # init 첫 시도 — 일시 장애
            raise urllib.error.HTTPError("http://x", 502, "bad gateway", None, None)
        if calls["n"] == 2:  # init 재시도 성공
            return _FakeResp(_INIT_OK)
        return _FakeResp({})  # PUT 업로드

    monkeypatch.setattr(tu.urllib.request, "urlopen", fake_urlopen)

    publish_id = tu.upload_video(video, "제목")

    assert publish_id == "pid-123"
    assert calls["n"] == 3
    saved = json.loads(history.read_text())
    assert saved[-1]["status"] == "success"
    assert saved[-1]["result"] == "pid-123"


def test_4xx_fails_immediately_and_records_failure(env, monkeypatch):
    history, video = env
    calls = {"n": 0}

    def fake_urlopen(req):
        calls["n"] += 1
        raise urllib.error.HTTPError("http://x", 401, "unauthorized", None, None)

    monkeypatch.setattr(tu.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(urllib.error.HTTPError):
        tu.upload_video(video, "제목")

    assert calls["n"] == 1, "4xx는 재시도하면 안 됨"
    saved = json.loads(history.read_text())
    assert saved[-1]["status"] == "failed"
    assert "401" in saved[-1]["error"] or "unauthorized" in saved[-1]["error"]
