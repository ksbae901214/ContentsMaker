"""Drafts CRUD 저장소 — Next.js API route가 subprocess로 호출.

FR-018: cut_duration ≤ 60s, FR-025: 게이트 실행 전까지 status='draft'.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from src.dem_shorts.config import CUT_MAX_SEC
from src.dem_shorts.editor.bgm_manifest import validate_bgm_filename, BgmManifestError

_ALLOWED_PRESETS = {"leejaemyung", "jungcheongrae", "youth", "hotissue", "default"}
_ALLOWED_TTS_VOICES = {None, "male_strong", "male_stable", "female_calm", "female_young"}


class DraftError(Exception):
    """Raised when draft operation fails."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_draft(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["commentary_blocks"] = json.loads(d.get("commentary_json") or "[]")
    d["fact_source_urls"] = json.loads(d.get("fact_source_urls") or "[]")
    d.pop("commentary_json", None)
    d["tts_enabled"] = bool(d.get("tts_enabled", 0))
    return d


def create_draft(conn: sqlite3.Connection, data: dict) -> dict:
    """POST /api/dem-shorts/drafts — 발언 구간에서 쇼츠 초안 생성."""
    segment_id = int(data["segment_id"])
    cut_start = float(data["cut_start_sec"])
    cut_end = float(data["cut_end_sec"])
    preset = data.get("subtitle_preset", "default")

    if cut_end <= cut_start:
        raise DraftError("cut_end must be > cut_start")
    if cut_end - cut_start > CUT_MAX_SEC:
        raise DraftError(f"cut_duration_exceeds: {cut_end-cut_start}s > {CUT_MAX_SEC}s (FR-018)")
    if preset not in _ALLOWED_PRESETS:
        raise DraftError(f"invalid_subtitle_preset: {preset}")

    # segment 존재 확인
    seg = conn.execute(
        "SELECT id FROM speech_segments WHERE id=?", (segment_id,)
    ).fetchone()
    if not seg:
        raise DraftError(f"segment_not_found: {segment_id}")

    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO shorts_drafts (
            segment_id, cut_start_sec, cut_end_sec,
            commentary_json, commentary_char_count,
            tts_voice, tts_enabled,
            subtitle_preset, bgm_filename, fact_source_urls,
            risk_score, status, created_at, updated_at
        ) VALUES (?, ?, ?, '[]', 0, NULL, 0, ?, NULL, '[]', 0.0, 'draft', ?, ?)
        """,
        (segment_id, cut_start, cut_end, preset, now, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM shorts_drafts WHERE id=?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_draft(row)


def update_draft(conn: sqlite3.Connection, draft_id: int, patch: dict) -> dict:
    """PATCH /api/dem-shorts/drafts/:id — commentary/tts/bgm/fact_urls 업데이트."""
    existing = conn.execute(
        "SELECT * FROM shorts_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if not existing:
        raise DraftError(f"draft_not_found: {draft_id}")

    fields: list[str] = []
    values: list = []

    if "commentary_blocks" in patch:
        blocks = patch["commentary_blocks"] or []
        if not isinstance(blocks, list):
            raise DraftError("commentary_blocks must be a list")
        char_count = sum(len(b.get("text", "")) for b in blocks)
        fields.append("commentary_json = ?")
        values.append(json.dumps(blocks, ensure_ascii=False))
        fields.append("commentary_char_count = ?")
        values.append(char_count)

    if "tts_voice" in patch:
        voice = patch["tts_voice"]
        if voice not in _ALLOWED_TTS_VOICES:
            raise DraftError(f"invalid_tts_voice: {voice}")
        fields.append("tts_voice = ?")
        values.append(voice)

    if "tts_enabled" in patch:
        fields.append("tts_enabled = ?")
        values.append(1 if patch["tts_enabled"] else 0)

    if "subtitle_preset" in patch:
        preset = patch["subtitle_preset"]
        if preset not in _ALLOWED_PRESETS:
            raise DraftError(f"invalid_subtitle_preset: {preset}")
        fields.append("subtitle_preset = ?")
        values.append(preset)

    if "bgm_filename" in patch:
        bgm = patch["bgm_filename"]
        try:
            validate_bgm_filename(bgm)
        except BgmManifestError as exc:
            raise DraftError(f"bgm_validation: {exc}") from exc
        fields.append("bgm_filename = ?")
        values.append(bgm)

    if "fact_source_urls" in patch:
        urls = patch["fact_source_urls"] or []
        if not isinstance(urls, list):
            raise DraftError("fact_source_urls must be a list")
        fields.append("fact_source_urls = ?")
        values.append(json.dumps(urls, ensure_ascii=False))

    if not fields:
        raise DraftError("no_updatable_fields")

    fields.append("updated_at = ?")
    values.append(_now())
    values.append(draft_id)

    conn.execute(
        f"UPDATE shorts_drafts SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM shorts_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    return _row_to_draft(row)


def get_draft(conn: sqlite3.Connection, draft_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM shorts_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    return _row_to_draft(row) if row else None
