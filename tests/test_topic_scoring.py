"""044 소재 추천기 — 순수 점수 로직 (scripts/topic_scoring.py)."""
from __future__ import annotations

import pytest

from scripts.topic_scoring import (
    HIT_RATE, Article, cluster_articles, recommend, score_topic, title_tokens,
)


def _a(title, comments, aid="1"):
    return Article(title=title, demand=comments, url=f"https://n/{aid}")


class TestTitleTokens:
    def test_strips_particles_brackets_and_short_words(self):
        toks = title_tokens("[단독] 박위는 강연을 취소했다…\"죄송\"")
        assert "박위" in toks
        assert "강연" in toks
        assert "단독" not in toks

    def test_splits_middle_dot_names(self):
        toks = title_tokens("김민석·한동훈 '자녀 파묘 전쟁'")
        assert {"김민석", "한동훈", "자녀", "파묘", "전쟁"} <= toks

    def test_single_hanja_dropped(self):
        assert "靑" not in title_tokens("靑 대구 사고 보고받았다")


class TestClusterArticles:
    def test_same_issue_merged_and_demand_summed(self):
        arts = [_a("박위 강연 줄줄이 취소", 900, "1"),
                _a("박위 강연 취소에 위라클 침묵", 300, "2"),
                _a("금리 또 동결 서민 대출 부담", 500, "3")]
        clusters = cluster_articles(arts)
        assert len(clusters) == 2
        top = clusters[0]
        assert top.label == "박위 강연 줄줄이 취소"
        assert top.demand == 1200
        assert len(top.articles) == 2

    def test_single_shared_word_does_not_merge(self):
        arts = [_a("대통령 골프장 논란", 900, "1"),
                _a("대통령 유엔 연설 전문", 300, "2")]
        assert len(cluster_articles(arts)) == 2

    def test_sorted_by_demand(self):
        arts = [_a("가나 다라 마바", 10, "1"), _a("사아 자차 카타", 99, "2")]
        assert [c.demand for c in cluster_articles(arts)] == [99, 10]


class TestScoreTopic:
    def test_tier_hit_rate_scales_sqrt_demand(self):
        assert score_topic(1600, "A") == pytest.approx(40 * HIT_RATE["A"])
        assert score_topic(1600, "C") == pytest.approx(40 * HIT_RATE["C"])

    def test_hot_politician_spat_does_not_beat_civilian_cost(self):
        """2026-10-12 실측: 댓글 37,700 골프 공방(C) vs 3,517 단체관람 취소(A).
        정치 소재는 뜨거워도 채널에선 1,300 밴드다(039 '인지도는 변수 아님')."""
        assert score_topic(3_517, "A") > score_topic(37_700, "C")

    def test_dead_is_zero(self):
        assert score_topic(10_000, "DEAD") == 0

    def test_money_and_followup_boosts(self):
        base = score_topic(1000, "B")
        assert score_topic(1000, "B", money=True) == pytest.approx(base * 1.5)
        assert score_topic(1000, "B", followup=True) == pytest.approx(base * 2)


class TestRecommend:
    def test_civilian_cost_beats_bigger_politician_spat(self):
        """댓글이 3배 많아도 정치인 공방(C)은 민간인+대가(A)에 진다 — 044 핵심."""
        clusters = cluster_articles([
            _a("민주당 의원 국민의힘 의원 공방 격화", 3000, "1"),
            _a("교사 폭행 학부모 결국 사과", 1000, "2"),
        ])
        recs = recommend(clusters, category="news")
        assert recs[0].label == "교사 폭행 학부모 결국 사과"
        assert recs[0].tier == "A"

    def test_inner_party_excluded(self):
        clusters = cluster_articles([_a("국민의힘 당대표 재신임 투표", 9000, "1")])
        assert recommend(clusters, category="news") == []

    def test_politician_foul_is_tier_b_with_record_angle(self):
        clusters = cluster_articles([_a("의원 다주택 내로남불 결국 매각", 1000, "1")])
        rec = recommend(clusters, category="news")[0]
        assert rec.tier == "B"
        assert "과거 발언" in rec.angle_hint

    def test_politician_plain_is_tier_c_with_person_angle(self):
        clusters = cluster_articles([_a("대통령 유엔 연설 북한 협력 제안", 1000, "1")])
        rec = recommend(clusters, category="news")[0]
        assert rec.tier == "C"
        assert "사람" in rec.angle_hint

    def test_money_words_flagged(self):
        clusters = cluster_articles([_a("월급 빼고 다 올랐다 세금 폭탄 직장인", 1000, "1")])
        assert recommend(clusters, category="news")[0].money is True

    def test_followup_flagged_when_matching_channel_breakout(self):
        clusters = cluster_articles([_a("박위 강연료 1500만원 추가 폭로", 500, "1")])
        rec = recommend(clusters, category="news",
                        followup_titles=["박위 강연 줄무산 사과 나흘 만에"])[0]
        assert rec.followup is True

    def test_entertainment_category_forced(self):
        clusters = cluster_articles([_a("배우 갑질 의혹 결국 하차", 600_000, "1")])
        rec = recommend(clusters, category="entertainment")[0]
        assert rec.category == "entertainment"
        assert rec.tier == "A"

    def test_top_limit(self):
        arts = [_a(f"교사{i} 폭행{i} 학부모{i} 사과", 100 + i, str(i))
                for i in range(8)]
        assert len(recommend(cluster_articles(arts), category="news", top=3)) == 3

    def test_result_is_immutable(self):
        rec = recommend(cluster_articles([_a("교사 폭행 학부모 사과", 10, "1")]),
                        category="news")[0]
        with pytest.raises(AttributeError):
            rec.score = 0


class TestLiveDataMisjudgments:
    """2026-10-12 실데이터 첫 실행에서 나온 오판 — 회귀 방지."""

    def _one(self, title, demand=1000, category="news"):
        return recommend(cluster_articles([_a(title, demand)]), category=category)

    def test_name_only_politician_is_not_civilian(self):
        rec = self._one('박지원 "추미애, 뭘 그렇게 잘했나" 결국 사과')
        assert rec[0].tier != "A"

    def test_chief_justice_is_public_figure(self):
        rec = self._one('감사원 "대법원장 격려금 지급 확인" 거짓해명 들통')
        assert rec[0].tier != "A"

    def test_cliche_phrase_does_not_merge(self):
        arts = [_a("크리스 수감 사진 알고 보니 조작", 900, "1"),
                _a("톰 크루즈 한강 산책 정체 알고 보니", 800, "2")]
        assert len(cluster_articles(arts)) == 2

    def test_fine_is_not_viewer_money(self):
        assert self._one("초등 담임 아동학대 벌금 500만원 확정")[0].money is False

    def test_no_cost_paid_is_not_tier_a(self):
        """대가 어휘가 없으면 당사자 실명을 확인할 길이 없다 — A 로 올리지 않는다."""
        assert self._one("스타벅스 투썸 제치고 결제액 1위 탈환")[0].tier != "A"

    def test_violent_crime_excluded(self):
        """040 사용자 확정: 범죄 소재는 편성 제외."""
        assert self._one("슈퍼마켓 업주 살해한 40대, 무기징역 확정") == []

    def test_generic_reveal_words_do_not_merge(self):
        """2026-10-12: '공개'·'만에'로 탑 팬사이트 묶음에 조세호·김용지 기사가 섞였다."""
        arts = [_a("나나 탑, 공개 열애 8일 만에 폭로 팬사이트 폐쇄", 900, "1"),
                _a("조세호, SNS 근황 공개 하루 만에 계폭위기", 800, "2"),
                _a("김용지, 열애 공개 없이 깜짝 결혼", 700, "3")]
        assert len(cluster_articles(arts)) == 3
