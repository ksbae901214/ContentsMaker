"""업로드 패키지의 카테고리 표기·원장 기록 (036 Phase 0) 테스트."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from scripts.political_upload_package import (
    build_upload_package_md, generate_upload_package,
)
from scripts.shorts_category import load_ledger

MONDAY = datetime(2026, 8, 17, 9, 0)


def _cfg(**over) -> dict:
    return {"slug": "t", "title": "배너", "yt_title": "결국 동결된 금리",
            "persons": ["이창용"], **over}


class TestCategoryInMarkdown:
    def test_default_category_is_political(self):
        md = build_upload_package_md(_cfg(), Path("out.mp4"), MONDAY)
        assert "political" in md

    def test_explicit_category_shown(self):
        md = build_upload_package_md(
            _cfg(category="economic"), Path("out.mp4"), MONDAY)
        assert "economic" in md

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="category"):
            build_upload_package_md(
                _cfg(category="sports"), Path("out.mp4"), MONDAY)


class TestLedgerRecording:
    def test_records_title_and_category(self, tmp_path):
        ledger = tmp_path / "category_ledger.json"
        generate_upload_package(
            _cfg(category="economic"), video_path=tmp_path / "missing.mp4",
            out_dir=tmp_path, ledger_path=ledger)
        assert load_ledger(ledger) == {"결국 동결된 금리": "economic"}

    def test_records_default_political_when_unset(self, tmp_path):
        ledger = tmp_path / "category_ledger.json"
        generate_upload_package(
            _cfg(), video_path=tmp_path / "missing.mp4",
            out_dir=tmp_path, ledger_path=ledger)
        assert load_ledger(ledger) == {"결국 동결된 금리": "political"}

    def test_strips_hashtags_from_key(self, tmp_path):
        ledger = tmp_path / "category_ledger.json"
        generate_upload_package(
            _cfg(yt_title="결국 동결된 금리 #금리 #한국은행", category="economic"),
            video_path=tmp_path / "missing.mp4", out_dir=tmp_path,
            ledger_path=ledger)
        assert load_ledger(ledger) == {"결국 동결된 금리": "economic"}

    def test_package_file_still_written(self, tmp_path):
        pkg = generate_upload_package(
            _cfg(category="economic"), video_path=tmp_path / "missing.mp4",
            out_dir=tmp_path, ledger_path=tmp_path / "l.json")
        assert pkg.exists()
        assert "economic" in pkg.read_text(encoding="utf-8")
