"""T085: Uploader 테스트 — NATV 출처/팩트 링크/operator_confirmed 검증.

2026-04-20: perspective ↔ channel_id 바인딩(SC-014) 추가에 따라 모든 테스트에
가짜 channel_id를 patch.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, migrate
from src.dem_shorts.uploader import (
    UploadError,
    UploadRequest,
    validate_upload_request,
)


@pytest.fixture(autouse=True)
def _patch_perspective_channel(monkeypatch):
    """테스트 중엔 양 perspective 모두 활성 채널이 있다고 가정."""
    from src.dem_shorts import config
    monkeypatch.setitem(config.PERSPECTIVE_CHANNEL_ID, "dem", "UC-test-dem")
    monkeypatch.setitem(config.PERSPECTIVE_CHANNEL_ID, "ppp", "UC-test-ppp")


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db = tmp_path / "up_test.db"
    with get_connection(db) as conn:
        migrate(conn)
    return db


def _minimal_req(**overrides) -> UploadRequest:
    base = dict(
        draft_id=1,
        title="이재명 민생경제 발언 요약",
        description=(
            "이재명 당대표의 본회의 발언을 요약합니다.\n\n"
            "📺 출처: NATV 국회방송\n"
            "📰 팩트 링크:\n"
            "- https://news.example.com/1\n"
            "- https://news.example.com/2\n"
        ),
        tags=("이재명", "민생", "NATV"),
        scheduled_publish_at=None,
        operator_confirmed=True,
    )
    base.update(overrides)
    return UploadRequest(**base)


class TestValidateUploadRequest:
    def test_happy_path(self):
        validate_upload_request(_minimal_req())  # no exception

    def test_operator_not_confirmed(self):
        with pytest.raises(UploadError) as ei:
            validate_upload_request(_minimal_req(operator_confirmed=False))
        assert "operator_confirmed" in str(ei.value).lower()

    def test_missing_natv_label_in_description(self):
        with pytest.raises(UploadError) as ei:
            validate_upload_request(
                _minimal_req(
                    description="팩트 링크:\n- https://a\n- https://b\n(NATV 누락)"
                )
            )
        msg = str(ei.value).lower()
        assert "natv" in msg or "출처" in msg

    def test_empty_title(self):
        with pytest.raises(UploadError):
            validate_upload_request(_minimal_req(title=""))

    def test_title_over_100_chars(self):
        with pytest.raises(UploadError):
            validate_upload_request(_minimal_req(title="이" * 120))


class TestFactLinkExtraction:
    def test_extract_from_description(self):
        from src.dem_shorts.uploader import extract_fact_links_from_description

        desc = (
            "설명 본문\n"
            "📰 팩트 링크:\n"
            "- https://news1.example.com/a\n"
            "- https://news2.example.com/b\n"
            "- http://news3.example.com/c\n"
            "텍스트\n"
        )
        links = extract_fact_links_from_description(desc)
        assert len(links) >= 3
        assert any("news1.example.com" in l for l in links)

    def test_under_2_links_raises_on_validate(self):
        with pytest.raises(UploadError) as ei:
            validate_upload_request(
                _minimal_req(description="NATV 국회방송\n\n- https://only.example.com/1\n")
            )
        assert "fact" in str(ei.value).lower() or "팩트" in str(ei.value)
