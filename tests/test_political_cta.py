"""정치쇼츠 중반 CTA (035) 테스트 — scripts/political_cta.py."""
from __future__ import annotations

import pytest

from scripts.political_cta import (
    CTA_CLOSING, DEFAULT_CTA_AT_FRAC, apply_cta, build_cta_scene,
    cta_insert_index, has_spoken_question, is_side_picking, lint_cta,
    lint_cta_closing, lint_cta_question, scene_cta_closing_warnings,
    trailing_cta_warnings,
)
from scripts.shorts_format import CTA_STYLE_SUBSCRIBE


def cfg_with_cta(**over) -> dict:
    cfg = {
        "slug": "test_cta",
        "title": "배너",
        "sources": {"a": {"query": "q"}, "b": {"url": "https://y/x"}},
        "scenes": [
            {"mode": "clip", "source": "a", "duration": 5.0, "text": "훅"},
            {"mode": "clip", "source": "b", "duration": 6.0, "text": "반박"},
            {"mode": "clip", "source": "a", "duration": 6.0, "text": "재반박"},
            {"mode": "tts", "source": "a", "frac": 0.5, "text": "정리",
             "voice": "라" * 148},
        ],
        "cta": {
            "text": "이거 누구 잘못?\n① 조국  ② 이준석",
            "voice": "이건 누구 잘못일까요? 1번, 2번 댓글로 알려주세요.",
            "hl": ["누구 잘못"],
        },
    }
    cfg.update(over)
    return cfg


# ── 편 가르기 질문 판정 ─────────────────────────────────────────────
class TestIsSidePicking:
    @pytest.mark.parametrize("text", [
        "이거 누구 잘못? ① 조국 ② 이준석",
        "1번인가요 2번인가요?",
        "어느 쪽이 맞다고 보세요?",
        "찬성? 반대?",
        "누가 더 문제입니까",
    ])
    def test_side_picking_forms(self, text):
        assert is_side_picking(text) is True

    @pytest.mark.parametrize("text", [
        "여러분 생각은 어떠신가요? 댓글로 남겨주세요",
        "구독과 좋아요 부탁드립니다",
        "많은 관심 바랍니다",
    ])
    def test_generic_forms_rejected(self, text):
        assert is_side_picking(text) is False


# ── CTA 블록 린트 ───────────────────────────────────────────────────
class TestLintCta:
    def test_valid_cta_no_warning(self):
        assert lint_cta(cfg_with_cta()["cta"]) == []

    def test_missing_text_or_voice_warns(self):
        assert lint_cta({"voice": "누구 잘못일까요? 1번 2번"}) != []
        assert lint_cta({"text": "누구 잘못? ① ②"}) != []

    def test_generic_question_warns(self):
        warns = lint_cta({"text": "생각은?", "voice": "여러분 생각은 어떠신가요? 댓글로 남겨주세요."})
        assert any("편" in w or "선택" in w for w in warns)

    def test_long_cta_voice_warns(self):
        warns = lint_cta({"text": "누구 잘못? ① ②", "voice": "누구 잘못일까요 " * 20})
        assert any("짧" in w or "초" in w for w in warns)


# ── 삽입 위치 계산 (40% 지점) ───────────────────────────────────────
class TestCtaInsertIndex:
    def test_default_frac_is_40_percent(self):
        assert DEFAULT_CTA_AT_FRAC == 0.4

    def test_picks_index_closest_to_target(self):
        # 총 40초, 40% = 16초. 누적 [0,3,13,23,33] → 13초(j=2)가 최근접
        assert cta_insert_index([3, 10, 10, 10, 7]) == 2

    def test_never_before_first_scene(self):
        assert cta_insert_index([100, 1, 1, 1]) >= 1

    def test_never_after_last_scene(self):
        durations = [1, 1, 1, 100]
        assert cta_insert_index(durations) <= len(durations) - 1

    def test_prefix_sec_shifts_target(self):
        """V2.1 훅(top-level)이 앞에 붙으면 40% 지점이 앞으로 당겨진다."""
        no_prefix = cta_insert_index([10, 10, 10, 10], prefix_sec=0.0)
        with_prefix = cta_insert_index([10, 10, 10, 10], prefix_sec=20.0)
        assert with_prefix <= no_prefix

    def test_single_scene_appends(self):
        assert cta_insert_index([10.0]) == 1

    def test_empty_durations(self):
        assert cta_insert_index([]) == 0


# ── CTA 씬 생성 ─────────────────────────────────────────────────────
class TestBuildCtaScene:
    def test_inherits_neighbor_source(self):
        sc = build_cta_scene({"text": "t", "voice": "v"}, {"source": "b", "frac": 0.7})
        assert sc["source"] == "b"
        assert sc["frac"] == 0.7

    def test_explicit_source_wins(self):
        sc = build_cta_scene({"text": "t", "voice": "v", "source": "a"}, {"source": "b"})
        assert sc["source"] == "a"

    def test_is_tts_mode_and_emphasized(self):
        sc = build_cta_scene({"text": "t", "voice": "v"}, {"source": "a"})
        assert sc["mode"] == "tts"
        assert sc["emph"] is True
        assert sc["color"] == "yellow"

    def test_inherits_neighbor_subtitle_position(self):
        """038 이후 CTA는 항상 마지막 씬이라 b-roll 이 방송 클립이다 —
        이웃이 번인 자막을 피해 bottom 에 있으면 CTA도 같이 내려가야 한다."""
        sc = build_cta_scene(
            {"text": "t", "voice": "v"},
            {"source": "a", "subtitle_position": "bottom"})
        assert sc["subtitle_position"] == "bottom"

    def test_explicit_subtitle_position_wins(self):
        sc = build_cta_scene(
            {"text": "t", "voice": "v", "subtitle_position": "bottom"},
            {"source": "a"})
        assert sc["subtitle_position"] == "bottom"

    def test_subtitle_position_defaults_to_empty(self):
        """미지정이면 빈 문자열 — 기존 config 동작(position_y 0.652) 유지."""
        sc = build_cta_scene({"text": "t", "voice": "v"}, {"source": "a"})
        assert sc["subtitle_position"] == ""


# ── cfg 적용 (불변) ─────────────────────────────────────────────────
class TestApplyCta:
    def test_no_cta_returns_config_unchanged(self):
        cfg = cfg_with_cta()
        del cfg["cta"]
        assert apply_cta(cfg) == cfg

    def test_inserts_one_scene(self):
        cfg = cfg_with_cta()
        out = apply_cta(cfg)
        assert len(out["scenes"]) == len(cfg["scenes"]) + 1

    def test_does_not_mutate_input(self):
        cfg = cfg_with_cta()
        before = len(cfg["scenes"])
        apply_cta(cfg)
        assert len(cfg["scenes"]) == before

    def test_cta_is_last_scene(self):
        """038: CTA는 항상 마지막 씬 — 40% 중반 삽입에서 되돌림."""
        out = apply_cta(cfg_with_cta())
        assert out["scenes"][-1].get("_cta") is True
        assert out["scenes"][-2].get("text") == "정리"

    def test_cta_not_first_scene(self):
        """scene[0]은 훅(clip) 유지 — V2.2 검증 규칙 보호."""
        out = apply_cta(cfg_with_cta())
        assert out["scenes"][0].get("mode") == "clip"

    def test_cta_inherits_last_scene_as_neighbor(self):
        cfg = cfg_with_cta()
        out = apply_cta(cfg)
        assert out["scenes"][-1]["source"] == cfg["scenes"][-1]["source"]

    def test_malformed_config_returns_unchanged(self):
        cfg = {"slug": "x", "cta": {"text": "t", "voice": "v"}}
        assert apply_cta(cfg) == cfg


# ── 말미 CTA 잔존 감지 ──────────────────────────────────────────────
class TestTrailingCtaWarnings:
    def test_warns_when_cta_phrase_left_in_normal_scene(self):
        cfg = cfg_with_cta()
        cfg["scenes"][-1]["voice"] = "정리하자면 이렇습니다. 여러분 생각은? 댓글로 남겨주세요."
        assert trailing_cta_warnings(cfg) != []

    def test_no_warning_when_clean(self):
        assert trailing_cta_warnings(cfg_with_cta()) == []

    def test_cta_scene_itself_not_flagged(self):
        out = apply_cta(cfg_with_cta())
        assert trailing_cta_warnings(out) == []


# ── CTA 종결 말투 (사용자 지시 2026-08-18) ──────────────────────────
class TestCtaClosing:
    def test_polite_closing_passes(self):
        assert lint_cta_closing(f"1번 조국, 2번 이준석. {CTA_CLOSING}.") == []

    def test_banmal_closing_warns(self):
        assert lint_cta_closing("누구 잘못일까요? 번호로 답글.") != []

    def test_empty_voice_not_flagged(self):
        """빈 나레이션은 종결이 아니라 '누락' 경고가 맡는다."""
        assert lint_cta_closing("") == []

    def test_lint_cta_reports_closing(self):
        cta = {"text": "누구 잘못?\n① A  ② B", "voice": "1번, 2번 번호로 답글."}
        assert any(CTA_CLOSING in w for w in lint_cta(cta))

    def test_clean_cta_block_has_no_warning(self):
        cta = {"text": "누구 잘못?\n① A  ② B",
               "voice": f"누구 잘못일까요? 1번 A, 2번 B. {CTA_CLOSING}."}
        assert lint_cta(cta) == []


# ── 씬으로 직접 쓴 CTA 의 종결 (top-level cta 블록 미사용 경로) ─────
class TestSceneCtaClosingWarnings:
    def test_scene_cta_with_banmal_closing_warns(self):
        cfg = {"scenes": [
            {"text": "정리", "voice": "결과는 109명 중 20명입니다."},
            {"text": "어느 쪽?\n① 결집이다  ② 고립이다",
             "voice": "어느 쪽일까요? 1번 결집, 2번 고립. 번호로 답글."},
        ]}
        out = scene_cta_closing_warnings(cfg)
        assert len(out) == 1 and out[0].startswith("scene[1]")

    def test_scene_cta_with_polite_closing_passes(self):
        cfg = {"scenes": [
            {"text": "어느 쪽?\n① 결집이다  ② 고립이다",
             "voice": f"어느 쪽일까요? 1번 결집, 2번 고립. {CTA_CLOSING}."},
        ]}
        assert scene_cta_closing_warnings(cfg) == []

    def test_normal_scene_with_side_word_not_flagged(self):
        """'찬성/반대'가 스쳐 가는 일반 나레이션은 CTA가 아니다 (오탐 방지)."""
        cfg = {"scenes": [
            {"text": "여야 격돌\n표결 무산", "voice": "찬성과 반대로 갈렸습니다."},
        ]}
        assert scene_cta_closing_warnings(cfg) == []

    def test_block_inserted_cta_scene_skipped(self):
        """블록에서 삽입된 씬은 lint_cta 가 이미 본다 — 중복 경고 금지."""
        cfg = apply_cta(cfg_with_cta())
        assert scene_cta_closing_warnings(cfg) == []


class TestCtaQuestionRead:
    """CTA 나레이션이 질문까지 읽는지 (V2.1·V2.2 고정 지침, 사용자 지시 2026-09-17).

    035는 4초 상한을 아끼려 "질문은 자막이 보여주니 나레이션에선 뺀다"였는데,
    선택지 번호만 들리면 소리만 듣는 시청자는 무엇을 고르라는 건지 알 수 없다.
    """

    def test_options_only_narration_warns(self):
        w = lint_cta_question("1번 조국, 2번 이준석. 댓글로 알려주세요.")
        assert len(w) == 1
        assert "질문을 안 읽" in w[0]

    def test_question_mark_passes(self):
        assert lint_cta_question(
            "이건 누가 잘못한 걸까요? 1번 조국, 2번 이준석. 댓글로 알려주세요.") == []

    def test_question_ending_without_mark_passes(self):
        # 물음표를 안 찍어도 의문형 어미면 소리로는 질문이다
        assert lint_cta_question("너무 약한가요 적당한가요 댓글로 알려주세요.") == []

    def test_empty_voice_not_flagged(self):
        assert lint_cta_question("") == []

    def test_subscribe_style_exempt(self):
        # 041 구독형 CTA는 질문이 아니라 부탁 — 면제
        assert lint_cta_question("구독 부탁드립니다.", CTA_STYLE_SUBSCRIBE) == []

    def test_has_spoken_question_detects_markers(self):
        assert has_spoken_question("누가 맞을까요")
        assert has_spoken_question("이게 맞나요")
        assert not has_spoken_question("1번 조국, 2번 이준석.")

    def test_lint_cta_reports_question(self):
        w = lint_cta({"text": "이거 누구 잘못?\n① 조국  ② 이준석",
                      "voice": "1번 조국, 2번 이준석. 댓글로 알려주세요."})
        assert any("질문을 안 읽" in x for x in w)

    def test_question_narration_fits_raised_cap(self):
        # 질문을 붙이면 4초를 넘으므로 상한을 5초로 올렸다 — 표준 문구는 통과해야 한다
        w = lint_cta({"text": "이거 누구 잘못?\n① 노인  ② 여성",
                      "voice": "이건 누가 잘못한 걸까요? 1번 노인, 2번 여성. "
                               "댓글로 알려주세요."})
        assert w == [], w

    def test_over_cap_still_warns(self):
        w = lint_cta({"text": "① 가  ② 나",
                      "voice": "이건 누가 잘못한 걸까요? " + "라" * 40
                               + " 댓글로 알려주세요."})
        assert any("이내로 짧게" in x for x in w)

    def test_scene_written_cta_without_question_warns(self):
        cfg = {"scenes": [
            {"text": "이거 누구 잘못?\n① 노인  ② 여성",
             "voice": "1번 노인, 2번 여성. 댓글로 알려주세요."}]}
        w = scene_cta_closing_warnings(cfg)
        assert any("질문을 안 읽" in x for x in w)

    def test_scene_written_cta_with_question_passes(self):
        cfg = {"scenes": [
            {"text": "이거 누구 잘못?\n① 노인  ② 여성",
             "voice": "이건 누가 잘못한 걸까요? 1번 노인, 2번 여성. "
                      "댓글로 알려주세요."}]}
        assert scene_cta_closing_warnings(cfg) == []

    def test_cta_scene_inherits_highlight_category(self):
        # BGM(emotion_type)만 바꾸려고 씬에서 강조색을 고정해 뒀는데 CTA만
        # emotion 색으로 튀면 눈에 걸린다
        scene = build_cta_scene({"text": "t", "voice": "v"},
                                {"source": "a", "highlight_category": "criticism"})
        assert scene["highlight_category"] == "criticism"

    def test_cta_scene_highlight_category_defaults_neutral(self):
        scene = build_cta_scene({"text": "t", "voice": "v"}, {"source": "a"})
        assert scene["highlight_category"] == "neutral"
