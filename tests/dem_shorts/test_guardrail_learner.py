"""T120: 가드레일 학습 배치 테스트 (FR-028, B-08).

규칙:
- guardrail_history.action == "operator_ignored" → 가드가 false positive 였음
  → 해당 키워드 multiplier -10% (덜 경고)
- guardrail_history.action == "operator_fixed" → 가드가 정확했음
  → 해당 키워드 multiplier +10% (더 경고)
- "warned" 액션은 운영자 판단 전이므로 학습에서 제외
- 같은 키워드의 fixed/ignored가 동시 존재할 수 있음 (네트 효과 = 합)
- multiplier 는 [0.5, 2.0] 으로 클램핑 (극단값 방지)
- 출력: data/dem_shorts/guardrail_weights.json (운영자 검토 후 keyword_dict.py 반영)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, init_db


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "state.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def _add_history(conn, *, keyword, category, action, days_ago=10, draft_id=None):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    conn.execute(
        """
        INSERT INTO guardrail_history (draft_id, keyword, category, action, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (draft_id, keyword, category, action, ts),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# aggregate_history
# ---------------------------------------------------------------------------


def test_aggregate_counts_fixed_and_ignored_per_keyword(db):
    from src.dem_shorts.compliance.guardrail_learner import aggregate_history

    _add_history(db, keyword="빨갱이", category="hate", action="operator_fixed")
    _add_history(db, keyword="빨갱이", category="hate", action="operator_fixed")
    _add_history(db, keyword="절대", category="false_claim", action="operator_ignored")
    _add_history(db, keyword="절대", category="false_claim", action="operator_ignored")
    _add_history(db, keyword="절대", category="false_claim", action="operator_ignored")
    _add_history(db, keyword="역대급", category="bias", action="warned")  # 학습 제외

    agg = aggregate_history(db, days=30)
    assert agg["빨갱이"]["fixed"] == 2
    assert agg["빨갱이"]["ignored"] == 0
    assert agg["절대"]["fixed"] == 0
    assert agg["절대"]["ignored"] == 3
    assert "역대급" not in agg  # warned-only 키워드 제외


def test_aggregate_respects_lookback_window(db):
    from src.dem_shorts.compliance.guardrail_learner import aggregate_history

    _add_history(db, keyword="빨갱이", category="hate", action="operator_fixed", days_ago=10)
    _add_history(db, keyword="빨갱이", category="hate", action="operator_fixed", days_ago=200)

    agg = aggregate_history(db, days=30)
    assert agg["빨갱이"]["fixed"] == 1  # 200일 전 건은 제외


# ---------------------------------------------------------------------------
# compute_multipliers
# ---------------------------------------------------------------------------


def test_compute_multipliers_increases_for_true_positives():
    from src.dem_shorts.compliance.guardrail_learner import compute_multipliers

    agg = {"빨갱이": {"fixed": 3, "ignored": 0, "category": "hate"}}
    mults = compute_multipliers(agg)
    # +10% × 3 = 1.30
    assert mults["빨갱이"]["multiplier"] == pytest.approx(1.30, rel=1e-6)
    assert mults["빨갱이"]["category"] == "hate"


def test_compute_multipliers_decreases_for_false_positives():
    from src.dem_shorts.compliance.guardrail_learner import compute_multipliers

    agg = {"절대": {"fixed": 0, "ignored": 4, "category": "false_claim"}}
    mults = compute_multipliers(agg)
    # 1.0 - 0.10 × 4 = 0.60
    assert mults["절대"]["multiplier"] == pytest.approx(0.60, rel=1e-6)


def test_compute_multipliers_clamps_to_safe_range():
    from src.dem_shorts.compliance.guardrail_learner import compute_multipliers

    agg = {
        "extreme_pos": {"fixed": 50, "ignored": 0, "category": "hate"},
        "extreme_neg": {"fixed": 0, "ignored": 50, "category": "bias"},
    }
    mults = compute_multipliers(agg)
    assert mults["extreme_pos"]["multiplier"] == pytest.approx(2.0)
    assert mults["extreme_neg"]["multiplier"] == pytest.approx(0.5)


def test_compute_multipliers_nets_fixed_and_ignored():
    from src.dem_shorts.compliance.guardrail_learner import compute_multipliers

    agg = {"중립": {"fixed": 2, "ignored": 2, "category": "bias"}}
    mults = compute_multipliers(agg)
    # net 0 → 1.0
    assert mults["중립"]["multiplier"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# run_learning — 통합 진입점
# ---------------------------------------------------------------------------


def test_run_learning_writes_json(db, tmp_path):
    from src.dem_shorts.compliance.guardrail_learner import run_learning

    _add_history(db, keyword="빨갱이", category="hate", action="operator_fixed")
    _add_history(db, keyword="절대", category="false_claim", action="operator_ignored")

    out_path = tmp_path / "weights.json"
    summary = run_learning(db, out_path=out_path, days=30)

    assert summary["keywords_analyzed"] == 2
    assert summary["adjustments"] == 2
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "generated_at" in payload
    assert "keyword_multipliers" in payload
    assert payload["keyword_multipliers"]["빨갱이"]["multiplier"] > 1.0
    assert payload["keyword_multipliers"]["절대"]["multiplier"] < 1.0


def test_run_learning_dry_run_skips_write(db, tmp_path):
    from src.dem_shorts.compliance.guardrail_learner import run_learning

    _add_history(db, keyword="빨갱이", category="hate", action="operator_fixed")

    out_path = tmp_path / "weights.json"
    summary = run_learning(db, out_path=out_path, days=30, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["adjustments"] >= 1
    assert not out_path.exists()


def test_run_learning_no_history_writes_empty(db, tmp_path):
    from src.dem_shorts.compliance.guardrail_learner import run_learning

    out_path = tmp_path / "weights.json"
    summary = run_learning(db, out_path=out_path, days=30)
    assert summary["keywords_analyzed"] == 0
    assert summary["adjustments"] == 0
    # 빈 결과도 파일은 생성 (운영자가 "이번 달은 변동 없음" 확인 가능)
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["keyword_multipliers"] == {}
