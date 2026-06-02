"""Tests for BlindPost and Comment data models."""
import json
import pytest
from src.scraper.models import BlindPost, Comment


class TestComment:
    def test_create_comment(self):
        c = Comment(text="ㅋㅋ", likes=7, author="DB하이텍 · qRPi60")
        assert c.text == "ㅋㅋ"
        assert c.likes == 7
        assert c.author == "DB하이텍 · qRPi60"

    def test_comment_defaults(self):
        c = Comment(text="hello")
        assert c.likes == 0
        assert c.author == ""

    def test_comment_frozen(self):
        c = Comment(text="test", likes=1)
        with pytest.raises(AttributeError):
            c.text = "mutated"

    def test_comment_roundtrip(self):
        original = Comment(text="ㅋㅋ", likes=7, author="테스트")
        d = original.to_dict()
        restored = Comment.from_dict(d)
        assert restored == original

    def test_comment_from_dict_minimal(self):
        c = Comment.from_dict({"text": "hi"})
        assert c.text == "hi"
        assert c.likes == 0


class TestBlindPost:
    def test_create_post(self):
        post = BlindPost(
            title="테스트 제목",
            author="회사 · 닉네임",
            body="본문 내용입니다. 충분히 긴 텍스트.",
        )
        assert post.title == "테스트 제목"
        assert post.comments == ()

    def test_post_frozen(self):
        post = BlindPost(title="test", author="a", body="b" * 20)
        with pytest.raises(AttributeError):
            post.title = "mutated"

    def test_post_with_comments(self):
        comments = (
            Comment(text="첫번째", likes=5),
            Comment(text="두번째", likes=3),
        )
        post = BlindPost(
            title="제목",
            author="작성자",
            body="본문" * 10,
            comments=comments,
        )
        assert len(post.comments) == 2
        assert post.comments[0].likes == 5

    def test_post_to_dict(self):
        post = BlindPost(
            title="제목",
            author="작성자",
            body="본문 내용 테스트",
            comments=(Comment(text="댓글", likes=1),),
            url="https://example.com",
            created_at="2026-03-23T16:00:00+09:00",
        )
        d = post.to_dict()
        assert d["title"] == "제목"
        assert len(d["comments"]) == 1
        assert d["comments"][0]["text"] == "댓글"

    def test_post_to_json_preserves_korean(self):
        post = BlindPost(title="한국어 제목", author="회사", body="한국어 본문입니다")
        json_str = post.to_json()
        assert "한국어 제목" in json_str
        assert "한국어 본문입니다" in json_str

    def test_post_roundtrip(self):
        original = BlindPost(
            title="곧 부동산 피바람 불 거다",
            author="부동산 · 빵코코",
            body="미국 부채를 돌려막기 하고있는 시점에서...",
            comments=(
                Comment(text="ㅋㅋ", likes=7),
                Comment(text="어그로나?", likes=3),
            ),
            url="https://www.teamblind.com/kr/post/test",
            created_at="2026-03-23T16:13:00+09:00",
        )
        d = original.to_dict()
        restored = BlindPost.from_dict(d)
        assert restored.title == original.title
        assert restored.body == original.body
        assert len(restored.comments) == 2

    def test_post_from_json(self):
        json_str = json.dumps({
            "title": "테스트",
            "body": "본문 내용 충분히 길게",
            "comments": [{"text": "댓글", "likes": 1}],
        }, ensure_ascii=False)
        post = BlindPost.from_json(json_str)
        assert post.title == "테스트"
        assert len(post.comments) == 1

    def test_post_from_dict_auto_created_at(self):
        post = BlindPost.from_dict({"title": "test", "body": "body content"})
        assert post.created_at != ""

    def test_emoji_preservation(self):
        post = BlindPost(
            title="이모지 테스트 😢🔥",
            author="회사",
            body="본문에 이모지 포함 😊👍",
        )
        json_str = post.to_json()
        restored = BlindPost.from_json(json_str)
        assert "😢" in restored.title
        assert "😊" in restored.body
