"""Tests for clip_selector module."""
import pytest

from src.analyzer.clip_selector import select_best_clip


def _seg(start, end, text):
    return {"start": start, "end": end, "text": text}


class TestSelectBestClip:
    def test_empty_transcript_returns_default(self):
        start, end = select_best_clip([])
        assert start == 0.0
        assert end == 55.0  # default max_duration

    def test_short_transcript_returns_full_range(self):
        transcript = [_seg(0, 10, "짧은 발언"), _seg(10, 20, "끝")]
        start, end = select_best_clip(transcript, max_duration=55.0)
        assert start == 0.0
        assert end == 20.0

    def test_long_transcript_returns_within_max_duration(self):
        transcript = [_seg(i, i + 1, "일반 발언") for i in range(120)]
        start, end = select_best_clip(transcript, max_duration=55.0)
        assert end - start <= 55.0 + 1  # at most max_duration (+ last segment rounding)

    def test_high_impact_keywords_preferred(self):
        # First 30s: boring
        boring = [_seg(i, i + 1, "설명 언급") for i in range(30)]
        # 30-60s: impactful
        impact = [_seg(30 + i, 31 + i, "충격 폭로 망언 비판") for i in range(30)]
        # 60-100s: boring
        boring2 = [_seg(60 + i, 61 + i, "토론 답변") for i in range(40)]
        transcript = boring + impact + boring2

        start, end = select_best_clip(transcript, max_duration=40.0)
        # Should prefer the impactful window starting around 30
        assert start >= 20.0  # somewhere near the impact zone

    def test_custom_max_duration(self):
        transcript = [_seg(i, i + 1, "발언") for i in range(100)]
        start, end = select_best_clip(transcript, max_duration=30.0)
        assert end - start <= 30.0 + 1

    def test_result_within_transcript_bounds(self):
        transcript = [_seg(5.0, 10.0, "발언"), _seg(10.0, 15.0, "끝")]
        start, end = select_best_clip(transcript, max_duration=55.0)
        assert start >= 5.0
        assert end <= 15.0
