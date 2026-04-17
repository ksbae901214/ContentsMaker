"""Tests for transcript_aligner — content-aware scene/video alignment.

natv_clip 모드에서 TTS 길이에 비례해 영상을 잘라 자막과 영상내용이
어긋나던 문제를 막기 위해, 각 씬의 voice_text를 원본 transcript에
퍼지 매칭해 해당 구간의 실제 timestamp 로 자르는 모듈.
"""
from __future__ import annotations

import pytest

from src.dem_shorts.editor.transcript_aligner import (
    align_scene_to_transcript,
    align_scenes_to_transcript,
)


# ---------------------------------------------------------------------------
# align_scene_to_transcript (단일 씬)
# ---------------------------------------------------------------------------


class TestAlignSceneToTranscript:
    def _transcript(self) -> list[dict]:
        return [
            {"start": 10.0, "end": 12.5, "text": "안녕하세요 존경하는 국민 여러분"},
            {"start": 12.5, "end": 15.0, "text": "오늘 이 자리에서 말씀드립니다"},
            {"start": 15.0, "end": 18.0, "text": "경제 위기를 극복하기 위한 방안"},
            {"start": 18.0, "end": 21.5, "text": "모두가 함께 나서야 합니다"},
            {"start": 21.5, "end": 24.0, "text": "감사합니다"},
        ]

    def test_exact_match_returns_segment_timestamps(self):
        t = self._transcript()
        result = align_scene_to_transcript(
            voice_text="경제 위기를 극복하기 위한 방안",
            transcript=t,
            clip_start=10.0,
            clip_end=24.0,
        )
        assert result is not None
        start, end = result
        assert start == pytest.approx(15.0, abs=0.01)
        assert end == pytest.approx(18.0, abs=0.01)

    def test_partial_match_picks_best_segment(self):
        t = self._transcript()
        # voice_text가 일부 단어만 공유 — 가장 유사한 segment 선택
        result = align_scene_to_transcript(
            voice_text="경제 위기 극복 방안을 말했습니다",
            transcript=t,
            clip_start=10.0,
            clip_end=24.0,
        )
        assert result is not None
        start, end = result
        # Should align to the "경제 위기…" segment (15.0~18.0)
        assert start == pytest.approx(15.0, abs=0.5)

    def test_returns_none_when_no_match(self):
        t = self._transcript()
        result = align_scene_to_transcript(
            voice_text="전혀 상관없는 문장입니다 날씨가 좋아요",
            transcript=t,
            clip_start=10.0,
            clip_end=24.0,
        )
        assert result is None

    def test_ignores_segments_outside_clip_window(self):
        t = self._transcript() + [
            {"start": 100.0, "end": 103.0, "text": "경제 위기를 극복하기 위한 방안"},
        ]
        # 동일한 텍스트가 밖에 있어도 clip 윈도우(10~24) 안에서만 매칭
        result = align_scene_to_transcript(
            voice_text="경제 위기를 극복하기 위한 방안",
            transcript=t,
            clip_start=10.0,
            clip_end=24.0,
        )
        assert result is not None
        start, _ = result
        assert 10.0 <= start <= 24.0

    def test_multi_segment_match_spans_across(self):
        """voice_text 가 두 연속 segment 를 아우르면 합쳐진 범위 반환."""
        t = self._transcript()
        result = align_scene_to_transcript(
            voice_text="안녕하세요 존경하는 국민 여러분 오늘 이 자리에서",
            transcript=t,
            clip_start=10.0,
            clip_end=24.0,
            max_merge=3,
        )
        assert result is not None
        start, end = result
        assert start == pytest.approx(10.0, abs=0.01)
        assert end >= 15.0  # covers segments 1-2

    def test_empty_voice_text_returns_none(self):
        t = self._transcript()
        assert align_scene_to_transcript("", t, 10.0, 24.0) is None
        assert align_scene_to_transcript("   ", t, 10.0, 24.0) is None

    def test_empty_transcript_returns_none(self):
        assert align_scene_to_transcript("경제 위기", [], 0.0, 30.0) is None


# ---------------------------------------------------------------------------
# align_scenes_to_transcript (전체)
# ---------------------------------------------------------------------------


class TestAlignScenesToTranscript:
    def test_monotonic_output(self):
        """Scene 순서는 보존, timestamp 가 역행해서는 안 된다."""
        transcript = [
            {"start": 0.0, "end": 3.0, "text": "첫 문장입니다"},
            {"start": 3.0, "end": 6.0, "text": "두 번째 문장이지요"},
            {"start": 6.0, "end": 9.0, "text": "마지막 문장입니다"},
        ]
        scenes = [
            {"scene_id": 1, "voice_text": "첫 문장입니다", "start_ms": 0, "end_ms": 2000},
            {"scene_id": 2, "voice_text": "두 번째 문장이지요", "start_ms": 2000, "end_ms": 4000},
            {"scene_id": 3, "voice_text": "마지막 문장입니다", "start_ms": 4000, "end_ms": 6500},
        ]
        result = align_scenes_to_transcript(
            scenes=scenes,
            transcript=transcript,
            clip_start=0.0,
            clip_end=9.0,
        )
        assert len(result) == 3
        # IDs preserved
        assert [r["scene_id"] for r in result] == [1, 2, 3]
        # Monotonic
        for i in range(1, len(result)):
            assert result[i]["start_sec"] >= result[i - 1]["start_sec"]

    def test_unmatched_scenes_fall_back_to_proportional(self):
        """매칭 실패 씬은 비례 컷 폴백 — 결과 키는 동일 스키마."""
        transcript = [
            {"start": 0.0, "end": 3.0, "text": "첫 문장입니다"},
        ]
        scenes = [
            {"scene_id": 1, "voice_text": "첫 문장입니다", "start_ms": 0, "end_ms": 2000},
            {"scene_id": 2, "voice_text": "관련없는 텍스트 입니다 정말", "start_ms": 2000, "end_ms": 4000},
        ]
        result = align_scenes_to_transcript(
            scenes=scenes,
            transcript=transcript,
            clip_start=0.0,
            clip_end=4.0,
        )
        assert len(result) == 2
        for r in result:
            assert "start_sec" in r and "end_sec" in r
            assert 0.0 <= r["start_sec"] <= 4.0
            assert r["end_sec"] > r["start_sec"]

    def test_duration_within_clip_range(self):
        """결과 (start,end) 는 [clip_start, clip_end] 범위 안."""
        transcript = [
            {"start": 5.0, "end": 8.0, "text": "한 문장 샘플"},
        ]
        scenes = [
            {"scene_id": 1, "voice_text": "한 문장 샘플", "start_ms": 0, "end_ms": 3000},
        ]
        result = align_scenes_to_transcript(
            scenes=scenes,
            transcript=transcript,
            clip_start=5.0,
            clip_end=8.0,
        )
        assert result[0]["start_sec"] >= 5.0
        assert result[0]["end_sec"] <= 8.0 + 0.01
