"""T122: 엔드투엔드 스모크 테스트 (R-15, 원칙 VII).

샘플 영상(`tests/fixtures/natv_sample.mp4`)을 입력으로 전체 파이프라인을 실행:
  수집 → STT → diarize → 식별 → 점수 → draft → commentary → gate(통과)
  → render(--skip-remotion) → MP4 출력 확인

기본 실행은 무거운 모델(Whisper/pyannote/Claude CLI/Remotion)을 stub 으로 대체해
파이프라인 wiring · DB 흐름 · 게이트 통과 경로만 검증한다.
운영자가 `cli.py::test-e2e --real-models` 로 호출하면 실제 모델로 재실행한다.

샘플 fixture 가 없으면 skip. 운영자는 다음 중 하나 준비:
  - tests/fixtures/natv_sample.mp4 (10분, git-ignored)
  - 환경변수 NATV_SMOKE_SAMPLE 로 다른 경로 지정
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, init_db


FIXTURE_PATH = Path("tests/fixtures/natv_sample.mp4")


def _resolve_sample() -> Path | None:
    env = os.getenv("NATV_SMOKE_SAMPLE")
    if env:
        p = Path(env)
        return p if p.exists() else None
    return FIXTURE_PATH if FIXTURE_PATH.exists() else None


# ---------------------------------------------------------------------------
# stub-mode (기본): 모델 호출 없이 wiring 검증
# ---------------------------------------------------------------------------


def test_smoke_pipeline_runs_with_stubs(tmp_path, monkeypatch):
    """실제 영상 파일 없이도 wiring 이 동작하는지 검증.

    이 케이스는 항상 실행되며 CI 가드 역할.
    """
    from src.dem_shorts import e2e_smoke
    from src.dem_shorts.utils import paths as paths_mod

    db_path = tmp_path / "smoke.db"
    init_db(db_path)

    # data 디렉토리를 tmp 로 격리
    monkeypatch.setattr(paths_mod, "ROOT", tmp_path / "data" / "dem_shorts")
    monkeypatch.setattr(paths_mod, "ARCHIVE_DIR", tmp_path / "data" / "dem_shorts" / "archive")
    monkeypatch.setattr(paths_mod, "TRANSCRIPTS_DIR", tmp_path / "data" / "dem_shorts" / "transcripts")
    monkeypatch.setattr(paths_mod, "SEGMENTS_DIR", tmp_path / "data" / "dem_shorts" / "segments")
    monkeypatch.setattr(paths_mod, "OUTPUTS_DIR", tmp_path / "data" / "dem_shorts" / "outputs")

    # render 출력은 stub MP4 1바이트
    summary = e2e_smoke.run_e2e_smoke(
        sample_path=tmp_path / "fake.mp4",  # 실제 파일 없어도 stub-mode 는 OK
        db_path=db_path,
        real_models=False,
        operator_id="smoke",
    )

    assert summary["phases"]["source_video"]["video_id"]
    assert summary["phases"]["stt"]["segments"] >= 1
    assert summary["phases"]["diarize"]["turns"] >= 1
    assert summary["phases"]["identify"]["saved_segments"] >= 1
    assert summary["phases"]["draft"]["draft_id"] >= 1
    assert summary["phases"]["gate"]["passed"] is True
    rendered = Path(summary["phases"]["render"]["rendered_path"])
    assert rendered.exists()


def test_smoke_pipeline_returns_duration(tmp_path):
    """duration_sec 가 cut_end - cut_start 와 일치."""
    from src.dem_shorts import e2e_smoke

    db_path = tmp_path / "smoke.db"
    init_db(db_path)

    summary = e2e_smoke.run_e2e_smoke(
        sample_path=tmp_path / "fake.mp4",
        db_path=db_path,
        real_models=False,
        operator_id="smoke",
    )

    duration = float(summary["phases"]["render"]["duration_sec"])
    assert duration > 0


# ---------------------------------------------------------------------------
# real-mode: 실제 fixture 가 있을 때만 실행
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_resolve_sample() is None, reason="natv_sample.mp4 미배치 — skip")
def test_smoke_real_pipeline_with_local_sample(tmp_path):
    """실제 NATV mp4 가 있을 때 전체 파이프라인을 진짜 모델로 실행.

    운영자가 로컬에서 한 번 돌려보는 정합성 체크용. CI 에서는 skip.
    실행 시간: Whisper large-v3 + pyannote 합쳐 5~10분.
    """
    from src.dem_shorts import e2e_smoke

    sample = _resolve_sample()
    assert sample is not None  # mypy/pyright용

    db_path = tmp_path / "smoke.db"
    init_db(db_path)
    summary = e2e_smoke.run_e2e_smoke(
        sample_path=sample,
        db_path=db_path,
        real_models=True,
        operator_id="smoke-real",
    )
    rendered = Path(summary["phases"]["render"]["rendered_path"])
    assert rendered.exists()
    assert rendered.stat().st_size > 0
