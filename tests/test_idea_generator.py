"""Tests for idea_generator module."""
import json
from unittest.mock import patch

import pytest

from src.analyzer.claude_analyzer import AnalyzerError
from src.analyzer.idea_generator import VideoIdea, _extract_json, _parse_ideas, generate_video_ideas


class TestVideoIdea:
    def test_frozen_dataclass(self):
        idea = VideoIdea(title="t", hook="h", angle="a", natv_keywords="k")
        with pytest.raises(Exception):
            idea.title = "changed"  # type: ignore

    def test_fields(self):
        idea = VideoIdea(title="제목", hook="훅", angle="각도", natv_keywords="키워드")
        assert idea.title == "제목"
        assert idea.hook == "훅"
        assert idea.angle == "각도"
        assert idea.natv_keywords == "키워드"


class TestExtractJson:
    def test_direct_json(self):
        raw = json.dumps({"ideas": []})
        data = _extract_json(raw)
        assert data == {"ideas": []}

    def test_code_block(self):
        raw = '```json\n{"ideas": [{"title": "t"}]}\n```'
        data = _extract_json(raw)
        assert data["ideas"][0]["title"] == "t"

    def test_bare_json_in_text(self):
        raw = 'Some preamble\n{"ideas": []} trailing text'
        data = _extract_json(raw)
        assert "ideas" in data

    def test_raises_on_unparseable(self):
        with pytest.raises((AnalyzerError, json.JSONDecodeError)):
            _extract_json("not json at all")


class TestParseIdeas:
    def test_parses_ideas(self):
        raw = json.dumps({
            "ideas": [
                {"title": "제목1", "hook": "훅1", "angle": "각도1", "natv_keywords": "키1"},
                {"title": "제목2", "hook": "훅2", "angle": "각도2", "natv_keywords": "키2"},
            ]
        })
        ideas = _parse_ideas(raw, max_ideas=5)
        assert len(ideas) == 2
        assert ideas[0].title == "제목1"
        assert ideas[1].natv_keywords == "키2"

    def test_respects_max_ideas(self):
        raw = json.dumps({
            "ideas": [
                {"title": f"제목{i}", "hook": "", "angle": "", "natv_keywords": ""}
                for i in range(10)
            ]
        })
        ideas = _parse_ideas(raw, max_ideas=3)
        assert len(ideas) == 3

    def test_handles_claude_wrapper(self):
        inner = json.dumps({"ideas": [{"title": "t", "hook": "h", "angle": "a", "natv_keywords": "k"}]})
        raw = json.dumps({"result": inner})
        ideas = _parse_ideas(raw, max_ideas=5)
        assert len(ideas) == 1
        assert ideas[0].title == "t"

    def test_empty_ideas_list(self):
        raw = json.dumps({"ideas": []})
        ideas = _parse_ideas(raw, max_ideas=5)
        assert ideas == []


class TestGenerateVideoIdeas:
    def test_raises_on_empty_titles(self):
        with pytest.raises(AnalyzerError, match="영상 제목이 없습니다"):
            generate_video_ideas("나경원", [])

    @patch("src.analyzer.idea_generator._call_claude")
    def test_success(self, mock_claude):
        mock_claude.return_value = json.dumps({
            "ideas": [
                {"title": "🔥 나경원 충격 발언", "hook": "이 발언으로 국회가 뒤집혔습니다",
                 "angle": "여야 충돌", "natv_keywords": "나경원 대정부질문"},
            ]
        })
        ideas = generate_video_ideas("나경원", ["나경원 의원 연금개혁 발언", "나경원 대정부질문"])
        assert len(ideas) == 1
        assert "나경원" in ideas[0].title
        assert ideas[0].natv_keywords == "나경원 대정부질문"

    @patch("src.analyzer.idea_generator._call_claude")
    def test_returns_all_ideas(self, mock_claude):
        mock_claude.return_value = json.dumps({
            "ideas": [
                {"title": f"제목{i}", "hook": "", "angle": "", "natv_keywords": "키워드"}
                for i in range(5)
            ]
        })
        ideas = generate_video_ideas("나경원", ["제목1", "제목2", "제목3"], max_ideas=5)
        assert len(ideas) == 5

    @patch("src.analyzer.idea_generator._call_claude")
    def test_propagates_analyzer_error(self, mock_claude):
        mock_claude.side_effect = AnalyzerError("Claude 실패")
        with pytest.raises(AnalyzerError):
            generate_video_ideas("나경원", ["영상 제목"])
