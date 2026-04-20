"""Phase 1 TDD: perspective 축 스키마 + 시드 테스트 (010 PPP perspective feature).

Spec: specs/007-dem-shorts-studio/spec.md (v2) §FR-006, §Key Entities Perspective
Plan: prompt_plan.md §010 PPP(국민의힘) 관점 영상 생성 — H2 Axis
Charter: docs/politics-bias-charter.md §2 Supported Perspectives
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, init_db, migrate


@pytest.fixture
def db():
    """Isolated SQLite DB per test."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        with get_connection(db_path) as conn:
            yield conn


class TestPerspectivesTable:
    """perspectives 테이블이 migration 002로 생성되는지 검증."""

    def test_table_exists(self, db: sqlite3.Connection):
        row = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='perspectives'"
        ).fetchone()
        assert row is not None, "perspectives 테이블이 없습니다 (migration 002 미적용)"

    def test_has_required_columns(self, db: sqlite3.Connection):
        cols = {r["name"] for r in db.execute("PRAGMA table_info(perspectives)")}
        required = {"id", "label", "channel_id", "is_active", "created_at"}
        missing = required - cols
        assert not missing, f"perspectives 테이블에 누락된 컬럼: {missing}"

    def test_channel_id_unique_constraint(self, db: sqlite3.Connection):
        """perspective ↔ channel_id는 1:1 고정 (charter §3.3)."""
        db.execute(
            "INSERT INTO perspectives (id, label, channel_id, is_active, created_at) "
            "VALUES ('tmp1', 'Test1', 'UC-same', 1, '2026-04-20T00:00:00')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO perspectives (id, label, channel_id, is_active, created_at) "
                "VALUES ('tmp2', 'Test2', 'UC-same', 1, '2026-04-20T00:00:00')"
            )

    def test_seed_rows_inserted(self, db: sqlite3.Connection):
        """init_db 시 dem·ppp 2개 perspective가 시드되어야 함."""
        rows = db.execute("SELECT id FROM perspectives ORDER BY id").fetchall()
        ids = [r["id"] for r in rows]
        assert "dem" in ids, "dem perspective seed 누락"
        assert "ppp" in ids, "ppp perspective seed 누락"

    def test_dem_channel_id_nullable(self, db: sqlite3.Connection):
        """Q6 결정: 이 채널은 PPP only. dem perspective channel_id는 NULL."""
        row = db.execute(
            "SELECT channel_id FROM perspectives WHERE id='dem'"
        ).fetchone()
        assert row["channel_id"] is None or row["channel_id"] == "", \
            f"dem perspective channel_id는 비어 있어야 함 (로컬 렌더 전용): {row['channel_id']}"


class TestPoliticiansPerspectiveColumn:
    """politicians 테이블에 affiliation_perspective 컬럼 추가 (FR-006)."""

    def test_column_exists(self, db: sqlite3.Connection):
        cols = {r["name"] for r in db.execute("PRAGMA table_info(politicians)")}
        assert "affiliation_perspective" in cols, \
            "politicians.affiliation_perspective 컬럼 누락"

    def test_dem_seed_has_dem_perspective(self, db: sqlite3.Connection):
        """이재명·조국·정청래는 affiliation_perspective='dem'."""
        rows = db.execute(
            "SELECT name, affiliation_perspective FROM politicians "
            "WHERE name IN ('이재명','조국','정청래')"
        ).fetchall()
        assert len(rows) == 3, "dem 시드 3명이 삽입되어야 함"
        for r in rows:
            assert r["affiliation_perspective"] == "dem", \
                f"{r['name']}의 perspective가 'dem'이 아님: {r['affiliation_perspective']}"

    def test_ppp_seed_has_ppp_perspective(self, db: sqlite3.Connection):
        """PPP 6명(한동훈·김기현·권성동·추경호·나경원·오세훈)은 affiliation_perspective='ppp'."""
        expected_names = {"한동훈", "김기현", "권성동", "추경호", "나경원", "오세훈"}
        rows = db.execute(
            "SELECT name, affiliation_perspective FROM politicians "
            f"WHERE name IN ({','.join(['?']*len(expected_names))})",
            tuple(expected_names),
        ).fetchall()
        found = {r["name"] for r in rows}
        missing = expected_names - found
        assert not missing, f"PPP 시드 누락: {missing}"
        for r in rows:
            assert r["affiliation_perspective"] == "ppp", \
                f"{r['name']}의 perspective가 'ppp'가 아님"


class TestSourceVideosPerspectiveColumn:
    """source_videos에 target_perspective + perspective_score 컬럼 추가."""

    def test_target_perspective_column(self, db: sqlite3.Connection):
        cols = {r["name"] for r in db.execute("PRAGMA table_info(source_videos)")}
        assert "target_perspective" in cols, "source_videos.target_perspective 누락"

    def test_perspective_score_column(self, db: sqlite3.Connection):
        cols = {r["name"] for r in db.execute("PRAGMA table_info(source_videos)")}
        assert "perspective_score" in cols, "source_videos.perspective_score 누락"


class TestAuxiliaryTablesPerspectiveColumn:
    """shorts_drafts, uploaded_shorts, weekly_rankings, bias_reports, guardrail_history."""

    @pytest.mark.parametrize("table", [
        "shorts_drafts",
        "uploaded_shorts",
        "weekly_rankings",
        "bias_reports",
        "guardrail_history",
    ])
    def test_perspective_column_present(self, db: sqlite3.Connection, table: str):
        cols_q = db.execute(f"PRAGMA table_info({table})").fetchall()
        if not cols_q:
            pytest.skip(f"테이블 {table} 존재하지 않음 (Phase 1 스코프 밖)")
        cols = {r["name"] for r in cols_q}
        assert "perspective" in cols, f"{table}.perspective 컬럼 누락"
