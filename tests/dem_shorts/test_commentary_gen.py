"""T062: Commentary generator 테스트 — Claude CLI mock + JSON 파싱 + 15자 필터.
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from src.dem_shorts.editor.commentary_gen import (
    CommentaryGenError,
    CommentaryContext,
    generate_commentary_candidates,
    parse_candidates,
    filter_by_max_chars,
)


SAMPLE_CONTEXT = CommentaryContext(
    politician_name="이재명",
    stt_text="민생경제를 살리기 위한 3% 성장 로드맵을 제시합니다.",
    tone_guide="팩트 기반 객관적",
    tone_hint="민생·개혁 리더 톤",
    session_type="plenary",
    is_election_period=False,
)


class TestParseCandidates:
    def test_parses_valid_json(self):
        raw = json.dumps({
            "candidates": [
                {"text": "민생경제 3% 성장 강조", "confidence": 0.85},
                {"text": "이재명, 국회서 정면돌파", "confidence": 0.78},
                {"text": "야당과 공방, 합의 예상", "confidence": 0.72},
            ]
        })
        cands = parse_candidates(raw)
        assert len(cands) == 3
        assert cands[0]["text"] == "민생경제 3% 성장 강조"
        assert cands[0]["confidence"] == 0.85

    def test_parses_markdown_code_block(self):
        raw = f"```json\n{json.dumps({'candidates': [{'text': 'x', 'confidence': 0.5}]})}\n```"
        cands = parse_candidates(raw)
        assert len(cands) == 1

    def test_rejects_empty_candidates(self):
        raw = json.dumps({"candidates": []})
        with pytest.raises(CommentaryGenError):
            parse_candidates(raw)

    def test_rejects_invalid_json(self):
        with pytest.raises(CommentaryGenError):
            parse_candidates("not json at all")

    def test_accepts_candidates_as_top_level_list(self):
        raw = json.dumps([
            {"text": "A", "confidence": 0.9},
            {"text": "B", "confidence": 0.8},
        ])
        cands = parse_candidates(raw)
        assert len(cands) == 2


class TestFilterByMaxChars:
    def test_filters_over_15_chars(self):
        cands = [
            {"text": "15자 이하 해설입니다", "confidence": 0.8},          # 11자
            {"text": "이건 15자를 확실히 넘어가는 아주 긴 해설", "confidence": 0.7},  # 24자
        ]
        filtered = filter_by_max_chars(cands, max_chars=15)
        assert len(filtered) == 1
        assert filtered[0]["text"] == "15자 이하 해설입니다"

    def test_counts_chars_not_bytes(self):
        """한글 1글자 = 1개로 카운트."""
        cand = [{"text": "가나다라마바사아자차카타", "confidence": 0.9}]  # 12자
        filtered = filter_by_max_chars(cand, max_chars=15)
        assert len(filtered) == 1

    def test_returns_empty_if_all_too_long(self):
        cands = [{"text": "이건 매우매우매우 긴 해설입니다정말정말정말", "confidence": 0.9}]
        filtered = filter_by_max_chars(cands, max_chars=15)
        assert filtered == []


class TestGenerateCommentaryCandidates:
    @mock.patch("src.dem_shorts.editor.commentary_gen._call_claude")
    def test_returns_3_candidates(self, mock_call):
        mock_call.return_value = json.dumps({
            "candidates": [
                {"text": "민생경제 3% 성장 강조", "confidence": 0.85},
                {"text": "이재명, 국회 정면돌파", "confidence": 0.78},
                {"text": "야당과 합의 이뤄내", "confidence": 0.72},
            ]
        })
        out = generate_commentary_candidates(SAMPLE_CONTEXT)
        assert len(out) == 3
        assert all("text" in c and "confidence" in c for c in out)

    @mock.patch("src.dem_shorts.editor.commentary_gen._call_claude")
    def test_filters_long_candidates_down(self, mock_call):
        mock_call.return_value = json.dumps({
            "candidates": [
                {"text": "짧은거OK", "confidence": 0.9},  # 6자
                {"text": "이건 너무 긴 해설로 반드시 걸러져야 한다정말정말", "confidence": 0.85},  # 27자
            ]
        })
        out = generate_commentary_candidates(SAMPLE_CONTEXT, max_chars=15)
        assert len(out) == 1
        assert out[0]["text"] == "짧은거OK"

    @mock.patch("src.dem_shorts.editor.commentary_gen._call_claude")
    def test_raises_on_claude_error(self, mock_call):
        mock_call.side_effect = RuntimeError("claude cli not found")
        with pytest.raises(CommentaryGenError):
            generate_commentary_candidates(SAMPLE_CONTEXT)


class TestElectionNeutralBranch:
    """T099: is_election_period=True → neutral prompt template 사용 (FR-032)."""

    @mock.patch("src.dem_shorts.editor.commentary_gen._call_claude")
    def test_neutral_prompt_when_in_election_period(self, mock_call):
        mock_call.return_value = json.dumps({
            "candidates": [{"text": "정책 중심 요약", "confidence": 0.8}],
        })
        ctx = CommentaryContext(
            politician_name="이재명",
            stt_text="민생경제 로드맵 발표",
            tone_guide="",
            tone_hint="",
            session_type="plenary",
            is_election_period=True,
        )
        generate_commentary_candidates(ctx)
        called_prompt = mock_call.call_args[0][0]
        # 중립 모드 프롬프트 마커 (commentary_prompt.COMMENTARY_NEUTRAL_PROMPT)
        assert "선거기간" in called_prompt
        assert "후보 우호 표현 절대 금지" in called_prompt

    @mock.patch("src.dem_shorts.editor.commentary_gen._call_claude")
    def test_default_prompt_when_not_in_election(self, mock_call):
        mock_call.return_value = json.dumps({
            "candidates": [{"text": "정책 중심 요약", "confidence": 0.8}],
        })
        generate_commentary_candidates(SAMPLE_CONTEXT)  # is_election_period=False
        called_prompt = mock_call.call_args[0][0]
        assert "선거기간" not in called_prompt
        assert "당신은 정치 쇼츠 해설 자막 작성 어시스턴트입니다" in called_prompt
