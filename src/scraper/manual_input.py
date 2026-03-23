"""Manual input module for BlindPost data.

Two modes:
1. --file: Read from a pre-written JSON file
2. --interactive: Prompt user for title, body, comments step by step
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config.settings import DATA_RAW_DIR, MAX_COMMENTS
from src.scraper.models import BlindPost, Comment, KST
from src.scraper.validator import validate_blind_post

logger = logging.getLogger(__name__)


class ManualInputError(Exception):
    """Raised when manual input fails validation or parsing."""


def load_from_file(file_path: Path) -> BlindPost:
    """Load and validate a BlindPost from a JSON file.

    Raises ManualInputError on parse or validation failure.
    """
    if not file_path.exists():
        raise ManualInputError(f"파일을 찾을 수 없습니다: {file_path}")

    text = file_path.read_text(encoding="utf-8")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ManualInputError(f"유효하지 않은 JSON 형식입니다: {e}") from e

    result = validate_blind_post(data)
    if not result.is_valid:
        error_lines = "\n".join(f"  - {msg}" for msg in result.error_messages())
        raise ManualInputError(f"스키마 검증 실패:\n{error_lines}")

    for msg in result.warning_messages():
        logger.warning(msg)

    return BlindPost.from_dict(data)


def collect_interactive() -> BlindPost:
    """Collect BlindPost data interactively from stdin."""
    print("=== 블라인드 게시글 수동 입력 ===\n")

    title = _prompt("제목: ").strip()
    if not title:
        raise ManualInputError("제목은 비어있을 수 없습니다")

    author = _prompt("작성자 (직장명 · 닉네임, 생략 가능): ").strip()

    print("본문을 입력하세요 (입력 완료 시 빈 줄에서 END 입력):")
    body_lines: list[str] = []
    while True:
        line = _prompt("")
        if line.strip() == "END":
            break
        body_lines.append(line)
    body = "\n".join(body_lines).strip()

    if not body:
        raise ManualInputError("본문은 비어있을 수 없습니다")

    comments = _collect_comments()

    return BlindPost(
        title=title,
        author=author,
        body=body,
        comments=tuple(comments),
        url="",
        created_at=datetime.now(KST).isoformat(),
    )


def _collect_comments() -> list[Comment]:
    """Collect comments interactively."""
    comments: list[Comment] = []
    print(f"\n댓글 입력 (최대 {MAX_COMMENTS}개, 건너뛰려면 빈 입력):")

    for i in range(MAX_COMMENTS):
        text = _prompt(f"  댓글 {i + 1} 내용: ").strip()
        if not text:
            break
        likes_str = _prompt(f"  댓글 {i + 1} 좋아요 수 (기본 0): ").strip()
        likes = int(likes_str) if likes_str.isdigit() else 0
        comment_author = _prompt(f"  댓글 {i + 1} 작성자 (생략 가능): ").strip()
        comments.append(Comment(text=text, likes=likes, author=comment_author))
        print()

    return comments


def _prompt(message: str) -> str:
    """Read input, supporting both interactive and piped input."""
    if sys.stdin.isatty():
        return input(message)
    line = sys.stdin.readline()
    return line.rstrip("\n") if line else ""


def save_post(post: BlindPost, output_dir: Path | None = None) -> Path:
    """Save a BlindPost as JSON to the output directory.

    Returns the path to the saved file.
    """
    target_dir = output_dir or DATA_RAW_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in post.title[:30] if c.isalnum() or c in " _-")
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    filename = f"{timestamp}_{safe_title}.json"

    file_path = target_dir / filename
    file_path.write_text(post.to_json(), encoding="utf-8")

    return file_path
