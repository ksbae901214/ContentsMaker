"""044 채널 방향 재조정 — 분석 도구 보수 (원제 복원·구독자·기간 비교·후속 알림)."""
from __future__ import annotations

from scripts.analyze_channel_performance import (
    apply_detail, build_report_md, carry_details, needs_detail, summarize,
)
from scripts.channel_trends import (
    followup_candidates, period_comparison, subscriber_change,
)


def _e(vid, title, views, date=None, dur=None, src=None):
    e = {"id": vid, "title": title, "view_count": views,
         "upload_date": date, "duration": dur}
    if src:
        e["title_source"] = src
    return e


class TestApplyDetail:
    """flat-playlist 는 YouTube 자동 번역 제목을 준다 — 개별 조회 원제로 덮는다."""

    def test_overwrites_translated_title_with_original(self):
        flat = _e("a", "President at the golf course", 100)
        out = apply_detail(flat, {"title": "38명 다친 날 골프장에 있던 대통령",
                                  "upload_date": "20261012", "duration": 51,
                                  "view_count": 424})
        assert out["title"] == "38명 다친 날 골프장에 있던 대통령"
        assert out["title_flat"] == "President at the golf course"
        assert out["title_source"] == "detail"
        assert out["upload_date"] == "20261012"
        assert out["view_count"] == 424

    def test_does_not_mutate_input(self):
        flat = _e("a", "translated", 100)
        apply_detail(flat, {"title": "원제"})
        assert flat["title"] == "translated"
        assert "title_source" not in flat

    def test_keeps_flat_values_when_detail_missing_fields(self):
        flat = _e("a", "원제", 100, "20261001", 40)
        out = apply_detail(flat, {})
        assert out["title"] == "원제"
        assert out["upload_date"] == "20261001"
        assert out["view_count"] == 100


class TestCarryDetails:
    """한 번 개별 조회한 편은 다음 회차부터 재조회 없이 원제·날짜를 이어받는다."""

    def test_carries_original_title_and_dates_but_keeps_fresh_views(self):
        prev = [_e("a", "원제", 100, "20260901", 41, src="detail")]
        cur = [_e("a", "Translated", 900)]
        out = carry_details(cur, prev)
        assert out[0]["title"] == "원제"
        assert out[0]["upload_date"] == "20260901"
        assert out[0]["duration"] == 41
        assert out[0]["view_count"] == 900
        assert out[0]["title_source"] == "detail"

    def test_ignores_prev_entries_without_detail_source(self):
        prev = [_e("a", "Old translated", 100)]
        out = carry_details([_e("a", "Translated", 900)], prev)
        assert out[0]["title"] == "Translated"
        assert "title_source" not in out[0]

    def test_does_not_mutate_input(self):
        cur = [_e("a", "Translated", 900)]
        carry_details(cur, [_e("a", "원제", 1, src="detail")])
        assert cur[0]["title"] == "Translated"


class TestNeedsDetail:
    def test_recent_window_always_refetched(self):
        assert needs_detail(0, _e("a", "t", 1, src="detail"), n=5) is True

    def test_older_entry_without_original_title_is_fetched(self):
        assert needs_detail(50, _e("a", "t", 1), n=5) is True

    def test_older_entry_with_original_title_is_skipped(self):
        assert needs_detail(50, _e("a", "t", 1, src="detail"), n=5) is False


class TestSubscriberChange:
    def test_delta_and_per_day(self):
        prev = {"subscribers": 515, "collected_at": "20260904_105716"}
        out = subscriber_change(prev, 659, "20261012_140646")
        assert out == {"subscribers": 659, "delta": 144, "days": 38,
                       "per_day": 3.8}

    def test_no_previous_count(self):
        out = subscriber_change({"collected_at": "20260904_105716"}, 659,
                                "20261012_140646")
        assert out == {"subscribers": 659, "delta": None, "days": None,
                       "per_day": None}

    def test_unknown_current_count(self):
        assert subscriber_change({}, None, "20261012_140646") is None


class TestPeriodComparison:
    """최근 N일 창을 거꾸로 쌓아 추세를 본다. 갓 올린 편(조회수 누적 중)은 뺀다."""

    ENTRIES = [
        _e("n1", "a", 5000, "20261011", 50),   # 3일 미만 → 제외
        _e("p1", "a", 1000, "20261005", 50),
        _e("p2", "a", 3000, "20260930", 60),
        _e("q1", "a", 2000, "20260925", 40),
        _e("q2", "a", 4000, "20260920", 40),
        _e("x", "a", 9999, None, None),        # 날짜 없음 → 제외
    ]

    def test_windows_newest_first(self):
        rows = period_comparison(self.ENTRIES, "20261012", window_days=10,
                                 periods=2, hit_views=2500, min_age_days=3)
        assert [r["from"] for r in rows] == ["2026-09-30", "2026-09-20"]
        assert [r["to"] for r in rows] == ["2026-10-09", "2026-09-29"]

    def test_window_stats(self):
        rows = period_comparison(self.ENTRIES, "20261012", window_days=10,
                                 periods=2, hit_views=2500, min_age_days=3)
        assert rows[0] == {"from": "2026-09-30", "to": "2026-10-09", "count": 2,
                           "median_views": 2000, "hits": 1, "hit_rate": 0.5,
                           "avg_duration": 55}
        assert rows[1]["count"] == 2
        assert rows[1]["hits"] == 1

    def test_empty_window(self):
        rows = period_comparison([], "20261012", window_days=7, periods=1,
                                 hit_views=100)
        assert rows[0]["count"] == 0
        assert rows[0]["median_views"] == 0
        assert rows[0]["hit_rate"] == 0.0
        assert rows[0]["avg_duration"] is None


class TestFollowupCandidates:
    """044: 터진 편은 후속이 먼저다(039 증폭기) — 리포트가 먼저 알린다."""

    def test_recent_breakout_flagged(self):
        entries = [_e("a", "박위", 4000, "20261010"),
                   _e("b", "평범", 1300, "20261010"),
                   _e("c", "오래된 대박", 9000, "20260901")]
        out = followup_candidates(entries, "20261012", overall_median=1300,
                                  window_days=7, ratio=1.5)
        assert [c["id"] for c in out] == ["a"]
        assert out[0]["age_days"] == 2
        assert out[0]["ratio"] == 3.1

    def test_sorted_by_views(self):
        entries = [_e("a", "x", 2000, "20261010"), _e("b", "y", 5000, "20261011")]
        out = followup_candidates(entries, "20261012", overall_median=1000)
        assert [c["id"] for c in out] == ["b", "a"]

    def test_zero_median_returns_empty(self):
        assert followup_candidates([_e("a", "x", 10, "20261011")], "20261012",
                                   overall_median=0) == []


class TestReport044Sections:
    SUMMARY = summarize([_e("a", "t", 1000)])

    def test_subscriber_line(self):
        md = build_report_md("ch", self.SUMMARY, [], [], "now",
                             subscribers={"subscribers": 659, "delta": 144,
                                          "days": 38, "per_day": 3.8})
        assert "구독자 659명" in md
        assert "+144명 / 38일" in md

    def test_period_table(self):
        rows = [{"from": "2026-09-30", "to": "2026-10-09", "count": 2,
                 "median_views": 2000, "hits": 1, "hit_rate": 0.5,
                 "avg_duration": 55}]
        md = build_report_md("ch", self.SUMMARY, [], [], "now", periods=rows,
                             hit_views=2050)
        assert "## 기간별 추세" in md
        assert "| 2026-09-30 ~ 2026-10-09 | 2 | 2,000 | 1 (50%) | 55초 |" in md
        assert "2,050회" in md

    def test_followup_section(self):
        cands = [{"id": "a", "title": "박위", "view_count": 4000,
                  "upload_date": "20261010", "age_days": 2, "ratio": 3.1}]
        md = build_report_md("ch", self.SUMMARY, [], [], "now", followups=cands)
        assert "후속 제작 후보" in md
        assert "박위" in md

    def test_sections_absent_by_default(self):
        md = build_report_md("ch", self.SUMMARY, [], [], "now")
        assert "기간별 추세" not in md
        assert "후속 제작 후보" not in md
        assert "구독자" not in md
