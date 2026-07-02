"""모먼트 검출기 파싱/폴백 로직 테스트 (LLM은 mock, Feature 027)."""
import json

import pytest

from src.jpolitics.analyzer.moment_detector import (
    MomentDetectError,
    _parse_moments_json,
    detect_moments_from_transcript,
)

VALID_PAYLOAD = [
    {
        "start_sec": 10.0,
        "end_sec": 40.0,
        "kind": "clash",
        "speaker": "추미애",
        "summary": "여야 충돌",
        "hook_question": "왜 회의가 멈췄을까요?",
        "keywords": ["충돌"],
        "confidence": 0.9,
    },
    {
        "start_sec": 100.0,
        "end_sec": 130.0,
        "kind": "laughter",
        "speaker": "박범계",
        "summary": "웃음 터짐",
        "hook_question": "청문회에서 누가 웃었을까요?",
        "keywords": ["웃음"],
        "confidence": 0.7,
    },
]


class TestParseMoments:
    def test_plain_json_array(self):
        moments = _parse_moments_json(json.dumps(VALID_PAYLOAD, ensure_ascii=False))
        assert len(moments) == 2
        assert moments[0].kind == "clash"

    def test_code_fenced_json(self):
        text = "```json\n" + json.dumps(VALID_PAYLOAD, ensure_ascii=False) + "\n```"
        assert len(_parse_moments_json(text)) == 2

    def test_json_with_surrounding_prose(self):
        text = "분석 결과입니다:\n" + json.dumps(VALID_PAYLOAD, ensure_ascii=False) + "\n이상입니다."
        assert len(_parse_moments_json(text)) == 2

    def test_invalid_items_skipped(self):
        payload = [VALID_PAYLOAD[0], {"kind": "dance", "start_sec": 1}, "garbage"]
        moments = _parse_moments_json(json.dumps(payload, ensure_ascii=False))
        assert len(moments) == 1

    def test_unparseable_raises(self):
        with pytest.raises(MomentDetectError):
            _parse_moments_json("응답이 JSON이 아님")

    def test_too_short_or_too_long_moments_dropped(self):
        payload = [
            {**VALID_PAYLOAD[0], "start_sec": 0.0, "end_sec": 2.0},     # 2초 — 너무 짧음
            {**VALID_PAYLOAD[0], "start_sec": 0.0, "end_sec": 120.0},   # 120초 — 너무 김
            VALID_PAYLOAD[1],
        ]
        moments = _parse_moments_json(json.dumps(payload, ensure_ascii=False))
        assert len(moments) == 1
        assert moments[0].kind == "laughter"


class TestTranscriptFallback:
    def test_detect_from_transcript_calls_llm(self, monkeypatch):
        captured = {}

        def fake_call_gemini(prompt, **kwargs):
            captured["prompt"] = prompt
            return json.dumps(VALID_PAYLOAD, ensure_ascii=False)

        monkeypatch.setattr(
            "src.jpolitics.analyzer.moment_detector._call_llm", fake_call_gemini
        )
        segments = [
            {"start": 0.0, "end": 5.0, "text": "의사진행 발언입니다"},
            {"start": 5.0, "end": 9.0, "text": "쇼츠 그만 찍고 퇴장하세요"},
        ]

        moments = detect_moments_from_transcript(segments)

        assert len(moments) == 2
        assert "쇼츠 그만 찍고" in captured["prompt"]
        assert "[5.0-9.0]" in captured["prompt"] or "5.0" in captured["prompt"]

    def test_empty_transcript_raises(self):
        with pytest.raises(MomentDetectError):
            detect_moments_from_transcript([])
