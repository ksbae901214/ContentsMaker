"""Tests for manual input module."""
import json
import pytest
from pathlib import Path

from src.scraper.manual_input import (
    ManualInputError,
    load_from_file,
    save_post,
)
from src.scraper.models import BlindPost, Comment


SAMPLES_DIR = Path(__file__).parent / "samples"


class TestLoadFromFile:
    def test_valid_post(self):
        post = load_from_file(SAMPLES_DIR / "valid_post.json")
        assert post.title == "곧 부동산 피바람 불 거다"
        assert len(post.comments) == 3
        assert post.comments[0].text == "ㅋㅋ"

    def test_valid_no_comments(self):
        post = load_from_file(SAMPLES_DIR / "valid_no_comments.json")
        assert post.title == "30대 중반 여자의 영끝연봉"
        assert len(post.comments) == 0

    def test_missing_title(self):
        with pytest.raises(ManualInputError, match="스키마 검증 실패"):
            load_from_file(SAMPLES_DIR / "invalid_missing_title.json")

    def test_bad_json(self):
        with pytest.raises(ManualInputError, match="유효하지 않은 JSON"):
            load_from_file(SAMPLES_DIR / "invalid_bad_json.txt")

    def test_file_not_found(self):
        with pytest.raises(ManualInputError, match="파일을 찾을 수 없습니다"):
            load_from_file(Path("/nonexistent/file.json"))

    def test_emoji_preserved(self):
        post = load_from_file(SAMPLES_DIR / "valid_no_comments.json")
        assert "😢" in post.body


class TestSavePost:
    def test_save_creates_file(self, tmp_path):
        post = BlindPost(
            title="테스트 제목",
            author="회사 · 닉네임",
            body="본문 내용 충분히 길게 작성합니다",
            comments=(Comment(text="댓글", likes=5),),
        )
        saved = save_post(post, output_dir=tmp_path)
        assert saved.exists()
        assert saved.suffix == ".json"

        data = json.loads(saved.read_text(encoding="utf-8"))
        assert data["title"] == "테스트 제목"
        assert len(data["comments"]) == 1

    def test_save_creates_directory(self, tmp_path):
        new_dir = tmp_path / "subdir" / "deep"
        post = BlindPost(title="test", author="a", body="body content here")
        saved = save_post(post, output_dir=new_dir)
        assert new_dir.exists()
        assert saved.exists()

    def test_save_korean_filename(self, tmp_path):
        post = BlindPost(title="한국어 제목 테스트", author="a", body="본문 내용")
        saved = save_post(post, output_dir=tmp_path)
        assert saved.exists()

    def test_save_preserves_utf8(self, tmp_path):
        post = BlindPost(
            title="이모지 🔥",
            author="회사",
            body="본문 😊 특수문자 ㅋㅋ",
        )
        saved = save_post(post, output_dir=tmp_path)
        content = saved.read_text(encoding="utf-8")
        assert "🔥" in content
        assert "😊" in content
