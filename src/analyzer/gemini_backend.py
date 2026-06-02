"""Gemini 2.5 Flash 분석 백본 (Phase 1B).

Claude CLI의 일시적 "Execution error" 응답을 우회하기 위한 대안 백엔드.
`ANALYZER_BACKEND` 환경변수로 토글:
  - "claude" (default, 안정성 검증 전): 기존 Claude CLI
  - "gemini": Gemini 2.5 Flash API (무료 한도 250 req/일)

호출자는 `call_analyzer(prompt) -> str` 추상화만 사용하면 백엔드 무관.
"""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_BACKEND = "claude"  # 검증 14일 동안은 claude 유지. 안정 확인 후 gemini로.


class GeminiBackendError(Exception):
    """Gemini 백엔드 호출 실패."""


def get_backend() -> str:
    """현재 활성 백엔드 이름을 반환."""
    raw = os.environ.get("ANALYZER_BACKEND", DEFAULT_BACKEND).strip().lower()
    return raw if raw in ("claude", "gemini") else DEFAULT_BACKEND


def _is_transient_gemini_error(err: Exception) -> bool:
    """503 UNAVAILABLE / 429 RESOURCE_EXHAUSTED / 네트워크 = 일시적 (긴 backoff 가치).

    검증된 운영 케이스: gemini 2.5 flash의 'high demand' 시간대 503은 30초~수분 후 회복.
    """
    s = str(err)
    return any(token in s for token in (
        "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
        "INTERNAL", "DEADLINE_EXCEEDED", "TIMEOUT", "timeout",
    ))


# 지수 backoff 스케줄 (초). 시도 1 실패 후 1s, 2 실패 후 5s, 3 실패 후 15s, 4 실패 후 30s.
# 일시적 오류(503) 시 추가로 2배 곱해서 더 길게 대기.
_BACKOFF_SCHEDULE = (1.0, 5.0, 15.0, 30.0)


def call_gemini(prompt: str, *, max_attempts: int = 5, temperature: float = 0.3) -> str:
    """Gemini 2.5 Flash 호출 → 응답 텍스트.

    Args:
        prompt: 사용자 프롬프트 문자열.
        max_attempts: 일시적 오류 재시도 횟수 (default 5 — high demand 시간대 대응).
        temperature: 생성 다양성 (0.0~1.0).

    Returns:
        모델 응답 텍스트 (전·후 공백 제거).

    Raises:
        GeminiBackendError: 키 미설정, 빈 응답, 호출 실패.

    Backoff: 시도 사이에 지수 대기 (1/5/15/30초). 503 등 일시적 오류는 2배 가산
        → 총 최대 약 100초 대기 → high demand 회복 가능성 ↑.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiBackendError(
            "GEMINI_API_KEY 미설정 — ANALYZER_BACKEND=gemini 사용 불가"
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise GeminiBackendError(f"google-genai 미설치: {e}") from e

    client = genai.Client(api_key=api_key)
    last_err: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            last_err = e
            logger.warning("Gemini 호출 실패 (attempt %d/%d): %s",
                           attempt, max_attempts, e)
            if attempt < max_attempts:
                idx = min(attempt - 1, len(_BACKOFF_SCHEDULE) - 1)
                wait = _BACKOFF_SCHEDULE[idx]
                if _is_transient_gemini_error(e):
                    wait *= 2  # 503/429는 더 길게 (high demand 회복 시간)
                logger.info("Gemini 재시도 %.1fs 대기...", wait)
                time.sleep(wait)
                continue
            break

        text = (getattr(response, "text", "") or "").strip()
        if not text:
            last_err = GeminiBackendError(
                f"빈 응답 (finish_reason={_finish_reason(response)})"
            )
            if attempt < max_attempts:
                logger.warning("Gemini 빈 응답 (attempt %d/%d) — 재시도",
                               attempt, max_attempts)
                idx = min(attempt - 1, len(_BACKOFF_SCHEDULE) - 1)
                time.sleep(_BACKOFF_SCHEDULE[idx])
                continue
            break
        return text

    # API 모든 시도 실패 — 일시적 오류면 웹 자동화 폴백 시도.
    if last_err is not None and _is_transient_gemini_error(last_err) and _web_fallback_enabled():
        logger.warning(
            "Gemini API %d회 모두 실패(일시적) — 웹 자동화 폴백 시도...",
            max_attempts,
        )
        try:
            from src.analyzer.gemini_web_chat import chat as _web_chat
            return _web_chat(prompt, json_mode=True)
        except Exception as web_err:
            logger.warning("웹 폴백도 실패: %s", web_err)
            raise GeminiBackendError(
                f"API {max_attempts}회 실패 + 웹 폴백 실패: api={last_err} web={web_err}"
            ) from web_err

    raise GeminiBackendError(f"Gemini 호출 {max_attempts}회 모두 실패: {last_err}")


def _web_fallback_enabled() -> bool:
    """GEMINI_WEB_FALLBACK=0 으로 명시 비활성화 안 했으면 True."""
    return os.environ.get("GEMINI_WEB_FALLBACK", "1") != "0"


def _finish_reason(response) -> str:
    """디버깅용 finish_reason 추출."""
    try:
        return str(response.candidates[0].finish_reason)
    except (AttributeError, IndexError):
        return "N/A"


def call_analyzer(
    prompt: str,
    *,
    claude_caller,
    backend: str | None = None,
) -> str:
    """백엔드 무관 추상 호출.

    Args:
        prompt: 사용자 프롬프트.
        claude_caller: 기존 Claude CLI 호출 함수 (fallback). 시그니처 ``(str) -> str``.
        backend: 강제 지정. None이면 ``ANALYZER_BACKEND`` 환경변수 사용.

    Returns:
        모델 응답 텍스트.

    Behavior:
        - backend="gemini": Gemini 시도 → 실패 시 Claude 폴백
        - backend="claude": Claude만 호출 (기본)
    """
    chosen = (backend or get_backend()).lower()
    if chosen == "gemini":
        try:
            return call_gemini(prompt)
        except GeminiBackendError as e:
            logger.warning("Gemini 백엔드 실패 → Claude 폴백: %s", e)
            return claude_caller(prompt)
    return claude_caller(prompt)
