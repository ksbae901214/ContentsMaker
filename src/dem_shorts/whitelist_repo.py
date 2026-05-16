"""T058: Whitelist 정치인 CRUD 저장소.

Next.js API route는 이 모듈을 subprocess로 호출한다.
- tier='auto' 직접 등록/전환 차단 (FR-009): auto 등급은 `ranking-batch` CLI 전용

Contract: contracts/rest-api.md §Whitelist 관리
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

_ALLOWED_TIERS_MANUAL = {"pinned", "pending", "blocked"}  # auto는 배치 전용
_ALLOWED_TIERS_ALL = {"pinned", "auto", "pending", "blocked"}
_ALLOWED_CATEGORIES = {"fixed", "female", "youth", "alliance"}


class WhitelistError(Exception):
    """Raised when whitelist operation fails validation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # SQLite INTEGER → Python bool for is_active
    d["is_active"] = bool(d.get("is_active", 1))
    return d


def list_politicians(
    conn: sqlite3.Connection,
    *,
    tier: str | None = None,
    category: str | None = None,
    active: bool | None = None,
) -> list[dict]:
    """FR-007: 정치인 목록 조회 (필터 지원)."""
    query = "SELECT * FROM politicians WHERE 1=1"
    params: list = []
    if tier is not None:
        if tier not in _ALLOWED_TIERS_ALL:
            raise WhitelistError(f"invalid tier filter: {tier}")
        query += " AND tier = ?"
        params.append(tier)
    if category is not None:
        if category not in _ALLOWED_CATEGORIES:
            raise WhitelistError(f"invalid category filter: {category}")
        query += " AND category = ?"
        params.append(category)
    if active is not None:
        query += " AND is_active = ?"
        params.append(1 if active else 0)
    query += " ORDER BY tier, name"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def create_politician(conn: sqlite3.Connection, data: dict) -> dict:
    """FR-007: 정치인 추가.

    Raises:
        WhitelistError: tier='auto' 직접 등록 / 중복 이름 / 잘못된 enum.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise WhitelistError("name_required")

    party = (data.get("party") or "").strip()
    if not party:
        raise WhitelistError("party_required")

    tier = data.get("tier", "pending")
    if tier == "auto":
        raise WhitelistError("tier_auto_blocked: auto tier is reserved for ranking batch")
    if tier not in _ALLOWED_TIERS_MANUAL:
        raise WhitelistError(f"invalid tier: {tier}")

    category = data.get("category", "fixed")
    if category not in _ALLOWED_CATEGORIES:
        raise WhitelistError(f"invalid category: {category}")

    existing = conn.execute(
        "SELECT id FROM politicians WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        raise WhitelistError(f"already_exists: politician '{name}' id={existing[0]}")

    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO politicians
          (name, party, role, photo_url, bio, tone_guide,
           tier, category, is_active, ranking_score, added_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, ?)
        """,
        (
            name,
            party,
            data.get("role", ""),
            data.get("photo_url"),
            data.get("bio", ""),
            data.get("tone_guide", ""),
            tier,
            category,
            now,
            now,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM politicians WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_dict(row)


def update_politician(conn: sqlite3.Connection, pid: int, patch: dict) -> dict:
    """PATCH: 등급·카테고리·활성·메타 변경.

    FR-009: tier='auto'로의 수동 전환 금지.
    """
    row = conn.execute(
        "SELECT * FROM politicians WHERE id = ?", (pid,)
    ).fetchone()
    if not row:
        raise WhitelistError(f"not_found: politician id={pid}")

    fields: list[str] = []
    values: list = []

    if "tier" in patch:
        tier = patch["tier"]
        if tier == "auto":
            raise WhitelistError("tier_auto_blocked: cannot patch to 'auto'")
        if tier not in _ALLOWED_TIERS_MANUAL:
            raise WhitelistError(f"invalid tier: {tier}")
        fields.append("tier = ?")
        values.append(tier)

    if "category" in patch:
        cat = patch["category"]
        if cat not in _ALLOWED_CATEGORIES:
            raise WhitelistError(f"invalid category: {cat}")
        fields.append("category = ?")
        values.append(cat)

    for key in ("party", "role", "bio", "tone_guide", "photo_url"):
        if key in patch:
            fields.append(f"{key} = ?")
            values.append(patch[key])

    if "is_active" in patch:
        fields.append("is_active = ?")
        values.append(1 if patch["is_active"] else 0)

    if not fields:
        raise WhitelistError("no_updatable_fields")

    fields.append("updated_at = ?")
    values.append(_now())
    values.append(pid)

    conn.execute(
        f"UPDATE politicians SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM politicians WHERE id = ?", (pid,)
    ).fetchone()
    return _row_to_dict(row)


def delete_politician(conn: sqlite3.Connection, pid: int) -> None:
    row = conn.execute(
        "SELECT id, tier FROM politicians WHERE id = ?", (pid,)
    ).fetchone()
    if not row:
        raise WhitelistError(f"not_found: politician id={pid}")
    conn.execute("DELETE FROM politicians WHERE id = ?", (pid,))
    conn.commit()


def get_politician(conn: sqlite3.Connection, pid: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM politicians WHERE id = ?", (pid,)
    ).fetchone()
    return _row_to_dict(row) if row else None
