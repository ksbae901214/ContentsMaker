"""Phase 1 TDD: SEED_POLITICIANS_DEM/PPP 분리 및 Politician.affiliation_perspective 라운드트립.

Spec: specs/007-dem-shorts-studio/spec.md (v2) §FR-006
Plan: prompt_plan.md §010 PPP perspective H2 Axis
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.dem_shorts.models.politician import (
    SEED_POLITICIANS,
    Politician,
)


class TestPerspectiveSeedConstants:
    def test_dem_seeds_defined(self):
        from src.dem_shorts.models.politician import SEED_POLITICIANS_DEM
        names = {s["name"] for s in SEED_POLITICIANS_DEM}
        assert names == {"이재명", "조국", "정청래"}, \
            f"dem 시드는 3명(이재명/조국/정청래)이어야 함: {names}"
        for seed in SEED_POLITICIANS_DEM:
            assert seed.get("affiliation_perspective") == "dem", \
                f"{seed['name']}의 affiliation_perspective가 'dem'이 아님"

    def test_ppp_seeds_defined(self):
        from src.dem_shorts.models.politician import SEED_POLITICIANS_PPP
        names = {s["name"] for s in SEED_POLITICIANS_PPP}
        expected = {"한동훈", "김기현", "권성동", "추경호", "나경원", "오세훈"}
        assert names == expected, f"ppp 시드는 6명이어야 함: {names}"
        for seed in SEED_POLITICIANS_PPP:
            assert seed.get("affiliation_perspective") == "ppp", \
                f"{seed['name']}의 affiliation_perspective가 'ppp'가 아님"

    def test_legacy_seed_politicians_is_dem_alias(self):
        """SEED_POLITICIANS는 하위호환 별칭으로 dem 시드와 동일해야 함."""
        from src.dem_shorts.models.politician import SEED_POLITICIANS_DEM
        assert SEED_POLITICIANS == SEED_POLITICIANS_DEM, \
            "SEED_POLITICIANS는 SEED_POLITICIANS_DEM의 별칭이어야 함 (하위호환)"

    def test_ppp_seeds_have_required_fields(self):
        from src.dem_shorts.models.politician import SEED_POLITICIANS_PPP
        required = {"name", "party", "tier", "category", "affiliation_perspective"}
        for seed in SEED_POLITICIANS_PPP:
            missing = required - set(seed.keys())
            assert not missing, f"{seed.get('name','?')} 필수 필드 누락: {missing}"
            assert seed["party"] == "국민의힘", \
                f"{seed['name']} party는 '국민의힘'이어야 함: {seed['party']}"
            assert seed["tier"] == "pinned"


class TestPoliticianDataclassPerspective:
    """Politician frozen dataclass에 affiliation_perspective 필드 추가."""

    def _make(self, perspective: str = "dem") -> Politician:
        now = datetime(2026, 4, 20, 0, 0, 0)
        return Politician(
            id=1,
            name="테스트",
            party="더불어민주당",
            role="당대표",
            photo_url=None,
            bio="bio",
            tone_guide="tone",
            tier="pinned",
            category="fixed",
            is_active=True,
            ranking_score=None,
            added_at=now,
            updated_at=now,
            affiliation_perspective=perspective,
        )

    def test_field_accepts_dem(self):
        p = self._make("dem")
        assert p.affiliation_perspective == "dem"

    def test_field_accepts_ppp(self):
        p = self._make("ppp")
        assert p.affiliation_perspective == "ppp"

    def test_invalid_perspective_rejected(self):
        with pytest.raises(ValueError, match="perspective"):
            self._make("invalid")

    def test_to_dict_includes_perspective(self):
        p = self._make("ppp")
        d = p.to_dict()
        assert d["affiliation_perspective"] == "ppp"

    def test_from_dict_roundtrip(self):
        original = self._make("ppp")
        d = original.to_dict()
        restored = Politician.from_dict(d)
        assert restored.affiliation_perspective == "ppp"
        assert restored == original

    def test_from_dict_defaults_to_dem_for_legacy(self):
        """기존 DB row에 affiliation_perspective가 없으면 dem으로 기본값."""
        legacy = {
            "id": 1,
            "name": "이재명",
            "party": "더불어민주당",
            "role": "당대표",
            "bio": "",
            "tone_guide": "",
            "tier": "pinned",
            "category": "fixed",
            "is_active": True,
            "added_at": "2026-04-20T00:00:00",
            "updated_at": "2026-04-20T00:00:00",
        }
        p = Politician.from_dict(legacy)
        assert p.affiliation_perspective == "dem"
