"""T079/T080: ⭐⭐⭐ 10-Item Compliance Gate — **100% 우회 불가** (SC-005, FR-025, FR-026).

**핵심 원칙**:
1. 모든 검사는 서버사이드에서만 결정 — 프론트엔드 우회 불가
2. `GateContext` dataclass는 `skip_gate` 같은 필드 없음 — 우회 시도 시 TypeError
3. `validate()`가 저장하는 `ComplianceGateResult.is_passed()`는 실제 아이템/서명/점수를
   재검증하므로, DB 수동 조작으로 overall_status만 바꿔도 거부됨
4. `render` / `upload` API는 `is_passed()` 재확인 (이중 방어)

**10개 아이템 (FR-025)**:
1. commentary 50자 이상 — 자동, 차단
2. 원본≤50%, 해설≥30% — 자동, 차단
3. 전체 길이 ≤60초 — 자동, 차단
4. NATV 출처 표시 — 자동, 차단
5. 편향 가드레일 통과 — 자동, 경고
6. 최근 3회 연속 동일 템플릿 아님 — 자동, 경고
7. Whitelist 인물 1명 이상 — 자동, 차단
8. 선거법 가드 — 자동, 차단 (Stub = 항상 pass)
9. 팩트 검증 (수동) — 수동, 차단
10. 명예훼손 없음 (수동) — 수동, 차단
"""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.dem_shorts.compliance.election_guard import (
    get_bias_threshold,
    is_in_election_period,
)
from src.dem_shorts.compliance.guardrail import run_guardrail
from src.dem_shorts.config import (
    COMMENTARY_MIN_CHARS,
    COMMENTARY_RATIO_MIN,
    CUT_MAX_SEC,
    FACT_LINKS_MIN,
    ORIGINAL_RATIO_MAX,
    RISK_SCORE_BLOCK,
    TEMPLATE_REPEAT_MAX,
)
from src.dem_shorts.db import get_connection
from src.dem_shorts.models.gate_result import ComplianceGateResult
from src.dem_shorts.utils.paths import DB_PATH

logger = logging.getLogger(__name__)


class GateError(Exception):
    """Raised when gate operation has a hard infrastructure failure (not item failure)."""


@dataclass(frozen=True)
class GateContext:
    """게이트 실행 컨텍스트.

    ⚠️ **이 dataclass는 skip 필드를 절대 포함하지 않음**. 우회 파라미터 주입 시
    Python 3 dataclass가 TypeError 발생 → 프론트엔드 우회 불가 (SC-005 시나리오 1).
    """

    draft_id: int
    manual_fact_check_signed_by: str | None
    manual_defamation_check_signed_by: str | None
    operator_id: str
    db_path: Path = field(default_factory=lambda: DB_PATH)


@dataclass(frozen=True)
class ItemResult:
    """단일 아이템 검사 결과."""

    status: str  # "pass"/"fail"/"warn"
    reason: str | None = None


class GateChecker:
    """10개 아이템 각각에 대한 검사 로직.

    DB에서 draft + 연관 데이터를 로드한 후 item_1~item_10 메서드로 각 아이템 평가.
    """

    def __init__(self, conn: sqlite3.Connection, draft_id: int):
        self._conn = conn
        self._draft_id = draft_id
        self._draft = self._load_draft(draft_id)
        if self._draft is None:
            raise GateError(f"draft_not_found: id={draft_id}")
        self._segment = self._load_segment(self._draft["segment_id"])
        self._politician = self._load_politician_for_segment(self._segment)

    # ── Data loaders ────────────────────────────────────────────

    def _load_draft(self, did: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM shorts_drafts WHERE id = ?", (did,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["commentary_blocks"] = json.loads(d.get("commentary_json") or "[]")
        d["fact_source_urls"] = json.loads(d.get("fact_source_urls") or "[]")
        return d

    def _load_segment(self, sid: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM speech_segments WHERE id = ?", (sid,)
        ).fetchone()
        return dict(row) if row else None

    def _load_politician_for_segment(self, segment: dict | None) -> dict | None:
        if not segment or segment.get("politician_id") is None:
            return None
        row = self._conn.execute(
            "SELECT * FROM politicians WHERE id = ?", (segment["politician_id"],)
        ).fetchone()
        return dict(row) if row else None

    # ── 10 item checks ──────────────────────────────────────────

    def item_1_commentary_length(self) -> ItemResult:
        """해설 50자 이상 (FR-024)."""
        count = int(self._draft.get("commentary_char_count", 0) or 0)
        if count >= COMMENTARY_MIN_CHARS:
            return ItemResult("pass")
        return ItemResult("fail", f"해설 자막 {count}자 (50자 이상 필요)")

    def item_2_ratio(self) -> ItemResult:
        """원본 ≤50%, 해설 ≥30%.

        - 원본 비율 = cut_duration / (cut_duration) = 100% (shorts는 자른 구간이 그대로 본체)
          → 실제로는 원본 음성 시간 vs 전체 영상 시간 비율로 판정하기 애매하므로
            "해설 자막이 cut_duration의 30% 이상 덮는지"로 근사.
        - 쇼츠 특성상 항상 원본이 100% 노출 → 원본 비율 제한은 의미가 다름.
          MVP에서는 "commentary 총 시간 / cut_duration >= 0.3" 만 체크.
        """
        cut_duration = float(self._draft["cut_end_sec"]) - float(self._draft["cut_start_sec"])
        if cut_duration <= 0:
            return ItemResult("fail", "cut_duration 비정상")
        blocks = self._draft["commentary_blocks"] or []
        commentary_total = sum(
            max(0.0, float(b.get("end", 0)) - float(b.get("start", 0))) for b in blocks
        )
        ratio = commentary_total / cut_duration
        if ratio >= COMMENTARY_RATIO_MIN:
            return ItemResult("pass")
        return ItemResult(
            "fail",
            f"해설 커버리지 {ratio*100:.1f}% (30% 이상 필요)",
        )

    def item_3_duration(self) -> ItemResult:
        """전체 길이 ≤60초 (FR-018)."""
        cut_duration = float(self._draft["cut_end_sec"]) - float(self._draft["cut_start_sec"])
        if 0 < cut_duration <= CUT_MAX_SEC:
            return ItemResult("pass")
        return ItemResult(
            "fail",
            f"cut_duration {cut_duration}초 ({CUT_MAX_SEC}초 초과 불가)",
        )

    def item_4_source_label(self) -> ItemResult:
        """NATV 출처 표시 — 해설 블록 존재 시 DemShortsComposition이 자동 렌더하므로
        commentary_blocks가 비어있지 않고, draft가 source_video_id와 연결되어 있으면 pass."""
        if not self._draft["commentary_blocks"]:
            return ItemResult("fail", "commentary_blocks 비어있음 (source_label 렌더 불가)")
        if not self._segment:
            return ItemResult("fail", "source segment 누락")
        return ItemResult("pass")

    def item_5_bias_guardrail(self) -> ItemResult:
        """편향 가드레일 (경고 등급). skip_llm=True로 계층1만 사용 (배치 속도).

        FR-031: 선거기간 중에는 편향 임계값이 30점으로 하향 적용된다.
        """
        blocks = self._draft["commentary_blocks"] or []
        text = "\n".join(b.get("text", "") for b in blocks)
        if not text:
            return ItemResult("warn", "commentary 없음")
        result = run_guardrail(text, skip_llm=True)
        threshold = get_bias_threshold()
        if result.risk_score >= threshold:
            return ItemResult(
                "fail",
                f"편향 리스크 {result.risk_score:.1f} ≥ {threshold}",
            )
        if result.status == "warn":
            return ItemResult("warn", f"편향 리스크 {result.risk_score:.1f} (경고)")
        return ItemResult("pass")

    def item_6_template_repeat(self) -> ItemResult:
        """최근 3회 연속 동일 subtitle_preset 사용 시 경고 (FR-027)."""
        current_preset = self._draft.get("subtitle_preset", "default")
        rows = self._conn.execute(
            "SELECT subtitle_preset FROM shorts_drafts "
            "WHERE id < ? AND status IN ('gate_passed','rendered','uploaded') "
            "ORDER BY id DESC LIMIT ?",
            (self._draft_id, TEMPLATE_REPEAT_MAX),
        ).fetchall()
        recent = [r[0] for r in rows]
        if len(recent) >= TEMPLATE_REPEAT_MAX and all(p == current_preset for p in recent):
            return ItemResult("warn", f"최근 {TEMPLATE_REPEAT_MAX}회 연속 '{current_preset}' 프리셋 사용")
        return ItemResult("pass")

    def item_7_whitelist_person(self) -> ItemResult:
        """Whitelist 인물 1명 이상 식별 + 활성 상태."""
        if not self._politician:
            return ItemResult("fail", "segment에 식별된 정치인 없음")
        if not self._politician.get("is_active"):
            return ItemResult("fail", f"{self._politician['name']}이(가) 비활성 상태")
        tier = self._politician.get("tier")
        if tier == "blocked":
            return ItemResult("fail", f"{self._politician['name']}은(는) 차단 등급")
        return ItemResult("pass")

    def item_8_election_guard(self) -> ItemResult:
        """선거법 가드 (Stub: 항상 pass, US4에서 실제 구현)."""
        if is_in_election_period():
            # 선거기간이면 편향 임계값이 하향 적용되어야 하지만, Stub이라 여기서는 pass.
            # US4 T098에서 실제 로직으로 교체.
            return ItemResult("pass", "선거기간 중 (neutral mode 권장)")
        return ItemResult("pass")

    def item_9_fact_checked(self, signed_by: str | None) -> ItemResult:
        """수동 팩트 체크 + 팩트 URL ≥2개 (FR-029)."""
        fact_urls = self._draft.get("fact_source_urls") or []
        if len(fact_urls) < FACT_LINKS_MIN:
            return ItemResult(
                "fail",
                f"팩트 URL {len(fact_urls)}개 ({FACT_LINKS_MIN}개 이상 필요)",
            )
        if not signed_by or not signed_by.strip():
            return ItemResult("fail", "수동 팩트 체크 서명 없음")
        return ItemResult("pass")

    def item_10_no_defamation(self, signed_by: str | None) -> ItemResult:
        """수동 명예훼손 체크."""
        if not signed_by or not signed_by.strip():
            return ItemResult("fail", "수동 명예훼손 체크 서명 없음")
        return ItemResult("pass")


def _compute_risk_score(checker: GateChecker) -> float:
    """전체 리스크 점수 (계층1+2 통합). gate bias 항목과 동일한 계산.

    DB/네트워크 비용 절감 위해 item_5와 동일 텍스트로 run_guardrail 호출.
    """
    blocks = checker._draft["commentary_blocks"] or []
    text = "\n".join(b.get("text", "") for b in blocks)
    if not text:
        return 0.0
    # skip_llm=True: gate에서는 계층1만 즉시 사용 (LLM은 별도 CLI commentary 단계에서).
    result = run_guardrail(text, skip_llm=True)
    return result.risk_score


def validate(ctx: GateContext) -> ComplianceGateResult:
    """10개 아이템 검사 + 수동 서명 검증 + gate_results 저장.

    Returns:
        ComplianceGateResult with is_passed() reflecting true state.

    Raises:
        GateError: draft 없음 or DB 실패.
    """
    with get_connection(ctx.db_path) as conn:
        checker = GateChecker(conn, ctx.draft_id)

        # Item checks
        r1 = checker.item_1_commentary_length()
        r2 = checker.item_2_ratio()
        r3 = checker.item_3_duration()
        r4 = checker.item_4_source_label()
        r5 = checker.item_5_bias_guardrail()
        r6 = checker.item_6_template_repeat()
        r7 = checker.item_7_whitelist_person()
        r8 = checker.item_8_election_guard()
        r9 = checker.item_9_fact_checked(ctx.manual_fact_check_signed_by)
        r10 = checker.item_10_no_defamation(ctx.manual_defamation_check_signed_by)

        results = {
            "item_1_commentary_length": r1,
            "item_2_ratio": r2,
            "item_3_duration": r3,
            "item_4_source_label": r4,
            "item_5_bias_guardrail": r5,
            "item_6_template_repeat": r6,
            "item_7_whitelist_person": r7,
            "item_8_election_guard": r8,
            "item_9_fact_checked": r9,
            "item_10_no_defamation": r10,
        }

        risk_score = _compute_risk_score(checker)

        # Failure reasons collected
        failure_reasons: list[dict] = []
        for key, res in results.items():
            if res.status in ("fail", "warn") and res.reason:
                failure_reasons.append({"item": key, "reason": res.reason})

        # Overall status (동일 조건을 ComplianceGateResult.is_passed()가 재검증)
        blocking_items = [
            "item_1_commentary_length",
            "item_2_ratio",
            "item_3_duration",
            "item_4_source_label",
            "item_7_whitelist_person",
            "item_8_election_guard",
            "item_9_fact_checked",
            "item_10_no_defamation",
        ]
        all_blocking_pass = all(results[k].status == "pass" for k in blocking_items)
        signed = bool(
            (ctx.manual_fact_check_signed_by or "").strip()
            and (ctx.manual_defamation_check_signed_by or "").strip()
        )
        risk_ok = risk_score < get_bias_threshold()

        if all_blocking_pass and signed and risk_ok:
            overall = "pass"
        elif all_blocking_pass and not any(results[k].status == "fail" for k in blocking_items):
            # 차단 아이템은 모두 pass인데 경고만 있고 서명/점수도 OK면 warn_only
            overall = "warn_only" if not signed or not risk_ok else "pass"
        else:
            overall = "fail"

        # 최종 방어: 하나라도 fail이면 강제 fail
        if any(r.status == "fail" for r in results.values()) or not signed or not risk_ok:
            overall = "fail" if not (all_blocking_pass and signed and risk_ok) else "pass"

        # 경고만 있는 경우
        if overall != "fail" and not all_blocking_pass:
            overall = "fail"

        now = datetime.now(timezone.utc).isoformat()

        # UPSERT gate_results (draft_id UNIQUE)
        conn.execute(
            """
            INSERT INTO gate_results (
                draft_id,
                item_1_commentary_length, item_2_ratio, item_3_duration, item_4_source_label,
                item_5_bias_guardrail, item_6_template_repeat, item_7_whitelist_person,
                item_8_election_guard, item_9_fact_checked, item_10_no_defamation,
                manual_fact_check_signed_by, manual_defamation_check_signed_by,
                failure_reasons, overall_status, risk_score, validated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(draft_id) DO UPDATE SET
                item_1_commentary_length=excluded.item_1_commentary_length,
                item_2_ratio=excluded.item_2_ratio,
                item_3_duration=excluded.item_3_duration,
                item_4_source_label=excluded.item_4_source_label,
                item_5_bias_guardrail=excluded.item_5_bias_guardrail,
                item_6_template_repeat=excluded.item_6_template_repeat,
                item_7_whitelist_person=excluded.item_7_whitelist_person,
                item_8_election_guard=excluded.item_8_election_guard,
                item_9_fact_checked=excluded.item_9_fact_checked,
                item_10_no_defamation=excluded.item_10_no_defamation,
                manual_fact_check_signed_by=excluded.manual_fact_check_signed_by,
                manual_defamation_check_signed_by=excluded.manual_defamation_check_signed_by,
                failure_reasons=excluded.failure_reasons,
                overall_status=excluded.overall_status,
                risk_score=excluded.risk_score,
                validated_at=excluded.validated_at
            """,
            (
                ctx.draft_id,
                r1.status, r2.status, r3.status, r4.status,
                r5.status, r6.status, r7.status, r8.status, r9.status, r10.status,
                ctx.manual_fact_check_signed_by,
                ctx.manual_defamation_check_signed_by,
                json.dumps(failure_reasons, ensure_ascii=False),
                overall,
                risk_score,
                now,
            ),
        )
        # Also update ShortsDraft.risk_score and status
        new_draft_status = "gate_passed" if overall == "pass" else "gate_failed"
        conn.execute(
            "UPDATE shorts_drafts SET risk_score=?, status=?, updated_at=? WHERE id=?",
            (risk_score, new_draft_status, now, ctx.draft_id),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM gate_results WHERE draft_id = ?", (ctx.draft_id,)
        ).fetchone()

    # Convert row → ComplianceGateResult (is_passed()가 재검증 수행)
    raw = dict(row)
    raw["failure_reasons"] = json.loads(raw.get("failure_reasons") or "[]")
    return ComplianceGateResult.from_dict(raw)


def get_latest_result(draft_id: int, db_path: Path | None = None) -> ComplianceGateResult | None:
    """render/upload API가 호출 — 저장된 gate_result를 로드해 `is_passed()` 재확인."""
    path = db_path or DB_PATH
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT * FROM gate_results WHERE draft_id = ?", (draft_id,)
        ).fetchone()
    if not row:
        return None
    raw = dict(row)
    raw["failure_reasons"] = json.loads(raw.get("failure_reasons") or "[]")
    return ComplianceGateResult.from_dict(raw)
