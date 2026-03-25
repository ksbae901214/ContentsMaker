"""Tests for YouTube metadata generator."""
import pytest
from src.upload.metadata_generator import generate_metadata, EMOTION_HASHTAGS
from src.analyzer.script_models import ShortsScript, Metadata, Scene, AudioConfig


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
