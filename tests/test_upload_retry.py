"""Tests for src/upload/retry.py — exponential backoff 재시도 유틸."""
import pytest

from src.upload.retry import with_retry


def test_success_first_try_no_sleep():
    sleeps: list[float] = []
    result = with_retry(lambda: "ok", sleep=sleeps.append)
    assert result == "ok"
    assert sleeps == []


def test_retries_then_succeeds_with_exponential_backoff():
    sleeps: list[float] = []
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    result = with_retry(flaky, max_attempts=3, base_delay=2.0, sleep=sleeps.append)

    assert result == "ok"
    assert calls["n"] == 3
    assert sleeps == [2.0, 4.0]  # 2^0*2, 2^1*2


def test_exhausted_attempts_reraises():
    sleeps: list[float] = []

    def always_fail():
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        with_retry(always_fail, max_attempts=3, sleep=sleeps.append)

    assert len(sleeps) == 2  # 마지막 시도 후에는 sleep 없음


def test_non_retryable_raises_immediately():
    calls = {"n": 0}

    def fail_fatal():
        calls["n"] += 1
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        with_retry(
            fail_fatal,
            max_attempts=3,
            should_retry=lambda exc: isinstance(exc, ConnectionError),
            sleep=lambda _: None,
        )

    assert calls["n"] == 1


def test_should_retry_predicate_allows_retry():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("transient")
        return "ok"

    result = with_retry(
        flaky,
        should_retry=lambda exc: isinstance(exc, ConnectionError),
        sleep=lambda _: None,
    )
    assert result == "ok"
    assert calls["n"] == 2
