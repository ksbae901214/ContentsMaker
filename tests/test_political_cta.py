"""정치쇼츠 중반 CTA (035) 테스트 — scripts/political_cta.py."""
from __future__ import annotations

import pytest

from scripts.political_cta import (
    CTA_CLOSING, DEFAULT_CTA_AT_FRAC, apply_cta, build_cta_scene,
    cta_insert_index, is_side_picking, lint_cta, lint_cta_closing,
    scene_cta_closing_warnings, trailing_cta_warnings,
)


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
               "voice": f"1번 A, 2번 B. {CTA_CLOSING}."}
        assert lint_cta(cta) == []


# ── 씬으로 직접 쓴 CTA 의 종결 (top-level cta 블록 미사용 경로) ─────
class TestSceneCtaClosingWarnings:
    def test_scene_cta_with_banmal_closing_warns(self):
        cfg = {"scenes": [
            {"text": "정리", "voice": "결과는 109명 중 20명입니다."},
            {"text": "어느 쪽?\n① 결집이다  ② 고립이다",
             "voice": "1번 결집, 2번 고립. 번호로 답글."},
        ]}
        out = scene_cta_closing_warnings(cfg)
        assert len(out) == 1 and out[0].startswith("scene[1]")

    def test_scene_cta_with_polite_closing_passes(self):
        cfg = {"scenes": [
            {"text": "어느 쪽?\n① 결집이다  ② 고립이다",
             "voice": f"1번 결집, 2번 고립. {CTA_CLOSING}."},
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
