"""T110: 주간 여성·청년 정치인 랭킹 배치 (FR-008, FR-009).

5개 공공·무료 데이터 소스를 가중합산 → z-score → sigmoid → 0~100 정규화 →
상위 N명을 `politicians.tier='auto'` 승격, 2주 연속 탈락자는 삭제.

- R-06 가중치: config.RANKING_SOURCE_WEIGHTS
- 태그 규칙:
    * 신규 등장: "new"
    * 전주 대비 +15 이상: "rising"
    * 상위 N 이탈: "pending"

의존성: T105~T109 (`ranking/` 하위 5개 모듈).
실행: `python3 -m src.dem_shorts.cli ranking-batch` (B-03 cron: `0 22 * * 0`)
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
import statistics
from datetime import date, datetime, timedelta
from typing import Iterable

from src.dem_shorts.config import (
    RANKING_PENDING_WEEKS,
    RANKING_SOURCE_WEIGHTS,
    RANKING_TOP_N,
)
from src.dem_shorts.ranking import (
    google_trends,
    naver_datalab,
    naver_news,
    wikipedia_pageviews,
    youtube_metrics,
)

logger = logging.getLogger(__name__)

_RISING_DELTA_THRESHOLD = 15.0


# ---------------------------------------------------------------------------
# 공통 계산 유틸
# ---------------------------------------------------------------------------


def resolve_week_start(today: date | None = None) -> date:
    """주어진 날짜가 속한 주의 월요일 반환 (ISO 주 규약)."""
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def combine_source_scores(raw_per_source: dict[str, float]) -> float:
    """개별 정치인의 소스별 점수에 RANKING_SOURCE_WEIGHTS 적용 후 가중합.

    누락 소스는 0 처리.
    """
    total = 0.0
    for source, weight in RANKING_SOURCE_WEIGHTS.items():
        total += float(raw_per_source.get(source, 0.0)) * weight
    return total


def normalize_scores(raw_scores: dict[int, float]) -> dict[int, float]:
    """z-score + sigmoid로 0~100 정규화.

    전원 동일 값이면 50점 균등 분포.
    """
    if not raw_scores:
        return {}
    values = list(raw_scores.values())
    if len(values) == 1:
        return {next(iter(raw_scores)): 50.0}

    mean = statistics.mean(values)
    stdev = statistics.pstdev(values) or 0.0
    out: dict[int, float] = {}
    for pid, v in raw_scores.items():
        if stdev == 0.0:
            out[pid] = 50.0
            continue
        z = (v - mean) / stdev
        # sigmoid(z) → 0~1 → 0~100
        sig = 1.0 / (1.0 + math.exp(-z))
        out[pid] = round(sig * 100.0, 3)
    return out


# ---------------------------------------------------------------------------
# 소스 호출
# ---------------------------------------------------------------------------


def fetch_all_sources(
    conn: sqlite3.Connection, names: Iterable[str]
) -> dict[str, dict[str, float]]:
    """5개 소스를 순회하며 각각 정치인별 raw score dict를 반환한다.

    테스트에서는 이 함수를 mock해 네트워크 호출을 우회한다.
    반환 형식: {source_name: {politician_name: raw_score, ...}, ...}
    """
    names_list = list(names)
    return {
        "naver_news": naver_news.fetch_scores(names_list),
        "google_trends": google_trends.fetch_scores(names_list),
        "youtube_metrics": youtube_metrics.fetch_scores(names_list),
        "wikipedia_pageviews": wikipedia_pageviews.fetch_scores(names_list),
        "naver_datalab": naver_datalab.fetch_scores(names_list),
    }


# ---------------------------------------------------------------------------
# 배치 실행
# ---------------------------------------------------------------------------


def _candidate_politicians(conn: sqlite3.Connection) -> list[dict]:
    """랭킹 대상: 여성·청년·연대 카테고리 + 활성 정치인.

    FR-008/R-06: 주간 랭킹은 여성·청년 정치인 확장을 위한 장치.
    'fixed'(이재명·조국·정청래) 및 'blocked'는 제외.
    """
    rows = conn.execute(
        """
        SELECT id, name, tier, category
        FROM politicians
        WHERE is_active = 1
          AND tier != 'blocked'
          AND category IN ('female', 'youth', 'alliance')
        ORDER BY id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _prev_score_map(
    conn: sqlite3.Connection, prev_week_start: date
) -> dict[int, float]:
    rows = conn.execute(
        "SELECT politician_id, score FROM weekly_rankings WHERE week_start=?",
        (prev_week_start.isoformat(),),
    ).fetchall()
    return {r["politician_id"]: r["score"] for r in rows}


def _existed_last_week(conn: sqlite3.Connection, prev_week_start: date) -> set[int]:
    rows = conn.execute(
        "SELECT politician_id FROM weekly_rankings WHERE week_start=?",
        (prev_week_start.isoformat(),),
    ).fetchall()
    return {r["politician_id"] for r in rows}


def _stale_weeks_count(
    conn: sqlite3.Connection, politician_id: int, current_week_start: date
) -> int:
    """최근 N주 연속으로 'pending' 태그를 받았는지 확인.

    과거 주에 기록이 전혀 없으면 랭킹 첫 참가로 간주 → stale 누적 중단.
    """
    count = 0
    for i in range(RANKING_PENDING_WEEKS):
        wk = (current_week_start - timedelta(days=7 * i)).isoformat()
        row = conn.execute(
            "SELECT tag FROM weekly_rankings WHERE week_start=? AND politician_id=?",
            (wk, politician_id),
        ).fetchone()
        if row is None:
            break  # 과거 이력 없음 → 신규 / 아직 누적 없음
        if row["tag"] != "pending":
            break
        count += 1
    return count


def run_ranking_batch(
    conn: sqlite3.Connection,
    *,
    week_start: date | None = None,
    top_n: int = RANKING_TOP_N,
    dry_run: bool = False,
) -> dict:
    """주간 랭킹 배치 메인 진입점.

    Args:
        conn: SQLite connection (트랜잭션 미완료 상태여도 commit은 본 함수에서).
        week_start: 랭킹 주 시작 날짜(월요일). None이면 이번 주.
        top_n: 상위 몇 명까지 tier='auto' 전환할지.
        dry_run: True면 DB 변경 없이 결과만 계산·반환.

    Returns:
        {
            "week_start": "2026-04-13",
            "total_inserted": 5,
            "auto_updated": 3,
            "removed": 0,
            "dry_run": False,
        }
    """
    week_start = week_start or resolve_week_start()
    prev_week = week_start - timedelta(days=7)

    candidates = _candidate_politicians(conn)
    if not candidates:
        logger.info("no ranking candidates found")
        return {
            "week_start": week_start.isoformat(),
            "total_inserted": 0,
            "auto_updated": 0,
            "removed": 0,
            "dry_run": dry_run,
        }

    # 이름→id, id→row 맵
    id_by_name = {c["name"]: c["id"] for c in candidates}
    names = list(id_by_name.keys())

    # 1) 5개 소스 호출
    per_source = fetch_all_sources(conn, names)

    # 2) 정치인별 소스값을 [0, 100] 클램핑 + 가중합 → 점수 (0~100)
    #    - google_trends / naver_datalab은 이미 0~100 범위
    #    - naver_news / youtube_metrics / wikipedia_pageviews은 상한 초과 시 100으로 캡
    raw_by_id: dict[int, float] = {}
    sources_detail: dict[int, dict[str, float]] = {}
    for name in names:
        pid = id_by_name[name]
        per_src = {}
        for src in RANKING_SOURCE_WEIGHTS:
            val = float(per_source.get(src, {}).get(name, 0.0))
            per_src[src] = max(0.0, min(100.0, val))
        raw_by_id[pid] = round(combine_source_scores(per_src), 3)
        sources_detail[pid] = per_src

    # 3) 순위 매기기 (가중합 점수 기준)
    ranked = sorted(raw_by_id.items(), key=lambda kv: kv[1], reverse=True)

    prev_scores = _prev_score_map(conn, prev_week)
    prev_present = _existed_last_week(conn, prev_week)
    top_ids = {pid for pid, _ in ranked[:top_n]}

    inserted = 0
    auto_updated = 0
    removed = 0
    now = datetime.utcnow().isoformat()

    for rank, (pid, score) in enumerate(ranked, start=1):
        prev_score = prev_scores.get(pid)
        delta = 0.0 if prev_score is None else round(score - prev_score, 3)

        if prev_score is None and rank <= top_n:
            tag = "new"
        elif prev_score is not None and delta >= _RISING_DELTA_THRESHOLD and rank <= top_n:
            tag = "rising"
        elif rank > top_n:
            tag = "pending"
        else:
            tag = None

        if dry_run:
            inserted += 1
            continue

        conn.execute(
            """
            INSERT INTO weekly_rankings
              (week_start, politician_id, rank, score,
               delta_vs_prev_week, tag, data_sources)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, politician_id) DO UPDATE SET
                rank=excluded.rank,
                score=excluded.score,
                delta_vs_prev_week=excluded.delta_vs_prev_week,
                tag=excluded.tag,
                data_sources=excluded.data_sources
            """,
            (
                week_start.isoformat(),
                pid,
                rank,
                score,
                delta,
                tag,
                json.dumps(sources_detail.get(pid, {}), ensure_ascii=False),
            ),
        )
        inserted += 1

    if not dry_run:
        # 5) tier 재배치
        for pid in top_ids:
            cur = conn.execute(
                "SELECT tier FROM politicians WHERE id=?", (pid,)
            ).fetchone()
            if not cur:
                continue
            # pinned는 유지 (사용자 고정)
            if cur["tier"] in ("pinned", "blocked"):
                continue
            if cur["tier"] != "auto":
                conn.execute(
                    "UPDATE politicians SET tier='auto', updated_at=? WHERE id=?",
                    (now, pid),
                )
                auto_updated += 1
            # ranking_score 캐시
            conn.execute(
                "UPDATE politicians SET ranking_score=? WHERE id=?",
                (raw_by_id[pid], pid),
            )

        # 6) 탈락 처리: 이번 주 top_n 외 + 기존 auto → pending
        #    + 이전 주 pending이었으면 삭제 (2주 연속)
        out_ids = set(id_by_name.values()) - top_ids
        for pid in out_ids:
            cur = conn.execute(
                "SELECT tier FROM politicians WHERE id=?", (pid,)
            ).fetchone()
            if not cur:
                continue
            if cur["tier"] == "pinned":
                continue

            stale = _stale_weeks_count(conn, pid, week_start)
            if stale >= RANKING_PENDING_WEEKS and cur["tier"] != "pinned":
                # FK 참조 정리 후 정치인 삭제
                conn.execute(
                    "DELETE FROM weekly_rankings WHERE politician_id=?",
                    (pid,),
                )
                conn.execute("DELETE FROM politicians WHERE id=?", (pid,))
                removed += 1
            elif cur["tier"] == "auto":
                conn.execute(
                    "UPDATE politicians SET tier='pending', updated_at=? WHERE id=?",
                    (now, pid),
                )

        conn.commit()

    logger.info(
        "ranking_batch done: week=%s inserted=%d auto=%d removed=%d",
        week_start.isoformat(),
        inserted,
        auto_updated,
        removed,
    )
    return {
        "week_start": week_start.isoformat(),
        "total_inserted": inserted,
        "auto_updated": auto_updated,
        "removed": removed,
        "dry_run": dry_run,
    }
