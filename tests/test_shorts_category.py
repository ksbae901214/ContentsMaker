"""카테고리 원장·추론 (scripts/shorts_category.py) 테스트 — 036 Phase 0."""
from __future__ import annotations

import json
import unicodedata

import pytest

from scripts.shorts_category import (
    CATEGORIES,
    DEFAULT_CATEGORY,
    UNKNOWN,
    classify_category,
    ledger_key,
    load_ledger,
    record_category,
    resolve_category,
    resolve_config_category,
)


class TestLedgerKey:
    def test_strips_hashtags(self):
        assert ledger_key("결국 동결된 금리 #금리 #한국은행") == "결국 동결된 금리"

    def test_collapses_whitespace(self):
        assert ledger_key("결국   동결된  금리") == "결국 동결된 금리"

    def test_nfc_normalized(self):
        nfd = unicodedata.normalize("NFD", "결국 동결된 금리")
        assert ledger_key(nfd) == "결국 동결된 금리"

    def test_empty(self):
        assert ledger_key("") == ""


class TestClassifyCategory:
    def test_political(self):
        assert classify_category("법사위 표결 끝내 부결된 특검법") == "political"

    def test_economic(self):
        assert classify_category("결국 동결된 금리, 전세 대출 어떻게 되나") == "economic"

    def test_society(self):
        assert classify_category("3년 재판 끝 무죄, 음주운전 판결 뒤집혔다") == "society"

    def test_entertainment(self):
        assert classify_category("9년 만에 컴백한 아이돌, 소속사가 인정한 열애") == "entertainment"

    def test_unknown_when_no_keyword(self):
        assert classify_category("그냥 아무 말") == UNKNOWN

    def test_empty_is_unknown(self):
        assert classify_category("") == UNKNOWN

    def test_hashtags_count_as_topic_signal(self):
        # 해시태그는 주제를 가장 직접적으로 말해주므로 분류에 포함한다
        # (제목 문체 분류 classify_title 이 해시태그를 벗기는 것과 목적이 다름)
        assert classify_category("결국 뒤집혔다 #종부세 #부동산 #대출") == "economic"

    def test_english_title_political(self):
        assert classify_category(
            "Lawmakers Vote Against Constitutional Amendment") == "political"

    def test_english_title_economic(self):
        assert classify_category(
            "The day the Korean stock market crashed #StockMarketCrash") == "economic"

    def test_english_case_insensitive(self):
        assert classify_category("REAL ESTATE DEBATE ERUPTS") == "economic"

    def test_higher_score_wins(self):
        # 경제 신호 3개 vs 정치 신호 1개
        t = "국회 앞 금리 물가 환율 삼중고"
        assert classify_category(t) == "economic"

    def test_tie_breaks_to_political(self):
        # 정치 1 : 사회 1 동점 → 채널 기본축(정치) 우선
        assert classify_category("국회 앞 경찰") == "political"

    def test_all_results_are_known_labels(self):
        for title in ("금리", "국회", "재판", "아이돌", "무의미"):
            assert classify_category(title) in (*CATEGORIES, UNKNOWN)


class TestResolveCategory:
    def test_ledger_wins_over_keywords(self):
        ledger = {ledger_key("끝내 부결된 특검법"): "economic"}
        assert resolve_category("끝내 부결된 특검법", ledger) == "economic"

    def test_falls_back_to_keywords(self):
        assert resolve_category("끝내 부결된 특검법", {}) == "political"

    def test_matches_when_upload_title_has_extra_hashtags(self):
        # config yt_title 은 해시태그 없음, 실제 업로드 제목엔 붙는다
        ledger = {ledger_key("결국 동결된 금리"): "economic"}
        assert resolve_category("결국 동결된 금리 #금리 #한국은행 #대출", ledger) == "economic"

    def test_matches_when_upload_title_has_suffix(self):
        ledger = {ledger_key("결국 동결된 금리"): "economic"}
        assert resolve_category("결국 동결된 금리, 영끌족 한숨", ledger) == "economic"

    def test_unknown_when_nothing_matches(self):
        assert resolve_category("그냥 아무 말", {}) == UNKNOWN

    def test_hashtag_only_title_still_inferred(self):
        # 원장 키는 비지만(해시태그를 떼면 남는 게 없음) 추론은 계속돼야 한다
        assert resolve_category("#종부세 #부동산 #대출", {}) == "economic"

    def test_empty_title(self):
        assert resolve_category("", {"": "economic"}) == UNKNOWN


class TestRecordCategory:
    def test_writes_and_reads_back(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        record_category(path, "결국 동결된 금리", "economic", slug="geumni_v2_2")
        assert load_ledger(path) == {"결국 동결된 금리": "economic"}

    def test_appends_without_dropping_existing(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        record_category(path, "A 제목", "economic")
        record_category(path, "B 제목", "society")
        assert load_ledger(path) == {"A 제목": "economic", "B 제목": "society"}

    def test_returns_new_mapping_without_mutating_input(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        record_category(path, "A 제목", "economic")
        before = load_ledger(path)
        after = record_category(path, "B 제목", "society")
        assert before == {"A 제목": "economic"}       # 원본 dict 불변
        assert after == {"A 제목": "economic", "B 제목": "society"}

    def test_rerecord_overwrites_category(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        record_category(path, "A 제목", "economic")
        record_category(path, "A 제목", "political")
        assert load_ledger(path) == {"A 제목": "political"}

    def test_stores_metadata(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        record_category(path, "A 제목", "economic", slug="my_slug")
        raw = json.loads(path.read_text(encoding="utf-8"))
        entry = raw["entries"]["A 제목"]
        assert entry["category"] == "economic"
        assert entry["slug"] == "my_slug"
        assert entry["recorded_at"]

    def test_rejects_unknown_category(self, tmp_path):
        with pytest.raises(ValueError, match="category"):
            record_category(tmp_path / "l.json", "A", "sports")

    def test_ignores_blank_title(self, tmp_path):
        path = tmp_path / "category_ledger.json"
        assert record_category(path, "   ", "economic") == {}
        assert not path.exists()


class TestLoadLedger:
    def test_missing_file_returns_empty(self, tmp_path):
        assert load_ledger(tmp_path / "nope.json") == {}

    def test_corrupt_file_returns_empty(self, tmp_path):
        path = tmp_path / "l.json"
        path.write_text("{not json", encoding="utf-8")
        assert load_ledger(path) == {}

    def test_skips_entries_with_invalid_category(self, tmp_path):
        path = tmp_path / "l.json"
        path.write_text(json.dumps({"entries": {
            "A": {"category": "economic"},
            "B": {"category": "sports"},
        }}, ensure_ascii=False), encoding="utf-8")
        assert load_ledger(path) == {"A": "economic"}


class TestResolveConfigCategory:
    def test_default_is_political(self):
        assert resolve_config_category({}) == DEFAULT_CATEGORY == "political"

    def test_reads_config_value(self):
        assert resolve_config_category({"category": "economic"}) == "economic"

    def test_rejects_unknown_value(self):
        with pytest.raises(ValueError, match="category"):
            resolve_config_category({"category": "sports"})
