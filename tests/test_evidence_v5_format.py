"""V5.0 증거 삽입형 TTS 논평 — 포맷 규칙·길이 캡·업로드 패키지 고지 (043 Phase A)."""
from __future__ import annotations

import pytest

from scripts.political_length import (
    OUTRO_SEC, TARGET_MAX_SEC, enforce_length, length_warnings, max_final_sec,
)
from scripts.shorts_format import (
    EVIDENCE_V5, FORMATS, PROFILE_V3, V2_1, V2_2, resolve_config_format,
    rules_for_format,
)


def _v5(**over) -> dict:
    cfg = {
        "format": EVIDENCE_V5,
        "slug": "t_v5",
        "title": "배너",
        "sources": {"a": {"query": "q"}},
        "scenes": [{"mode": "tts", "source": "a", "text": "t", "voice": "가" * 74}],
    }
    cfg.update(over)
    return cfg


class TestFormatRules:
    def test_registered(self):
        assert EVIDENCE_V5 == "evidence_v5"
        assert EVIDENCE_V5 in FORMATS
        assert resolve_config_format({"format": "evidence_v5"}) == EVIDENCE_V5

    def test_symmetry_silenced_attack_allowed(self):
        # 사용자 확정 2026-10-01 — 한쪽 진영 공격 허용
        assert rules_for_format(EVIDENCE_V5).symmetry_applies is False

    def test_cta_follows_channel_rule(self):
        # 사용자 확정 — CTA 는 우리 지침(선택지형 + 질문 + 댓글로 알려주세요)
        assert rules_for_format(EVIDENCE_V5).default_cta_style == "pick"

    def test_breakout_warnings_kept(self):
        assert rules_for_format(EVIDENCE_V5).breakout_notice_only is False

    def test_no_intro_line(self):
        # 훅이 즉시 시작하는 포맷 — 상위 10편 전부 인트로 없음
        assert rules_for_format(EVIDENCE_V5).intro_required is False

    def test_length_cap_raised_only_for_v5(self):
        assert rules_for_format(EVIDENCE_V5).max_final_sec == 70.0
        for fmt in (V2_1, V2_2, PROFILE_V3):
            assert rules_for_format(fmt).max_final_sec == 0.0

    def test_symmetry_off_note_present(self):
        assert "진영" in rules_for_format(EVIDENCE_V5).symmetry_off_note
        assert rules_for_format(V2_1).symmetry_off_note == ""

    def test_checklist_mentions_evidence_and_sources(self):
        joined = " ".join(rules_for_format(EVIDENCE_V5).checklist)
        assert "증거" in joined
        assert "fact_sources" in joined


class TestFormatAwareLength:
    def test_default_cap_unchanged(self):
        assert max_final_sec({}) == TARGET_MAX_SEC
        assert max_final_sec({"format": "v2_2"}) == TARGET_MAX_SEC

    def test_v5_cap(self):
        assert max_final_sec(_v5()) == 70.0

    def test_unknown_format_falls_back(self):
        assert max_final_sec({"format": "nope"}) == TARGET_MAX_SEC

    def test_v5_allows_66s(self):
        enforce_length(66.0 - OUTRO_SEC, _v5())

    def test_v2_still_blocks_66s(self):
        with pytest.raises(ValueError, match="캡"):
            enforce_length(66.0 - OUTRO_SEC, {"format": "v2_2"})

    def test_v5_blocks_over_70(self):
        with pytest.raises(ValueError, match="70"):
            enforce_length(71.0 - OUTRO_SEC, _v5())

    def test_warning_uses_v5_cap(self):
        # 74자 × 6씬 @1.1배속 ≈ 54.5s + 아웃트로 4s ≈ 58.5s — V2 캡(62)·V5 캡(70) 모두 통과
        assert length_warnings(_v5(scenes=[
            {"mode": "tts", "source": "a", "text": "t", "voice": "가" * 74}] * 6)) == []
        # ≈ 72.7s + 4 → V5 캡 초과 경고
        warns = length_warnings(_v5(scenes=[
            {"mode": "tts", "source": "a", "text": "t", "voice": "가" * 74}] * 8))
        assert warns and "70" in warns[0]


def _md(cfg: dict) -> str:
    from datetime import datetime
    from pathlib import Path

    from scripts.political_upload_package import build_upload_package_md
    return build_upload_package_md(cfg, Path("x.mp4"), datetime(2026, 10, 1, 18, 0))


class TestUploadPackageNote:
    def test_v5_note_replaces_profile_note(self):
        md = _md(_v5(yt_title="배너 제목"))
        assert "한쪽 진영" in md
        assert "인물 1명을 다루고" not in md

    def test_profile_note_unchanged(self):
        md = _md({**_v5(yt_title="배너 제목"), "format": PROFILE_V3})
        assert ("진영 대칭·선택지형 CTA 항목은 이 포맷에 적용되지 않는다** — "
                "인물 1명을 다루고 CTA 는 구독 유도형이다") in md
