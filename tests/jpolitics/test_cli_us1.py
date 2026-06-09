"""T014 [US1]: CLI argparse 분기 + 종료 코드 검증.

RED 상태 — T024 구현 후 GREEN.
"""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest


def test_main_module_importable() -> None:
    from src.jpolitics import main  # noqa: F401


def test_cli_help_returns_zero() -> None:
    """python3 -m src.jpolitics.main --help → exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "src.jpolitics.main", "--help"],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0
    assert b"jpolitics" in result.stdout.lower() or b"v3" in result.stdout.lower() or b"shorts" in result.stdout.lower()


def test_cli_invalid_url_returns_2() -> None:
    """잘못된 URL → exit 2 (입력 검증 실패)."""
    result = subprocess.run(
        [sys.executable, "-m", "src.jpolitics.main", "not-a-url"],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 2


def test_cli_topic_mode_requires_topic_arg() -> None:
    """--source-type topic 시 --topic 누락 → exit 2."""
    result = subprocess.run(
        [sys.executable, "-m", "src.jpolitics.main", "--source-type", "topic"],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 2


def test_cli_select_plan_validates_range() -> None:
    """--select-plan 4 → exit 2 (범위 초과)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.jpolitics.main",
            "https://www.youtube.com/watch?v=test",
            "--select-plan",
            "4",
        ],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 2
