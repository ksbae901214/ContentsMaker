"""T044: 쇼츠 추천 점수 공식 (FR-016) 테스트."""
from __future__ import annotations

from src.dem_shorts.scoring import RecommendationInputs, calculate_recommendation_score


def _inputs(**overrides) -> RecommendationInputs:
    base = dict(
        is_top_whitelist=False,
        duration_sec=30.0,
        emotion_strength=0.0,
        issue_keyword_count=0,
        is_solo=False,
        has_profanity=False,
    )
    base.update(overrides)
    return RecommendationInputs(**base)


class TestRecommendationScore:
    def test_zero_inputs(self):
        """모든 입력이 기본값이어도 duration이 적정 범위이므로 최소 40점."""
        s = calculate_recommendation_score(_inputs())
        assert s == 40.0  # duration 30s → 만점

    def test_top_whitelist_bonus(self):
        s = calculate_recommendation_score(_inputs(is_top_whitelist=True))
        assert s == 40 + 20

    def test_duration_too_short(self):
        """30초 미만은 감점."""
        s = calculate_recommendation_score(_inputs(duration_sec=10.0))
        assert s < 40

    def test_duration_too_long(self):
        """90초 초과는 감점."""
        s = calculate_recommendation_score(_inputs(duration_sec=120.0))
        assert s < 40

    def test_duration_in_ideal_range(self):
        for d in (30.0, 60.0, 90.0):
            s = calculate_recommendation_score(_inputs(duration_sec=d))
            assert s == 40.0

    def test_emotion_strength(self):
        s = calculate_recommendation_score(_inputs(emotion_strength=1.0))
        # 40 + 30 = 70
        assert s == 70.0

    def test_issue_keywords(self):
        """키워드 당 +5점."""
        s = calculate_recommendation_score(_inputs(issue_keyword_count=3))
        assert s == 40 + 15

    def test_solo_bonus(self):
        s = calculate_recommendation_score(_inputs(is_solo=True))
        assert s == 40 + 10

    def test_profanity_heavy_penalty(self):
        """욕설 감지 시 -50점."""
        s = calculate_recommendation_score(_inputs(is_top_whitelist=True, has_profanity=True))
        # 40 + 20 - 50 = 10
        assert s == 10.0

    def test_clamped_to_zero(self):
        s = calculate_recommendation_score(
            _inputs(duration_sec=5.0, has_profanity=True)
        )
        assert s >= 0
