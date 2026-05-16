"""ComplianceGateResult — 10개 항목 컴플라이언스 검증 이력.

Spec: specs/007-dem-shorts-studio/data-model.md §5
⚠️ SC-005: 100% 우회 불가 게이트 — 모든 판정은 서버사이드에서만 결정
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_ITEM_STATUSES = {"pass", "fail", "warn"}
_OVERALL = {"pass", "fail", "warn_only"}

RISK_SCORE_BLOCK_THRESHOLD = 61.0  # FR-026


@dataclass(frozen=True)
class ComplianceGateResult:
    """10개 항목 검증 + 수동 서명 2개. overall_status='pass' 조건은 validate()에서 강제."""

    id: int
    draft_id: int

    # 10 items (FR-025)
    item_1_commentary_length: str  # 해설 ≥50자 (차단)
    item_2_ratio: str  # 원본≤50%, 해설≥30% (차단)
    item_3_duration: str  # ≤60초 (차단)
    item_4_source_label: str  # NATV 출처 (차단)
    item_5_bias_guardrail: str  # 편향 게이트 (경고)
    item_6_template_repeat: str  # 최근 3회 연속 아님 (경고)
    item_7_whitelist_person: str  # Whitelist 1명↑ (차단)
    item_8_election_guard: str  # 선거법 (차단)
    item_9_fact_checked: str  # 운영자 수동 (차단)
    item_10_no_defamation: str  # 운영자 수동 (차단)

    # Manual signatures (FR-025 items 9, 10)
    manual_fact_check_signed_by: str | None
    manual_defamation_check_signed_by: str | None

    failure_reasons: tuple[dict, ...]
    overall_status: str  # pass/fail/warn_only
    risk_score: float  # 0~100
    validated_at: datetime

    # Item keys blocked if fail (차단 vs 경고)
    _BLOCKING_ITEMS = (
        "item_1_commentary_length",
        "item_2_ratio",
        "item_3_duration",
        "item_4_source_label",
        "item_7_whitelist_person",
        "item_8_election_guard",
        "item_9_fact_checked",
        "item_10_no_defamation",
    )
    _WARNING_ITEMS = (
        "item_5_bias_guardrail",
        "item_6_template_repeat",
    )

    def __post_init__(self) -> None:
        all_items = self._BLOCKING_ITEMS + self._WARNING_ITEMS
        for k in all_items:
            v = getattr(self, k)
            if v not in _ITEM_STATUSES:
                raise ValueError(f"invalid status for {k}: {v}")
        if self.overall_status not in _OVERALL:
            raise ValueError(f"invalid overall_status: {self.overall_status}")

    def is_passed(self) -> bool:
        """⭐ 우회 불가 조건 (SC-005).

        모든 blocking items가 pass **AND** 수동 서명 2개 NOT NULL **AND**
        risk_score < 61.
        """
        for item_key in self._BLOCKING_ITEMS:
            if getattr(self, item_key) != "pass":
                return False
        if self.manual_fact_check_signed_by is None:
            return False
        if self.manual_defamation_check_signed_by is None:
            return False
        if self.risk_score >= RISK_SCORE_BLOCK_THRESHOLD:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "draft_id": self.draft_id,
            "item_1_commentary_length": self.item_1_commentary_length,
            "item_2_ratio": self.item_2_ratio,
            "item_3_duration": self.item_3_duration,
            "item_4_source_label": self.item_4_source_label,
            "item_5_bias_guardrail": self.item_5_bias_guardrail,
            "item_6_template_repeat": self.item_6_template_repeat,
            "item_7_whitelist_person": self.item_7_whitelist_person,
            "item_8_election_guard": self.item_8_election_guard,
            "item_9_fact_checked": self.item_9_fact_checked,
            "item_10_no_defamation": self.item_10_no_defamation,
            "manual_fact_check_signed_by": self.manual_fact_check_signed_by,
            "manual_defamation_check_signed_by": self.manual_defamation_check_signed_by,
            "failure_reasons": list(self.failure_reasons),
            "overall_status": self.overall_status,
            "risk_score": self.risk_score,
            "validated_at": self.validated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ComplianceGateResult:
        return cls(
            id=int(data["id"]),
            draft_id=int(data["draft_id"]),
            item_1_commentary_length=data["item_1_commentary_length"],
            item_2_ratio=data["item_2_ratio"],
            item_3_duration=data["item_3_duration"],
            item_4_source_label=data["item_4_source_label"],
            item_5_bias_guardrail=data["item_5_bias_guardrail"],
            item_6_template_repeat=data["item_6_template_repeat"],
            item_7_whitelist_person=data["item_7_whitelist_person"],
            item_8_election_guard=data["item_8_election_guard"],
            item_9_fact_checked=data["item_9_fact_checked"],
            item_10_no_defamation=data["item_10_no_defamation"],
            manual_fact_check_signed_by=data.get("manual_fact_check_signed_by"),
            manual_defamation_check_signed_by=data.get("manual_defamation_check_signed_by"),
            failure_reasons=tuple(data.get("failure_reasons") or []),
            overall_status=data["overall_status"],
            risk_score=float(data.get("risk_score", 0.0)),
            validated_at=_parse_dt(data["validated_at"]),
        )


def _parse_dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)
