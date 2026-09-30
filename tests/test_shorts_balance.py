"""편성 비중 추적 (scripts/shorts_balance.py) 테스트 — 040.

실측 배경: 133편 중 political 88편(66%, 중앙 1,200) / society 8편(1,912) /
인물 논란 23편(2,200) / economic 14편(1,150). 중앙값이 높은 카테고리가 편성의
6~17% 뿐이라 채널 중앙값이 정치에 끌려간다.
"""
from __future__ import annotations

import json

from scripts.shorts_balance import (
    GATE_KEY,
    GATE_OFF,
    MIN_SAMPLE,
    TARGET_MIX,
    TOLERANCE,
    WINDOW,
    balance_warnings,
    load_recent_categories,
    mix_of,
    mix_report_lines,
    over_target,
    under_target,
)


def write_ledger(path, rows: list[tuple[str, str, str]]) -> None:
    """rows = [(제목, category, recorded_at), ...]"""
    path.write_text(json.dumps({
        "version": 1,
        "entries": {
            title: {"category": cat, "slug": "", "recorded_at": at}
            for title, cat, at in rows
        },
    }, ensure_ascii=False), encoding="utf-8")


class TestTargets:
    def test_target_mix_sums_to_one(self):
        assert abs(sum(TARGET_MIX.values()) - 1.0) < 1e-9

    def test_political_target_is_forty_percent(self):
        assert TARGET_MIX["political"] == 0.40


class TestMixOf:
    def test_empty_is_empty(self):
        assert mix_of(()) == {}

    def test_shares_are_fractions(self):
        mix = mix_of(("political", "political", "society", "economic"))
        assert mix["political"] == 0.5
        assert mix["society"] == 0.25

    def test_unknown_categories_are_counted(self):
        mix = mix_of(("political", "unknown"))
        assert mix["unknown"] == 0.5


class TestLoadRecent:
    def test_returns_newest_first(self, tmp_path):
        p = tmp_path / "ledger.json"
        write_ledger(p, [
            ("옛날편", "political", "2026-08-01 10:00"),
            ("최신편", "society", "2026-09-03 17:00"),
            ("중간편", "economic", "2026-08-20 09:00"),
        ])
        assert load_recent_categories(p) == ("society", "economic", "political")

    def test_window_truncates(self, tmp_path):
        p = tmp_path / "ledger.json"
        write_ledger(p, [
            (f"편{i}", "political", f"2026-08-{i:02d} 10:00") for i in range(1, 12)
        ])
        assert len(load_recent_categories(p, window=5)) == 5

    def test_missing_file_is_empty(self, tmp_path):
        assert load_recent_categories(tmp_path / "nope.json") == ()

    def test_corrupt_file_is_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{{{", encoding="utf-8")
        assert load_recent_categories(p) == ()


class TestOverUnder:
    def test_over_target_detects_excess(self):
        mix = {"political": 0.70, "society": 0.30}
        assert "political" in over_target(mix)

    def test_within_tolerance_is_not_over(self):
        mix = {"political": TARGET_MIX["political"] + TOLERANCE / 2}
        assert "political" not in over_target(mix)

    def test_under_target_lists_shortfalls(self):
        mix = {"political": 0.90, "society": 0.10}
        assert "entertainment" in under_target(mix)


class TestBalanceWarnings:
    def _ledger(self, tmp_path, political: int, others: int):
        p = tmp_path / "ledger.json"
        rows = [(f"정치{i}", "political", f"2026-09-{i % 28 + 1:02d} 10:00")
                for i in range(political)]
        rows += [(f"사회{i}", "society", f"2026-08-{i % 28 + 1:02d} 10:00")
                 for i in range(others)]
        write_ledger(p, rows)
        return p

    def test_warns_when_current_category_is_over_target(self, tmp_path):
        p = self._ledger(tmp_path, political=18, others=2)
        ws = balance_warnings({"category": "political"}, ledger_path=p)
        assert any("편성 비중" in w for w in ws)
        assert all(w.startswith("[040]") for w in ws)

    def test_silent_when_current_category_is_under_target(self, tmp_path):
        p = self._ledger(tmp_path, political=18, others=2)
        assert balance_warnings({"category": "society"}, ledger_path=p) == []

    def test_silent_below_min_sample(self, tmp_path):
        p = self._ledger(tmp_path, political=MIN_SAMPLE - 1, others=0)
        assert balance_warnings({"category": "political"}, ledger_path=p) == []

    def test_gate_off_silences(self, tmp_path):
        p = self._ledger(tmp_path, political=18, others=2)
        cfg = {"category": "political", GATE_KEY: GATE_OFF}
        assert balance_warnings(cfg, ledger_path=p) == []

    def test_missing_ledger_is_silent(self, tmp_path):
        assert balance_warnings({"category": "political"},
                                ledger_path=tmp_path / "nope.json") == []

    def test_warning_names_an_under_target_alternative(self, tmp_path):
        p = self._ledger(tmp_path, political=18, others=2)
        ws = balance_warnings({"category": "political"}, ledger_path=p)
        assert any("entertainment" in w or "연예" in w for w in ws)


class TestReportLines:
    def test_lines_cover_every_target_category(self):
        lines = mix_report_lines(("political",) * 10 + ("society",) * 10)
        joined = "\n".join(lines)
        for cat in TARGET_MIX:
            assert cat in joined

    def test_window_default_is_twenty(self):
        assert WINDOW == 20
