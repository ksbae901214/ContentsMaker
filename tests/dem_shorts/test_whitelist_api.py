"""T057: Whitelist 관리 API 계약 테스트.

API는 Next.js subprocess를 경유하므로, 핵심 DB 조작 로직(upsert/delete/
tier='auto' 차단)을 파이썬 side에서 검증한다.

Contract: contracts/rest-api.md §Whitelist 관리 (FR-007, FR-009, FR-011)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, migrate
from src.dem_shorts.whitelist_repo import (
    WhitelistError,
    create_politician,
    delete_politician,
    list_politicians,
    update_politician,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db = tmp_path / "wl_test.db"
    with get_connection(db) as conn:
        migrate(conn)
    return db


class TestListPoliticians:
    def test_empty_list(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            rows = list_politicians(conn)
        assert rows == []

    def test_tier_filter(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            create_politician(
                conn,
                {"name": "A", "party": "더불어민주당", "tier": "pinned", "category": "fixed"},
            )
            create_politician(
                conn,
                {"name": "B", "party": "더불어민주당", "tier": "pending", "category": "female"},
            )
            rows = list_politicians(conn, tier="pinned")
        assert len(rows) == 1
        assert rows[0]["name"] == "A"

    def test_category_filter(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            create_politician(
                conn,
                {"name": "A", "party": "더불어민주당", "tier": "pinned", "category": "fixed"},
            )
            create_politician(
                conn,
                {"name": "Y", "party": "더불어민주당", "tier": "pinned", "category": "youth"},
            )
            rows = list_politicians(conn, category="youth")
        assert [r["name"] for r in rows] == ["Y"]


class TestCreatePolitician:
    def test_creates_pinned(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            p = create_politician(
                conn,
                {
                    "name": "전용기",
                    "party": "더불어민주당",
                    "role": "국회의원",
                    "tier": "pinned",
                    "category": "youth",
                    "bio": "",
                    "tone_guide": "",
                },
            )
        assert p["name"] == "전용기"
        assert p["tier"] == "pinned"
        assert p["id"] > 0

    def test_duplicate_name_rejected(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            create_politician(
                conn,
                {"name": "이재명", "party": "더불어민주당", "tier": "pinned", "category": "fixed"},
            )
            with pytest.raises(WhitelistError) as ei:
                create_politician(
                    conn,
                    {"name": "이재명", "party": "더불어민주당", "tier": "pinned", "category": "fixed"},
                )
            assert "already_exists" in str(ei.value) or "duplicate" in str(ei.value).lower()

    def test_tier_auto_direct_registration_blocked(self, temp_db: Path):
        """FR-009: tier='auto'로 직접 등록은 랭킹 배치만 가능."""
        with get_connection(temp_db) as conn:
            with pytest.raises(WhitelistError) as ei:
                create_politician(
                    conn,
                    {"name": "X", "party": "더불어민주당", "tier": "auto", "category": "female"},
                )
            assert "tier_auto_blocked" in str(ei.value) or "auto" in str(ei.value).lower()

    def test_invalid_tier_rejected(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            with pytest.raises(WhitelistError):
                create_politician(
                    conn,
                    {"name": "Z", "party": "더불어민주당", "tier": "bogus", "category": "fixed"},
                )


class TestUpdatePolitician:
    def test_updates_tier_and_category(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            p = create_politician(
                conn,
                {"name": "X", "party": "더불어민주당", "tier": "pending", "category": "female"},
            )
            updated = update_politician(
                conn, p["id"], {"tier": "pinned", "category": "youth"}
            )
        assert updated["tier"] == "pinned"
        assert updated["category"] == "youth"

    def test_update_nonexistent(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            with pytest.raises(WhitelistError) as ei:
                update_politician(conn, 9999, {"tier": "pinned"})
            assert "not_found" in str(ei.value).lower()

    def test_cannot_switch_tier_to_auto_via_patch(self, temp_db: Path):
        """FR-009: PATCH로도 tier='auto' 강제 불가 (ranking batch 전용)."""
        with get_connection(temp_db) as conn:
            p = create_politician(
                conn,
                {"name": "X", "party": "더불어민주당", "tier": "pending", "category": "female"},
            )
            with pytest.raises(WhitelistError):
                update_politician(conn, p["id"], {"tier": "auto"})


class TestDeletePolitician:
    def test_deletes(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            p = create_politician(
                conn,
                {"name": "X", "party": "더불어민주당", "tier": "pending", "category": "female"},
            )
            delete_politician(conn, p["id"])
            rows = list_politicians(conn)
        assert rows == []

    def test_delete_nonexistent(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            with pytest.raises(WhitelistError) as ei:
                delete_politician(conn, 12345)
            assert "not_found" in str(ei.value).lower()
