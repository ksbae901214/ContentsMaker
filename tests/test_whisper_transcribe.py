"""Bugfix: NATV 영상에 자막이 없을 때 Whisper STT fallback 동작 검증.

사용자 시나리오: YouTube 영상에 한국어 자막 없음 → VTT 다운로드 실패 → 기존 코드는
빈 transcript로 진행해 Claude가 힌트만 보고 엉뚱한 내용 생성(환각).

수정: transcript 비었으면 Whisper STT 자동 fallback. Whisper도 실패하면 clear 에러.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestTranscribeVideoOrFallback:
    """Helper 함수: VTT 다운로드 시도 → 실패 시 Whisper STT 폴백."""

    def test_vtt_success_returns_transcript(self, tmp_path):
        """VTT가 존재하면 Whisper 호출 없이 그대로 반환."""
        from src.scraper.youtube_downloader import transcribe_video_or_fallback

        vtt = tmp_path / "x.ko.vtt"
        vtt.write_text(
            "WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nhello\n\n"
            "00:00:03.000 --> 00:00:06.000\nworld\n",
            encoding="utf-8",
        )
        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake")

        with patch(
            "src.scraper.youtube_downloader.download_subtitles",
            return_value=vtt,
        ), patch(
            "src.scraper.youtube_downloader._whisper_transcribe"
        ) as mock_whisper:
            transcript = transcribe_video_or_fallback(
                url="https://y.example/w", video_path=video, out_dir=tmp_path
            )

        assert len(transcript) >= 1
        mock_whisper.assert_not_called()

    def test_vtt_missing_falls_back_to_whisper(self, tmp_path):
        """VTT 다운로드 실패 → Whisper STT 호출, 그 결과를 transcript로 반환."""
        from src.scraper.youtube_downloader import transcribe_video_or_fallback

        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake")

        whisper_result = [
            {"start": 0.0, "end": 4.0, "text": "국민의힘 의원 발언"},
            {"start": 4.0, "end": 8.0, "text": "경제 정책 비판"},
        ]

        with patch(
            "src.scraper.youtube_downloader.download_subtitles",
            return_value=None,
        ), patch(
            "src.scraper.youtube_downloader._whisper_transcribe",
            return_value=whisper_result,
        ) as mock_whisper:
            transcript = transcribe_video_or_fallback(
                url="https://y.example/w", video_path=video, out_dir=tmp_path
            )

        assert transcript == whisper_result
        mock_whisper.assert_called_once()

    def test_whisper_also_fails_raises(self, tmp_path):
        """VTT·Whisper 모두 실패하면 명확한 에러 (환각 방지)."""
        from src.scraper.youtube_downloader import (
            TranscriptUnavailableError,
            transcribe_video_or_fallback,
        )

        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake")

        with patch(
            "src.scraper.youtube_downloader.download_subtitles",
            return_value=None,
        ), patch(
            "src.scraper.youtube_downloader._whisper_transcribe",
            side_effect=RuntimeError("whisper model 로딩 실패"),
        ):
            with pytest.raises(TranscriptUnavailableError) as ei:
                transcribe_video_or_fallback(
                    url="https://y.example/w",
                    video_path=video,
                    out_dir=tmp_path,
                )
            # 에러 메시지에 원인 힌트 포함
            msg = str(ei.value)
            assert "자막" in msg or "STT" in msg or "transcript" in msg.lower()

    def test_empty_whisper_result_treated_as_failure(self, tmp_path):
        """Whisper가 빈 리스트 반환해도 환각 방지를 위해 에러."""
        from src.scraper.youtube_downloader import (
            TranscriptUnavailableError,
            transcribe_video_or_fallback,
        )

        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake")

        with patch(
            "src.scraper.youtube_downloader.download_subtitles",
            return_value=None,
        ), patch(
            "src.scraper.youtube_downloader._whisper_transcribe",
            return_value=[],
        ):
            with pytest.raises(TranscriptUnavailableError):
                transcribe_video_or_fallback(
                    url="https://y.example/w",
                    video_path=video,
                    out_dir=tmp_path,
                )

    def test_missing_video_file_raises_before_whisper(self, tmp_path):
        """영상 파일 자체가 없으면 Whisper 시도 안 함."""
        from src.scraper.youtube_downloader import (
            TranscriptUnavailableError,
            transcribe_video_or_fallback,
        )

        missing = tmp_path / "missing.mp4"

        with patch(
            "src.scraper.youtube_downloader.download_subtitles",
            return_value=None,
        ), patch(
            "src.scraper.youtube_downloader._whisper_transcribe"
        ) as mock_whisper:
            with pytest.raises(TranscriptUnavailableError):
                transcribe_video_or_fallback(
                    url="https://y.example/w",
                    video_path=missing,
                    out_dir=tmp_path,
                )
        mock_whisper.assert_not_called()
