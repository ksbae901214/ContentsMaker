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
        # 모든 라인에 실제 대본 내용이 들어가야 한다 — 고정 인트로 금지
        for ln in lines:
            assert ln.strip()
        # 첫 줄은 타이틀/hook 씬 기반이어야 한다
        assert any(w in lines[0] for w in ("결혼식", "남자친구", "언니"))
        # 마지막 줄은 최종 씬의 핵심 내용을 반영해야 한다
        assert "심하" in lines[2] or "레드" in lines[2]


class TestBuildThreeLineSummary:
    """대본 전체(voice_text) 에서 첫·중·말 문장을 뽑아 3줄 요약."""

    def _script(self, *voices, **meta):
        from src.analyzer.script_models import (
            ShortsScript, Scene, Metadata, AudioConfig, BackgroundConfig,
        )
        scenes = tuple(
            Scene(
                id=i + 1,
                timestamp=float(i * 4),
                duration=4.0,
                type="title" if i == 0 else "body",
                text=v,
                voice_text=v,
                emphasis="high" if i == 0 else "medium",
            )
            for i, v in enumerate(voices)
        )
        return ShortsScript(
            metadata=Metadata(
                title=meta.get("title", voices[0]),
                emotion_type=meta.get("emotion", "relatable"),
                duration=float(len(voices) * 4),
            ),
            scenes=scenes,
            audio=AudioConfig(tts_script=" ".join(voices)),
            background=BackgroundConfig(type="gradient", colors=("#000",)),
        )

    def test_three_distinct_lines(self):
        from src.upload.metadata_generator import _build_three_line_summary
        script = self._script(
            "하루 12시간 근무 이야기입니다",
            "사장은 매일 야근을 강요했어요.",
            "결국 퇴직금 없이 나왔죠.",
            "법적 대응을 준비 중입니다.",
            "여러분이라면 어떻게 하시겠어요?",
        )
        lines = _build_three_line_summary(script).split("\n")
        assert len(lines) == 3
        assert lines[0] != lines[1]
        assert lines[1] != lines[2]

    def test_first_line_uses_title_or_hook(self):
        from src.upload.metadata_generator import _build_three_line_summary
        script = self._script(
            "회사 월급 이야기",
            "월급이 밀렸어요.",
            "3개월째 못 받았습니다.",
        )
        lines = _build_three_line_summary(script).split("\n")
        # 첫 줄에 타이틀의 핵심 키워드가 있어야 한다
        assert "월급" in lines[0] or "회사" in lines[0]

    def test_last_line_comes_from_closing_scene(self):
        from src.upload.metadata_generator import _build_three_line_summary
        script = self._script(
            "사건의 시작",
            "중간 전개",
            "절정 장면",
            "예상 밖의 결말 반전",
        )
        lines = _build_three_line_summary(script).split("\n")
        # 마지막 줄은 맨 마지막 씬의 어휘를 반영
        assert "결말" in lines[2] or "반전" in lines[2]

    def test_single_sentence_script_is_handled(self):
        from src.upload.metadata_generator import _build_three_line_summary
        script = self._script("한 문장뿐인 영상이에요.")
        result = _build_three_line_summary(script)
        lines = result.split("\n")
        # 최소한 한 줄에 원본 문구가 들어가야 한다 (빈 요약 금지)
        assert any("한 문장뿐" in ln for ln in lines)

    def test_empty_voice_falls_back_to_display_text(self):
        from src.upload.metadata_generator import _build_three_line_summary
        from src.analyzer.script_models import (
            ShortsScript, Scene, Metadata, AudioConfig, BackgroundConfig,
        )
        script = ShortsScript(
            metadata=Metadata(title="제목", emotion_type="funny", duration=8.0),
            scenes=(
                Scene(id=1, timestamp=0, duration=4, type="title",
                      text="첫 씬 텍스트", voice_text=""),
                Scene(id=2, timestamp=4, duration=4, type="body",
                      text="본문 텍스트 내용", voice_text=""),
            ),
            audio=AudioConfig(tts_script=""),
            background=BackgroundConfig(type="gradient", colors=()),
        )
        result = _build_three_line_summary(script)
        # voice_text 가 비어도 text 로 폴백
        assert "첫 씬" in result or "본문" in result

    def test_line_length_trimmed_when_very_long(self):
        """한 문장이 120자 넘으면 60자 근처에서 자른다 (읽기 편의)."""
        from src.upload.metadata_generator import _build_three_line_summary
        long_voice = "가" * 150
        script = self._script(
            "타이틀",
            long_voice,
            "마지막",
        )
        lines = _build_three_line_summary(script).split("\n")
        assert all(len(ln) <= 90 for ln in lines), f"line too long: {[len(ln) for ln in lines]}"

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
