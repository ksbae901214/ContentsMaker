"""T042 [US2]: PoliticianCard 페치 + 정당 컬러 매핑 테스트.

- fetch_politician_card() 캐시 히트/미스
- PARTY_COLORS 매핑 (민주 #004EA2, 국힘 #E61E2B, 무소속/기타 #888888)
- infer_party() 모킹 (Claude _call_claude patch)
- Naver 호출 mock + 이미지 다운로드 mock
- 미매핑 정당 → 회색 폴백 + 경고 로그 (caplog)
- 직렬화 라운드트립
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────── 정당 컬러 매핑 ───────────────────────────


def test_party_colors_table_required_entries() -> None:
    """PARTY_COLORS 사전 정의 (FR-024)."""
    from src.jpolitics.constants import PARTY_COLORS

    assert PARTY_COLORS["더불어민주당"] == "#004EA2"
    assert PARTY_COLORS["국민의힘"] == "#E61E2B"
    assert PARTY_COLORS["무소속"] == "#888888"
    assert PARTY_COLORS["기타"] == "#888888"


def test_get_party_color_known_party() -> None:
    """매핑된 정당은 정확한 헥스 컬러 반환."""
    from src.jpolitics.scraper.politician_card import get_party_color

    assert get_party_color("더불어민주당") == "#004EA2"
    assert get_party_color("국민의힘") == "#E61E2B"


def test_get_party_color_unknown_party_falls_back_to_gray_with_warning() -> None:
    """FR-028: 미매핑 정당 → 회색 #888 + 경고 로그.

    jpolitics 로거는 propagate=False 이라 caplog 대신 메모리 핸들러 부착으로 확인.
    """
    from src.jpolitics.scraper.politician_card import get_party_color

    target_logger = logging.getLogger("jpolitics.scraper.politician_card")
    records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _ListHandler(level=logging.WARNING)
    target_logger.addHandler(handler)
    try:
        color = get_party_color("외계인당")
    finally:
        target_logger.removeHandler(handler)

    assert color == "#888888"
    assert any("외계인당" in rec.getMessage() for rec in records), records


# ─────────────────────────── PoliticianCard 모델 (T047 검증) ───────────────────────────


def test_politician_card_serialization_roundtrip() -> None:
    """to_dict / from_dict 라운드트립."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="양향자",
        party="국민의힘",
        party_color="#E61E2B",
        photo_path="data/politician_cards/photos/양향자.jpg",
    )
    restored = PoliticianCard.from_dict(card.to_dict())
    assert restored == card


def test_politician_card_serialization_with_data_fields() -> None:
    """data_label/data_value 포함 직렬화."""
    from src.jpolitics.models.politician_card import PoliticianCard

    card = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0073CF",
        photo_path=None,
        data_label="재산",
        data_value="56억",
    )
    d = card.to_dict()
    assert d["data_label"] == "재산"
    assert d["data_value"] == "56억"
    assert "photo_path" not in d  # None은 제외
    restored = PoliticianCard.from_dict(d)
    assert restored.data_label == "재산"
    assert restored.data_value == "56억"
    assert restored.photo_path is None


# ─────────────────────────── 캐시 ───────────────────────────


def test_fetch_politician_card_cache_hit_returns_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """캐시 히트 시 Naver 호출 없이 즉시 반환 (SC-005)."""
    from src.jpolitics import constants
    from src.jpolitics.models.politician_card import PoliticianCard
    from src.jpolitics.scraper import politician_card as pc_mod

    # 캐시 디렉토리 격리
    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")

    # 사전 캐시 저장
    cached = PoliticianCard(
        name="조국",
        party="조국혁신당",
        party_color="#0073CF",
        photo_path="data/politician_cards/photos/조국.jpg",
    )
    pc_mod.save_cached_card(cached)

    # Naver 호출이 발생하면 fail (캐시 히트 보장)
    with patch.object(pc_mod, "_naver_fetch_photo") as naver:
        result = pc_mod.fetch_politician_card("조국")
        assert naver.call_count == 0

    assert result.name == "조국"
    assert result.party == "조국혁신당"
    assert result.party_color == "#0073CF"


def test_fetch_politician_card_cache_miss_calls_naver_and_saves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """캐시 미스 → Naver 호출 + 이미지 다운로드 + 캐시 저장."""
    from src.jpolitics import constants
    from src.jpolitics.scraper import politician_card as pc_mod

    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")

    fake_photo = tmp_path / "photos" / "양향자.jpg"

    def fake_naver(name: str) -> str | None:
        (tmp_path / "photos").mkdir(parents=True, exist_ok=True)
        fake_photo.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
        return str(fake_photo)

    with patch.object(pc_mod, "_naver_fetch_photo", side_effect=fake_naver) as naver:
        result = pc_mod.fetch_politician_card("양향자", party="국민의힘")

    assert naver.call_count == 1
    assert result.name == "양향자"
    assert result.party == "국민의힘"
    assert result.party_color == "#E61E2B"
    assert result.photo_path == str(fake_photo)

    # 캐시 파일 저장 확인
    cache_file = tmp_path / "양향자.json"
    assert cache_file.exists()
    cached = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached["name"] == "양향자"
    assert cached["party"] == "국민의힘"
    assert cached["party_color"] == "#E61E2B"


def test_fetch_politician_card_naver_failure_falls_back_to_no_photo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Naver 검색 실패 → photo_path=None 폴백 (FR-027)."""
    from src.jpolitics import constants
    from src.jpolitics.scraper import politician_card as pc_mod

    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")

    with patch.object(pc_mod, "_naver_fetch_photo", return_value=None):
        result = pc_mod.fetch_politician_card("무명정치인", party="더불어민주당")

    assert result.photo_path is None
    assert result.party_color == "#004EA2"  # 민주당 컬러는 유지


# ─────────────────────────── infer_party ───────────────────────────


def test_infer_party_mapped_returns_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    """Claude 응답이 PARTY_COLORS 키와 정확히 매칭되면 그대로 반환."""
    from src.jpolitics.scraper import politician_card as pc_mod

    with patch.object(pc_mod, "_call_claude", return_value="더불어민주당"):
        assert pc_mod.infer_party("이재명") == "더불어민주당"


def test_infer_party_unmapped_returns_etc_with_warning() -> None:
    """미매핑 정당 → '기타' + 경고."""
    from src.jpolitics.scraper import politician_card as pc_mod

    target_logger = logging.getLogger("jpolitics.scraper.politician_card")
    records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _ListHandler(level=logging.WARNING)
    target_logger.addHandler(handler)
    try:
        with patch.object(pc_mod, "_call_claude", return_value="새로운정당123"):
            result = pc_mod.infer_party("미상인물")
    finally:
        target_logger.removeHandler(handler)

    assert result == "기타"
    assert any("미상인물" in rec.getMessage() for rec in records), records


def test_infer_party_strips_extra_whitespace_and_punctuation() -> None:
    """Claude가 ' 국민의힘 .\\n' 같이 돌려줘도 정규화."""
    from src.jpolitics.scraper import politician_card as pc_mod

    with patch.object(pc_mod, "_call_claude", return_value=" 국민의힘 .\n"):
        assert pc_mod.infer_party("양향자") == "국민의힘"


# ─────────────────────────── infer_party 통합 (fetch에서 party=None) ───────────────────────────


def test_fetch_politician_card_calls_infer_party_when_party_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """party=None이면 infer_party 호출 후 매핑 적용."""
    from src.jpolitics import constants
    from src.jpolitics.scraper import politician_card as pc_mod

    monkeypatch.setattr(constants, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(constants, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(pc_mod, "POLITICIAN_CARDS_DIR", tmp_path)
    monkeypatch.setattr(pc_mod, "POLITICIAN_PHOTOS_DIR", tmp_path / "photos")

    with patch.object(
        pc_mod, "_naver_fetch_photo", return_value=None
    ), patch.object(pc_mod, "infer_party", return_value="국민의힘") as infer:
        card = pc_mod.fetch_politician_card("양향자")  # party 생략

    infer.assert_called_once_with("양향자")
    assert card.party == "국민의힘"
    assert card.party_color == "#E61E2B"
