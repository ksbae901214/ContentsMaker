"""Tests for TTS generator — generate_voice with mocked edge-tts."""
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from src.tts.edge_tts_generator import generate_voice, TTSError
from src.analyzer.script_models import ShortsScript, Metadata, AudioConfig, Scene


def _make_script(tts_text="테스트 음성 텍스트", voice="ko-KR-SunHiNeural"):
    return ShortsScript(
        metadata=Metadata(title="테스트", emotion_type="funny", duration=30),
        scenes=(
            Scene(id=1, timestamp=0, duration=5, type="title",
                  text="제목", voice_text="제목입니다"),
        ),
        audio=AudioConfig(tts_script=tts_text, voice=voice, rate="+20%", pitch="+0Hz"),
    )


class TestGenerateVoice:
    @patch("src.tts.edge_tts_generator._generate_async")
    def test_success(self, mock_async, tmp_data_dir):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"fake mp3 content")

        mock_async.side_effect = fake_gen
        script = _make_script()
        result = generate_voice(script, output_dir=tmp_data_dir / "audio")
        assert result.exists()
        assert result.suffix == ".mp3"
        assert result.stat().st_size > 0

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_empty_output_raises(self, mock_async, tmp_data_dir):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"")

        mock_async.side_effect = fake_gen
        script = _make_script()
        with pytest.raises(TTSError, match="생성되지 않았습니다"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_exception_wrapped(self, mock_async, tmp_data_dir):
        async def fail(*a, **k):
            raise RuntimeError("edge-tts broken")

        mock_async.side_effect = fail
        script = _make_script()
        with pytest.raises(TTSError, match="TTS 생성 실패"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    def test_empty_tts_text_raises(self, tmp_data_dir):
        script = _make_script(tts_text="")
        with pytest.raises(TTSError, match="비어있습니다"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    def test_whitespace_tts_text_raises(self, tmp_data_dir):
        script = _make_script(tts_text="   \n  ")
        with pytest.raises(TTSError, match="비어있습니다"):
            generate_voice(script, output_dir=tmp_data_dir / "audio")

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_output_dir_created(self, mock_async, tmp_path):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"mp3")

        mock_async.side_effect = fake_gen
        script = _make_script()
        new_dir = tmp_path / "new" / "audio"
        assert not new_dir.exists()
        result = generate_voice(script, output_dir=new_dir)
        assert new_dir.exists()
        assert result.exists()

    @patch("src.tts.edge_tts_generator._generate_async")
    def test_filename_contains_title(self, mock_async, tmp_data_dir):
        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"mp3")

        mock_async.side_effect = fake_gen
        script = _make_script()
        result = generate_voice(script, output_dir=tmp_data_dir / "audio")
        assert "mp3" in result.name


class TestSubtitleGroupTTS:
    """Phase 6 (2026-05-20): 분할 자식 씬 그룹 단위 1회 합성 — 무음 누적 제거."""

    def test_group_scenes_by_subtitle_group_single(self):
        from src.tts.edge_tts_generator import _group_scenes_by_subtitle_group
        scenes = [
            Scene(id=0, timestamp=0, duration=2, type="title", text="단독", voice_text="단독"),
            Scene(id=1, timestamp=2, duration=2, type="body", text="다른 단독", voice_text="다른"),
        ]
        groups = _group_scenes_by_subtitle_group(scenes)
        assert len(groups) == 2
        assert all(len(g) == 1 for g in groups)

    def test_group_scenes_by_subtitle_group_grouped(self):
        from src.tts.edge_tts_generator import _group_scenes_by_subtitle_group
        scenes = [
            Scene(id=0, timestamp=0, duration=2, type="title", text="a", voice_text="a"),
            Scene(id=1, timestamp=2, duration=2, type="body", text="b1", voice_text="b1",
                  subtitle_group_id=10, subtitle_group_first=True),
            Scene(id=2, timestamp=4, duration=2, type="body", text="b2", voice_text="b2",
                  subtitle_group_id=10, subtitle_group_first=False),
            Scene(id=3, timestamp=6, duration=2, type="body", text="b3", voice_text="b3",
                  subtitle_group_id=10, subtitle_group_first=False),
            Scene(id=4, timestamp=8, duration=2, type="comment", text="c", voice_text="c"),
        ]
        groups = _group_scenes_by_subtitle_group(scenes)
        assert len(groups) == 3
        assert [len(g) for g in groups] == [1, 3, 1]
        # 가운데 그룹의 자식들이 모두 같은 group_id
        assert all(s.subtitle_group_id == 10 for s in groups[1])

    def test_group_breaks_on_different_group_id(self):
        from src.tts.edge_tts_generator import _group_scenes_by_subtitle_group
        scenes = [
            Scene(id=0, timestamp=0, duration=1, type="body", text="a", voice_text="a",
                  subtitle_group_id=1, subtitle_group_first=True),
            Scene(id=1, timestamp=1, duration=1, type="body", text="b", voice_text="b",
                  subtitle_group_id=2, subtitle_group_first=True),  # 다른 group
        ]
        groups = _group_scenes_by_subtitle_group(scenes)
        assert len(groups) == 2

    @patch("src.tts.edge_tts_generator._get_mp3_duration_ms")
    @patch("src.tts.edge_tts_generator._generate_async")
    def test_grouped_synthesis_calls_tts_once_per_group(
        self, mock_async, mock_dur, tmp_data_dir
    ):
        """4-자식 그룹 → TTS 호출 1번 (4번이 아님)."""
        from src.tts.edge_tts_generator import generate_voice_with_timing

        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"fake mp3")

        mock_async.side_effect = fake_gen
        mock_dur.return_value = 2000  # 2초

        script = ShortsScript(
            metadata=Metadata(title="g", emotion_type="angry", duration=10),
            scenes=(
                Scene(id=0, timestamp=0, duration=2, type="body", text="ab", voice_text="ab",
                      subtitle_group_id=5, subtitle_group_first=True),
                Scene(id=1, timestamp=2, duration=2, type="body", text="cd", voice_text="cd",
                      subtitle_group_id=5, subtitle_group_first=False),
                Scene(id=2, timestamp=4, duration=2, type="body", text="ef", voice_text="ef",
                      subtitle_group_id=5, subtitle_group_first=False),
                Scene(id=3, timestamp=6, duration=2, type="body", text="gh", voice_text="gh",
                      subtitle_group_id=5, subtitle_group_first=False),
            ),
            audio=AudioConfig(tts_script="ab cd ef gh", voice="ko-KR-SunHiNeural",
                              rate="+20%", pitch="+0Hz"),
        )

        _path, timings = generate_voice_with_timing(
            script, output_dir=tmp_data_dir / "audio",
        )
        # TTS 호출은 그룹 1 + 아웃트로 1 = 2번 (4번이 아님)
        assert mock_async.call_count == 2

        # 첫 호출이 join된 텍스트
        first_call_text = mock_async.call_args_list[0].args[0]
        assert first_call_text == "ab cd ef gh"

        # 자식별 timing 분배 — 4개 씬 + 아웃트로(-1) = 5
        main_timings = [t for t in timings if t["scene_id"] != -1]
        assert len(main_timings) == 4
        # 글자수 동일(2자씩) → 각 500ms 근처
        for t in main_timings:
            child_dur = t["end_ms"] - t["start_ms"]
            assert 400 <= child_dur <= 600

        # 마지막 자식의 end_ms == 그룹 total (2000ms)
        assert main_timings[-1]["end_ms"] == 2000

    @patch("src.tts.edge_tts_generator._get_mp3_duration_ms")
    @patch("src.tts.edge_tts_generator._generate_async")
    def test_non_grouped_still_synth_per_scene(self, mock_async, mock_dur, tmp_data_dir):
        """group_id=None 씬들은 기존처럼 씬마다 TTS 호출."""
        from src.tts.edge_tts_generator import generate_voice_with_timing

        async def fake_gen(text, voice, rate, pitch, output_path):
            output_path.write_bytes(b"fake")

        mock_async.side_effect = fake_gen
        mock_dur.return_value = 1000

        script = ShortsScript(
            metadata=Metadata(title="ng", emotion_type="angry", duration=6),
            scenes=(
                Scene(id=0, timestamp=0, duration=2, type="body", text="A", voice_text="A"),
                Scene(id=1, timestamp=2, duration=2, type="body", text="B", voice_text="B"),
                Scene(id=2, timestamp=4, duration=2, type="body", text="C", voice_text="C"),
            ),
            audio=AudioConfig(tts_script="A B C", voice="ko-KR-SunHiNeural",
                              rate="+20%", pitch="+0Hz"),
        )

        _path, timings = generate_voice_with_timing(
            script, output_dir=tmp_data_dir / "audio",
        )
        # 단일 씬 3개 + 아웃트로 = 4 TTS 호출
        assert mock_async.call_count == 4
