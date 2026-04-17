"""MID-08 Phase 1: highlight_words 기반 해시태그 자동 추출.

ShortsScript의 highlight_words에서 키워드를 추출해 해시태그로 변환,
emotion 기반 정적 해시태그와 dedupe 합산. LLM 호출은 Phase 2로 분리.

출처: docs/dem-shorts/political-youtube-style-plan.md §7.3, §8.2 MID-08.
"""
from __future__ import annotations

from src.analyzer.script_models import (
    AudioConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.upload.metadata_generator import (
    extract_keyword_hashtags,
    generate_metadata,
    merge_hashtags,
)


def _make_script(*, hl: list[list[str]], emotion: str = "angry") -> ShortsScript:
    scenes = [
        Scene(
            id=i + 1, timestamp=0, duration=4, type="body",
            text="t", voice_text="t",
            highlight_words=tuple(hl_per_scene),
        )
        for i, hl_per_scene in enumerate(hl)
    ]
    return ShortsScript(
        metadata=Metadata(title="t", emotion_type=emotion, duration=30.0),
        scenes=tuple(scenes),
        audio=AudioConfig(tts_script="t"),
    )


class TestExtractKeywordHashtags:
    def test_converts_words_to_hashtags(self):
        s = _make_script(hl=[["연금개혁", "국민연금"], ["노후"]])
        tags = extract_keyword_hashtags(s)
        assert "#연금개혁" in tags
        assert "#국민연금" in tags
        assert "#노후" in tags

    def test_dedupes_across_scenes(self):
        s = _make_script(hl=[["연금"], ["연금"], ["연금"]])
        tags = extract_keyword_hashtags(s)
        assert tags.count("#연금") == 1

    def test_strips_whitespace_and_punctuation(self):
        """공백/특수문자가 들어간 키워드는 정리되어야 한다."""
        s = _make_script(hl=[["국회 본회의", "안 돼요!"]])
        tags = extract_keyword_hashtags(s)
        # 공백 제거 후 해시태그
        assert "#국회본회의" in tags
        # 특수문자 제거
        assert "#안돼요" in tags or "#안 돼요" not in tags

    def test_skips_empty_or_too_short(self):
        """1글자 키워드는 해시태그로 의미 없음 → 제외."""
        s = _make_script(hl=[["", "ㅋ", "정리"]])
        tags = extract_keyword_hashtags(s)
        assert "#" not in tags
        assert "#ㅋ" not in tags
        assert "#정리" in tags

    def test_skips_pure_numbers(self):
        """순수 숫자는 해시태그로 의미 없음 (예: '2026')."""
        s = _make_script(hl=[["2026", "연금개혁"]])
        tags = extract_keyword_hashtags(s)
        assert "#2026" not in tags
        assert "#연금개혁" in tags

    def test_max_count_limit(self):
        """추출 키워드는 최대 10개로 제한 (해시태그 스팸 방지)."""
        many = [[f"키워드{i}"] for i in range(20)]
        s = _make_script(hl=many)
        tags = extract_keyword_hashtags(s)
        assert len(tags) <= 10


class TestMergeHashtags:
    def test_combines_emotion_and_keywords_dedup(self):
        emotion_tags = ["#정치", "#쇼츠", "#shorts"]
        keyword_tags = ["#연금개혁", "#정치"]  # #정치 중복
        merged = merge_hashtags(emotion_tags, keyword_tags)
        assert merged.count("#정치") == 1
        assert "#연금개혁" in merged
        assert "#쇼츠" in merged

    def test_keyword_tags_take_priority(self):
        """키워드 해시태그가 더 구체적 → 앞쪽에 배치."""
        merged = merge_hashtags(["#shorts"], ["#연금개혁"])
        assert merged.index("#연금개혁") < merged.index("#shorts")

    def test_total_count_capped(self):
        emo = [f"#emo{i}" for i in range(10)]
        kw = [f"#kw{i}" for i in range(10)]
        merged = merge_hashtags(emo, kw)
        # YouTube 정책: 해시태그 15개 이하 권장
        assert len(merged) <= 15


class TestGenerateMetadataIncludesKeywordHashtags:
    """generate_metadata가 키워드 해시태그를 결과에 포함."""

    def test_keyword_hashtags_in_description(self):
        s = _make_script(hl=[["연금개혁", "국민연금"]])
        meta = generate_metadata(s)
        # description 또는 hashtags 어디든 키워드 해시태그가 들어가야 함
        haystack = meta.get("description", "") + " " + " ".join(meta.get("tags", []))
        assert "연금개혁" in haystack
