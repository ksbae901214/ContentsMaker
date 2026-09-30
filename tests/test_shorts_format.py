"""포맷 원장·규칙 팩 (scripts/shorts_format.py) 테스트 — 041 Phase A1."""
from __future__ import annotations

import json

import pytest

from scripts.shorts_category import load_ledger, record_category
from scripts.shorts_format import (
    DEFAULT_FORMAT,
    FORMATS,
    NEWS_V4,
    PROFILE_V3,
    UNKNOWN_FORMAT,
    V2_1,
    V2_2,
    load_formats,
    record_format,
    resolve_config_format,
    resolve_format,
    rules_for_config,
    rules_for_format,
)


class TestResolveConfigFormat:
    def test_missing_key_falls_back_to_v2_1(self):
        """기존 config 107개는 format 키가 없다 — 동작이 바뀌면 안 된다."""
        assert resolve_config_format({"slug": "x"}) == DEFAULT_FORMAT
        assert DEFAULT_FORMAT == V2_1

    def test_empty_string_falls_back(self):
        assert resolve_config_format({"format": ""}) == V2_1

    @pytest.mark.parametrize("fmt", FORMATS)
    def test_explicit_values(self, fmt):
        assert resolve_config_format({"format": fmt}) == fmt

    def test_typo_raises(self):
        with pytest.raises(ValueError, match="profile_v3"):
            resolve_config_format({"format": "profile_v3.0"})


class TestFormatRules:
    def test_profile_v3_opts_out_of_symmetry(self):
        """인물 1명 포맷이라 040 진영 대칭이 개념상 성립하지 않는다."""
        assert rules_for_format(PROFILE_V3).symmetry_applies is False

    @pytest.mark.parametrize("fmt", [V2_1, V2_2])
    def test_v2_keeps_symmetry(self, fmt):
        assert rules_for_format(fmt).symmetry_applies is True

    def test_profile_v3_defaults_to_subscribe_cta(self):
        assert rules_for_format(PROFILE_V3).default_cta_style == "subscribe"

    def test_v2_defaults_to_pick_cta(self):
        assert rules_for_format(V2_1).default_cta_style == "pick"

    def test_profile_v3_headline_font(self):
        """037 규격(Noto)은 V2 전용 — V3.0만 궁서체."""
        assert rules_for_format(PROFILE_V3).headline_font == "GungSeo"
        assert rules_for_format(V2_1).headline_font == ""

    def test_profile_v3_breakout_notice_only(self):
        assert rules_for_format(PROFILE_V3).breakout_notice_only is True
        assert rules_for_format(V2_1).breakout_notice_only is False

    def test_rules_for_config_uses_default(self):
        assert rules_for_config({}).format == V2_1

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError):
            rules_for_format("v9")

    def test_news_v4_registered(self):
        assert NEWS_V4 in FORMATS
        assert resolve_config_format({"format": "news_v4"}) == NEWS_V4

    def test_news_v4_rules(self):
        """정치 1편 안의 대칭이 벤치마크 구조 — 040 적용, 039 개별 경고 유지."""
        rules = rules_for_format(NEWS_V4)
        assert rules.symmetry_applies is True
        assert rules.breakout_notice_only is False
        assert rules.default_cta_style == "pick"
        assert rules.intro_required is False
        assert rules.headline_font == "BM Dohyeon"

    def test_every_format_has_checklist(self):
        for fmt in FORMATS:
            assert rules_for_format(fmt).checklist


class TestLedger:
    def test_record_and_load(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        record_format(path, "이해민은 누구인가", PROFILE_V3, slug="leehm")
        assert load_formats(path) == {"이해민은 누구인가": PROFILE_V3}

    def test_record_format_preserves_category(self, tmp_path):
        """포맷 기록이 카테고리를 지우면 036 리포트가 조용히 망가진다."""
        path = tmp_path / "category_ledger.json"
        record_category(path, "이해민은 누구인가", "political", slug="leehm")
        record_format(path, "이해민은 누구인가", PROFILE_V3, slug="leehm")
        assert load_ledger(path) == {"이해민은 누구인가": "political"}
        assert load_formats(path) == {"이해민은 누구인가": PROFILE_V3}

    def test_record_category_preserves_format(self, tmp_path):
        """반대 순서로 기록해도 양쪽이 남아야 한다 (엔트리 병합 회귀)."""
        path = tmp_path / "category_ledger.json"
        record_format(path, "이해민은 누구인가", PROFILE_V3)
        record_category(path, "이해민은 누구인가", "political")
        assert load_formats(path) == {"이해민은 누구인가": PROFILE_V3}
        assert load_ledger(path) == {"이해민은 누구인가": "political"}

    def test_hashtags_stripped_from_key(self, tmp_path):
        path = tmp_path / "l.json"
        record_format(path, "이해민은 누구인가 #이해민 #프로필", PROFILE_V3)
        assert load_formats(path) == {"이해민은 누구인가": PROFILE_V3}

    def test_empty_title_not_recorded(self, tmp_path):
        path = tmp_path / "l.json"
        record_format(path, "   ", PROFILE_V3)
        assert load_formats(path) == {}

    def test_invalid_format_raises(self, tmp_path):
        with pytest.raises(ValueError):
            record_format(tmp_path / "l.json", "제목", "nope")

    def test_broken_file_is_not_fatal(self, tmp_path):
        path = tmp_path / "l.json"
        path.write_text("{ broken", encoding="utf-8")
        assert load_formats(path) == {}

    def test_missing_file(self, tmp_path):
        assert load_formats(tmp_path / "none.json") == {}

    def test_ledger_file_stays_valid_json(self, tmp_path):
        path = tmp_path / "l.json"
        record_format(path, "제목", PROFILE_V3, slug="s")
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["entries"]["제목"]["format"] == PROFILE_V3
        assert raw["entries"]["제목"]["slug"] == "s"


class TestResolveFormat:
    def test_exact_match(self):
        assert resolve_format("제목", {"제목": PROFILE_V3}) == PROFILE_V3

    def test_prefix_match_absorbs_trailing_hashtags(self):
        """업로드 시 제목 뒤에 해시태그가 붙는다 (036 접두 일치와 같은 이유)."""
        ledger = {"이해민은 누구인가": PROFILE_V3}
        assert resolve_format("이해민은 누구인가 — 구글 출신?", ledger) == PROFILE_V3

    def test_absent_is_unknown(self):
        """과거 107편은 포맷 기록이 없다 — 추론하지 않고 unknown 으로 둔다."""
        assert resolve_format("옛날 편", {}) == UNKNOWN_FORMAT

    def test_empty_title(self):
        assert resolve_format("", {"제목": PROFILE_V3}) == UNKNOWN_FORMAT
