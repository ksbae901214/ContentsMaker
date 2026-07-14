"""채널 성과 분석 CLI (scripts/analyze_channel_performance.py) 순수 로직 테스트."""
from __future__ import annotations

from scripts.analyze_channel_performance import (
    classify_title, compare_snapshots, duration_bucket, summarize, upload_gaps,
)


class TestClassifyTitle:
    def test_question_is_hook(self):
        assert classify_title("이름표만 바꾸면 살아날까?") == "hook"

    def test_marker_word_is_hook(self):
        assert classify_title("조국을 참교육한 이준석") == "hook"

    def test_quote_is_hook(self):
        assert classify_title('나경원 "검열사회" 직격') == "hook"

    def test_report_suffix(self):
        assert classify_title("민주당 추천권 배제 및 특검팀 규모와 기간 설명") == "report"

    def test_neutral(self):
        assert classify_title("안규백 국방장관 후보자 청문회") == "neutral"

    def test_empty(self):
        assert classify_title("") == "neutral"


class TestDurationBucket:
    def test_buckets(self):
        assert duration_bucket(None) == "unknown"
        assert duration_bucket(0) == "unknown"
        assert duration_bucket(25) == "<30s"
        assert duration_bucket(30) == "30-45s"
        assert duration_bucket(44.9) == "30-45s"
        assert duration_bucket(45) == "45-60s"
        assert duration_bucket(60) == "45-60s"
        assert duration_bucket(61) == "60s+"


def _entry(vid, title, views, dur=35):
    return {"id": vid, "title": title, "view_count": views, "duration": dur}


class TestSummarize:
    def test_median_and_groups(self):
        entries = [
            _entry("a", "조국을 참교육한 이준석", 1000, 25),
            _entry("b", "특검팀 규모와 기간 설명", 100, 50),
            _entry("c", "그냥 제목", 400, 35),
        ]
        s = summarize(entries)
        assert s["count"] == 3
        assert s["median_views"] == 400
        assert s["by_title_type"]["hook"]["median_views"] == 1000
        assert s["by_title_type"]["report"]["median_views"] == 100
        assert s["by_duration"]["<30s"]["count"] == 1

    def test_none_views_filtered(self):
        entries = [_entry("a", "t", 100), {"id": "b", "title": "x", "view_count": None}]
        assert summarize(entries)["count"] == 1

    def test_top_bottom_order(self):
        entries = [_entry(str(i), f"t{i}", i * 100) for i in range(1, 8)]
        s = summarize(entries)
        assert s["top5"][0]["view_count"] == 700
        assert s["bottom5"][0]["view_count"] == 100


class TestUploadGaps:
    def test_detects_long_gap(self):
        gaps = upload_gaps(["20260615", "20260616", "20260618", "20260629"])
        assert len(gaps) == 1
        assert gaps[0]["gap_days"] == 11
        assert gaps[0]["from"] == "2026-06-18"

    def test_no_gap_within_threshold(self):
        assert upload_gaps(["20260615", "20260617"]) == []

    def test_empty_and_blank_dates(self):
        assert upload_gaps([]) == []
        assert upload_gaps(["", ""]) == []


class TestCompareSnapshots:
    def test_delta_and_new_flag(self):
        prev = [_entry("a", "t", 100)]
        cur = [_entry("a", "t", 350), _entry("b", "신규", 200)]
        deltas = compare_snapshots(prev, cur)
        assert deltas[0] == {"id": "a", "title": "t", "view_count": 350,
                             "delta": 250, "new": False}
        assert deltas[1]["new"] is True

    def test_zero_delta_excluded(self):
        prev = [_entry("a", "t", 100)]
        assert compare_snapshots(prev, [_entry("a", "t", 100)]) == []
