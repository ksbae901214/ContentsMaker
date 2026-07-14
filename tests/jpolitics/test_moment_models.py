"""신규 V3 모먼트 모델 테스트 (Feature 027)."""
import json
from pathlib import Path

import pytest

from src.jpolitics.models.moment import (
    Moment,
    MomentDetectionResult,
    MOMENT_KINDS,
)


def _moment(**over) -> Moment:
    base = dict(
        start_sec=12.0,
        end_sec=45.0,
        kind="clash",
        speaker="추미애",
        summary="추미애가 나경원에게 쇼츠 그만 찍으라고 일갈",
        hook_question="국회에서 왜 쇼츠 얘기가 나왔을까요?",
        keywords=("쇼츠", "퇴장"),
        confidence=0.9,
    )
    base.update(over)
    return Moment(**base)


class TestMoment:
    def test_valid_moment(self):
        m = _moment()
        assert m.duration_sec == pytest.approx(33.0)
        assert m.kind in MOMENT_KINDS

    def test_frozen(self):
        m = _moment()
        with pytest.raises(Exception):
            m.kind = "laughter"  # type: ignore[misc]

    def test_end_must_be_after_start(self):
        with pytest.raises(ValueError):
            _moment(start_sec=50.0, end_sec=10.0)

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValueError):
            _moment(kind="dance")

    def test_confidence_range(self):
        with pytest.raises(ValueError):
            _moment(confidence=1.5)
        with pytest.raises(ValueError):
            _moment(confidence=-0.1)

    def test_roundtrip_dict(self):
        m = _moment()
        restored = Moment.from_dict(m.to_dict())
        assert restored == m

    def test_from_dict_accepts_camel_case(self):
        d = {
            "startSec": 1.0,
            "endSec": 8.0,
            "kind": "laughter",
            "speaker": "박범계",
            "summary": "청문회 도중 웃음 터짐",
            "hookQuestion": "청문회에서 왜 웃음이 터졌을까요?",
            "keywords": ["웃음"],
            "confidence": 0.8,
        }
        m = Moment.from_dict(d)
        assert m.start_sec == 1.0
        assert m.hook_question.startswith("청문회")


class TestMomentDetectionResult:
    def test_roundtrip_and_save(self, tmp_path: Path):
        result = MomentDetectionResult(
            source_url="https://youtube.com/watch?v=x",
            video_title="법사위 대혼란",
            channel="국회방송",
            detector="gemini_multimodal",
            moments=(_moment(), _moment(kind="laughter", confidence=0.7)),
        )
        out = tmp_path / "moments.json"
        result.save(out)

        loaded = MomentDetectionResult.from_dict(json.loads(out.read_text()))
        assert loaded == result
        assert len(loaded.moments) == 2

    def test_moments_sorted_by_confidence_desc(self):
        result = MomentDetectionResult(
            source_url="u", video_title="t", channel="c", detector="transcript",
            moments=(_moment(confidence=0.5), _moment(confidence=0.95)),
        )
        top = result.top(1)
        assert top[0].confidence == 0.95
