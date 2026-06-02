"""T018: 8개 frozen dataclass 모델 단위 테스트."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from src.dem_shorts.models import (
    BiasReport,
    ComplianceGateResult,
    Politician,
    ShortsDraft,
    SourceVideo,
    SpeechSegment,
    UploadedShorts,
    WeeklyRanking,
)
from src.dem_shorts.models.politician import SEED_POLITICIANS
from src.dem_shorts.models.uploaded_shorts import NATV_SOURCE_LABEL


# ─────────────────────────── Shared helpers ────────────────────────────

NOW = datetime(2026, 4, 16, 12, 0, 0)


def _source_video(**overrides) -> SourceVideo:
    base = dict(
        video_id="abc123",
        title="제422회 국회 본회의",
        description="민생경제 대책 논의",
        published_at=NOW,
        duration_sec=7200,
        thumbnail_url="https://img.example.com/t.jpg",
        session_type="plenary",
        download_path=None,
        stt_status="pending",
        diarization_status="pending",
        dem_score=0.0,
        excluded_reason=None,
        status="new",
        created_at=NOW,
        updated_at=NOW,
    )
    base.update(overrides)
    return SourceVideo(**base)


def _politician(**overrides) -> Politician:
    base = dict(
        id=1,
        name="이재명",
        party="더불어민주당",
        role="당대표",
        photo_url=None,
        bio="",
        tone_guide="",
        tier="pinned",
        category="fixed",
        is_active=True,
        ranking_score=None,
        added_at=NOW,
        updated_at=NOW,
    )
    base.update(overrides)
    return Politician(**base)


# ─────────────────────────── SourceVideo ────────────────────────────

class TestSourceVideo:
    def test_valid_creation(self):
        sv = _source_video()
        assert sv.video_id == "abc123"
        assert sv.session_type == "plenary"

    def test_invalid_session_type(self):
        with pytest.raises(ValueError, match="session_type"):
            _source_video(session_type="invalid")

    def test_invalid_status(self):
        with pytest.raises(ValueError, match="status"):
            _source_video(status="invalid")

    def test_dem_score_out_of_range(self):
        with pytest.raises(ValueError, match="dem_score"):
            _source_video(dem_score=150.0)

    def test_frozen(self):
        sv = _source_video()
        with pytest.raises(Exception):
            sv.title = "changed"  # type: ignore

    def test_to_from_dict_roundtrip(self):
        sv = _source_video(dem_score=82.5, status="ready")
        d = sv.to_dict()
        sv2 = SourceVideo.from_dict(d)
        assert sv2 == sv

    def test_excluded_reason_validation(self):
        with pytest.raises(ValueError, match="excluded_reason"):
            _source_video(excluded_reason="unknown_reason")


# ─────────────────────────── Politician ────────────────────────────

class TestPolitician:
    def test_valid_tier_category(self):
        p = _politician(tier="auto", category="female")
        assert p.tier == "auto"

    def test_invalid_tier(self):
        with pytest.raises(ValueError, match="tier"):
            _politician(tier="super_pinned")

    def test_invalid_category(self):
        with pytest.raises(ValueError, match="category"):
            _politician(category="elderly")

    def test_roundtrip(self):
        p = _politician(bio="정치인", tone_guide="직설")
        assert Politician.from_dict(p.to_dict()) == p

    def test_seed_has_three(self):
        """FR-006: 이재명·조국·정청래 고정."""
        names = {s["name"] for s in SEED_POLITICIANS}
        assert names == {"이재명", "조국", "정청래"}
        for s in SEED_POLITICIANS:
            assert s["tier"] == "pinned"
            assert s["category"] == "fixed"


# ─────────────────────────── SpeechSegment ────────────────────────────

class TestSpeechSegment:
    def test_valid(self):
        s = SpeechSegment(
            id=1, source_video_id="abc", start_sec=10.0, end_sec=20.0,
            politician_id=1, confidence=0.85, stt_text="발언",
            recommendation_score=70.0, emotion_strength=0.5,
            issue_keywords=("연금",), is_solo=True, has_profanity=False,
        )
        assert s.duration_sec == 10.0

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="end_sec"):
            SpeechSegment(
                id=1, source_video_id="a", start_sec=20.0, end_sec=10.0,
                politician_id=None, confidence=0.5, stt_text="",
                recommendation_score=0, emotion_strength=0,
                issue_keywords=(), is_solo=False, has_profanity=False,
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError, match="confidence"):
            SpeechSegment(
                id=1, source_video_id="a", start_sec=0, end_sec=1,
                politician_id=None, confidence=1.5, stt_text="",
                recommendation_score=0, emotion_strength=0,
                issue_keywords=(), is_solo=False, has_profanity=False,
            )

    def test_roundtrip(self):
        s = SpeechSegment(
            id=42, source_video_id="abc", start_sec=0, end_sec=5,
            politician_id=None, confidence=0.3, stt_text="t",
            recommendation_score=10, emotion_strength=0.1,
            issue_keywords=("민생", "경제"), is_solo=False, has_profanity=False,
        )
        assert SpeechSegment.from_dict(s.to_dict()) == s


# ─────────────────────────── ShortsDraft ────────────────────────────

def _draft(**overrides) -> ShortsDraft:
    base = dict(
        id=1, segment_id=10, cut_start_sec=0.0, cut_end_sec=30.0,
        commentary_blocks=(), commentary_char_count=0,
        tts_voice=None, tts_enabled=False, subtitle_preset="default",
        bgm_filename=None, fact_source_urls=(),
        risk_score=0.0, status="draft", rendered_path=None,
        created_at=NOW, updated_at=NOW,
    )
    base.update(overrides)
    return ShortsDraft(**base)


class TestShortsDraft:
    def test_cut_over_60_rejected(self):
        """FR-018: cut_duration > 60초 거부."""
        with pytest.raises(ValueError, match="exceeds"):
            _draft(cut_start_sec=0.0, cut_end_sec=61.0)

    def test_cut_end_before_start(self):
        with pytest.raises(ValueError):
            _draft(cut_start_sec=30.0, cut_end_sec=10.0)

    def test_invalid_preset(self):
        with pytest.raises(ValueError, match="subtitle_preset"):
            _draft(subtitle_preset="pink")

    def test_invalid_voice(self):
        with pytest.raises(ValueError, match="tts_voice"):
            _draft(tts_voice="unknown")

    def test_commentary_min(self):
        """FR-024 / 게이트 item_1."""
        assert _draft(commentary_char_count=49).meets_commentary_minimum() is False
        assert _draft(commentary_char_count=50).meets_commentary_minimum() is True

    def test_fact_urls_min(self):
        """FR-029."""
        assert _draft(fact_source_urls=("https://a.com",)).meets_fact_urls_minimum() is False
        assert _draft(
            fact_source_urls=("https://a.com", "https://b.com")
        ).meets_fact_urls_minimum() is True

    def test_roundtrip(self):
        d = _draft(
            commentary_blocks=({"start": 0, "end": 3, "text": "t", "style": "high"},),
            commentary_char_count=52, fact_source_urls=("a", "b"),
            subtitle_preset="leejaemyung", risk_score=24.5,
        )
        assert ShortsDraft.from_dict(d.to_dict()) == d


# ─────────────────────────── ComplianceGateResult ────────────────────────────

def _gate(**overrides) -> ComplianceGateResult:
    base = dict(
        id=1, draft_id=1,
        item_1_commentary_length="pass",
        item_2_ratio="pass",
        item_3_duration="pass",
        item_4_source_label="pass",
        item_5_bias_guardrail="pass",
        item_6_template_repeat="pass",
        item_7_whitelist_person="pass",
        item_8_election_guard="pass",
        item_9_fact_checked="pass",
        item_10_no_defamation="pass",
        manual_fact_check_signed_by="owner",
        manual_defamation_check_signed_by="owner",
        failure_reasons=(),
        overall_status="pass",
        risk_score=20.0,
        validated_at=NOW,
    )
    base.update(overrides)
    return ComplianceGateResult(**base)


class TestComplianceGateResult:
    def test_passes_when_all_pass_and_signed(self):
        g = _gate()
        assert g.is_passed() is True

    def test_blocked_if_any_item_fails(self):
        g = _gate(item_1_commentary_length="fail")
        assert g.is_passed() is False

    def test_blocked_if_manual_fact_not_signed(self):
        g = _gate(manual_fact_check_signed_by=None)
        assert g.is_passed() is False

    def test_blocked_if_manual_defamation_not_signed(self):
        g = _gate(manual_defamation_check_signed_by=None)
        assert g.is_passed() is False

    def test_blocked_if_risk_score_over_61(self):
        """FR-026: risk_score >= 61 강제 차단."""
        g = _gate(risk_score=61.0)
        assert g.is_passed() is False

    def test_warn_items_do_not_block(self):
        """item_5 (bias) / item_6 (template) 경고여도 통과 가능."""
        g = _gate(item_5_bias_guardrail="warn", item_6_template_repeat="warn")
        assert g.is_passed() is True

    def test_item_status_enum(self):
        with pytest.raises(ValueError):
            _gate(item_3_duration="skipped")

    def test_roundtrip(self):
        g = _gate(risk_score=45.2)
        assert ComplianceGateResult.from_dict(g.to_dict()) == g


# ─────────────────────────── WeeklyRanking ────────────────────────────

class TestWeeklyRanking:
    def test_valid(self):
        r = WeeklyRanking(
            id=1, week_start=date(2026, 4, 13), politician_id=5,
            rank=3, score=85.2, delta_vs_prev_week=4.5,
            tag="rising", data_sources={"naver_news": 30},
        )
        assert r.rank == 3

    def test_invalid_tag(self):
        with pytest.raises(ValueError):
            WeeklyRanking(
                id=1, week_start=date(2026, 4, 13), politician_id=1,
                rank=1, score=50.0, delta_vs_prev_week=0,
                tag="hot", data_sources={},
            )

    def test_score_range(self):
        with pytest.raises(ValueError):
            WeeklyRanking(
                id=1, week_start=date(2026, 4, 13), politician_id=1,
                rank=1, score=150.0, delta_vs_prev_week=0,
                tag=None, data_sources={},
            )

    def test_roundtrip(self):
        r = WeeklyRanking(
            id=1, week_start=date(2026, 4, 13), politician_id=5,
            rank=3, score=85.2, delta_vs_prev_week=4.5,
            tag="new", data_sources={"s": 1},
        )
        assert WeeklyRanking.from_dict(r.to_dict()) == r


# ─────────────────────────── UploadedShorts ────────────────────────────

class TestUploadedShorts:
    def test_requires_natv_label(self):
        """FR-029: 설명란에 NATV 출처 필수."""
        with pytest.raises(ValueError, match="NATV"):
            UploadedShorts(
                id=1, draft_id=1, final_mp4_path="x.mp4",
                youtube_video_id="yt1", title="t", description="no source",
                tags=(), scheduled_publish_at=None, published_at=None,
                fact_links=("a", "b"), view_count=0, like_count=0,
                comment_count=0, est_revenue=None, is_taken_down=False,
                takedown_reason=None, uploaded_at=NOW, metrics_updated_at=NOW,
            )

    def test_requires_two_fact_links(self):
        """FR-029: 팩트 링크 2개 이상."""
        with pytest.raises(ValueError, match="fact_links"):
            UploadedShorts(
                id=1, draft_id=1, final_mp4_path="x.mp4",
                youtube_video_id="yt1", title="t",
                description=f"... {NATV_SOURCE_LABEL} ...",
                tags=(), scheduled_publish_at=None, published_at=None,
                fact_links=("only_one",), view_count=0, like_count=0,
                comment_count=0, est_revenue=None, is_taken_down=False,
                takedown_reason=None, uploaded_at=NOW, metrics_updated_at=NOW,
            )

    def test_valid(self):
        u = UploadedShorts(
            id=1, draft_id=1, final_mp4_path="x.mp4",
            youtube_video_id="yt1", title="t",
            description=f"설명 {NATV_SOURCE_LABEL} 출처",
            tags=("a",), scheduled_publish_at=None, published_at=NOW,
            fact_links=("https://a.com", "https://b.com"),
            view_count=0, like_count=0, comment_count=0,
            est_revenue=None, is_taken_down=False, takedown_reason=None,
            uploaded_at=NOW, metrics_updated_at=NOW,
        )
        assert UploadedShorts.from_dict(u.to_dict()) == u


# ─────────────────────────── BiasReport ────────────────────────────

class TestBiasReport:
    def test_valid(self):
        r = BiasReport(
            id=1, month=date(2026, 4, 1), total_uploads=30,
            person_shares={"이재명": 0.3}, party_shares={"더불어민주당": 0.8},
            template_usage={"default": 12}, avg_risk_score=22.5,
            top_n_person_warning=(), recommendations=(),
            generated_at=NOW,
        )
        assert r.total_uploads == 30

    def test_negative_uploads_raises(self):
        with pytest.raises(ValueError):
            BiasReport(
                id=1, month=date(2026, 4, 1), total_uploads=-1,
                person_shares={}, party_shares={}, template_usage={},
                avg_risk_score=0, top_n_person_warning=(),
                recommendations=(), generated_at=NOW,
            )

    def test_roundtrip(self):
        r = BiasReport(
            id=1, month=date(2026, 4, 1), total_uploads=30,
            person_shares={"이재명": 0.5}, party_shares={"민주": 0.9},
            template_usage={"default": 15}, avg_risk_score=33.0,
            top_n_person_warning=("이재명",),
            recommendations=("이재명 50% — 권장 30% 초과",),
            generated_at=NOW,
        )
        assert BiasReport.from_dict(r.to_dict()) == r
