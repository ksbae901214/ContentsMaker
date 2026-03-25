"""Image extractor — OCR Blind post screenshots via Claude Code.

Takes one or more screenshots of a Blind post and extracts
title, author, body, and comments into a BlindPost.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import subprocess
from pathlib import Path

from src.config.settings import CLAUDE_TIMEOUT_SECONDS
from src.scraper.models import BlindPost
from src.scraper.validator import validate_blind_post

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

IMAGE_EXTRACT_PROMPT = """첨부된 이미지는 블라인드(Blind) 앱의 게시글 스크린샷입니다.
이미지에서 다음 정보를 추출하여 JSON으로 출력해주세요.

## 추출 규칙

1. **title**: 게시글 제목 (굵은 글씨로 표시된 부분)
2. **author**: 작성자 정보 ("직장명 · 닉네임" 형식). 게시판명이 있으면 "게시판명 · 닉네임"
3. **body**: 본문 전체 텍스트. 줄바꿈 유지. 광고/배너는 제외
4. **comments**: 댓글 배열. 각 댓글은 {"text": "내용", "likes": 좋아요수, "author": "직장명 · 닉네임"}
   - 좋아요 수가 보이지 않으면 0으로 설정
   - 댓글이 없으면 빈 배열 []
5. **url**: 빈 문자열 "" (스크린샷에서는 URL을 알 수 없음)

## 주의사항

- 이미지가 여러 장이면, 모두 같은 게시글의 스크린샷입니다. 내용을 합쳐서 하나의 JSON으로 만드세요
- 블라인드 UI 요소(좋아요 버튼, 대화하기, 시간 표시 등)는 무시하세요
- 광고 배너, 아이폰 특가 등 게시글과 관련 없는 내용은 제외하세요
- 한국어를 정확하게 추출하세요. ㅋㅋㅋ, ㅠㅠ 등 이모티콘도 그대로 보존

## 출력 형식 (반드시 이 JSON 형식으로만 출력)

```json
{
  "title": "게시글 제목",
  "author": "직장명 · 닉네임",
  "body": "본문 전체 텍스트",
  "comments": [
    {"text": "댓글 내용", "likes": 0, "author": "직장명 · 닉네임"}
  ],
  "url": ""
}
```

JSON만 출력하세요. 다른 설명은 포함하지 마세요."""


class ImageExtractError(Exception):
    """Raised when image extraction fails."""


def _normalize_keys(data: dict) -> dict:
    """Normalize common key variations from Claude responses."""
    KEY_MAP = {
        "제목": "title",
        "본문": "body",
        "작성자": "author",
        "댓글": "comments",
        "content": "body",
        "text": "body",
        "post_title": "title",
        "post_body": "body",
    }
    normalized = {}
    for k, v in data.items():
        mapped = KEY_MAP.get(k, k)
        normalized[mapped] = v

    # If body is missing but there's a long string field, use it
    if "body" not in normalized and "title" in normalized:
        for k, v in normalized.items():
            if k not in ("title", "author", "url", "comments") and isinstance(v, str) and len(v) > 20:
                normalized["body"] = v
                break

    # Ensure comments is a list
    if "comments" in normalized and not isinstance(normalized["comments"], list):
        normalized["comments"] = []

    # Default empty fields
    if "author" not in normalized:
        normalized["author"] = ""
    if "url" not in normalized:
        normalized["url"] = ""
    if "comments" not in normalized:
        normalized["comments"] = []

    return normalized


def extract_from_images(image_paths: list[Path]) -> BlindPost:
    """Extract BlindPost data from Blind screenshot images.

    Uses Claude Code's multimodal capability to OCR the images.
    Supports multiple images of the same post (scrolled screenshots).
    """
    for path in image_paths:
        if not path.exists():
            raise ImageExtractError(f"이미지 파일을 찾을 수 없습니다: {path}")
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ImageExtractError(
                f"지원하지 않는 이미지 형식입니다: {path.suffix} "
                f"(지원: {', '.join(SUPPORTED_FORMATS)})"
            )

    logger.info("이미지 %d장에서 텍스트 추출 중...", len(image_paths))

    raw_json = _call_claude_with_images(image_paths)
    data = _parse_response(raw_json)
    data = _normalize_keys(data)

    logger.info("추출된 데이터 키: %s", list(data.keys()))

    result = validate_blind_post(data)
    if not result.is_valid:
        error_lines = "\n".join(f"  - {msg}" for msg in result.error_messages())
        raise ImageExtractError(f"추출된 데이터 검증 실패:\n{error_lines}")

    for msg in result.warning_messages():
        logger.warning(msg)

    post = BlindPost.from_dict(data)
    logger.info("추출 완료: '%s' (댓글 %d개)", post.title, len(post.comments))

    return post


def _call_claude_with_images(image_paths: list[Path]) -> str:
    """Call Claude Code with base64-encoded images in the prompt.

    Encodes images as data URIs and includes them directly in the prompt
    so Claude can see them without needing the Read tool.
    """
    image_parts = []
    for i, path in enumerate(image_paths):
        img_data = base64.b64encode(path.read_bytes()).decode("ascii")
        suffix = path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/png")
        image_parts.append(f"![이미지 {i+1}](data:{mime};base64,{img_data})")

    images_block = "\n\n".join(image_parts)

    prompt = f"""{images_block}

{IMAGE_EXTRACT_PROMPT}"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise ImageExtractError(
            "Claude Code가 설치되지 않았습니다. "
            "'claude' 명령어가 PATH에 있는지 확인하세요."
        )
    except subprocess.TimeoutExpired:
        raise ImageExtractError(
            f"Claude Code 응답 시간 초과 ({CLAUDE_TIMEOUT_SECONDS}초)"
        )

    if result.returncode != 0:
        raise ImageExtractError(
            f"Claude Code 실행 실패 (exit {result.returncode}): {result.stderr[:300]}"
        )

    return result.stdout


def _parse_response(raw: str) -> dict:
    """Parse Claude Code's response into a dict."""
    if not raw or not raw.strip():
        raise ImageExtractError("Claude Code 응답이 비어있습니다.")

    # Direct JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "result" in data:
            inner = data["result"]
            if isinstance(inner, str) and inner.strip():
                return _parse_response(inner)
            if isinstance(inner, dict) and "title" in inner:
                return inner
            # result is empty — Claude didn't produce output
            if not inner or (isinstance(inner, str) and not inner.strip()):
                raise ImageExtractError(
                    "Claude Code가 이미지에서 텍스트를 추출하지 못했습니다. "
                    "이미지가 블라인드 게시글 스크린샷인지 확인해주세요."
                )
        if isinstance(data, dict) and "title" in data:
            return data
    except ImageExtractError:
        raise
    except (json.JSONDecodeError, KeyError):
        pass

    # JSON in code block
    for pattern in [
        r"```(?:json)?\s*\n(.*?)\n```",
        r"```(.*?)```",
    ]:
        json_match = re.search(pattern, raw, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, dict) and "title" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

    # Raw JSON object in text
    brace_match = re.search(r"\{[^{}]*\"title\"[^{}]*\}", raw, re.DOTALL)
    if not brace_match:
        brace_match = re.search(r"\{[\s\S]*\}", raw)
    if brace_match:
        try:
            parsed = json.loads(brace_match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ImageExtractError(
        f"이미지에서 텍스트를 추출할 수 없습니다.\n응답 미리보기: {raw[:300]}"
    )
