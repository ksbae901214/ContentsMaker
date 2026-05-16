"""T120: 가드레일 키워드 가중치 재학습 배치 (FR-028, B-08).

운영자 수정·무시 이력(`guardrail_history`)을 분석해 키워드별 multiplier 를 재계산.

규칙:
- `operator_fixed` (운영자가 가드 지적을 받아 본문 수정) → 가드가 정확 → +10%/건
- `operator_ignored` (가드 지적을 무시하고 그대로 업로드) → false positive → -10%/건
- `warned` (운영자 확정 전 단계) → 학습 제외
- 같은 키워드의 fixed/ignored 는 합산 (네트 효과)
- multiplier 안전 범위: [0.5, 2.0] — 단일 키워드 폭주 방지

산출물: `data/dem_shorts/guardrail_weights.json`
- 운영자가 월간 검토 후 `keyword_dict.py` 의 KEYWORDS 목록에 수동 반영하거나,
  스캐너가 향후 이 파일을 overlay 로 로드해 자동 적용.

cron: `0 3 1 * *` (매월 1일 03:00)
명령: `python3 -m src.dem_shorts.cli guardrail-learn [--days 30] [--out PATH] [--dry-run]`
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_OUT_PATH = Path("data/dem_shorts/guardrail_weights.json")

# 단일 이력 1건의 multiplier 영향
PER_FIXED_DELTA = 0.10  # +10%
PER_IGNORED_DELTA = 0.10  # -10%

# multiplier 안전 범위
MULTIPLIER_MIN = 0.5
MULTIPLIER_MAX = 2.0


# ---------------------------------------------------------------------------
# 집계
# ---------------------------------------------------------------------------


def aggregate_history(
    conn: sqlite3.Connection, *, days: int = DEFAULT_LOOKBACK_DAYS
) -> dict[str, dict]:
    """guardrail_history 에서 fixed/ignored 액션을 키워드별로 집계.

    Returns:
        {keyword: {"fixed": int, "ignored": int, "category": str}}

    'warned' 만 있는 키워드는 결과에 포함하지 않음 (학습 시그널 없음).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT keyword, category, action
          FROM guardrail_history
         WHERE created_at >= ?
           AND action IN ('operator_fixed', 'operator_ignored')
        """,
        (cutoff,),
    ).fetchall()

    out: dict[str, dict] = {}
    for r in rows:
        kw = r["keyword"]
        bucket = out.setdefault(
            kw, {"fixed": 0, "ignored": 0, "category": r["category"]}
        )
        if r["action"] == "operator_fixed":
            bucket["fixed"] += 1
        elif r["action"] == "operator_ignored":
            bucket["ignored"] += 1
        # 마지막에 본 카테고리로 갱신 (보통 동일)
        bucket["category"] = r["category"]
    return out


# ---------------------------------------------------------------------------
# multiplier 계산
# ---------------------------------------------------------------------------


def compute_multipliers(
    aggregated: dict[str, dict],
) -> dict[str, dict]:
    """집계 결과로부터 키워드별 multiplier 를 계산.

    multiplier = clamp(1.0 + 0.10*fixed - 0.10*ignored, MIN, MAX)

    Returns:
        {keyword: {"multiplier": float, "category": str, "fixed": int, "ignored": int}}
    """
    out: dict[str, dict] = {}
    for kw, info in aggregated.items():
        fixed = int(info.get("fixed", 0))
        ignored = int(info.get("ignored", 0))
        net = fixed - ignored
        mult = 1.0 + PER_FIXED_DELTA * net
        mult = max(MULTIPLIER_MIN, min(MULTIPLIER_MAX, mult))
        out[kw] = {
            "multiplier": round(mult, 4),
            "category": info.get("category", ""),
            "fixed": fixed,
            "ignored": ignored,
        }
    return out


# ---------------------------------------------------------------------------
# 배치 진입점
# ---------------------------------------------------------------------------


def run_learning(
    conn: sqlite3.Connection,
    *,
    out_path: Path | str | None = None,
    days: int = DEFAULT_LOOKBACK_DAYS,
    dry_run: bool = False,
) -> dict:
    """월간 가드레일 키워드 가중치 재학습 메인 진입점.

    Returns:
        {
            "keywords_analyzed": int,
            "adjustments": int,           # multiplier != 1.0 인 키워드 수
            "out_path": str,
            "dry_run": bool,
        }
    """
    aggregated = aggregate_history(conn, days=days)
    multipliers = compute_multipliers(aggregated)

    adjustments = sum(1 for m in multipliers.values() if abs(m["multiplier"] - 1.0) > 1e-6)

    target = Path(out_path) if out_path else DEFAULT_OUT_PATH

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days": days,
        "keyword_multipliers": multipliers,
    }

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary = {
        "keywords_analyzed": len(multipliers),
        "adjustments": adjustments,
        "out_path": str(target),
        "dry_run": dry_run,
        "lookback_days": days,
    }
    logger.info("guardrail-learn done %s", summary)
    return summary
