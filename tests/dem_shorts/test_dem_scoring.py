"""T027: 민주당 점유도 점수 (FR-004, R-05) 테스트."""
from __future__ import annotations

import pytest

from src.dem_shorts.scoring import (
    DemScoreInputs,
    calculate_dem_score,
)


def _inputs(**kwargs) -> DemScoreInputs:
    """2026-04-20: perspective='dem' 명시 → 기존 dem 시드(이재명·조국·정청래) 기준 테스트.

    DEFAULT_PERSPECTIVE가 ppp로 바뀌어도 dem 로직은 여전히 유효함을 증명한다.
    """
    base = dict(
        dem_person_count=0,
        has_top_whitelist=False,
        top3_present={"이재명": False, "조국": False, "정청래": False},
        female_or_youth_present=False,
        issue_keyword_matches=0,
        duration_sec=3600,
        recent_repeat_count=0,
        perspective="dem",
    )
    base.update(kwargs)
    return DemScoreInputs(**base)


class TestCalculateDemScore:
    def test_all_zero_inputs_returns_zero(self):
        assert calculate_dem_score(_inputs()) == 0.0

    def test_per_person_capped_at_40(self):
        """민주당 10명 → 100점이 아니라 40점 상한."""
        s = calculate_dem_score(_inputs(dem_person_count=10))
        assert s == 40.0

    def test_three_dem_people(self):
        """3명 × 10 = 30점."""
        assert calculate_dem_score(_inputs(dem_person_count=3)) == 30.0

    def test_top_whitelist_bonus(self):
        """상위 Whitelist 인물 포함 → +20점."""
        assert (
            calculate_dem_score(
                _inputs(dem_person_count=1, has_top_whitelist=True)
            )
            == 10 + 20
        )

    def test_single_top3_bonus(self):
        """이재명 등장 시 +15점."""
        s = calculate_dem_score(
            _inputs(
                dem_person_count=1,
                top3_present={"이재명": True, "조국": False, "정청래": False},
            )
        )
        assert s == 10 + 15

    def test_all_top3_capped_at_30(self):
        """3명 모두 등장해도 상한 30점."""
        s = calculate_dem_score(
            _inputs(
                dem_person_count=3,
                top3_present={"이재명": True, "조국": True, "정청래": True},
            )
        )
        # 30(per_person) + 30(top3 cap) = 60
        assert s == 60.0

    def test_female_or_youth_bonus(self):
        s = calculate_dem_score(
            _inputs(dem_person_count=1, female_or_youth_present=True)
        )
        assert s == 10 + 10

    def test_issue_keyword_capped_at_20(self):
        """이슈 키워드 5개 매칭 시 5×5=25가 아니라 20점 상한."""
        s = calculate_dem_score(
            _inputs(dem_person_count=1, issue_keyword_matches=5)
        )
        assert s == 10 + 20

    def test_over_6h_penalty(self):
        s = calculate_dem_score(
            _inputs(dem_person_count=2, duration_sec=7 * 3600)
        )
        assert s == 20 - 10

    def test_repeat_penalty_up_to_30(self):
        s = calculate_dem_score(
            _inputs(dem_person_count=4, recent_repeat_count=10)
        )
        # 40(max) - 30(cap) = 10
        assert s == 40 - 30

    def test_clamped_to_0_100(self):
        """감점이 많아도 0 미만 반환 안 됨."""
        s = calculate_dem_score(
            _inputs(dem_person_count=0, duration_sec=7 * 3600, recent_repeat_count=10)
        )
        assert s == 0.0

    def test_clamped_upper_100(self):
        """전체 합산도 100점을 초과하지 않음."""
        s = calculate_dem_score(
            _inputs(
                dem_person_count=10,
                has_top_whitelist=True,
                top3_present={"이재명": True, "조국": True, "정청래": True},
                female_or_youth_present=True,
                issue_keyword_matches=10,
            )
        )
        # 40 + 20 + 30 + 10 + 20 = 120 → 100 clamp
        assert s == 100.0
