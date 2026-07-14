"""브라우저 자동화 실패 원인 분류 (Feature 026).

Freepik/deevid/Gemini 웹 자동화에서 selector를 못 찾았을 때, 단순히
"실패"가 아니라 무엇이 문제인지 구분해 안내한다:

- ``page_unreachable``: 페이지가 닫혔거나 응답 불가 (네트워크/크래시)
- ``session_expired``: 로그인 버튼이 보임 — 세션 만료, 재로그인 필요
- ``selector_missing``: 페이지는 정상인데 요소만 없음 — 사이트 UI(DOM) 변경 추정

기존 generic 에러를 대체하지 않고, 에러 메시지를 풍부하게 만드는 용도.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FailureDiagnosis:
    """실패 원인 분류 결과."""

    cause: str  # "page_unreachable" | "session_expired" | "selector_missing"
    detail: str


async def diagnose_page_failure(
    page,
    *,
    login_button: str | None = None,
) -> FailureDiagnosis:
    """selector 실패 직후 페이지 상태를 검사해 원인을 분류한다.

    Args:
        page: Playwright Page (또는 호환 객체)
        login_button: 로그인 버튼 selector — 보이면 세션 만료로 판단
    """
    try:
        if page.is_closed():
            return FailureDiagnosis(
                cause="page_unreachable",
                detail="브라우저 페이지가 닫혀 있음 (크래시 또는 네트워크 단절)",
            )
    except Exception as exc:
        return FailureDiagnosis(
            cause="page_unreachable",
            detail=f"페이지 상태 확인 불가: {exc}",
        )

    if login_button:
        try:
            if await page.is_visible(login_button):
                return FailureDiagnosis(
                    cause="session_expired",
                    detail="로그인 버튼이 노출됨 — 저장된 세션이 만료된 것으로 보임",
                )
        except Exception as exc:
            return FailureDiagnosis(
                cause="page_unreachable",
                detail=f"페이지 응답 없음: {exc}",
            )

    return FailureDiagnosis(
        cause="selector_missing",
        detail=f"페이지는 응답하지만 대상 요소가 없음 — 사이트 DOM 변경 추정 (url={page.url})",
    )


def format_diagnosis(
    *,
    provider: str,
    action: str,
    diagnosis: FailureDiagnosis,
    relogin_cmd: str,
) -> str:
    """진단 결과를 사용자 안내 메시지로 변환한다."""
    if diagnosis.cause == "session_expired":
        return (
            f"[{provider}] {action} 실패 — 세션 만료로 보입니다. "
            f"`{relogin_cmd}` 를 다시 실행해주세요. ({diagnosis.detail})"
        )
    if diagnosis.cause == "page_unreachable":
        return (
            f"[{provider}] {action} 실패 — 페이지 응답 없음 (네트워크/브라우저 문제). "
            f"잠시 후 재시도해주세요. ({diagnosis.detail})"
        )
    return (
        f"[{provider}] {action} 실패 — 사이트 UI 변경(DOM)으로 selector가 깨진 것으로 보입니다. "
        f"selector 파일 업데이트가 필요할 수 있습니다. ({diagnosis.detail})"
    )
