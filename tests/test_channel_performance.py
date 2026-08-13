"""채널 성과 분석 CLI (scripts/analyze_channel_performance.py) 순수 로직 테스트."""
from __future__ import annotations

from scripts.analyze_channel_performance import (
    build_report_md, category_mix_warnings, classify_title, compare_snapshots,
    duration_bucket, summarize, upload_gaps,
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


# ── 034: 보도체 시그널 확장 + 해시태그 추적 ─────────────────────────
class TestClassifyTitle034:
    def test_report_verb_ending(self):
        assert classify_title(
            "윤석열 397억은 1심인데 434억 이재명은 재판조차 안 한다") == "report"

    def test_report_word(self):
        assert classify_title("신현송 한은총재 후보 국적상실 신고 논란") == "report"

    def test_hashtags_stripped_before_classification(self):
        # 해시태그를 벗기면 '~외쳤다' 보도체 — hook 오분류 방지
        assert classify_title(
            "선관위 해체 여야가 같이 외쳤다 #장동혁 #선관위 #선관위해체") == "report"

    def test_question_still_hook_even_with_hashtags(self):
        assert classify_title(
            "부산에서 박근혜가 뒤집을 수 있을까?? #박근혜 #한동훈") == "hook"


class TestHashtagCount:
    def test_counts_hashtags(self):
        from scripts.analyze_channel_performance import hashtag_count
        assert hashtag_count("제목 #a #b #c") == 3

    def test_zero_when_none(self):
        from scripts.analyze_channel_performance import hashtag_count
        assert hashtag_count("해시태그 없는 제목") == 0


class TestSummarizeHashtagBucket:
    def test_by_hashtag_bucket(self):
        entries = [
            _entry("a", "깔끔한 제목 #하나", 1000),
            _entry("b", "스팸 제목 #a #b #c #d #e", 100),
            _entry("c", "태그 없는 제목", 3000),
        ]
        s = summarize(entries)
        assert s["by_hashtag"]["0-3"]["count"] == 2
        assert s["by_hashtag"]["4+"]["count"] == 1
        assert s["by_hashtag"]["4+"]["median_views"] == 100


class TestNfcNormalization:
    def test_nfd_title_classified_as_report(self):
        # yt-dlp가 반환하는 제목은 NFD(자모 분해형)일 수 있음 — 034 실측 버그
        import unicodedata
        t = unicodedata.normalize(
            "NFD", "윤석열 397억은 1심인데 재판조차 안 한다 #정점식")
        assert classify_title(t) == "report"


# ── 036 Phase 0: 카테고리 축 계측 ──────────────────────────────────
class TestSummarizeByCategory:
    def test_groups_by_inferred_category(self):
        entries = [
            _entry("a", "끝내 부결된 특검법", 1000),
            _entry("b", "결국 동결된 금리", 3000),
            _entry("c", "본회의 표결 뒤집혔다", 500),
        ]
        s = summarize(entries)
        assert s["by_category"]["political"]["count"] == 2
        assert s["by_category"]["political"]["median_views"] == 750
        assert s["by_category"]["economic"]["median_views"] == 3000

    def test_ledger_overrides_inference(self):
        entries = [_entry("a", "끝내 부결된 특검법", 1000)]
        s = summarize(entries, ledger={"끝내 부결된 특검법": "economic"})
        assert "political" not in s["by_category"]
        assert s["by_category"]["economic"]["count"] == 1

    def test_unclassifiable_goes_to_unknown(self):
        s = summarize([_entry("a", "그냥 아무 말", 100)])
        assert s["by_category"]["unknown"]["count"] == 1

    def test_backward_compatible_without_ledger(self):
        # 기존 호출부(인자 1개)가 그대로 동작해야 한다
        s = summarize([_entry("a", "국회 표결", 100)])
        assert s["count"] == 1


class TestCategoryMixWarnings:
    def test_flags_diluting_category(self):
        by_category = {
            "political": {"count": 20, "median_views": 1200},
            "entertainment": {"count": 5, "median_views": 400},
        }
        warnings = category_mix_warnings(by_category, overall_median=1100)
        assert any("entertainment" in w and "희석" in w for w in warnings)
        assert not any("political" in w for w in warnings)

    def test_flags_breakout_category(self):
        by_category = {
            "political": {"count": 20, "median_views": 1100},
            "economic": {"count": 6, "median_views": 3000},
        }
        warnings = category_mix_warnings(by_category, overall_median=1200)
        assert any("economic" in w and "확대" in w for w in warnings)

    def test_ignores_small_samples(self):
        by_category = {"entertainment": {"count": 2, "median_views": 10}}
        assert category_mix_warnings(by_category, overall_median=1100) == []

    def test_ignores_unknown_bucket(self):
        by_category = {"unknown": {"count": 50, "median_views": 10}}
        assert category_mix_warnings(by_category, overall_median=1100) == []

    def test_no_warning_when_median_zero(self):
        by_category = {"economic": {"count": 5, "median_views": 3000}}
        assert category_mix_warnings(by_category, overall_median=0) == []


class TestReportIncludesCategory:
    def test_category_section_rendered(self):
        entries = [
            _entry("a", "끝내 부결된 특검법", 1000),
            _entry("b", "결국 동결된 금리", 3000),
        ]
        md = build_report_md("UC123", summarize(entries), [], [], "2026-08-13 10:00")
        assert "## 카테고리별" in md
        assert "economic" in md
