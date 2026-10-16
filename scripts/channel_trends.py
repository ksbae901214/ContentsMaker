"""채널 추세 계측 (044) — 구독자 증감 · 기간별 추세 · 후속 제작 후보.

`analyze_channel_performance.py` 의 리포트가 쓰는 순수 함수 모음.
044 진단은 "전체 중앙값 하나"로는 하락 추세가 안 보였다는 데서 출발했다
(174편 누적 중앙값은 1,367 로 오히려 올랐는데 최근 2주 중앙값은 1,674 → 1,295).
누적값은 과거 편이 깔고 앉아 있어 최근 편성 변화를 가린다 — 그래서 창(window)으로 본다.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta

FOLLOWUP_WINDOW_DAYS = 7    # 039 증폭기: 박위·용혜인 후속은 모두 1주 안에 붙었다
FOLLOWUP_RATIO = 1.5        # 채널 중앙값 대비 — 1,300 기준 약 2,000회
PERIOD_WINDOW_DAYS = 14
PERIOD_COUNT = 4
MIN_AGE_DAYS = 3            # 갓 올린 편은 조회수 누적 중이라 추세 표에서 뺀다


def _parse_date(yyyymmdd: str) -> datetime:
    return datetime.strptime(yyyymmdd, "%Y%m%d")


def _median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def subscriber_change(prev_meta: dict, cur_subs: int | None,
                      cur_stamp: str) -> dict | None:
    """직전 스냅샷 대비 구독자 증감. 현재 값을 못 받았으면 None."""
    if cur_subs is None:
        return None
    prev_subs = prev_meta.get("subscribers")
    prev_stamp = prev_meta.get("collected_at")
    if prev_subs is None or not prev_stamp:
        return {"subscribers": cur_subs, "delta": None, "days": None,
                "per_day": None}
    days = (_parse_date(cur_stamp[:8]) - _parse_date(prev_stamp[:8])).days
    delta = cur_subs - prev_subs
    per_day = round(delta / days, 1) if days > 0 else None
    return {"subscribers": cur_subs, "delta": delta, "days": days,
            "per_day": per_day}


def period_comparison(entries: list[dict], today: str,
                      window_days: int = PERIOD_WINDOW_DAYS,
                      periods: int = PERIOD_COUNT, *, hit_views: int,
                      min_age_days: int = MIN_AGE_DAYS) -> list[dict]:
    """최근 `window_days` 일 창을 `periods` 개 거꾸로 쌓은 추세표 (최신 창 먼저).

    hit = `hit_views` 이상 편. 업로드일 없는 편(상세 미조회)은 제외한다.
    """
    dated = [e for e in entries
             if e.get("upload_date") and e.get("view_count") is not None]
    end = _parse_date(today) - timedelta(days=min_age_days)
    rows = []
    for i in range(periods):
        hi = end - timedelta(days=window_days * i)
        lo = hi - timedelta(days=window_days - 1)
        inside = [e for e in dated
                  if lo <= _parse_date(e["upload_date"]) <= hi]
        views = [e["view_count"] for e in inside]
        durs = [e["duration"] for e in inside if e.get("duration")]
        hits = sum(v >= hit_views for v in views)
        rows.append({
            "from": lo.strftime("%Y-%m-%d"),
            "to": hi.strftime("%Y-%m-%d"),
            "count": len(inside),
            "median_views": _median(views),
            "hits": hits,
            "hit_rate": round(hits / len(inside), 2) if inside else 0.0,
            "avg_duration": round(statistics.mean(durs)) if durs else None,
        })
    return rows


def followup_candidates(entries: list[dict], today: str, overall_median: int,
                        window_days: int = FOLLOWUP_WINDOW_DAYS,
                        ratio: float = FOLLOWUP_RATIO) -> list[dict]:
    """최근 `window_days` 일 안에 올린 편 중 채널 중앙값의 `ratio` 배 이상 (조회수 순)."""
    if overall_median <= 0:
        return []
    now = _parse_date(today)
    out = []
    for e in entries:
        if not e.get("upload_date") or e.get("view_count") is None:
            continue
        age = (now - _parse_date(e["upload_date"])).days
        r = e["view_count"] / overall_median
        if 0 <= age <= window_days and r >= ratio:
            out.append({"id": e.get("id", ""), "title": e.get("title", ""),
                        "view_count": e["view_count"],
                        "upload_date": e["upload_date"], "age_days": age,
                        "ratio": round(r, 1)})
    return sorted(out, key=lambda c: c["view_count"], reverse=True)


def trend_report_lines(subscribers: dict | None = None,
                       periods: list[dict] | None = None,
                       hit_views: int | None = None,
                       followups: list[dict] | None = None) -> list[str]:
    """리포트 상단에 붙는 044 섹션 (값이 없는 섹션은 생략)."""
    lines: list[str] = []
    if subscribers:
        line = f"구독자 {subscribers['subscribers']:,}명"
        if subscribers.get("delta") is not None:
            line += (f" (직전 스냅샷 대비 {subscribers['delta']:+,}명 / "
                     f"{subscribers['days']}일")
            if subscribers.get("per_day") is not None:
                line += f", 하루 {subscribers['per_day']}명"
            line += ")"
        lines += ["", line]
    if followups:
        lines += ["", "## 🔥 후속 제작 후보 (044 — 터진 편은 후속이 먼저다)", ""]
        lines.extend(
            f"- {c['view_count']:,}회 (중앙값의 {c['ratio']}배, 업로드 "
            f"{c['age_days']}일차) — {c['title']}" for c in followups)
    if periods:
        hit_label = f"{hit_views:,}회 이상" if hit_views else "hit"
        lines += ["", "## 기간별 추세 (044 — 최신 창 먼저, 갓 올린 편 제외)", "",
                  f"| 기간 | 편수 | 중앙값 | {hit_label} | 평균 길이 |",
                  "|---|---|---|---|---|"]
        for r in periods:
            dur = f"{r['avg_duration']}초" if r["avg_duration"] else "—"
            lines.append(
                f"| {r['from']} ~ {r['to']} | {r['count']} | "
                f"{r['median_views']:,} | {r['hits']} ({r['hit_rate'] * 100:.0f}%) "
                f"| {dur} |")
    return lines
