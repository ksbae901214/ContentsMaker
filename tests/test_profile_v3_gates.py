"""V3.0 인물 프로필 포맷의 게이트 예외 (041 Phase A4).

041 §4 표의 ①②③ — 040 대칭 침묵 / 039 고지 톤 / 구독형 CTA 면제.
**기존 V2.1/V2.2 config 의 동작은 한 줄도 바뀌면 안 된다** (각 테스트의 대조군).
"""
from __future__ import annotations

import pytest

from scripts.political_cta import (
    CTA_STYLE_PICK,
    CTA_STYLE_SUBSCRIBE,
    lint_cta,
    lint_cta_closing,
    resolve_cta_style,
    scene_cta_closing_warnings,
)
from scripts.shorts_breakout import breakout_warnings
from scripts.shorts_symmetry import symmetry_warnings

ONE_SIDED = {
    "yt_title": "이해민은 누구인가",
    "category": "political",
    "scenes": [{"text": "민주당 이해민 수석 내정"}],
}


class TestSymmetrySilentForProfileV3:
    def test_v2_1_still_warns(self):
        """대조군 — 한쪽 진영만 등장하는 V2.1 편은 그대로 경고."""
        assert symmetry_warnings(ONE_SIDED)

    def test_profile_v3_silent(self):
        cfg = {**ONE_SIDED, "format": "profile_v3"}
        assert symmetry_warnings(cfg) == []

    def test_profile_v3_silent_even_with_record_contrast_missing(self):
        cfg = {**ONE_SIDED, "format": "profile_v3", "scenes": []}
        assert symmetry_warnings(cfg) == []


class TestBreakoutNoticeForProfileV3:
    def test_v2_1_emits_separate_warnings(self):
        """대조군 — 정치인·대가 없음이면 개별 경고가 여러 줄 붙는다."""
        assert len(breakout_warnings(ONE_SIDED)) >= 2

    def test_profile_v3_collapses_to_single_notice(self):
        cfg = {**ONE_SIDED, "format": "profile_v3"}
        warnings = breakout_warnings(cfg)
        assert len(warnings) == 1
        assert "인물 프로필" in warnings[0]

    def test_profile_v3_keeps_dead_warning(self):
        """③ 당내 절차 0%는 인물편이라고 면제될 근거가 없다."""
        cfg = {**ONE_SIDED, "format": "profile_v3",
               "yt_title": "이해민 공천 재신임 요구"}
        warnings = breakout_warnings(cfg)
        assert any("당내 정치" in w for w in warnings)

    def test_gate_off_still_silences_everything(self):
        cfg = {**ONE_SIDED, "format": "profile_v3", "breakout_gate": "off"}
        assert breakout_warnings(cfg) == []


class TestResolveCtaStyle:
    def test_v2_defaults_to_pick(self):
        assert resolve_cta_style({}) == CTA_STYLE_PICK

    def test_profile_v3_defaults_to_subscribe(self):
        assert resolve_cta_style({"format": "profile_v3"}) == CTA_STYLE_SUBSCRIBE

    def test_explicit_wins(self):
        assert resolve_cta_style(
            {"format": "profile_v3", "cta_style": "pick"}) == CTA_STYLE_PICK

    def test_unknown_style_raises(self):
        with pytest.raises(ValueError):
            resolve_cta_style({"cta_style": "구독형"})


class TestLintCtaSubscribe:
    SUBSCRIBE = {
        "text": "더 궁금하다면?\n댓글 + 구독",
        "voice": "궁금한 점은 댓글로 남겨주세요.",
    }

    def test_pick_style_still_requires_side_picking(self):
        """대조군 — 기본 스타일에서 열린 질문은 그대로 경고."""
        warnings = lint_cta({"text": "여러분 생각은?", "voice": "댓글로 알려주세요."})
        assert any("선택지형" in w for w in warnings)

    def test_subscribe_style_exempts_side_picking(self):
        warnings = lint_cta(self.SUBSCRIBE, style=CTA_STYLE_SUBSCRIBE)
        assert not any("선택지형" in w for w in warnings)

    def test_subscribe_style_still_warns_on_blunt_closing(self):
        """말투 규칙(2026-08-18)은 포맷과 무관하다."""
        cta = {**self.SUBSCRIBE, "voice": "궁금하면 댓글. 구독 필수."}
        assert any("종결" in w for w in lint_cta(cta, style=CTA_STYLE_SUBSCRIBE))

    def test_subscribe_style_accepts_polite_closings(self):
        for voice in ("댓글로 남겨주세요.", "구독 부탁드립니다.", "댓글로 알려주세요."):
            cta = {**self.SUBSCRIBE, "voice": voice}
            assert not any("종결" in w for w in lint_cta(cta, style=CTA_STYLE_SUBSCRIBE))

    def test_subscribe_style_requires_comment_or_subscribe_ask(self):
        cta = {"text": "다음 인물도 기대해주세요", "voice": "다음 편에서 뵙겠습니다."}
        warnings = lint_cta(cta, style=CTA_STYLE_SUBSCRIBE)
        assert any("구독" in w for w in warnings)

    def test_length_cap_still_applies(self):
        cta = {**self.SUBSCRIBE,
               "voice": "이 인물에 대해 더 알고 싶은 점이 있다면 무엇이든 댓글로 남겨주시고 "
                        "다음 인물 프로필도 보고 싶다면 구독 부탁드립니다."}
        assert any("초" in w for w in lint_cta(cta, style=CTA_STYLE_SUBSCRIBE))

    def test_two_arg_call_still_works(self):
        """기존 호출부(lint_cta(cta, category))가 깨지면 안 된다."""
        assert isinstance(lint_cta({"text": "① A ② B", "voice": "댓글로 알려주세요."},
                                   "political"), list)


class TestLintCtaClosingStyles:
    def test_pick_requires_exact_phrase(self):
        assert lint_cta_closing("1번 조국, 2번 이준석. 번호로 답글.")
        assert lint_cta_closing("1번 조국, 2번 이준석. 댓글로 알려주세요.") == []

    def test_subscribe_accepts_any_polite_closing(self):
        assert lint_cta_closing("댓글로 남겨주세요.", CTA_STYLE_SUBSCRIBE) == []
        assert lint_cta_closing("구독 부탁드립니다.", CTA_STYLE_SUBSCRIBE) == []
        assert lint_cta_closing("구독 필수.", CTA_STYLE_SUBSCRIBE)


class TestSceneCtaDetection:
    def test_pick_style_detects_choice_markers(self):
        """대조군 — 씬에 직접 쓴 선택지형 CTA 검사는 그대로."""
        cfg = {"scenes": [{"text": "① 그때가 맞다 ② 지금이 맞다", "voice": "번호로 답글."}]}
        assert scene_cta_closing_warnings(cfg)

    def test_subscribe_style_detects_subscribe_scene(self):
        """구독형 CTA 씬에는 ①/1번이 없어 기존 탐지기가 통째로 놓친다."""
        cfg = {
            "format": "profile_v3",
            "scenes": [{"text": "더 궁금하다면?\n댓글 + 구독", "voice": "댓글 남겨."}],
        }
        assert scene_cta_closing_warnings(cfg)

    def test_subscribe_style_polite_scene_passes(self):
        cfg = {
            "format": "profile_v3",
            "scenes": [{"text": "더 궁금하다면?\n댓글 + 구독",
                        "voice": "궁금한 점은 댓글로 남겨주세요."}],
        }
        assert scene_cta_closing_warnings(cfg) == []

    def test_ordinary_scene_not_flagged(self):
        cfg = {"format": "profile_v3",
               "scenes": [{"text": "구글 엔지니어 출신", "voice": "그는 구글에서 일했습니다."}]}
        assert scene_cta_closing_warnings(cfg) == []
