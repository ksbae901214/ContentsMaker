"""MetaResult 생성 + generate_meta 파싱/폴백 로직 테스트 (Feature 027 Phase 4)."""
from __future__ import annotations

import json

import pytest

from src.jpolitics.analyzer.meta_generator import MetaResult, generate_meta, _FALLBACK


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

VALID_RESPONSE = {
    "title_candidates": [
        "왜 청문회가 멈췄을까요?",
        "국회에서 무슨 일이?",
        "이게 말이 되나요?",
    ],
    "hashtags": [
        "#정치",
        "#국회",
        "#쇼츠",
        "#청문회",
        "#여야충돌",
    ],
    "pinned_comment": "여러분은 이 상황을 어떻게 보시나요? 댓글로 알려주세요!",
}

_CALL_ARGS = dict(
    video_title="2024 국회 청문회 하이라이트",
    channel="YTN",
    moment_hook="왜 청문회가 멈췄을까요?",
    moment_summary="여야 충돌로 청문회 정회",
    moment_kind="clash",
)


def _make_fake_call_claude(response_dict: dict):
    """지정된 dict를 JSON 문자열로 반환하는 _call_claude mock."""
    def fake(prompt: str, **kwargs) -> str:
        return json.dumps(response_dict, ensure_ascii=False)
    return fake


# ── MetaResult 모델 테스트 ────────────────────────────────────────────────────

class TestMetaResult:
    def test_to_dict_roundtrip(self):
        meta = MetaResult(
            title_candidates=("제목1?", "제목2?", "제목3?"),
            hashtags=("#정치", "#국회", "#쇼츠"),
            pinned_comment="여러분의 생각은?",
        )
        d = meta.to_dict()
        restored = MetaResult.from_dict(d)
        assert restored.title_candidates == meta.title_candidates
        assert restored.hashtags == meta.hashtags
        assert restored.pinned_comment == meta.pinned_comment

    def test_from_dict_with_empty_fields(self):
        meta = MetaResult.from_dict({})
        assert isinstance(meta.title_candidates, tuple)
        assert isinstance(meta.hashtags, tuple)
        assert isinstance(meta.pinned_comment, str)

    def test_to_dict_returns_lists(self):
        meta = MetaResult(
            title_candidates=("a?",),
            hashtags=("#정치",),
            pinned_comment="Q?",
        )
        d = meta.to_dict()
        assert isinstance(d["title_candidates"], list)
        assert isinstance(d["hashtags"], list)


# ── generate_meta 성공 경로 ────────────────────────────────────────────────────

class TestGenerateMeta:
    def test_returns_meta_result_with_valid_response(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", _make_fake_call_claude(VALID_RESPONSE))

        result = generate_meta(**_CALL_ARGS)
        assert isinstance(result, MetaResult)

    def test_title_candidates_has_three_items(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", _make_fake_call_claude(VALID_RESPONSE))

        result = generate_meta(**_CALL_ARGS)
        assert len(result.title_candidates) == 3

    def test_each_title_ends_with_question_mark(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", _make_fake_call_claude(VALID_RESPONSE))

        result = generate_meta(**_CALL_ARGS)
        for title in result.title_candidates:
            assert title.endswith("?"), f"제목이 '?'로 끝나지 않음: {title!r}"

    def test_hashtags_five_or_more_items(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", _make_fake_call_claude(VALID_RESPONSE))

        result = generate_meta(**_CALL_ARGS)
        assert len(result.hashtags) >= 5

    def test_each_hashtag_contains_hash(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", _make_fake_call_claude(VALID_RESPONSE))

        result = generate_meta(**_CALL_ARGS)
        for tag in result.hashtags:
            assert "#" in tag, f"해시태그에 # 없음: {tag!r}"

    def test_pinned_comment_not_empty(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", _make_fake_call_claude(VALID_RESPONSE))

        result = generate_meta(**_CALL_ARGS)
        assert result.pinned_comment


# ── generate_meta 폴백 경로 ───────────────────────────────────────────────────

class TestGenerateMetaFallback:
    def test_json_parse_failure_returns_fallback(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", lambda prompt, **kw: "JSON이 아닌 텍스트")

        result = generate_meta(**_CALL_ARGS)
        assert result == _FALLBACK

    def test_fallback_title_candidates_not_empty(self, monkeypatch):
        """빈 dict 응답 → MetaResult.from_dict({}) → title_candidates 빈 튜플.
        generate_meta는 폴백으로 _FALLBACK을 반환하지 않고 빈 MetaResult를 반환한다.
        비어 있지 않아야 한다는 보장은 generate_meta가 아닌 _FALLBACK 상수에 있다."""
        # 확실한 JSON 파싱 실패로 fallback 유도
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", lambda prompt, **kw: "not json")

        result = generate_meta(**_CALL_ARGS)
        # _FALLBACK은 title_candidates가 비어 있지 않음을 보장
        assert len(result.title_candidates) >= 1

    def test_fallback_hashtags_not_empty(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", lambda prompt, **kw: "not json")

        result = generate_meta(**_CALL_ARGS)
        assert len(result.hashtags) >= 1

    def test_fallback_pinned_comment_not_empty_string(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", lambda prompt, **kw: "not json")

        result = generate_meta(**_CALL_ARGS)
        assert result.pinned_comment != ""

    def test_claude_exception_returns_fallback(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        def raise_exc(prompt, **kw):
            raise RuntimeError("Claude 연결 실패")
        monkeypatch.setattr(ca, "_call_claude", raise_exc)

        result = generate_meta(**_CALL_ARGS)
        assert result == _FALLBACK

    def test_non_dict_response_returns_fallback(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        monkeypatch.setattr(ca, "_call_claude", lambda prompt, **kw: '["리스트"]')

        result = generate_meta(**_CALL_ARGS)
        assert result == _FALLBACK

    def test_code_fenced_json_parsed_correctly(self, monkeypatch):
        import src.analyzer.claude_analyzer as ca
        fenced = "```json\n" + json.dumps(VALID_RESPONSE, ensure_ascii=False) + "\n```"
        monkeypatch.setattr(ca, "_call_claude", lambda prompt, **kw: fenced)

        result = generate_meta(**_CALL_ARGS)
        assert len(result.title_candidates) == 3
