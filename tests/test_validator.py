"""Tests for BlindPost validator."""
import pytest
from src.scraper.validator import validate_blind_post, ValidationResult


class TestValidateBlindPost:
    def test_valid_post(self):
        data = {
            "title": "테스트 제목",
            "body": "충분히 긴 본문 내용입니다.",
            "comments": [{"text": "댓글", "likes": 1}],
        }
        result = validate_blind_post(data)
        assert result.is_valid

    def test_valid_no_comments(self):
        data = {"title": "제목", "body": "본문 내용 충분히 길게"}
        result = validate_blind_post(data)
        assert result.is_valid

    def test_valid_empty_comments(self):
        data = {"title": "제목", "body": "본문 내용 충분히", "comments": []}
        result = validate_blind_post(data)
        assert result.is_valid

    def test_missing_title(self):
        data = {"body": "본문만 있습니다"}
        result = validate_blind_post(data)
        assert not result.is_valid
        assert any("title" in e.field for e in result.errors)

    def test_empty_title(self):
        data = {"title": "", "body": "본문 내용 충분히"}
        result = validate_blind_post(data)
        assert not result.is_valid
        assert any("비어있을 수 없습니다" in e.message for e in result.errors)

    def test_whitespace_title(self):
        data = {"title": "   ", "body": "본문 내용 충분히"}
        result = validate_blind_post(data)
        assert not result.is_valid

    def test_missing_body(self):
        data = {"title": "제목만 있습니다"}
        result = validate_blind_post(data)
        assert not result.is_valid
        assert any("body" in e.field for e in result.errors)

    def test_short_body_warning(self):
        data = {"title": "제목", "body": "짧음"}
        result = validate_blind_post(data)
        assert result.is_valid  # warning, not error
        assert len(result.warnings) > 0
        assert any("짧습니다" in w.message for w in result.warnings)

    def test_title_not_string(self):
        data = {"title": 123, "body": "본문 내용 충분히"}
        result = validate_blind_post(data)
        assert not result.is_valid

    def test_body_not_string(self):
        data = {"title": "제목", "body": 456}
        result = validate_blind_post(data)
        assert not result.is_valid

    def test_comments_not_list(self):
        data = {"title": "제목", "body": "본문 내용 충분히", "comments": "not a list"}
        result = validate_blind_post(data)
        assert not result.is_valid

    def test_comment_missing_text(self):
        data = {
            "title": "제목",
            "body": "본문 내용 충분히",
            "comments": [{"likes": 5}],
        }
        result = validate_blind_post(data)
        assert not result.is_valid
        assert any("comments[0].text" in e.field for e in result.errors)

    def test_comment_likes_not_int(self):
        data = {
            "title": "제목",
            "body": "본문 내용 충분히",
            "comments": [{"text": "댓글", "likes": "five"}],
        }
        result = validate_blind_post(data)
        assert not result.is_valid

    def test_multiple_errors(self):
        data = {"comments": "not a list"}
        result = validate_blind_post(data)
        assert not result.is_valid
        assert len(result.errors) >= 2  # title + body missing

    def test_error_messages_format(self):
        data = {}
        result = validate_blind_post(data)
        messages = result.error_messages()
        assert all(msg.startswith("[") for msg in messages)
