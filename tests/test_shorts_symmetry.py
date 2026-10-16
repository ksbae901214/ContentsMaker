"""진영 대칭·기록 대조 검사 (scripts/shorts_symmetry.py) 테스트 — 040.

실측 배경: 133편의 제목 진영 감사에서 여권만 21편(중앙 1,400) / 야권만 22편
(1,300) / 양쪽 32편(1,297)이 나왔다. 타깃 배분은 이미 균형인데 **한 편만 보면
한쪽만 보인다**. 이 모듈은 그 '한 편 단위 대칭'을 검사한다.
"""
from __future__ import annotations

from scripts.shorts_symmetry import (
    BOTH_MARKERS,
    GATE_KEY,
    GATE_OFF,
    LEFT,
    RIGHT,
    SymmetryVerdict,
    evaluate_symmetry,
    has_record_contrast,
    sides_in,
    symmetry_text,
    symmetry_warnings,
)


def cfg(**kw) -> dict:
    base = {"title": "", "yt_title": "", "scenes": [], "category": "political"}
    return {**base, **kw}


def scene(text: str) -> dict:
    return {"text": text, "voice": "", "source": "s"}


class TestSidesIn:
    def test_left_person(self):
        assert sides_in("이재명 대통령의 결단") == frozenset({LEFT})

    def test_right_person(self):
        assert sides_in("장동혁 대표의 침묵") == frozenset({RIGHT})

    def test_both_when_two_sides_present(self):
        assert sides_in("이재명과 한동훈의 정면충돌") == frozenset({LEFT, RIGHT})

    def test_english_titles_match_case_insensitively(self):
        assert sides_in("Lee Jae-myung and Han Dong-hoon clash") == frozenset(
            {LEFT, RIGHT})

    def test_yeoya_counts_as_both(self):
        # '여야'는 한 단어로 양쪽을 가리킨다 — 여당/야당 개별 매칭으로는 안 잡힌다
        assert "여야" in BOTH_MARKERS
        assert sides_in("여야 합의 무산") == frozenset({LEFT, RIGHT})

    def test_no_marker_returns_empty(self):
        assert sides_in("출근 첫날 폭행당한 교사") == frozenset()


class TestSymmetryText:
    def test_uses_title_and_scene_text_not_voice(self):
        c = cfg(yt_title="이재명 발언", scenes=[
            {"text": "한동훈 반박", "voice": "오세훈 나레이션"}])
        text = symmetry_text(c)
        assert "이재명" in text and "한동훈" in text
        assert "오세훈" not in text


class TestEvaluate:
    def test_symmetric_when_both_sides_on_screen(self):
        c = cfg(yt_title="같은 사안, 다른 말",
                scenes=[scene("이재명 '집값 잡겠다'"), scene("장동혁 '그때는 달랐다'")])
        v = evaluate_symmetry(c)
        assert isinstance(v, SymmetryVerdict)
        assert v.symmetric is True
        assert v.sides == frozenset({LEFT, RIGHT})

    def test_asymmetric_when_one_side_only(self):
        c = cfg(yt_title="용혜인 내로남불", scenes=[scene("민주당의 침묵")])
        v = evaluate_symmetry(c)
        assert v.symmetric is False
        assert v.sides == frozenset({LEFT})

    def test_verdict_is_frozen(self):
        v = evaluate_symmetry(cfg(yt_title="이재명"))
        try:
            v.symmetric = True  # type: ignore[misc]
        except Exception as exc:
            assert exc.__class__.__name__ == "FrozenInstanceError"
        else:
            raise AssertionError("SymmetryVerdict 는 frozen 이어야 합니다")


class TestRecordContrast:
    def test_detects_past_vs_present_frame(self):
        assert has_record_contrast("'다주택은 손 떼라'더니 4채 한성숙 지명")

    def test_detects_naeronambul(self):
        assert has_record_contrast("용혜인 내로남불")

    def test_detects_english_frame(self):
        assert has_record_contrast("What he said back then vs now")

    def test_plain_report_has_no_contrast(self):
        assert not has_record_contrast("국회 본회의 예산안 통과")


class TestWarnings:
    def test_warns_on_one_sided_political_config(self):
        c = cfg(yt_title="이재명 근저당 논란", scenes=[scene("민주당 해명")])
        ws = symmetry_warnings(c)
        assert any("한쪽 진영" in w for w in ws)
        assert all(w.startswith("[040]") for w in ws)

    def test_no_side_warning_when_both_present(self):
        c = cfg(yt_title="같은 질문에 여야 다른 답",
                scenes=[scene("이재명 답변"), scene("장동혁 답변")])
        assert not any("한쪽 진영" in w for w in symmetry_warnings(c))

    def test_silent_when_no_political_figure_detected(self):
        # 사전에 없는 인물이면 오탐 대신 침묵 — 경고 남발이 게이트를 죽인다
        c = cfg(yt_title="출근 첫날 폭행당한 교사", scenes=[scene("학교의 조치")])
        assert not any("한쪽 진영" in w for w in symmetry_warnings(c))

    def test_recommends_record_contrast_frame(self):
        c = cfg(yt_title="이재명 장동혁 예산 공방",
                scenes=[scene("이재명 발언"), scene("장동혁 발언")])
        assert any("기록 대조" in w for w in symmetry_warnings(c))

    def test_no_contrast_recommendation_when_frame_present(self):
        c = cfg(yt_title="'집값 잡겠다'더니 이재명 장동혁 정반대 행보",
                scenes=[scene("이재명 발언"), scene("장동혁 발언")])
        assert not any("기록 대조" in w for w in symmetry_warnings(c))

    def test_non_political_category_is_skipped(self):
        c = cfg(yt_title="이재명 언급된 연예 기사", category="entertainment")
        assert symmetry_warnings(c) == []

    def test_gate_off_silences_everything(self):
        c = cfg(yt_title="용혜인 내로남불", **{GATE_KEY: GATE_OFF})
        assert symmetry_warnings(c) == []
