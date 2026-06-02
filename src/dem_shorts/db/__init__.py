"""SQLite connection + migrations + seed for Dem-Shorts Studio (007).

Entry point: `from src.dem_shorts.db import get_connection, migrate, seed_pinned_politicians`
Default DB path: `data/dem_shorts/state.db`
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from src.dem_shorts.config import PERSPECTIVE_CHANNEL_ID, PERSPECTIVE_LABELS
from src.dem_shorts.models.politician import (
    SEED_POLITICIANS_DEM,
    SEED_POLITICIANS_PPP,
)

_DEFAULT_DB = Path("data/dem_shorts/state.db")
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with Row factory + FK enabled."""
    path = db_path or _DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply all pending SQL migrations in alphabetical order.

    Returns a list of applied migration filenames.
    """
    applied: set[str] = set()
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        applied = {r[0] for r in rows}
    except sqlite3.OperationalError:
        # schema_migrations table does not exist yet — fine, first migration will create it
        pass

    newly_applied: list[str] = []
    for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        version = sql_file.stem
        if version in applied:
            continue
        sql = sql_file.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.utcnow().isoformat()),
        )
        conn.commit()
        newly_applied.append(sql_file.name)
    return newly_applied


def seed_pinned_politicians(conn: sqlite3.Connection) -> int:
    """FR-006: perspective별 pinned 시드 삽입 (이미 있으면 스킵).

    dem 시드 3명 + ppp 시드 6명. Returns 신규 삽입 행 수.
    """
    # migration 002 적용 여부에 따라 컬럼 존재 확인 (하위호환)
    has_perspective = any(
        r["name"] == "affiliation_perspective"
        for r in conn.execute("PRAGMA table_info(politicians)")
    )

    now = datetime.utcnow().isoformat()
    inserted = 0
    all_seeds = list(SEED_POLITICIANS_DEM) + (
        list(SEED_POLITICIANS_PPP) if has_perspective else []
    )
    for seed in all_seeds:
        existing = conn.execute(
            "SELECT 1 FROM politicians WHERE name = ?", (seed["name"],)
        ).fetchone()
        if existing:
            continue
        if has_perspective:
            conn.execute(
                """
                INSERT INTO politicians
                  (name, party, role, photo_url, bio, tone_guide,
                   tier, category, is_active, ranking_score,
                   added_at, updated_at, affiliation_perspective)
                VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 1, NULL, ?, ?, ?)
                """,
                (
                    seed["name"],
                    seed["party"],
                    seed.get("role", ""),
                    seed.get("bio", ""),
                    seed.get("tone_guide", ""),
                    seed["tier"],
                    seed["category"],
                    now,
                    now,
                    seed.get("affiliation_perspective", "dem"),
                ),
            )
        else:
            # migration 002 미적용 상태 (하위호환 경로)
            conn.execute(
                """
                INSERT INTO politicians
                  (name, party, role, photo_url, bio, tone_guide,
                   tier, category, is_active, ranking_score, added_at, updated_at)
                VALUES (?, ?, ?, NULL, ?, ?, ?, ?, 1, NULL, ?, ?)
                """,
                (
                    seed["name"],
                    seed["party"],
                    seed.get("role", ""),
                    seed.get("bio", ""),
                    seed.get("tone_guide", ""),
                    seed["tier"],
                    seed["category"],
                    now,
                    now,
                ),
            )
        inserted += 1
    conn.commit()
    return inserted


def seed_perspectives(conn: sqlite3.Connection) -> int:
    """perspectives 테이블에 dem/ppp 시드 삽입 (migration 002 적용 시에만).

    charter §2, §3.3 (channel-perspective 1:1 고정). 이미 있으면 스킵.
    Returns 신규 삽입 행 수.
    """
    # perspectives 테이블 존재 여부 확인
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='perspectives'"
    ).fetchone()
    if not exists:
        return 0

    now = datetime.utcnow().isoformat()
    inserted = 0
    for pid in ("dem", "ppp"):
        row = conn.execute(
            "SELECT 1 FROM perspectives WHERE id = ?", (pid,)
        ).fetchone()
        if row:
            continue
        channel_id = PERSPECTIVE_CHANNEL_ID.get(pid, "") or None
        conn.execute(
            "INSERT INTO perspectives (id, label, channel_id, is_active, created_at) "
            "VALUES (?, ?, ?, 1, ?)",
            (pid, PERSPECTIVE_LABELS.get(pid, pid), channel_id, now),
        )
        inserted += 1
    conn.commit()
    return inserted


def init_db(db_path: Path | None = None) -> dict:
    """One-shot: migrate + seed. Returns a summary for CLI logs."""
    with get_connection(db_path) as conn:
        migrations = migrate(conn)
        perspectives_seeded = seed_perspectives(conn)
        politicians_seeded = seed_pinned_politicians(conn)
    return {
        "migrations_applied": migrations,
        "perspectives_seeded": perspectives_seeded,
        "politicians_seeded": politicians_seeded,
    }
