"""T078: ⭐⭐⭐ 10-Item Compliance Gate 우회 불가 검증 (SC-005, FR-025).

**MVP 릴리스 Gate**: 이 파일의 모든 테스트가 통과해야 MVP 배포 가능.

3가지 우회 시나리오가 모두 서버사이드에서 거부되는지 검증:
1. 프론트엔드 건너뛰기 파라미터
2. API 직접 호출 우회
3. DB 수동 조작 (is_passed() 재검증)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from src.dem_shorts.compliance.gate import (
    GateChecker,
    GateContext,
    GateError,
    validate,
)
from src.dem_shorts.db import get_connection, migrate
from src.dem_shorts.models.gate_result import ComplianceGateResult


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db = tmp_path / "gate_test.db"
    with get_connection(db) as conn:
        migrate(conn)
    return db


def _insert_complete_politician_segment_draft(conn) -> tuple[int, int, int]:
    """모든 필드가 gate를 통과할 만한 정상 draft 1개 준비."""
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
        "VALUES ('v1', 'Test', '', ?, 3600, '', 'plenary', 80.0, 'ready', ?, ?)",
        (now, now, now),
    )
    conn.execute(
        "INSERT INTO speech_segments (source_video_id, start_sec, end_sec, politician_id, "
        "confidence, stt_text, recommendation_score, is_solo, has_profanity) "
        "VALUES ('v1', 120.0, 180.0, ?, 0.9, '민생 경제 정책 설명', 75.0, 1, 0)",
        (pid,),
    )
    sid = conn.execute("SELECT id FROM speech_segments WHERE source_video_id='v1'").fetchone()[0]

    # Commentary 50자 이상, 해설 비율 ≥30%, fact urls 2개
    # cut_duration = 50초 (120→170), 해설 커버리지 최소 15초 필요
    import json as _json
    commentary_blocks = [
        {"start": 0, "end": 5, "text": "민생경제를\n정면돌파한 의지 보여줌", "style": "high"},
        {"start": 5, "end": 10, "text": "실효성 있는\n정책 적극 강조", "style": "medium"},
        {"start": 10, "end": 18, "text": "국회에서 직접\n책임지는 자세 발언", "style": "medium"},
        {"start": 18, "end": 25, "text": "여야 협치를\n강조했다는 평가", "style": "medium"},
    ]
    char_count = sum(len(b["text"]) for b in commentary_blocks)
    fact_urls = ["https://news.example.com/a", "https://news.example.com/b"]

    conn.execute(
        "INSERT INTO shorts_drafts (segment_id, cut_start_sec, cut_end_sec, "
        "commentary_json, commentary_char_count, tts_voice, tts_enabled, "
        "subtitle_preset, bgm_filename, fact_source_urls, risk_score, status, created_at, updated_at) "
        "VALUES (?, 120.0, 170.0, ?, ?, 'male_strong', 1, 'leejaemyung', NULL, ?, 0.0, 'draft', ?, ?)",
        (sid, _json.dumps(commentary_blocks), char_count, _json.dumps(fact_urls), now, now),
    )
    did = conn.execute("SELECT id FROM shorts_drafts WHERE segment_id=?", (sid,)).fetchone()[0]
    conn.commit()
    return pid, sid, did


# ──────────────────────────────────────────────────────────────────────
# 1. 기본 동작 — 정상 경로
# ──────────────────────────────────────────────────────────────────────


class TestHappyPath:
    def test_complete_draft_passes(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        assert result.overall_status == "pass"
        assert result.is_passed() is True


class TestEachItemFailure:
    def test_short_commentary_blocks(self, temp_db: Path):
        """item_1: commentary 50자 미만 → fail."""
        import json as _json
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            # 짧게 바꿈
            conn.execute(
                "UPDATE shorts_drafts SET commentary_json=?, commentary_char_count=?, updated_at=datetime('now') "
                "WHERE id=?",
                (_json.dumps([{"start": 0, "end": 2, "text": "짧음", "style": "high"}]), 2, did),
            )
            conn.commit()
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        assert result.item_1_commentary_length == "fail"
        assert result.overall_status == "fail"

    def test_duration_over_60_blocked_at_draft_level(self, temp_db: Path):
        """item_3: cut_duration > 60 → fail.

        실제로는 ShortsDraft 모델 __post_init__에서 거부하지만, 수동 DB 조작
        우회 시에도 gate가 잡아내는지 검증 (SC-005 우회 불가).
        """
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            # 수동으로 DB에 불법 값 주입
            conn.execute(
                "UPDATE shorts_drafts SET cut_end_sec=? WHERE id=?", (250.0, did)
            )
            conn.commit()
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        assert result.item_3_duration == "fail"
        assert result.overall_status == "fail"

    def test_fact_urls_under_2_blocks(self, temp_db: Path):
        """item_9: fact urls < 2 → fail."""
        import json as _json
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            conn.execute(
                "UPDATE shorts_drafts SET fact_source_urls=? WHERE id=?",
                (_json.dumps(["https://only-one.example.com"]), did),
            )
            conn.commit()
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        assert result.item_9_fact_checked == "fail"
        assert result.overall_status == "fail"


# ──────────────────────────────────────────────────────────────────────
# 2. ⭐ 우회 불가 검증 (SC-005) — 3가지 시나리오 모두 거부
# ──────────────────────────────────────────────────────────────────────


class TestBypassResistance:
    """⭐ MVP Gate: SC-005 우회 불가 검증"""

    def test_scenario_1_frontend_skip_parameter_is_ignored(self, temp_db: Path):
        """시나리오 1: 프론트엔드에서 'skip=true'를 GateContext에 전달해도 서버는 무시.

        GateContext 인터페이스에는 skip 필드가 아예 없으므로 외부에서 주입 불가.
        - 커스텀 kwargs/dict로 skip 플래그 주입 시도 → 거부됨을 검증.
        """
        import json as _json
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            # draft를 의도적으로 실패 상태로 만듦 (짧은 commentary)
            conn.execute(
                "UPDATE shorts_drafts SET commentary_json=?, commentary_char_count=? WHERE id=?",
                (_json.dumps([{"start": 0, "end": 1, "text": "짧", "style": "high"}]), 1, did),
            )
            conn.commit()

            # 어떤 형식으로도 gate를 건너뛰려 해도 → GateContext dataclass가 skip 필드를 안 받음
            with pytest.raises(TypeError):
                # dataclass에 불법 필드 주입 시도
                GateContext(
                    draft_id=did,
                    manual_fact_check_signed_by="owner",
                    manual_defamation_check_signed_by="owner",
                    operator_id="owner",
                    db_path=temp_db,
                    skip_gate=True,  # type: ignore
                )

            # 정상 호출은 여전히 실패해야 함 (commentary 너무 짧음)
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        assert result.overall_status == "fail"
        assert result.is_passed() is False

    def test_scenario_2_direct_api_without_manual_signatures(self, temp_db: Path):
        """시나리오 2: API를 직접 호출하며 manual 서명을 빈 값으로 전달 → 거부.

        manual_fact_check_signed_by = None 또는 빈 문자열 시 item_9/10 = fail.
        """
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by=None,  # 서명 안함
                manual_defamation_check_signed_by=None,
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        assert result.item_9_fact_checked == "fail"
        assert result.item_10_no_defamation == "fail"
        assert result.overall_status == "fail"
        assert result.is_passed() is False

    def test_scenario_2b_empty_string_signature_rejected(self, temp_db: Path):
        """서명을 빈 문자열로 주입해도 is_passed() 재검증에서 거부."""
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="",  # 빈 문자열
                manual_defamation_check_signed_by="",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)
        # 빈 문자열도 unsigned로 간주해야 함
        assert result.is_passed() is False

    def test_scenario_3_db_manipulation_re_verified(self, temp_db: Path):
        """시나리오 3: DB에 overall_status='pass'를 수동 삽입 후 is_passed() 호출 → 재검증으로 거부.

        악의적 사용자가 `UPDATE gate_results SET overall_status='pass'`를 해도,
        `is_passed()` 메서드는 저장된 아이템 상태와 서명을 다시 체크하므로 False 반환.
        """
        # 모든 아이템을 'fail'로 설정했지만 overall_status만 'pass'로 조작
        now = datetime.now(timezone.utc)
        fake = ComplianceGateResult(
            id=1,
            draft_id=1,
            item_1_commentary_length="fail",  # ← 실패 아이템
            item_2_ratio="pass",
            item_3_duration="pass",
            item_4_source_label="pass",
            item_5_bias_guardrail="pass",
            item_6_template_repeat="pass",
            item_7_whitelist_person="pass",
            item_8_election_guard="pass",
            item_9_fact_checked="pass",
            item_10_no_defamation="pass",
            manual_fact_check_signed_by="owner",
            manual_defamation_check_signed_by="owner",
            failure_reasons=(),
            overall_status="pass",  # ← 조작된 값
            risk_score=20.0,
            validated_at=now,
        )
        # is_passed()는 저장 필드를 재검증 → False
        assert fake.is_passed() is False

    def test_scenario_3b_risk_score_above_61_blocks_even_when_items_pass(self, temp_db: Path):
        """DB에 risk_score=70을 조작하고 overall='pass'로 저장해도 is_passed() = False."""
        now = datetime.now(timezone.utc)
        fake = ComplianceGateResult(
            id=1,
            draft_id=1,
            item_1_commentary_length="pass",
            item_2_ratio="pass",
            item_3_duration="pass",
            item_4_source_label="pass",
            item_5_bias_guardrail="pass",
            item_6_template_repeat="pass",
            item_7_whitelist_person="pass",
            item_8_election_guard="pass",
            item_9_fact_checked="pass",
            item_10_no_defamation="pass",
            manual_fact_check_signed_by="owner",
            manual_defamation_check_signed_by="owner",
            failure_reasons=(),
            overall_status="pass",
            risk_score=70.0,  # ← FR-026 임계값 61 초과
            validated_at=now,
        )
        assert fake.is_passed() is False


# ──────────────────────────────────────────────────────────────────────
# 3. validate() 저장 계약 — gate_results 테이블에 결과 저장
# ──────────────────────────────────────────────────────────────────────


class TestValidatePersistence:
    def test_result_saved_to_db(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            result = validate(ctx)

            # DB에 저장되었는지 확인
            row = conn.execute(
                "SELECT overall_status, manual_fact_check_signed_by FROM gate_results WHERE draft_id=?",
                (did,),
            ).fetchone()
        assert row is not None
        assert row[0] == result.overall_status
        assert row[1] == "owner"

    def test_idempotent_same_draft_updates_existing(self, temp_db: Path):
        """같은 draft_id로 두 번 호출 시 기존 행 업데이트 (1:1 unique)."""
        with get_connection(temp_db) as conn:
            _, _, did = _insert_complete_politician_segment_draft(conn)
            ctx = GateContext(
                draft_id=did,
                manual_fact_check_signed_by="owner",
                manual_defamation_check_signed_by="owner",
                operator_id="owner",
                db_path=temp_db,
            )
            validate(ctx)
            validate(ctx)
            cnt = conn.execute(
                "SELECT COUNT(*) FROM gate_results WHERE draft_id=?", (did,)
            ).fetchone()[0]
        assert cnt == 1
