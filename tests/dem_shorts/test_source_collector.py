"""T026: NATV 영상 수집·세션 분류 테스트."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.dem_shorts.source_collector import (
    _exceeds_duration_limit,
    parse_session_type,
    parse_youtube_duration,
)


# ─────────────── parse_session_type (FR-003) ───────────────

class TestParseSessionType:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("제422회 국회 본회의 [영상]", "plenary"),
            ("본회의", "plenary"),
            ("법제사법위원회 전체회의", "committee"),
            ("상임위원회 회의", "committee"),
            ("2025 국정감사 - 기획재정위원회", "audit"),
            ("국감", "audit"),
            ("인사청문회 - 국무총리 후보자", "hearing"),
            ("청문회", "hearing"),
            ("당대표 기자회견", "press"),
            ("긴급 기자회견", "press"),
            ("기타 이벤트", "other"),
            ("", "other"),
        ],
    )
    def test_classify(self, text: str, expected: str):
        assert parse_session_type(text, "") == expected

    def test_description_fallback(self):
        """제목에 힌트 없으면 설명에서 찾음."""
        assert parse_session_type("알림", "본회의 중계") == "plenary"


# ─────────────── parse_youtube_duration ───────────────

class TestParseYoutubeDuration:
    @pytest.mark.parametrize(
        "iso,expected_sec",
        [
            ("PT1H30M", 5400),
            ("PT45M30S", 2730),
            ("PT30S", 30),
            ("PT2H", 7200),
            ("PT0S", 0),
        ],
    )
    def test_iso8601_parse(self, iso: str, expected_sec: int):
        assert parse_youtube_duration(iso) == expected_sec

    def test_invalid_returns_zero(self):
        assert parse_youtube_duration("invalid") == 0


# ─────────────── Duration limit (FR-002) ───────────────

class TestDurationLimit:
    def test_under_6h_accepted(self):
        assert _exceeds_duration_limit(6 * 3600 - 1) is False

    def test_exactly_6h_accepted(self):
        assert _exceeds_duration_limit(6 * 3600) is False

    def test_over_6h_rejected(self):
        assert _exceeds_duration_limit(6 * 3600 + 1) is True
