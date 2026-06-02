"""T021: SQLite migration + seed 검증."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, init_db, migrate, seed_pinned_politicians


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_state.db"


class TestMigrate:
    def test_creates_all_tables(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            migrate(conn)
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        expected = {
            "politicians",
            "source_videos",
            "speech_segments",
            "shorts_drafts",
            "gate_results",
            "weekly_rankings",
            "uploaded_shorts",
            "bias_reports",
            "guardrail_history",
            "schema_migrations",
        }
        assert expected.issubset(tables)

    def test_idempotent(self, temp_db: Path):
        """두 번 실행해도 에러 없고 두 번째는 0개 적용."""
        with get_connection(temp_db) as conn:
            first = migrate(conn)
            assert len(first) >= 1
            second = migrate(conn)
            assert second == []


class TestSeedPoliticians:
    def test_seeds_both_perspectives_pinned(self, temp_db: Path):
        """2026-04-20: dem(3) + ppp(6) = 9명 pinned 시드 (migration 002 이후)."""
        with get_connection(temp_db) as conn:
            migrate(conn)
            inserted = seed_pinned_politicians(conn)
            assert inserted == 9  # dem 3 + ppp 6
            rows = conn.execute(
                "SELECT name, tier, category, affiliation_perspective "
                "FROM politicians ORDER BY name"
            ).fetchall()
        names = {r[0] for r in rows}
        assert names == {
            "이재명", "조국", "정청래",
            "한동훈", "김기현", "권성동", "추경호", "나경원", "오세훈",
        }
        for r in rows:
            assert r[1] == "pinned"
            assert r[2] == "fixed"
            assert r[3] in ("dem", "ppp")

    def test_idempotent(self, temp_db: Path):
        """두 번 호출해도 중복 삽입 안 됨 (dem 3 + ppp 6 = 9)."""
        with get_connection(temp_db) as conn:
            migrate(conn)
            seed_pinned_politicians(conn)
            second = seed_pinned_politicians(conn)
            assert second == 0
            total = conn.execute("SELECT COUNT(*) FROM politicians").fetchone()[0]
        assert total == 9


class TestCrudRoundtrip:
    def test_source_video_insert_fetch(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            migrate(conn)
            conn.execute(
                """
                INSERT INTO source_videos
                  (video_id, title, description, published_at, duration_sec,
                   thumbnail_url, session_type, dem_score, status,
                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "abc123",
                    "제422회 본회의",
                    "desc",
                    "2026-04-16T14:00:00",
                    7200,
                    "https://img.example.com/t.jpg",
                    "plenary",
                    82.5,
                    "ready",
                    "2026-04-16T14:00:00",
                    "2026-04-16T14:00:00",
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT video_id, dem_score FROM source_videos WHERE video_id = ?",
                ("abc123",),
            ).fetchone()
        assert row[0] == "abc123"
        assert row[1] == 82.5


class TestInitDB:
    def test_init_db_runs_migrate_and_seed(self, temp_db: Path):
        result = init_db(temp_db)
        assert len(result["migrations_applied"]) >= 2  # 001 + 002
        assert result["politicians_seeded"] == 9  # dem 3 + ppp 6
        assert result["perspectives_seeded"] == 2  # dem + ppp


class TestTierCheck:
    def test_invalid_tier_rejected_by_db(self, temp_db: Path):
        import sqlite3

        with get_connection(temp_db) as conn:
            migrate(conn)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO politicians
                      (name, party, tier, category, added_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("X", "X", "super_pinned", "fixed", "2026-04-16", "2026-04-16"),
                )
                conn.commit()
