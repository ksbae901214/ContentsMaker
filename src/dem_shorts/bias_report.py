"""T112: 월간 편향 밸런스 리포트 생성 (FR-038, perspective-aware).

`uploaded_shorts` 집계 → 인물·정당·자막 프리셋 점유율 + 권고 메시지.

검증 기준 (2026-04-20 perspective 일반화):
- SC-011: 단일 인물 30% 초과 / 활성 perspective TOP 인물 합계 60% 초과 → 권고
- SC-012: 여성·청년 카테고리 합계 40% 미만 → 차별화 미달 권고

Storage: SQLite `bias_reports` (materialized view).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

from src.dem_shorts.config import DEFAULT_PERSPECTIVE, PERSPECTIVE_LABELS
from src.dem_shorts.models.bias_report import BiasReport
from src.dem_shorts.scoring import get_top_names

logger = logging.getLogger(__name__)

_SINGLE_PERSON_WARN_THRESHOLD = 0.30  # SC-011
_TOP3_SUM_WARN_THRESHOLD = 0.60  # SC-011
_FEMALE_YOUTH_MIN = 0.40  # SC-012


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------


def resolve_previous_month(today: date | None = None) -> date:
    """주어진 날짜가 속한 달의 직전 달 1일 반환."""
    today = today or date.today()
    year = today.year
    month = today.month - 1
    if month == 0:
        month = 12
        year -= 1
    return date(year, month, 1)


def _next_month_first(month: date) -> date:
    """다음 달 1일 반환 (월별 범위 상한)."""
    year = month.year
    m = month.month + 1
    if m == 13:
        m = 1
        year += 1
    return date(year, m, 1)


def _ratio(counter: Counter, total: int) -> dict:
    if total <= 0:
        return {}
    return {k: round(v / total, 6) for k, v in counter.items()}


# ---------------------------------------------------------------------------
# 집계
# ---------------------------------------------------------------------------


def _fetch_uploads(
    conn: sqlite3.Connection, month: date
) -> list[sqlite3.Row]:
    """해당 월의 업로드 레코드 + 연결된 정치인/프리셋 JOIN.

    uploaded_shorts.uploaded_at을 월 필터 기준으로 사용.
    """
    start = month.isoformat()
    end = _next_month_first(month).isoformat()
    return conn.execute(
        """
        SELECT
          us.id                     AS upload_id,
          us.uploaded_at            AS uploaded_at,
          sd.subtitle_preset        AS subtitle_preset,
          sd.risk_score             AS risk_score,
          p.name                    AS politician_name,
          p.party                   AS politician_party,
          p.category                AS politician_category
        FROM uploaded_shorts us
        JOIN shorts_drafts sd ON sd.id = us.draft_id
        LEFT JOIN speech_segments ss ON ss.id = sd.segment_id
        LEFT JOIN politicians p      ON p.id = ss.politician_id
        WHERE us.uploaded_at >= ? AND us.uploaded_at < ?
        """,
        (start, end),
    ).fetchall()


def _build_recommendations(
    person_shares: dict[str, float],
    party_shares: dict[str, float],
    female_youth_share: float,
    perspective: str = DEFAULT_PERSPECTIVE,
) -> list[str]:
    recs: list[str] = []

    # SC-011: 단일 인물 30% 초과
    for name, share in person_shares.items():
        if share > _SINGLE_PERSON_WARN_THRESHOLD:
            recs.append(
                f"{name} 점유율 {share * 100:.1f}% — 권장 상한 30% 초과. 비중 조정 필요."
            )

    # SC-011: 활성 perspective TOP 인물 합계 60% 초과
    top_names = get_top_names(perspective)
    top_sum = sum(person_shares.get(n, 0.0) for n in top_names)
    if top_sum > _TOP3_SUM_WARN_THRESHOLD:
        label = PERSPECTIVE_LABELS.get(perspective, perspective)
        names_str = "·".join(top_names)
        recs.append(
            f"{label} TOP 인물({names_str}) 합계 {top_sum * 100:.1f}% — "
            "권장 상한 60% 초과. 여성·청년 정치인 다양성 보강 필요."
        )

    # SC-012: 여성·청년 40% 미만
    if female_youth_share < _FEMALE_YOUTH_MIN:
        recs.append(
            f"여성·청년 카테고리 합계 {female_youth_share * 100:.1f}% — 권장 최소 40% 미달. "
            "차별화를 위해 여성·청년 정치인 발언 업로드를 늘릴 것."
        )

    return recs


def generate_bias_report(
    conn: sqlite3.Connection,
    *,
    month: date | None = None,
    persist: bool = False,
    perspective: str = DEFAULT_PERSPECTIVE,
) -> BiasReport:
    """월간 편향 리포트 생성.

    Args:
        conn: SQLite connection.
        month: 리포트 대상 월의 1일. None이면 지난 달.
        persist: True면 bias_reports 테이블에 upsert.

    Returns:
        BiasReport frozen dataclass.
    """
    month = month or resolve_previous_month()
    rows = _fetch_uploads(conn, month)

    total = len(rows)
    person_counter: Counter = Counter()
    party_counter: Counter = Counter()
    template_counter: Counter = Counter()
    category_counter: Counter = Counter()
    risk_sum = 0.0

    for r in rows:
        name = r["politician_name"] or "(미식별)"
        party = r["politician_party"] or "(미식별)"
        category = r["politician_category"] or "(미식별)"
        preset = r["subtitle_preset"] or "default"
        person_counter[name] += 1
        party_counter[party] += 1
        template_counter[preset] += 1
        category_counter[category] += 1
        try:
            risk_sum += float(r["risk_score"] or 0.0)
        except (TypeError, ValueError):
            pass

    person_shares = _ratio(person_counter, total)
    party_shares = _ratio(party_counter, total)
    template_usage = dict(template_counter)  # 점유율이 아니라 절대 사용 횟수

    female_youth = category_counter.get("female", 0) + category_counter.get("youth", 0)
    female_youth_share = (female_youth / total) if total else 0.0

    # SC-011 경고 대상
    warning_names = tuple(
        name for name, share in person_shares.items()
        if share > _SINGLE_PERSON_WARN_THRESHOLD
    )

    recommendations: tuple[str, ...] = (
        tuple(_build_recommendations(person_shares, party_shares, female_youth_share, perspective))
        if total
        else ()
    )

    now = datetime.now(timezone.utc)
    report = BiasReport(
        id=0,
        month=month,
        total_uploads=total,
        person_shares=person_shares,
        party_shares=party_shares,
        template_usage=template_usage,
        avg_risk_score=(risk_sum / total) if total else 0.0,
        top_n_person_warning=warning_names,
        recommendations=recommendations,
        generated_at=now,
    )

    if persist:
        _upsert_report(conn, report)

    return report


def _upsert_report(conn: sqlite3.Connection, report: BiasReport) -> int:
    """bias_reports에 month 기준 upsert."""
    now = report.generated_at.isoformat()
    existing = conn.execute(
        "SELECT id FROM bias_reports WHERE month=?",
        (report.month.isoformat(),),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE bias_reports
               SET total_uploads=?, person_shares=?, party_shares=?,
                   template_usage=?, avg_risk_score=?,
                   top_n_person_warning=?, recommendations=?, generated_at=?
             WHERE id=?
            """,
            (
                report.total_uploads,
                json.dumps(report.person_shares, ensure_ascii=False),
                json.dumps(report.party_shares, ensure_ascii=False),
                json.dumps(report.template_usage, ensure_ascii=False),
                report.avg_risk_score,
                json.dumps(list(report.top_n_person_warning), ensure_ascii=False),
                json.dumps(list(report.recommendations), ensure_ascii=False),
                now,
                existing["id"],
            ),
        )
        conn.commit()
        return existing["id"]

    cur = conn.execute(
        """
        INSERT INTO bias_reports
          (month, total_uploads, person_shares, party_shares, template_usage,
           avg_risk_score, top_n_person_warning, recommendations, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.month.isoformat(),
            report.total_uploads,
            json.dumps(report.person_shares, ensure_ascii=False),
            json.dumps(report.party_shares, ensure_ascii=False),
            json.dumps(report.template_usage, ensure_ascii=False),
            report.avg_risk_score,
            json.dumps(list(report.top_n_person_warning), ensure_ascii=False),
            json.dumps(list(report.recommendations), ensure_ascii=False),
            now,
        ),
    )
    conn.commit()
    return cur.lastrowid
