"""Tests for src/video_gen/browser_diagnostics.py — 자동화 실패 원인 분류."""
import asyncio

from src.video_gen.browser_diagnostics import (
    FailureDiagnosis,
    diagnose_page_failure,
    format_diagnosis,
)


class FakePage:
    def __init__(self, *, closed=False, login_visible=False, visible_raises=False,
                 url="https://example.com/app"):
        self._closed = closed
        self._login_visible = login_visible
        self._visible_raises = visible_raises
        self.url = url

    def is_closed(self) -> bool:
        return self._closed

    async def is_visible(self, selector: str) -> bool:
        if self._visible_raises:
            raise RuntimeError("page crashed")
        return self._login_visible


def _diagnose(page, **kwargs) -> FailureDiagnosis:
    return asyncio.run(diagnose_page_failure(page, **kwargs))


def test_closed_page_is_unreachable():
    diag = _diagnose(FakePage(closed=True))
    assert diag.cause == "page_unreachable"


def test_visible_login_button_means_session_expired():
    diag = _diagnose(
        FakePage(login_visible=True), login_button="button.login"
    )
    assert diag.cause == "session_expired"


def test_responsive_page_without_login_button_is_dom_change():
    diag = _diagnose(
        FakePage(login_visible=False), login_button="button.login"
    )
    assert diag.cause == "selector_missing"
    assert "example.com" in diag.detail


def test_crashed_page_check_is_unreachable():
    diag = _diagnose(
        FakePage(visible_raises=True), login_button="button.login"
    )
    assert diag.cause == "page_unreachable"


def test_no_login_selector_defaults_to_dom_change():
    diag = _diagnose(FakePage())
    assert diag.cause == "selector_missing"


def test_format_diagnosis_includes_relogin_hint_on_session_expired():
    diag = FailureDiagnosis(cause="session_expired", detail="로그인 버튼 노출")
    msg = format_diagnosis(
        provider="freepik",
        action="모델 드롭다운 열기",
        diagnosis=diag,
        relogin_cmd="python3 -m src.main freepik_login",
    )
    assert "freepik_login" in msg
    assert "세션 만료" in msg
    assert "모델 드롭다운 열기" in msg


def test_format_diagnosis_selector_missing_mentions_dom():
    diag = FailureDiagnosis(cause="selector_missing", detail="url=https://x")
    msg = format_diagnosis(
        provider="deevid",
        action="프롬프트 입력",
        diagnosis=diag,
        relogin_cmd="python3 -m src.main deevid_login",
    )
    assert "DOM" in msg or "UI 변경" in msg
