"""api_bridge.py stdout/stderr 출력 + 모의 의존성 테스트 (Feature 027 Phase 4).

각 api_* 함수가 마지막 stdout 줄에 유효한 JSON을 출력하는지 검증한다.
실제 Claude API / 네트워크 / ffmpeg 호출은 모두 mock한다.

patch 대상은 api_bridge 모듈 수준 이름(src.jpolitics.api_bridge.*)이다.
api_bridge.py가 top-level import를 사용하므로 이 경로가 유효하다.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _last_json(capsys) -> dict:
    """capsys 캡처 stdout의 마지막 줄을 JSON으로 파싱한다."""
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert lines, "stdout 출력이 없습니다"
    return json.loads(lines[-1])


def _make_moment(
    start_sec=10.0,
    end_sec=40.0,
    kind="clash",
    speaker="추미애",
    summary="여야 충돌",
    hook_question="왜 멈췄나요?",
    keywords=("충돌",),
    confidence=0.9,
):
    from src.jpolitics.models.moment import Moment
    return Moment(
        start_sec=start_sec,
        end_sec=end_sec,
        kind=kind,
        speaker=speaker,
        summary=summary,
        hook_question=hook_question,
        keywords=keywords,
        confidence=confidence,
    )


# ── api_detect 테스트 ─────────────────────────────────────────────────────────

class TestApiDetect:
    def test_outputs_valid_json_on_stdout(self, capsys, tmp_path):
        fake_moment = _make_moment()

        with (
            patch("src.jpolitics.api_bridge.JPOLITICS_DATA_DIR", tmp_path),
            patch("src.jpolitics.api_bridge.get_video_metadata",
                  return_value={"title": "테스트영상", "channel": "YTN"}),
            patch("src.jpolitics.api_bridge.download_video",
                  return_value=tmp_path / "video.mp4"),
            patch("src.jpolitics.api_bridge.detect_moments_from_video",
                  return_value=[fake_moment]),
        ):
            from src.jpolitics.api_bridge import api_detect
            api_detect("https://youtu.be/test")

        data = _last_json(capsys)
        assert "work_dir" in data
        assert "moments" in data
        assert "channel" in data
        assert "video_title" in data

    def test_moments_sorted_by_confidence_desc(self, capsys, tmp_path):
        m_low = _make_moment(
            start_sec=10.0, end_sec=40.0, kind="clash", confidence=0.3,
        )
        m_high = _make_moment(
            start_sec=50.0, end_sec=80.0, kind="laughter",
            hook_question="왜 웃었나요?", confidence=0.9,
        )

        with (
            patch("src.jpolitics.api_bridge.JPOLITICS_DATA_DIR", tmp_path),
            patch("src.jpolitics.api_bridge.get_video_metadata",
                  return_value={"title": "vid", "channel": "MBC"}),
            patch("src.jpolitics.api_bridge.download_video",
                  return_value=tmp_path / "v.mp4"),
            patch("src.jpolitics.api_bridge.detect_moments_from_video",
                  return_value=[m_low, m_high]),
        ):
            from src.jpolitics.api_bridge import api_detect
            api_detect("https://youtu.be/test2")

        data = _last_json(capsys)
        confidences = [m["confidence"] for m in data["moments"]]
        assert confidences == sorted(confidences, reverse=True)

    def test_stderr_has_progress_messages(self, capsys, tmp_path):
        fake_moment = _make_moment(kind="other", hook_question="무슨 일?", confidence=0.5)

        with (
            patch("src.jpolitics.api_bridge.JPOLITICS_DATA_DIR", tmp_path),
            patch("src.jpolitics.api_bridge.get_video_metadata",
                  return_value={"title": "v", "channel": "KBS"}),
            patch("src.jpolitics.api_bridge.download_video",
                  return_value=tmp_path / "v.mp4"),
            patch("src.jpolitics.api_bridge.detect_moments_from_video",
                  return_value=[fake_moment]),
        ):
            from src.jpolitics.api_bridge import api_detect
            api_detect("https://youtu.be/test3")

        captured = capsys.readouterr()
        assert len(captured.err) > 0, "stderr 진행 메시지가 없습니다"

    def test_channel_in_output(self, capsys, tmp_path):
        fake_moment = _make_moment()

        with (
            patch("src.jpolitics.api_bridge.JPOLITICS_DATA_DIR", tmp_path),
            patch("src.jpolitics.api_bridge.get_video_metadata",
                  return_value={"title": "영상", "channel": "JTBC뉴스룸"}),
            patch("src.jpolitics.api_bridge.download_video",
                  return_value=tmp_path / "v.mp4"),
            patch("src.jpolitics.api_bridge.detect_moments_from_video",
                  return_value=[fake_moment]),
        ):
            from src.jpolitics.api_bridge import api_detect
            api_detect("https://youtu.be/ch_test")

        data = _last_json(capsys)
        assert data["channel"] == "JTBC뉴스룸"


# ── api_cut 테스트 ────────────────────────────────────────────────────────────

class TestApiCut:
    def _make_moments_json(self, work_dir: Path) -> None:
        from src.jpolitics.models.moment import MomentDetectionResult
        moment = _make_moment(
            speaker="박범계",
            summary="여야충돌",
            hook_question="왜 회의가 멈췄을까요?",
            confidence=0.85,
        )
        result = MomentDetectionResult(
            source_url="https://youtu.be/abc",
            video_title="테스트",
            channel="YTN",
            detector="gemini_multimodal",
            moments=(moment,),
        )
        result.save(work_dir / "moments.json")
        # 더미 원본 영상 파일 생성
        (work_dir / "video.mp4").touch()

    def test_outputs_valid_json_on_stdout(self, capsys, tmp_path):
        self._make_moments_json(tmp_path)

        from src.jpolitics.models.clip import ClipResult

        fake_clip = ClipResult(
            source_video=str(tmp_path / "video.mp4"),
            clip_path=str(tmp_path / "clip_1.mp4"),
            moment_dict={"hook_question": "q?", "keywords": []},
            width=1080, height=1920, fps=30.0, duration_sec=32.5, crop_x=0.5,
        )
        (tmp_path / "clip_1.mp4").touch()

        with (
            patch("src.jpolitics.api_bridge.make_moment_clip", return_value=fake_clip),
            patch("src.jpolitics.api_bridge.build_caption_cues", return_value=[]),
            patch("src.jpolitics.api_bridge.save_caption_cues",
                  return_value=tmp_path / "captions_1.json"),
        ):
            from src.jpolitics.api_bridge import api_cut
            api_cut(str(tmp_path), moment_idx=0)

        data = _last_json(capsys)
        assert "clip_path" in data
        assert "clip_json" in data
        assert "captions_json" in data
        assert "duration_sec" in data

    def test_duration_sec_matches_clip(self, capsys, tmp_path):
        self._make_moments_json(tmp_path)

        from src.jpolitics.models.clip import ClipResult

        fake_clip = ClipResult(
            source_video=str(tmp_path / "video.mp4"),
            clip_path=str(tmp_path / "clip_1.mp4"),
            moment_dict={"hook_question": "q?", "keywords": []},
            width=1080, height=1920, fps=30.0, duration_sec=44.2, crop_x=0.5,
        )
        (tmp_path / "clip_1.mp4").touch()

        with (
            patch("src.jpolitics.api_bridge.make_moment_clip", return_value=fake_clip),
            patch("src.jpolitics.api_bridge.build_caption_cues", return_value=[]),
            patch("src.jpolitics.api_bridge.save_caption_cues",
                  return_value=tmp_path / "captions_1.json"),
        ):
            from src.jpolitics.api_bridge import api_cut
            api_cut(str(tmp_path), moment_idx=0)

        data = _last_json(capsys)
        assert data["duration_sec"] == pytest.approx(44.2)

    def test_clip_path_ends_with_clip_1_mp4(self, capsys, tmp_path):
        self._make_moments_json(tmp_path)

        from src.jpolitics.models.clip import ClipResult

        fake_clip = ClipResult(
            source_video=str(tmp_path / "video.mp4"),
            clip_path=str(tmp_path / "clip_1.mp4"),
            moment_dict={"hook_question": "q?", "keywords": []},
            width=1080, height=1920, fps=30.0, duration_sec=30.0, crop_x=0.5,
        )
        (tmp_path / "clip_1.mp4").touch()

        with (
            patch("src.jpolitics.api_bridge.make_moment_clip", return_value=fake_clip),
            patch("src.jpolitics.api_bridge.build_caption_cues", return_value=[]),
            patch("src.jpolitics.api_bridge.save_caption_cues",
                  return_value=tmp_path / "captions_1.json"),
        ):
            from src.jpolitics.api_bridge import api_cut
            api_cut(str(tmp_path), moment_idx=0)

        data = _last_json(capsys)
        assert data["clip_path"].endswith("clip_1.mp4")


# ── api_render 테스트 ─────────────────────────────────────────────────────────

class TestApiRender:
    def _setup_work_dir(self, work_dir: Path) -> None:
        from src.jpolitics.models.moment import MomentDetectionResult
        from src.jpolitics.models.clip import ClipResult

        moment = _make_moment(summary="충돌", hook_question="왜?", confidence=0.8)
        det = MomentDetectionResult(
            source_url="https://youtu.be/xyz",
            video_title="영상",
            channel="JTBC",
            detector="transcript",
            moments=(moment,),
        )
        det.save(work_dir / "moments.json")

        clip = ClipResult(
            source_video=str(work_dir / "video.mp4"),
            clip_path=str(work_dir / "clip_1.mp4"),
            moment_dict=moment.to_dict(),
            width=1080, height=1920, fps=30.0, duration_sec=31.0, crop_x=0.5,
        )
        clip.save(work_dir, 1)

    def test_outputs_valid_json_on_stdout(self, capsys, tmp_path):
        # work_dir 이름에 날짜 접두사 추가 (renderer가 파싱)
        wd = tmp_path / "20240101_120000_테스트"
        wd.mkdir()
        self._setup_work_dir(wd)
        output_mp4 = wd / "output_1.mp4"
        output_mp4.touch()

        with patch("src.jpolitics.api_bridge.render_moment_short",
                   return_value=output_mp4):
            from src.jpolitics.api_bridge import api_render
            api_render(str(wd), moment_idx=0)

        data = _last_json(capsys)
        assert "output_path" in data
        assert data["output_path"].endswith("output_1.mp4")

    def test_output_path_is_absolute(self, capsys, tmp_path):
        wd = tmp_path / "20240615_093000_국회"
        wd.mkdir()
        self._setup_work_dir(wd)
        output_mp4 = wd / "output_1.mp4"
        output_mp4.touch()

        with patch("src.jpolitics.api_bridge.render_moment_short",
                   return_value=output_mp4):
            from src.jpolitics.api_bridge import api_render
            api_render(str(wd), moment_idx=0)

        data = _last_json(capsys)
        assert Path(data["output_path"]).is_absolute()

    def test_stderr_progress_messages(self, capsys, tmp_path):
        wd = tmp_path / "20241010_100000_test"
        wd.mkdir()
        self._setup_work_dir(wd)
        output_mp4 = wd / "output_1.mp4"
        output_mp4.touch()

        with patch("src.jpolitics.api_bridge.render_moment_short",
                   return_value=output_mp4):
            from src.jpolitics.api_bridge import api_render
            api_render(str(wd), moment_idx=0)

        captured = capsys.readouterr()
        assert len(captured.err) > 0


# ── api_meta 테스트 ───────────────────────────────────────────────────────────

class TestApiMeta:
    def _make_moments_json(self, work_dir: Path) -> None:
        from src.jpolitics.models.moment import MomentDetectionResult
        moment = _make_moment(
            start_sec=5.0, end_sec=35.0, kind="laughter", speaker="박범계",
            summary="웃음 터짐", hook_question="왜 청문회에서 웃었을까요?",
            keywords=("웃음", "청문회"), confidence=0.92,
        )
        det = MomentDetectionResult(
            source_url="https://youtu.be/meta_test",
            video_title="청문회 하이라이트",
            channel="YTN",
            detector="gemini_multimodal",
            moments=(moment,),
        )
        det.save(work_dir / "moments.json")

    def _fake_meta(self):
        from src.jpolitics.analyzer.meta_generator import MetaResult
        return MetaResult(
            title_candidates=("제목1?", "제목2?", "제목3?"),
            hashtags=("#정치", "#국회", "#쇼츠", "#청문회", "#여야"),
            pinned_comment="여러분은 어떻게 생각하시나요?",
        )

    def test_outputs_valid_json_on_stdout(self, capsys, tmp_path):
        self._make_moments_json(tmp_path)

        with patch("src.jpolitics.api_bridge.generate_meta",
                   return_value=self._fake_meta()):
            from src.jpolitics.api_bridge import api_meta
            api_meta(str(tmp_path), moment_idx=0)

        data = _last_json(capsys)
        assert "title_candidates" in data
        assert "hashtags" in data
        assert "pinned_comment" in data

    def test_title_candidates_is_list(self, capsys, tmp_path):
        self._make_moments_json(tmp_path)

        with patch("src.jpolitics.api_bridge.generate_meta",
                   return_value=self._fake_meta()):
            from src.jpolitics.api_bridge import api_meta
            api_meta(str(tmp_path), moment_idx=0)

        data = _last_json(capsys)
        assert isinstance(data["title_candidates"], list)
        assert isinstance(data["hashtags"], list)

    def test_progress_to_stderr(self, capsys, tmp_path):
        self._make_moments_json(tmp_path)

        with patch("src.jpolitics.api_bridge.generate_meta",
                   return_value=self._fake_meta()):
            from src.jpolitics.api_bridge import api_meta
            api_meta(str(tmp_path), moment_idx=0)

        captured = capsys.readouterr()
        # 마지막 stdout 줄은 JSON이어야 함
        json.loads(captured.out.strip().splitlines()[-1])
        # stderr에 진행 메시지가 있어야 함
        assert len(captured.err) > 0

    def test_no_real_claude_call(self, capsys, tmp_path):
        """generate_meta가 mock되므로 실제 Claude API 호출 없음을 확인."""
        self._make_moments_json(tmp_path)

        call_count = {"n": 0}

        def fake_generate_meta(**kwargs):
            call_count["n"] += 1
            from src.jpolitics.analyzer.meta_generator import MetaResult
            return MetaResult(
                title_candidates=("t?",),
                hashtags=("#정치", "#국회", "#쇼츠"),
                pinned_comment="p",
            )

        with patch("src.jpolitics.api_bridge.generate_meta", fake_generate_meta):
            from src.jpolitics.api_bridge import api_meta
            api_meta(str(tmp_path), moment_idx=0)

        assert call_count["n"] == 1
        _last_json(capsys)  # JSON 출력 검증

    def test_stdout_last_line_is_json(self, capsys, tmp_path):
        """stdout에 여러 줄 있어도 마지막 줄이 JSON임을 확인."""
        self._make_moments_json(tmp_path)

        with patch("src.jpolitics.api_bridge.generate_meta",
                   return_value=self._fake_meta()):
            from src.jpolitics.api_bridge import api_meta
            api_meta(str(tmp_path), moment_idx=0)

        data = _last_json(capsys)
        # JSON 구조 검증
        assert isinstance(data, dict)
        assert "title_candidates" in data
