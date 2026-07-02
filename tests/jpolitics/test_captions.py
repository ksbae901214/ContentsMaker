"""CaptionCue / build_caption_cues 테스트 (Feature 027 Phase 2)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.jpolitics.models.clip import CaptionCue
from src.jpolitics.models.moment import Moment
from src.jpolitics.video.captions import (
    _deduplicate_consecutive,
    _segments_to_cues,
    _split_to_lines,
    build_caption_cues,
    save_caption_cues,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _moment(start: float = 10.0, end: float = 30.0) -> Moment:
    return Moment(
        start_sec=start,
        end_sec=end,
        kind="clash",
        speaker="테스트",
        summary="테스트 모먼트",
        hook_question="왜?",
        keywords=("테스트",),
        confidence=0.9,
    )


def _fake_vtt(tmp_path: Path, cues: list[tuple[str, str, str]]) -> Path:
    """가짜 VTT 파일 생성. cues = [(start_hms, end_hms, text), ...]."""
    lines = ["WEBVTT", ""]
    for start, end, text in cues:
        lines += [f"{start} --> {end}", text, ""]
    vtt_path = tmp_path / "test.ko.vtt"
    vtt_path.write_text("\n".join(lines), encoding="utf-8")
    return vtt_path


# ── CaptionCue 모델 테스트 ─────────────────────────────────────────────────

class TestCaptionCue:
    def test_roundtrip(self):
        cue = CaptionCue(start_sec=1.5, end_sec=3.0, text="테스트")
        restored = CaptionCue.from_dict(cue.to_dict())
        assert restored == cue

    def test_frozen(self):
        cue = CaptionCue(start_sec=0.0, end_sec=1.0, text="x")
        with pytest.raises(Exception):
            cue.text = "y"  # type: ignore[misc]

    def test_camel_case_from_dict(self):
        cue = CaptionCue.from_dict({"startSec": 2.0, "endSec": 4.0, "text": "hello"})
        assert cue.start_sec == 2.0
        assert cue.end_sec == 4.0


# ── 텍스트 분리 테스트 ────────────────────────────────────────────────────

class TestSplitToLines:
    def test_short_text_unchanged(self):
        assert "\n" not in _split_to_lines("짧은 텍스트")

    def test_long_text_split(self):
        result = _split_to_lines("국회에서 정말 재밌는 일이 일어났습니다 여기서 설명합니다")
        assert "\n" in result

    def test_single_long_word_split(self):
        # 공백 없는 30자 이상 단어
        result = _split_to_lines("이렇게아주길고긴단어가공백없이하나만있는경우에도줄바꿈이")
        assert "\n" in result


# ── 중복 제거 테스트 ──────────────────────────────────────────────────────

class TestDeduplicateConsecutive:
    def test_removes_consecutive_duplicates(self):
        cues = [
            CaptionCue(0.0, 1.0, "같은 텍스트"),
            CaptionCue(1.0, 2.0, "같은 텍스트"),
            CaptionCue(2.0, 3.0, "다른 텍스트"),
        ]
        result = _deduplicate_consecutive(cues)
        assert len(result) == 2
        assert result[0].text == "같은 텍스트"
        assert result[1].text == "다른 텍스트"

    def test_non_consecutive_duplicates_kept(self):
        cues = [
            CaptionCue(0.0, 1.0, "A"),
            CaptionCue(1.0, 2.0, "B"),
            CaptionCue(2.0, 3.0, "A"),
        ]
        result = _deduplicate_consecutive(cues)
        assert len(result) == 3

    def test_empty_list(self):
        assert _deduplicate_consecutive([]) == []


# ── segments_to_cues 필터·상대화 테스트 ───────────────────────────────────

class TestSegmentsToCues:
    def test_filters_out_of_range(self):
        segments = [
            {"start": 0.0, "end": 5.0, "text": "범위 밖"},
            {"start": 10.0, "end": 15.0, "text": "범위 안"},
            {"start": 30.0, "end": 35.0, "text": "범위 밖"},
        ]
        cues = _segments_to_cues(segments, clip_start=9.5, clip_end=25.5)
        assert len(cues) == 1
        assert "범위 안" in cues[0].text

    def test_relativizes_timestamps(self):
        segments = [{"start": 10.0, "end": 12.0, "text": "발언"}]
        cues = _segments_to_cues(segments, clip_start=9.5, clip_end=25.0)
        assert len(cues) == 1
        assert cues[0].start_sec == pytest.approx(0.5, abs=0.01)
        assert cues[0].end_sec == pytest.approx(2.5, abs=0.01)

    def test_clamps_negative_start(self):
        segments = [{"start": 9.0, "end": 11.0, "text": "걸침"}]
        cues = _segments_to_cues(segments, clip_start=10.0, clip_end=20.0)
        assert len(cues) == 1
        assert cues[0].start_sec == 0.0  # 클램프

    def test_empty_text_skipped(self):
        segments = [{"start": 10.0, "end": 11.0, "text": ""}]
        cues = _segments_to_cues(segments, clip_start=9.0, clip_end=20.0)
        assert len(cues) == 0


# ── build_caption_cues 통합 테스트 ────────────────────────────────────────

class TestBuildCaptionCues:
    def test_reuses_existing_vtt(self, tmp_path: Path):
        """기존 VTT 파일이 있으면 download_subtitles를 호출하지 않는다."""
        _fake_vtt(tmp_path, [
            ("00:00:09.500", "00:00:11.000", "먼저 발언"),
            ("00:00:11.500", "00:00:13.000", "이어서 발언"),
        ])
        moment = _moment(start=10.0, end=20.0)
        # 소스 모듈에서 패치 (captions.py는 함수 내 lazy import를 사용함)
        with patch("src.scraper.youtube_downloader.download_subtitles") as mock_dl:
            cues = build_caption_cues(
                work_dir=tmp_path,
                source_url="https://youtube.com/watch?v=test",
                video_path=tmp_path / "fake.mp4",
                moment=moment,
                pad_before=0.5,
            )
        mock_dl.assert_not_called()
        assert len(cues) >= 1

    def test_downloads_when_no_vtt(self, tmp_path: Path):
        """VTT 없을 때 download_subtitles() 호출 후 결과 VTT 파싱."""
        # work_dir에 VTT 파일 없는 상태에서 시작
        work_dir = tmp_path / "no_vtt_work"
        work_dir.mkdir()

        # download_subtitles가 반환할 VTT 파일은 work_dir 외부에 미리 생성
        vtt_file = tmp_path / "downloaded.ko.vtt"
        vtt_content = "\n".join([
            "WEBVTT", "",
            "00:00:09.500 --> 00:00:11.000", "다운로드된 자막", "",
        ])
        vtt_file.write_text(vtt_content, encoding="utf-8")

        moment = _moment(start=10.0, end=20.0)
        # 소스 모듈에서 패치
        with patch("src.scraper.youtube_downloader.download_subtitles") as mock_dl:
            mock_dl.return_value = vtt_file
            cues = build_caption_cues(
                work_dir=work_dir,
                source_url="https://youtube.com/watch?v=test",
                video_path=tmp_path / "fake.mp4",
                moment=moment,
                pad_before=0.5,
            )
        mock_dl.assert_called_once()
        assert isinstance(cues, list)

    def test_fallback_to_transcribe_when_download_fails(self, tmp_path: Path):
        """download_subtitles 실패 시 transcribe_video_or_fallback 폴백."""
        moment = _moment(start=10.0, end=20.0)
        fake_segments = [
            {"start": 9.5, "end": 11.0, "text": "Whisper로 인식된 발언"},
        ]
        # 소스 모듈에서 패치
        with (
            patch("src.scraper.youtube_downloader.download_subtitles", return_value=None),
            patch("src.scraper.youtube_downloader.transcribe_video_or_fallback", return_value=fake_segments) as mock_tr,
        ):
            cues = build_caption_cues(
                work_dir=tmp_path,
                source_url="https://youtube.com/watch?v=test",
                video_path=tmp_path / "fake.mp4",
                moment=moment,
                pad_before=0.5,
            )
        mock_tr.assert_called_once()
        assert any("Whisper" in c.text for c in cues)

    def test_duplicate_vtt_text_merged(self, tmp_path: Path):
        """VTT 누적 자막 중복 제거 확인."""
        _fake_vtt(tmp_path, [
            ("00:00:09.500", "00:00:11.000", "누적 자막 텍스트"),
            ("00:00:10.000", "00:00:11.500", "누적 자막 텍스트"),  # 중복
            ("00:00:11.500", "00:00:13.000", "다른 발언"),
        ])
        moment = _moment(start=10.0, end=20.0)
        cues = build_caption_cues(
            work_dir=tmp_path,
            source_url="https://youtube.com/watch?v=test",
            video_path=tmp_path / "fake.mp4",
            moment=moment,
            pad_before=0.5,
        )
        texts = [c.text for c in cues]
        # 연속 중복은 1개만 남아야 한다
        for i in range(len(texts) - 1):
            assert texts[i] != texts[i + 1], f"연속 중복 발견: {texts[i]!r}"

    def test_save_caption_cues(self, tmp_path: Path):
        """save_caption_cues() — JSON 저장 및 복원."""
        import json
        cues = [
            CaptionCue(0.5, 2.0, "첫 번째 자막"),
            CaptionCue(2.5, 4.0, "두 번째 자막"),
        ]
        out = save_caption_cues(cues, tmp_path, 1)
        assert out.name == "captions_1.json"
        loaded = json.loads(out.read_text())
        assert len(loaded) == 2
        assert loaded[0]["text"] == "첫 번째 자막"
