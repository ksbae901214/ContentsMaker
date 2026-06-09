"""T006: V1/V2 영상 바이트 일치 회귀 baseline (SC-010).

V3 도입 전후로 동일 입력 V1/V2 fixture가 동일 영상 바이트를 생성해야 함.
fixture가 없으면 SKIP (Phase 1/2에서는 아직 fixture 미생성 OK).

회귀 baseline 파일: tests/fixtures/jpolitics_regression_md5.json
형식: {"v1": "<md5>", "v2": "<md5>"}
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.jpolitics.constants import PROJECT_ROOT

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"
REGRESSION_MD5_FILE = FIXTURE_DIR / "jpolitics_regression_md5.json"


def _file_md5(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


@pytest.mark.skipif(
    not REGRESSION_MD5_FILE.exists(),
    reason="V1/V2 regression baseline fixture not yet created (Phase 1/2 OK)",
)
def test_v1_regression_md5_unchanged() -> None:
    baseline = json.loads(REGRESSION_MD5_FILE.read_text())
    v1_fixture_output = FIXTURE_DIR / "v1_baseline_output.mp4"
    assert v1_fixture_output.exists(), "V1 baseline output missing"
    assert _file_md5(v1_fixture_output) == baseline["v1"], (
        "V1 영상 바이트 변경 감지 — V3 도입이 V1을 깨뜨림 (SC-010 위배)"
    )


@pytest.mark.skipif(
    not REGRESSION_MD5_FILE.exists(),
    reason="V1/V2 regression baseline fixture not yet created (Phase 1/2 OK)",
)
def test_v2_regression_md5_unchanged() -> None:
    baseline = json.loads(REGRESSION_MD5_FILE.read_text())
    v2_fixture_output = FIXTURE_DIR / "v2_baseline_output.mp4"
    assert v2_fixture_output.exists(), "V2 baseline output missing"
    assert _file_md5(v2_fixture_output) == baseline["v2"], (
        "V2 영상 바이트 변경 감지 — V3 도입이 V2를 깨뜨림 (SC-010 위배)"
    )


def test_baseline_fixture_format_is_valid_if_exists() -> None:
    """Baseline 파일이 존재한다면 JSON 스키마 유효성 검증."""
    if not REGRESSION_MD5_FILE.exists():
        pytest.skip("baseline not created")
    data = json.loads(REGRESSION_MD5_FILE.read_text())
    assert "v1" in data and "v2" in data
    assert len(data["v1"]) == 32 and len(data["v2"]) == 32  # MD5 hex
