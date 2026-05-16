"""T082: Renderer 테스트 — 게이트 미통과 draft 거부, 스마트 캐싱 검증.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from src.dem_shorts.db import get_connection, migrate
from src.dem_shorts.models.gate_result import ComplianceGateResult
from src.dem_shorts.renderer import (
    RenderError,
    compute_render_cache_key,
    render_draft,
    verify_gate_passed,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db = tmp_path / "render_test.db"
    with get_connection(db) as conn:
        migrate(conn)
    return db


def _insert_draft_with_gate(
    conn,
    *,
    overall_status: str,
    risk_score: float = 20.0,
    all_items_pass: bool = True,
    signed: bool = True,
) -> int:
    """draft + gate_result 쌍 삽입."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO politicians (name, party, role, bio, tone_guide, tier, category, is_active, added_at, updated_at) "
        "VALUES ('이재명', '더불어민주당', '당대표', '', '', 'pinned', 'fixed', 1, ?, ?)",
        (now, now),
    )
    pid = conn.execute("SELECT id FROM politicians WHERE name='이재명'").fetchone()[0]
    conn.execute(
        "INSERT INTO source_videos (video_id, title, description, published_at, duration_sec, "
        "thumbnail_url, session_type, dem_score, status, created_at, updated_at) "
        "VALUES ('v1', 'T', '', ?, 3600, '', 'plenary', 80.0, 'ready', ?, ?)",
        (now, now, now),
    )
    conn.execute(
        "INSERT INTO speech_segments (source_video_id, start_sec, end_sec, politician_id, "
        "confidence, stt_text, recommendation_score, is_solo, has_profanity) "
        "VALUES ('v1', 120.0, 180.0, ?, 0.9, '민생', 75.0, 1, 0)",
        (pid,),
    )
    sid = conn.execute("SELECT id FROM speech_segments WHERE source_video_id='v1'").fetchone()[0]
    import json as _json
    conn.execute(
        "INSERT INTO shorts_drafts (segment_id, cut_start_sec, cut_end_sec, commentary_json, "
        "commentary_char_count, tts_voice, tts_enabled, subtitle_preset, bgm_filename, fact_source_urls, "
        "risk_score, status, created_at, updated_at) "
        "VALUES (?, 120.0, 170.0, ?, ?, 'male_strong', 1, 'leejaemyung', NULL, ?, ?, 'gate_passed', ?, ?)",
        (sid, _json.dumps([{"text": "a" * 60, "start": 0, "end": 20}]), 60,
         _json.dumps(["https://a", "https://b"]), risk_score, now, now),
    )
    did = conn.execute("SELECT id FROM shorts_drafts WHERE segment_id=?", (sid,)).fetchone()[0]

    item_status = "pass" if all_items_pass else "fail"
    sig = "owner" if signed else None
    conn.execute(
        "INSERT INTO gate_results (draft_id, "
        "item_1_commentary_length, item_2_ratio, item_3_duration, item_4_source_label, "
        "item_5_bias_guardrail, item_6_template_repeat, item_7_whitelist_person, "
        "item_8_election_guard, item_9_fact_checked, item_10_no_defamation, "
        "manual_fact_check_signed_by, manual_defamation_check_signed_by, "
        "failure_reasons, overall_status, risk_score, validated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?)",
        (did, item_status, item_status, item_status, item_status, item_status, item_status,
         item_status, item_status, item_status, item_status, sig, sig, overall_status, risk_score, now),
    )
    conn.commit()
    return did


class TestVerifyGatePassed:
    def test_passes_when_all_green(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            did = _insert_draft_with_gate(
                conn, overall_status="pass", risk_score=15.0, all_items_pass=True, signed=True,
            )
        # Should not raise
        verify_gate_passed(did, db_path=temp_db)

    def test_rejects_when_no_gate_result(self, temp_db: Path):
        """Gate 실행 전 draft는 render 불가."""
        # Insert draft without gate_result
        with get_connection(temp_db) as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO politicians (name, party, role, bio, tone_guide, tier, category, is_active, added_at, updated_at) "
                "VALUES ('X', '더불어민주당', '', '', '', 'pinned', 'fixed', 1, ?, ?)",
                (now, now),
            )
            pid = conn.execute("SELECT id FROM politicians").fetchone()[0]
            conn.execute(
                "INSERT INTO source_videos (video_id, title, description, published_at, duration_sec, "
                "thumbnail_url, session_type, dem_score, status, created_at, updated_at) "
                "VALUES ('v9', 'T', '', ?, 3600, '', 'plenary', 50, 'ready', ?, ?)",
                (now, now, now),
            )
            conn.execute(
                "INSERT INTO speech_segments (source_video_id, start_sec, end_sec, politician_id, confidence, stt_text, recommendation_score) "
                "VALUES ('v9', 0, 60, ?, 0.9, 'x', 70)",
                (pid,),
            )
            sid = conn.execute("SELECT id FROM speech_segments").fetchone()[0]
            import json as _json
            conn.execute(
                "INSERT INTO shorts_drafts (segment_id, cut_start_sec, cut_end_sec, commentary_json, "
                "commentary_char_count, subtitle_preset, fact_source_urls, status, created_at, updated_at) "
                "VALUES (?, 0, 30, '[]', 0, 'default', '[]', 'draft', ?, ?)",
                (sid, now, now),
            )
            did = conn.execute("SELECT id FROM shorts_drafts").fetchone()[0]
            conn.commit()

        with pytest.raises(RenderError) as ei:
            verify_gate_passed(did, db_path=temp_db)
        assert "gate" in str(ei.value).lower()

    def test_rejects_failed_gate(self, temp_db: Path):
        """overall_status='pass'여도 실제 아이템이 fail이면 거부 (DB 조작 방어)."""
        with get_connection(temp_db) as conn:
            did = _insert_draft_with_gate(
                conn,
                overall_status="pass",  # ← DB 조작
                risk_score=15.0,
                all_items_pass=False,  # ← 하지만 실제 아이템은 fail
                signed=True,
            )
        with pytest.raises(RenderError) as ei:
            verify_gate_passed(did, db_path=temp_db)
        assert "gate_not_passed" in str(ei.value).lower()

    def test_rejects_high_risk_score(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            did = _insert_draft_with_gate(
                conn, overall_status="pass", risk_score=75.0,  # ← 임계값 초과
                all_items_pass=True, signed=True,
            )
        with pytest.raises(RenderError):
            verify_gate_passed(did, db_path=temp_db)

    def test_rejects_unsigned(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            did = _insert_draft_with_gate(
                conn, overall_status="pass", risk_score=15.0, all_items_pass=True, signed=False,
            )
        with pytest.raises(RenderError):
            verify_gate_passed(did, db_path=temp_db)


class TestCacheKey:
    def test_same_inputs_same_key(self):
        draft_data = {
            "id": 1,
            "segment_id": 5,
            "cut_start_sec": 10.0,
            "cut_end_sec": 40.0,
            "commentary_blocks": [{"text": "a", "start": 0, "end": 2}],
            "subtitle_preset": "default",
            "tts_voice": "male_stable",
            "bgm_filename": None,
        }
        k1 = compute_render_cache_key(draft_data)
        k2 = compute_render_cache_key(draft_data)
        assert k1 == k2

    def test_different_commentary_different_key(self):
        base = {
            "id": 1,
            "segment_id": 5,
            "cut_start_sec": 10.0,
            "cut_end_sec": 40.0,
            "commentary_blocks": [{"text": "a", "start": 0, "end": 2}],
            "subtitle_preset": "default",
            "tts_voice": "male_stable",
            "bgm_filename": None,
        }
        modified = {**base, "commentary_blocks": [{"text": "b", "start": 0, "end": 2}]}
        assert compute_render_cache_key(base) != compute_render_cache_key(modified)
