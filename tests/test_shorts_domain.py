"""도메인 규칙 팩 (scripts/shorts_domain.py) 테스트 — 036 Phase 1/2."""
from __future__ import annotations

import pytest

from scripts.shorts_domain import (
    DOMAIN_RULES,
    collect_config_text,
    domain_warnings,
    gate_domain_words,
    rules_for,
    rules_for_config,
)
from scripts.shorts_category import CATEGORIES


class TestRulesLookup:
    def test_every_category_has_rules(self):
        assert set(DOMAIN_RULES) == set(CATEGORIES)

    def test_rules_are_immutable(self):
        with pytest.raises(Exception):
            rules_for("political").outcome_words = ()

    def test_default_config_is_political(self):
        assert rules_for_config({}).category == "political"

    def test_config_category_respected(self):
        assert rules_for_config({"category": "economic"}).category == "economic"

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="category"):
            rules_for("sports")

    def test_emotion_types_are_valid(self):
        valid = {"funny", "touching", "angry", "relatable"}
        assert all(r.emotion_type in valid for r in DOMAIN_RULES.values())

    def test_bg_colors_are_hex_triples(self):
        for r in DOMAIN_RULES.values():
            assert len(r.bg_colors) == 3
            assert all(c.startswith("#") for c in r.bg_colors)


class TestPoliticalRegression:
    """category 미지정 = 기존 정치쇼츠 동작 — 035까지의 상수와 동일해야 한다."""

    def test_outcome_words_preserved(self):
        from scripts.political_upload_package import _OUTCOME_WORDS
        assert rules_for("political").outcome_words == _OUTCOME_WORDS

    def test_clash_words_preserved(self):
        from scripts.political_upload_package import _CLASH_WORDS
        assert rules_for("political").clash_words == _CLASH_WORDS

    def test_pinned_comment_preserved(self):
        from scripts.political_upload_package import DEFAULT_PINNED_COMMENT
        assert rules_for("political").default_pinned_comment == DEFAULT_PINNED_COMMENT

    def test_political_has_no_banned_words(self):
        assert rules_for("political").banned_words == ()


class TestDomainOutcomeWords:
    def test_economic_outcome(self):
        assert "동결" in rules_for("economic").outcome_words
        assert "급락" in rules_for("economic").outcome_words

    def test_society_outcome(self):
        assert "무죄" in rules_for("society").outcome_words

    def test_entertainment_outcome(self):
        assert "하차" in rules_for("entertainment").outcome_words

    def test_no_category_shares_all_words_with_political(self):
        pol = set(rules_for("political").outcome_words)
        for cat in ("economic", "society", "entertainment"):
            assert set(rules_for(cat).outcome_words) - pol


class TestCollectConfigText:
    def test_gathers_title_scenes_and_cta(self):
        cfg = {
            "yt_title": "제목",
            "scenes": [{"text": "자막", "voice": "나레이션"}],
            "cta": {"text": "씨티에이", "voice": "씨티에이보이스"},
        }
        text = collect_config_text(cfg)
        for piece in ("제목", "자막", "나레이션", "씨티에이", "씨티에이보이스"):
            assert piece in text

    def test_handles_missing_keys(self):
        assert collect_config_text({}) == ""


class TestGateDomainWords:
    def test_economic_investment_advice_blocked(self):
        cfg = {"category": "economic",
               "scenes": [{"voice": "지금이 매수 타이밍입니다"}]}
        with pytest.raises(ValueError, match="투자"):
            gate_domain_words(cfg)

    def test_economic_clean_narration_passes(self):
        cfg = {"category": "economic",
               "scenes": [{"voice": "기준금리는 결국 동결됐습니다"}]}
        gate_domain_words(cfg)

    def test_political_unaffected_by_economic_banned_words(self):
        # 정치 편에서 '매수'(표 매수 등)는 차단 대상이 아니다
        cfg = {"scenes": [{"voice": "표 매수 의혹이 제기됐습니다"}]}
        gate_domain_words(cfg)

    def test_bypass_key(self):
        cfg = {"category": "economic", "domain_gate": "off",
               "scenes": [{"voice": "지금 매수하세요"}]}
        gate_domain_words(cfg)

    def test_error_names_the_word(self):
        cfg = {"category": "economic", "scenes": [{"voice": "존버가 답입니다"}]}
        with pytest.raises(ValueError, match="존버"):
            gate_domain_words(cfg)


class TestDomainWarnings:
    def test_society_suspect_naming_warned(self):
        cfg = {"category": "society",
               "scenes": [{"voice": "피의자는 범행을 부인했습니다"}]}
        assert any("피의자" in w for w in domain_warnings(cfg))

    def test_entertainment_unconfirmed_private_life_warned(self):
        cfg = {"category": "entertainment",
               "yt_title": "결국 인정한 열애설", "source_channel": "채널",
               "scenes": [{"voice": "이혼설이 돌고 있습니다"}]}
        assert any("이혼설" in w for w in domain_warnings(cfg))

    def test_entertainment_requires_source_channel(self):
        cfg = {"category": "entertainment", "scenes": [{"voice": "복귀했습니다"}]}
        assert any("출처" in w for w in domain_warnings(cfg))

    def test_entertainment_with_source_channel_no_source_warning(self):
        cfg = {"category": "entertainment", "source_channel": "SBS",
               "scenes": [{"voice": "복귀했습니다"}]}
        assert not any("출처" in w for w in domain_warnings(cfg))

    def test_political_clean_config_has_no_warnings(self):
        cfg = {"scenes": [{"voice": "표결은 결국 부결됐습니다"}]}
        assert domain_warnings(cfg) == []

    def test_bypass_key_silences_warnings(self):
        cfg = {"category": "society", "domain_gate": "off",
               "scenes": [{"voice": "피의자는 범행을 부인했습니다"}]}
        assert domain_warnings(cfg) == []
