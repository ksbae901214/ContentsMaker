"""chatgpt.com 화면 요소 선택자 — UI 가 바뀌면 이 파일만 고친다 (045).

2026-10-14 라이브 페이지 실측(한국어 UI, Plus):
  - `data-testid` 가 거의 사라졌다 → aria-label 기준. 영어 UI 라벨도 함께 둔다.
  - 입력창은 ProseMirror contenteditable, **Enter 로 전송**된다.
  - 응답 중에는 '중지' 버튼이 보이고, 끝나면 사라진다.
  - 생성 이미지는 `alt="생성된 이미지 1"`, src 는 **blob: URL**(1254×1254) —
    HTTP 로 못 받으므로 페이지 안에서 fetch 해 바이트를 꺼낸다.
"""
from __future__ import annotations

CHATGPT_SELECTORS = {
    "chat_input": "div.ProseMirror[contenteditable='true']",
    "stop_button": "button[aria-label='중지'], button[aria-label^='Stop']",
    # 로그인 상태에서만 보이는 프로필 메뉴 — 로그아웃 홈에도 입력창은 있어서 이걸로 판정
    "logged_in_marker": "button[aria-label='프로필 메뉴 열기'], button[aria-label='Open profile menu']",
    "generated_image": "img[alt^='생성된 이미지'], img[alt^='Generated image']",
    # 실패 진단용 — 이미지 대신 글로 답했을 때(거절·한도 안내) 그 내용을 읽는다
    "assistant_message": "[data-message-author-role='assistant']",
}

IMAGE_GENERATION_TIMEOUT_SEC = 300.0   # 실측 약 40초, 혼잡 시 수 분
IMAGE_POLL_INTERVAL_SEC = 3.0
SETTLE_AFTER_DONE_SEC = 4.0             # 점진 렌더가 끝나 최종 blob 으로 바뀔 때까지
PACING_BETWEEN_IMAGES_SEC = 20.0        # 사람 속도에 맞춘 간격 (약관 회색지대 완화)
