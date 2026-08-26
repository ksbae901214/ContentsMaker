"""039 Phase 5 — 슬롯 완료/보류 알림.

보류가 기본 동작이라 **알림이 곧 작업 지시**다. 사유를 다 싣지 않으면 사람이
산출물을 열어보고 처음부터 판단해야 한다.

두 가지 '올라간 줄 아는' 함정을 알림에 명시한다:
  - TikTok 은 초안까지만 올라간다 (심사 전 앱은 SELF_ONLY 고정).
  - 고정댓글은 작성까지만 된다 (YouTube API 에 고정 엔드포인트가 없다).

제목·3줄요약·해시태그는 `build_chat_ready_block()` 출력을 **그대로 인용**한다 —
손으로 다시 쓰면 누락된다 (038).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from scripts.auto_daily.review_gate import Decision

logger = logging.getLogger(__name__)


def build_summary(*, slot: str, decision: Decision, video: Path | None,
                  chat_block: str, youtube_url: str | None = None,
                  tiktok_publish_id: str | None = None,
                  comment_posted: bool = False,
                  errors: tuple[str, ...] = ()) -> str:
    """알림/로그에 쓸 요약 텍스트."""
    head = "게시 완료" if decision.should_publish else "보류 — 승인 필요"
    lines = [f"[{slot}] {head}"]

    if not decision.should_publish:
        lines += ["", "보류 사유:"]
        lines += [f"  - {r}" for r in decision.reasons]

    if youtube_url:
        lines += ["", f"YouTube: {youtube_url}"]
    if tiktok_publish_id:
        lines.append(f"TikTok: 초안 업로드됨({tiktok_publish_id}) "
                     "— 앱에서 1탭 게시가 필요합니다")
    if comment_posted:
        lines.append("고정댓글: 작성됨 — 스튜디오에서 '고정'을 눌러야 합니다 "
                     "(API 미지원)")
    if video:
        lines += ["", f"영상: {video}"]
    if errors:
        lines += ["", "오류:"]
        lines += [f"  - {e}" for e in errors]
    if chat_block:
        lines += ["", "─" * 40, chat_block]
    return "\n".join(lines)


def notify(title: str, message: str, *, reveal: Path | None = None,
           runner=subprocess.run) -> None:
    """macOS 알림 + 결과 폴더 열기. **실패해도 예외를 올리지 않는다.**"""
    try:
        body = message.replace('"', "'").replace("\\", "")
        runner(["osascript", "-e",
                f'display notification "{body[:200]}" with title "{title}"'],
               capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        logger.warning("알림 표시 실패: %s", exc)

    if reveal is None or not Path(reveal).exists():
        return
    try:
        runner(["open", "-R", str(reveal)], capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        logger.warning("결과 폴더 열기 실패: %s", exc)
