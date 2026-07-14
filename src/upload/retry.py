"""업로드용 exponential backoff 재시도 유틸 (Feature 026).

네트워크성 일시 장애(타임아웃, 5xx)는 재시도하고, 인증 실패·파일 없음 같은
영구 오류는 즉시 전파한다. 판단은 호출자가 ``should_retry``로 결정한다.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY_SECONDS = 2.0


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    should_retry: Callable[[BaseException], bool] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> T:
    """fn을 실행하고 실패 시 exponential backoff로 재시도한다.

    Args:
        fn: 인자 없는 호출 대상
        max_attempts: 총 시도 횟수 (기본 3)
        base_delay: 첫 재시도 대기 시간 — 이후 2배씩 증가 (2s, 4s, ...)
        should_retry: 예외를 받아 재시도 여부를 반환. 미지정 시 모든 예외 재시도.
        sleep: 대기 함수 (테스트 주입용)

    Raises:
        마지막 시도의 예외, 또는 should_retry가 False를 반환한 예외.
    """
    attempt = 1
    while True:
        try:
            return fn()
        except Exception as exc:
            if should_retry is not None and not should_retry(exc):
                raise
            if attempt >= max_attempts:
                logger.error("재시도 %d회 모두 실패: %s", max_attempts, exc)
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "시도 %d/%d 실패 (%s) — %.1fs 후 재시도",
                attempt, max_attempts, exc, delay,
            )
            (sleep if sleep is not None else time.sleep)(delay)
            attempt += 1
