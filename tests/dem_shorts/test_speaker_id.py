"""T043: 발언자 호명 패턴 정규식 + Whitelist 매칭 + confidence 필터 (FR-013, FR-014)."""
from __future__ import annotations

import pytest

from src.dem_shorts.speaker_id.name_patterns import (
    NAME_ROLE_RE,
    extract_named_speakers,
    match_whitelist,
)


class TestNameRolePattern:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("정청래 의원님 발언하시죠", [("정청래", "의원")]),
            ("이재명 대표의 발언을 들었습니다", [("이재명", "대표")]),
            ("조국 대표님, 한지아 의원님 두 분 말씀을", [("조국", "대표"), ("한지아", "의원")]),
            ("박주민 위원장이 정회를 선포", [("박주민", "위원장")]),
            ("법무부 장관", [("법무부", "장관")]),
            ("안녕하세요 반갑습니다", []),
        ],
    )
    def test_extracts_name_role(self, text: str, expected: list):
        matches = [(m.group("name"), m.group("role")) for m in NAME_ROLE_RE.finditer(text)]
        assert matches == expected


class TestExtractNamedSpeakers:
    def test_deduplicates_by_name(self):
        text = "이재명 대표, 이재명 대표님 다시 발언"
        result = extract_named_speakers(text)
        assert result == {"이재명"}

    def test_ignores_two_char_common_noun(self):
        """2글자 이하 한글 + 역할명은 노이즈가 많으므로 3글자 이상만 확정."""
        text = "그 분 의원님께서는"
        # "그 분" 은 2글자이므로 추출되면 안 됨
        assert extract_named_speakers(text) == set()


class TestMatchWhitelist:
    def test_matches_active_pinned(self):
        whitelist = [
            {"id": 1, "name": "이재명", "tier": "pinned", "is_active": True},
            {"id": 2, "name": "정청래", "tier": "pinned", "is_active": True},
        ]
        result = match_whitelist({"이재명", "한지아"}, whitelist)
        assert result == {"이재명": 1}

    def test_excludes_inactive(self):
        whitelist = [
            {"id": 1, "name": "이재명", "tier": "pinned", "is_active": False},
        ]
        assert match_whitelist({"이재명"}, whitelist) == {}

    def test_excludes_blocked(self):
        whitelist = [
            {"id": 1, "name": "이재명", "tier": "blocked", "is_active": True},
        ]
        assert match_whitelist({"이재명"}, whitelist) == {}


class TestConfidenceThreshold:
    """FR-014: confidence <0.7 → (미식별)."""

    def test_below_threshold_unidentified(self):
        from src.dem_shorts.config import SPEAKER_CONFIDENCE_MIN

        def is_confirmed(confidence: float) -> bool:
            return confidence >= SPEAKER_CONFIDENCE_MIN

        assert is_confirmed(0.69) is False
        assert is_confirmed(0.70) is True
        assert is_confirmed(0.85) is True
