"""도메인 규칙이 업로드 패키지·CTA·렌더러에 관통되는지 — 036 Phase 1/2.

핵심 회귀 조건: **category 미지정 = 기존 정치쇼츠 동작과 동일**.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from scripts.political_cta import lint_cta
from scripts.political_upload_package import (
    build_upload_package_md, has_outcome_frame, is_clash_frame,
    lint_topic_frame, lint_yt_title, resolve_pinned_comment,
)
from scripts.shorts_domain import rules_for

MONDAY = datetime(2026, 8, 17, 9, 0)


class TestOutcomeFrameByCategory:
    def test_political_default_unchanged(self):
        assert has_outcome_frame("끝내 부결된 특검법")
        assert has_outcome_frame("끝내 부결된 특검법", "political")

    def test_economic_outcome_recognized(self):
        # '동결'은 정치 결과어에 없고 경제 결과어에만 있다
        assert not has_outcome_frame("결과적으로 동결된 기준금리", "political")
        assert has_outcome_frame("동결된 기준금리", "economic")

    def test_entertainment_outcome_recognized(self):
        assert has_outcome_frame("결국 하차한 주연배우", "entertainment")

    def test_clash_frame_shared_signal(self):
        assert is_clash_frame("금리 두고 정면충돌", "economic")

    def test_topic_frame_warning_uses_domain_examples(self):
        warns = lint_topic_frame("금리 두고 정면충돌", "economic")
        assert len(warns) == 1
        assert "동결" in warns[0]        # 경제 예시가 안내돼야 한다

    def test_topic_frame_silent_when_outcome_present(self):
        assert lint_topic_frame("정면충돌 끝에 동결된 금리", "economic") == []


class TestPinnedCommentByCategory:
    def test_political_default_unchanged(self):
        from scripts.political_upload_package import DEFAULT_PINNED_COMMENT
        assert resolve_pinned_comment({}) == DEFAULT_PINNED_COMMENT

    def test_economic_default(self):
        assert resolve_pinned_comment({"category": "economic"}) == \
            rules_for("economic").default_pinned_comment

    def test_explicit_value_still_wins(self):
        cfg = {"category": "economic", "pinned_comment": "직접 지정"}
        assert resolve_pinned_comment(cfg) == "직접 지정"

    def test_cta_voice_beats_domain_default(self):
        cfg = {"category": "economic", "cta": {"voice": "1번 2번 골라주세요"}}
        assert resolve_pinned_comment(cfg) == "1번 2번 골라주세요"


class TestTitleAnchorByCategory:
    def test_political_requires_person_name(self):
        warns = lint_yt_title("끝내 부결된 그 법안", ["장동혁"])
        assert any("실명" in w for w in warns)

    def test_economic_anchor_label_differs(self):
        warns = lint_yt_title("결국 동결된 그것", ["한국은행"], category="economic")
        anchor = [w for w in warns if "미포함" in w]
        assert anchor and "실명" not in anchor[0]

    def test_no_anchor_warning_when_present(self):
        warns = lint_yt_title("한국은행이 결국 동결", ["한국은행"], category="economic")
        assert not any("미포함" in w for w in warns)


class TestCtaByCategory:
    def test_political_open_question_warned(self):
        assert any("선택지형" in w for w in lint_cta({"text": "어떻게 보세요?",
                                                    "voice": "의견 주세요"}))

    def test_economic_example_in_warning(self):
        warns = lint_cta({"text": "어떻게 보세요?", "voice": "의견 주세요"},
                         category="economic")
        assert any(rules_for("economic").cta_example in w for w in warns)

    def test_side_picking_passes_in_any_category(self):
        cta = {"text": "① 오른다 ② 내린다", "voice": "1번 2번 골라주세요"}
        assert not any("선택지형" in w for w in lint_cta(cta, category="economic"))


class TestUploadPackageByCategory:
    def _cfg(self, **over):
        return {"slug": "t", "title": "배너", "yt_title": "결국 동결된 금리",
                "persons": ["한국은행"], **over}

    def test_domain_checklist_rendered(self, tmp_path):
        md = build_upload_package_md(
            self._cfg(category="economic"), Path("out.mp4"), MONDAY)
        assert rules_for("economic").checklist[0] in md

    def test_political_checklist_unchanged(self):
        md = build_upload_package_md(self._cfg(), Path("out.mp4"), MONDAY)
        assert "썸네일 = 인물 표정 절정 컷인가" in md

    def test_entertainment_copyright_checklist(self):
        md = build_upload_package_md(
            self._cfg(category="entertainment", yt_title="결국 하차한 주연"),
            Path("out.mp4"), MONDAY)
        assert any("저작권" in line for line in md.splitlines())


class TestRendererDomainDefaults:
    def test_political_defaults_unchanged(self):
        from scripts.shorts_domain import resolve_bg_colors, resolve_emotion_type
        assert resolve_emotion_type({}) == "angry"
        assert resolve_bg_colors({}) == ("#7f1d1d", "#450a0a", "#000000")

    def test_economic_defaults_differ(self):
        from scripts.shorts_domain import resolve_bg_colors, resolve_emotion_type
        assert resolve_emotion_type({"category": "economic"}) == "relatable"
        assert resolve_bg_colors({"category": "economic"}) != \
            ("#7f1d1d", "#450a0a", "#000000")

    def test_explicit_config_wins(self):
        from scripts.shorts_domain import resolve_bg_colors, resolve_emotion_type
        cfg = {"category": "economic", "emotion_type": "angry",
               "bg_colors": ["#111111", "#222222", "#333333"]}
        assert resolve_emotion_type(cfg) == "angry"
        assert resolve_bg_colors(cfg) == ("#111111", "#222222", "#333333")


class TestValidateBlocksInvestmentAdvice:
    def test_v2_2_validate_raises(self):
        from scripts.render_political_v2_2 import validate_config
        cfg = {
            "slug": "s", "title": "t", "category": "economic",
            "sources": {"a": {"query": "q"}},
            "scenes": [
                {"mode": "clip", "source": "a", "duration": 3.0, "text": "훅"},
                {"mode": "tts", "source": "a", "voice": "지금 매수하세요"},
            ],
        }
        with pytest.raises(ValueError, match="투자"):
            validate_config(cfg)
