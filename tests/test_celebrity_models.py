"""Tests for CelebrityInfo model (Phase 9-1).

TDD RED phase: defines expected behavior before implementation.
"""
import pytest

from src.scraper.celebrity_models import CelebrityInfo, CelebrityInfoError


class TestCreateCelebrityInfo:
    def test_create_minimal(self):
        info = CelebrityInfo(
            name="손흥민",
            summary="대한민국의 축구 선수",
            source_url="https://namu.wiki/w/손흥민",
        )
        assert info.name == "손흥민"
        assert info.summary == "대한민국의 축구 선수"
        assert info.source_url == "https://namu.wiki/w/손흥민"
        assert info.birth_date == ""
        assert info.profession == ""
        assert info.career_highlights == ()
        assert info.trivia == ()

    def test_create_full(self):
        info = CelebrityInfo(
            name="손흥민",
            summary="대한민국의 축구 선수",
            birth_date="1992-07-08",
            profession="축구 선수",
            career_highlights=("토트넘 이적 (2015)", "EPL 득점왕 (2022)"),
            trivia=("아버지는 축구 감독 출신",),
            source_url="https://namu.wiki/w/손흥민",
        )
        assert info.birth_date == "1992-07-08"
        assert info.profession == "축구 선수"
        assert len(info.career_highlights) == 2
        assert len(info.trivia) == 1

    def test_frozen(self):
        info = CelebrityInfo(name="세종", summary="요약", source_url="https://namu.wiki/w/세종")
        with pytest.raises(AttributeError):
            info.name = "다른 이름"

    def test_highlights_are_tuples(self):
        """Sequences must be tuples (immutable) not lists."""
        info = CelebrityInfo(
            name="세종",
            summary="요약",
            source_url="https://namu.wiki/w/세종",
            career_highlights=("1", "2"),
        )
        assert isinstance(info.career_highlights, tuple)


class TestValidation:
    def test_empty_name_rejected(self):
        with pytest.raises(CelebrityInfoError, match="이름"):
            CelebrityInfo(name="", summary="요약", source_url="https://namu.wiki/w/x")

    def test_whitespace_name_rejected(self):
        with pytest.raises(CelebrityInfoError, match="이름"):
            CelebrityInfo(name="   ", summary="요약", source_url="https://namu.wiki/w/x")

    def test_empty_summary_rejected(self):
        with pytest.raises(CelebrityInfoError, match="요약"):
            CelebrityInfo(name="세종", summary="", source_url="https://namu.wiki/w/세종")

    def test_non_namuwiki_url_rejected(self):
        """Source URL must be a namu.wiki page (licensing + provenance)."""
        with pytest.raises(CelebrityInfoError, match="namu.wiki"):
            CelebrityInfo(
                name="세종", summary="요약", source_url="https://en.wikipedia.org/wiki/Sejong"
            )

    def test_http_source_url_rejected(self):
        """Only HTTPS allowed to prevent mixed-content / MITM."""
        with pytest.raises(CelebrityInfoError, match="https"):
            CelebrityInfo(
                name="세종", summary="요약", source_url="http://namu.wiki/w/세종"
            )


class TestSerialization:
    def test_to_dict_roundtrip(self):
        original = CelebrityInfo(
            name="손흥민",
            summary="대한민국의 축구 선수",
            birth_date="1992-07-08",
            profession="축구 선수",
            career_highlights=("토트넘 이적",),
            trivia=("아버지는 감독",),
            source_url="https://namu.wiki/w/손흥민",
        )
        data = original.to_dict()
        restored = CelebrityInfo.from_dict(data)
        assert restored == original

    def test_to_dict_keys(self):
        info = CelebrityInfo(name="x", summary="y", source_url="https://namu.wiki/w/x")
        data = info.to_dict()
        assert set(data.keys()) == {
            "name",
            "summary",
            "birth_date",
            "profession",
            "career_highlights",
            "trivia",
            "source_url",
        }

    def test_from_dict_missing_optional_fields(self):
        info = CelebrityInfo.from_dict({
            "name": "손흥민",
            "summary": "축구 선수",
            "source_url": "https://namu.wiki/w/손흥민",
        })
        assert info.birth_date == ""
        assert info.career_highlights == ()
