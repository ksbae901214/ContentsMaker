"""돌파 조건 게이트 (scripts/shorts_breakout.py) 테스트 — 039.

실측 사례(2026-09-03 스냅샷 130편)를 그대로 케이스로 쓴다. 규칙이 실제로
뚫린 편은 통과시키고 밴드에 갇힌 편은 잡아내는지가 유일한 판정 기준이다.
"""
from __future__ import annotations

import pytest

from scripts.shorts_breakout import (
    CIVILIAN,
    GATE_KEY,
    GATE_OFF,
    INSTITUTION,
    POLITICIAN,
    TIER_A,
    TIER_B,
    TIER_C,
    TIER_DEAD,
    BreakoutVerdict,
    breakout_warnings,
    evaluate,
    frame_text,
    infer_subject_type,
    subject_text,
    verdict_line,
)


def cfg(**kw) -> dict:
    base = {"title": "", "yt_title": "", "persons": [], "scenes": []}
    return {**base, **kw}


class TestSubjectType:
    def test_declared_wins_over_inference(self):
        c = cfg(yt_title="이재명 의원의 사과", subject_type=CIVILIAN)
        assert infer_subject_type(c) == CIVILIAN

    def test_invalid_declared_falls_back_to_inference(self):
        c = cfg(yt_title="이재명 의원의 사과", subject_type="bogus")
        assert infer_subject_type(c) == POLITICIAN

    def test_title_marker_infers_politician(self):
        assert infer_subject_type(cfg(yt_title="용혜인 의원 겸직 논란")) == POLITICIAN

    def test_named_person_without_title_uses_category(self):
        c = cfg(yt_title="17년 만에 뒤집힌 배정남 폭행 진술", persons=["배정남"],
                category="entertainment")
        assert infer_subject_type(c) == CIVILIAN

    def test_bare_politician_name_is_not_civilian(self):
        """직함이 없어도 정치 카테고리면 정치인 — 게이트가 조용히 통과하면 안 된다."""
        assert infer_subject_type(cfg(yt_title="용혜인 내로남불",
                                      persons=["용혜인"])) == POLITICIAN

    def test_no_person_is_institution(self):
        assert infer_subject_type(
            cfg(yt_title="금감원 세종 이전", category="society")) == INSTITUTION

    def test_subject_text_ignores_scene_captions(self):
        """씬에 인용된 정치인 때문에 연예 편이 정치인으로 오분류되면 안 된다."""
        c = cfg(yt_title="박수홍 비행기 지연의 진실", persons=["박수홍"],
                category="entertainment",
                scenes=[{"text": "국회 의원들도 언급했다"}])
        assert "의원" not in subject_text(c)
        assert infer_subject_type(c) == CIVILIAN


class TestFrameText:
    def test_includes_scene_captions(self):
        c = cfg(yt_title="제목", scenes=[{"text": "결국 사과했다"}])
        assert "사과" in frame_text(c)

    def test_excludes_narration(self):
        """대가·결말은 화면 자막에 보여야 클릭에 반영된다."""
        c = cfg(yt_title="제목", scenes=[{"text": "자막", "voice": "사퇴했습니다"}])
        assert "사퇴" not in frame_text(c)


class TestRealBreakouts:
    """실제로 3,000회를 뚫은 편 — A 또는 B 등급이 나와야 한다."""

    def test_park_we_civilian_cost(self):
        c = cfg(yt_title="KTX 갑질 논란 위라클 박위 반복되는 3번째 사과",
                persons=["박위"], category="entertainment")
        v = evaluate(c)
        assert v.tier == TIER_A
        assert v.cost_paid and v.settled and v.partisan_free

    def test_hayoung_civilian_cost(self):
        c = cfg(yt_title="4대 의사집안 하영 자랑에서 사과까지 닷새",
                persons=["하영"], category="society")
        assert evaluate(c).tier == TIER_A

    def test_yong_hye_in_politician_but_foul(self):
        """정치인이지만 겸직 = 진영 무관 반칙 → B (실측 25%)."""
        c = cfg(yt_title="용혜인 장관 되고도 의원직 겸직", persons=["용혜인"])
        v = evaluate(c)
        assert v.tier == TIER_B
        assert v.partisan_free

    def test_naeronambul_is_foul(self):
        c = cfg(yt_title="용혜인 내로남불", persons=["용혜인"])
        assert evaluate(c).tier == TIER_B


class TestRealFailures:
    """'대가' 어휘를 달고도 전멸한 편 — DEAD 로 잡아야 한다."""

    @pytest.mark.parametrize("title", [
        "당 지키려던 장동혁 되레 제명 위기",
        "장동혁 당대표 사퇴 재신임 요구 수용 조건 제시",
        "한동훈 제명, 장동혁의 징계정치",
        "국민의힘 당원 2.2만 명 청원",
        "조국 평택을 낙선, 출구조사 1위가 뒤집혔다",
    ])
    def test_inner_party_topics_are_dead(self, title):
        assert evaluate(cfg(yt_title=title, persons=["장동혁"])).tier == TIER_DEAD

    def test_dead_wins_even_with_cost_words(self):
        """②를 갖춰도 ③을 어기면 죽는다 — 실측 6편 0%."""
        v = evaluate(cfg(yt_title="조국 징역 2년 확정 뒤 당대표 사퇴"))
        assert v.cost_paid
        assert v.tier == TIER_DEAD

    def test_unsettled_politician_is_tier_c(self):
        c = cfg(yt_title="특검법 처리 촉구", persons=["정청래"])
        v = evaluate(c)
        assert v.tier == TIER_C
        assert not v.settled

    def test_plain_politician_topic_is_tier_c(self):
        v = evaluate(cfg(yt_title="이재명 대통령 부동산 세제 개편", persons=["이재명"]))
        assert v.tier == TIER_C
        assert not v.partisan_free


class TestWarnings:
    def test_dead_returns_single_blocking_style_warning(self):
        w = breakout_warnings(cfg(yt_title="장동혁 제명 위기"))
        assert len(w) == 1
        assert "돌파율 0%" in w[0]

    def test_tier_c_lists_each_missing_condition(self):
        w = breakout_warnings(cfg(yt_title="이재명 대통령 세제 개편 추진",
                                  persons=["이재명"]))
        joined = " ".join(w)
        assert "직업 정치인" in joined
        assert "대가" in joined
        assert "진행 중" in joined

    def test_tier_a_with_cost_has_no_warning(self):
        assert breakout_warnings(cfg(yt_title="박위 3번째 사과", persons=["박위"],
                                     category="entertainment")) == []

    def test_civilian_without_cost_still_warns(self):
        w = breakout_warnings(cfg(yt_title="배정남 근황", persons=["배정남"],
                                  category="entertainment"))
        assert any("대가" in x for x in w)

    def test_gate_off_silences_everything(self):
        c = cfg(yt_title="장동혁 제명 위기", **{GATE_KEY: GATE_OFF})
        assert breakout_warnings(c) == []


class TestVerdictShape:
    def test_verdict_is_immutable(self):
        v = evaluate(cfg(yt_title="박위 사과", persons=["박위"],
                         category="entertainment"))
        with pytest.raises(Exception):
            v.tier = TIER_C

    def test_conditions_met_counts_three_axes(self):
        v = evaluate(cfg(yt_title="박위 3번째 사과", persons=["박위"],
                         category="entertainment"))
        assert v.conditions_met == 3

    def test_note_present_for_every_tier(self):
        for tier in (TIER_A, TIER_B, TIER_C, TIER_DEAD):
            v = BreakoutVerdict(tier=tier, subject_type=CIVILIAN,
                                partisan_free=True, cost_paid=True,
                                settled=True, hits=())
            assert v.note

    def test_verdict_line_is_one_line(self):
        line = verdict_line(cfg(yt_title="박위 3번째 사과", persons=["박위"],
                                category="entertainment"))
        assert "\n" not in line
        assert TIER_A in line

    def test_evaluate_does_not_mutate_config(self):
        c = cfg(yt_title="박위 사과", persons=["박위"], category="entertainment")
        before = dict(c)
        evaluate(c)
        assert c == before
