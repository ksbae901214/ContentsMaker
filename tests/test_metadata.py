"""Tests for YouTube metadata generator."""
import pytest
from src.upload.metadata_generator import (
    generate_metadata,
    EMOTION_HASHTAGS,
    BANNED_CLICKBAIT_WORDS,
)
from src.analyzer.script_models import ShortsScript, Metadata, Scene, AudioConfig


def _make_script(title: str, source_type: str = "blind", duration: float = 45.0) -> ShortsScript:
    return ShortsScript(
        metadata=Metadata(
            title=title,
            emotion_type="relatable",
            duration=duration,
            source_type=source_type,
        ),
        scenes=(
            Scene(
                id=1, timestamp=0, duration=5, type="title",
                text="이재명 의원 본회의 발언", voice_text="이재명 의원 본회의 발언",
            ),
            Scene(
                id=2, timestamp=5, duration=8, type="body",
                text="오늘 국회 본회의에서 주요 안건이 논의되었습니다",
                voice_text="오늘 국회 본회의에서 주요 안건이 논의되었습니다",
            ),
        ),
        audio=AudioConfig(tts_script="test"),
    )


class TestGenerateMetadata:
    def test_basic_metadata(self, sample_script):
        meta = generate_metadata(sample_script)
        assert "title" in meta
        assert "description" in meta
        assert "tags" in meta
        assert "summary" in meta
        assert "hashtags" in meta

    def test_title_format(self, sample_script):
        meta = generate_metadata(sample_script)
        assert meta["title"] == sample_script.metadata.title

    def test_title_max_length(self, sample_script):
        meta = generate_metadata(sample_script)
        assert len(meta["title"]) <= 100

    def test_description_contains_emotion(self, sample_script):
        meta = generate_metadata(sample_script)
        assert sample_script.metadata.emotion_type in meta["description"]

    def test_description_contains_duration(self, sample_script):
        meta = generate_metadata(sample_script)
        assert str(sample_script.metadata.duration) in meta["description"]

    def test_tags_list(self, sample_script):
        meta = generate_metadata(sample_script)
        assert isinstance(meta["tags"], list)
        assert len(meta["tags"]) <= 30
        assert "블라인드" in meta["tags"]
        assert "shorts" in meta["tags"]

    def test_hashtags_string(self, sample_script):
        meta = generate_metadata(sample_script)
        assert "#" in meta["hashtags"]
        assert isinstance(meta["hashtags"], str)

    def test_summary_three_lines(self, sample_script):
        meta = generate_metadata(sample_script)
        lines = meta["summary"].split("\n")
        assert len(lines) == 3
        assert "커뮤니티" in lines[0]  # fixed intro line

    def test_all_emotions_have_hashtags(self):
        for emotion in ["funny", "touching", "angry", "relatable"]:
            assert emotion in EMOTION_HASHTAGS
            tags = EMOTION_HASHTAGS[emotion]
            assert "#블라인드" in tags
            assert "#shorts" in tags

    def test_tags_include_scene_keywords(self):
        script = ShortsScript(
            metadata=Metadata(title="회사 월급", emotion_type="angry", duration=40),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="title",
                      text="회사에서 짤렸어요", voice_text="회사에서 짤렸어요"),
                Scene(id=2, timestamp=5, duration=8, type="body",
                      text="상사가 갑자기 나가라고 했어요", voice_text="상사가 갑자기 나가라고 했어요"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        meta = generate_metadata(script)
        # Tags should include words from scenes
        assert len(meta["tags"]) > 5

    def test_unknown_emotion_defaults(self):
        script = ShortsScript(
            metadata=Metadata(title="제목", emotion_type="unknown", duration=30),
            scenes=(
                Scene(id=1, timestamp=0, duration=5, type="title",
                      text="제목", voice_text="제목"),
            ),
            audio=AudioConfig(tts_script="test"),
        )
        meta = generate_metadata(script)
        # Should fallback to relatable hashtags
        assert "#일상" in meta["hashtags"]


class TestClickbaitGuard:
    """QW-08: YouTube 정책 위반 / 계정 정지 리스크 차단."""

    def test_banned_words_constant_includes_required(self):
        for word in [
            "충격", "충격적", "믿을 수 없는", "절대", "100%",
            "완벽한", "반드시", "결국", "경악", "폭로",
        ]:
            assert word in BANNED_CLICKBAIT_WORDS, f"missing banned word: {word}"

    def test_clean_title_passes_through(self):
        script = _make_script("국회 본회의 정리")
        meta = generate_metadata(script)
        assert meta["title"] == "국회 본회의 정리"

    def test_clickbait_word_triggers_fallback_title(self):
        script = _make_script("충격! 이재명 의원 발언", source_type="political")
        meta = generate_metadata(script)
        # No banned word should remain in title
        for word in BANNED_CLICKBAIT_WORDS:
            assert word not in meta["title"]

    def test_political_source_uses_political_category(self):
        script = _make_script("100% 폭로된 발언", source_type="political")
        meta = generate_metadata(script)
        assert "[국회]" in meta["title"]

    def test_blind_source_does_not_use_political_category(self):
        script = _make_script("충격적인 사연", source_type="blind")
        meta = generate_metadata(script)
        assert "[국회]" not in meta["title"]

    def test_multiple_banned_words_all_removed(self):
        script = _make_script("믿을 수 없는 폭로 100% 충격")
        meta = generate_metadata(script)
        for word in ["믿을 수 없는", "폭로", "100%", "충격"]:
            assert word not in meta["title"]

    def test_fact_kernel_preserved_in_fallback(self):
        # Fact words (의원 이름, 발언) should survive sanitization
        script = _make_script("충격! 이재명 의원 본회의 발언", source_type="political")
        meta = generate_metadata(script)
        assert "이재명" in meta["title"] or "본회의" in meta["title"]

    def test_fallback_title_within_max_length(self):
        long_title = "충격! " + "가" * 200
        script = _make_script(long_title)
        meta = generate_metadata(script)
        assert len(meta["title"]) <= 100

    def test_description_strips_banned_words(self):
        script = _make_script("충격 폭로 사건")
        meta = generate_metadata(script)
        for word in ["충격", "폭로"]:
            assert word not in meta["description"]

    def test_chunglyeokjok_matched_before_chunglyeok(self):
        # "충격적" must be replaced as a whole, not leave "적" residue from "충격"
        script = _make_script("충격적 발언")
        meta = generate_metadata(script)
        assert "충격" not in meta["title"]
        assert "충격적" not in meta["title"]

    def test_empty_after_sanitization_uses_default_kernel(self):
        # Title made entirely of banned words → fallback still produces something
        script = _make_script("충격 경악 폭로 100%", source_type="political")
        meta = generate_metadata(script)
        assert meta["title"]  # non-empty
        assert "[국회]" in meta["title"]
        assert "발언" in meta["title"] or "정리" in meta["title"]
