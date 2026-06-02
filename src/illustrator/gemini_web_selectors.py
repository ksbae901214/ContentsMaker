"""gemini.google.com 웹앱 DOM selector — 2026-05-19 라이브 페이지 탐색으로 확정.

탐색 도구: `/tmp/gemini_selector_probe.py`, `gemini_image_tool_probe2.py`.
재확인 필요 시 동일 패턴으로 probe 스크립트 실행 → DOM dump로 selector 갱신.
"""
from __future__ import annotations

# ─────────────────────────── Common chat surface ───────────────────────────

GEMINI_SELECTORS = {
    # 채팅 입력란 (Quill editor 기반 contenteditable div)
    "chat_input": "rich-textarea div[contenteditable='true']",
    # 전송 버튼 (한국어 UI)
    "send_button": "button[aria-label*='보내']",

    # 응답 컨테이너 (live: model-response, message-content 둘 다 발견)
    "response_container": "model-response",

    # 이미지 응답 - blob URL로 제공됨 (httpx 다운로드 불가, screenshot 또는 fetch→base64 사용)
    "image_in_response": "model-response button.image-button img",
    "image_button_wrapper": "model-response button.image-button",

    # 영상 응답 (Veo 3) - 응답 형태 별도 확인 필요
    "video_in_response": "model-response video",

    # 도구 활성화 버튼 (한국어 UI)
    "image_tool_button": "button[aria-label*='이미지 만들기']",
    "video_tool_button": "button[aria-label*='동영상 만들기']",

    # 로그인 여부 판단
    "login_required_marker": "a[href*='accounts.google.com/ServiceLogin']",
    "logged_in_marker": "rich-textarea div[contenteditable='true']",
}


# ─────────────────────────── Modal dismissal ───────────────────────────

# Gemini는 첫 방문 시 "이메일 수신 동의" 등의 cdk-overlay 모달을 띄움.
# 자동화 클릭이 차단되므로 ESC 2회로 안전하게 닫는다.
MODAL_DISMISS_VIA_ESC = True
MODAL_DISMISS_COUNT = 2


# ─────────────────────────── Image (Imagen) ───────────────────────────

# Gemini 웹앱은 "🖼️ 이미지 만들기" 도구 버튼을 한 번 클릭하면
# 다음 입력부터 이미지 모드. 별도 prefix 불필요.
IMAGE_PROMPT_PREFIX = ""
IMAGE_ASPECT_HINT = " (9:16 vertical aspect ratio, portrait orientation)"

# 결과 폴링
IMAGE_GENERATION_TIMEOUT_SEC = 180.0
IMAGE_POLL_INTERVAL_SEC = 3.0


# ─────────────────────────── Video (Veo 3) ───────────────────────────

# "동영상 만들기" 버튼 클릭 후 입력. Veo 3는 평균 3~5분 소요.
VIDEO_PROMPT_PREFIX = ""
VIDEO_ASPECT_HINT = " (9:16 vertical, ~8 seconds)"

VIDEO_GENERATION_TIMEOUT_SEC = 600.0
VIDEO_POLL_INTERVAL_SEC = 5.0


# ─────────────────────────── Gem Labs (Opal) chat ───────────────────────────

# Gem Labs 채팅 인터페이스 — navigate_to_gem() → Start 클릭 후의 opal_frame 내 셀렉터.
# opal_frame은 page 전체가 아닌 opal._app iframe 내에서만 사용.
GEM_LABS_SELECTORS = {
    # 씬 설명 입력창 (오른쪽 채팅 패널)
    "gem_chat_input": "textarea[placeholder*='Type or upload']",
    # 전송 버튼 (aria-label='send' 또는 텍스트 'send')
    "gem_send_button": "button[aria-label='send'], button:has-text('send')",
    # 응답 이미지 (Imagen 결과)
    "image_in_opal": "img[src^='blob:'], img[src*='googleapis']",
    # 응답 영상 (Veo 결과)
    "video_in_opal": "video",
    # 처리 중 표시 (결과 대기용)
    "loading_indicator": "[aria-label*='loading' i], [class*='spinner'], [class*='loading']",
}
