"""유튜브 쇼츠 메타데이터 생성기 (Feature 027 Phase 4).

Claude 1-shot으로 제목 후보 3개, 해시태그, 고정댓글을 생성한다.

격리 boundary: src.analyzer.claude_analyzer._call_claude 는 read-only import.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass

from src.jpolitics.logger import logger


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetaResult:
    """쇼츠 메타데이터 — 제목 후보·해시태그·고정댓글 묶음."""

    title_candidates: tuple[str, ...]  # 3개, 질문형 (~20자, "?"로 끝남)
    hashtags: tuple[str, ...]          # 5~8개, # 포함
    pinned_comment: str                # 고정댓글 1~2문장

    def to_dict(self) -> dict:
        return {
            "title_candidates": list(self.title_candidates),
            "hashtags": list(self.hashtags),
            "pinned_comment": self.pinned_comment,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MetaResult":
        return cls(
            title_candidates=tuple(str(t) for t in d.get("title_candidates") or ()),
            hashtags=tuple(str(h) for h in d.get("hashtags") or ()),
            pinned_comment=str(d.get("pinned_comment", "")),
        )


# ── 기본값 ────────────────────────────────────────────────────────────────────

_FALLBACK = MetaResult(
    title_candidates=("제목을 생성할 수 없습니다",),
    hashtags=("#정치", "#국회", "#쇼츠"),
    pinned_comment="여러분의 생각은 어떠신가요?",
)


# ── 프롬프트 ──────────────────────────────────────────────────────────────────

def _build_prompt(
    video_title: str,
    channel: str,
    moment_hook: str,
    moment_summary: str,
    moment_kind: str,
) -> str:
    return f"""당신은 유튜브 쇼츠 메타데이터 전문가입니다.

영상 정보:
- 출처: {channel}
- 영상 제목: {video_title}
- 모먼트 요약: {moment_summary}
- 훅 질문: {moment_hook}
- 모먼트 종류: {moment_kind}

다음을 JSON으로 출력하세요:
1. title_candidates: 질문형 제목 3개 (각 20자 이내, "?" 로 끝남, 답을 알려주지 않는 떡밥형)
2. hashtags: 관련 해시태그 5~8개 (# 포함, #정치 #국회 #쇼츠 필수 포함)
3. pinned_comment: 고정댓글 질문 1~2문장 (시청자 참여 유도)

JSON만 출력 (마크다운 코드블록 제외):
{{
  "title_candidates": ["...", "...", "..."],
  "hashtags": ["#정치", "..."],
  "pinned_comment": "..."
}}"""


# ── 공개 API ──────────────────────────────────────────────────────────────────

def generate_meta(
    video_title: str,
    channel: str,
    moment_hook: str,
    moment_summary: str,
    moment_kind: str,
) -> MetaResult:
    """제목 후보 3개 + 해시태그 + 고정댓글을 Claude로 생성한다.

    Claude 호출 실패 또는 JSON 파싱 실패 시 _FALLBACK 을 반환한다.

    Args:
        video_title: 원본 YouTube 영상 제목.
        channel: 채널명 (예: "YTN").
        moment_hook: 훅 질문 (Moment.hook_question).
        moment_summary: 모먼트 요약 (Moment.summary).
        moment_kind: 모먼트 종류 (Moment.kind).

    Returns:
        MetaResult (frozen dataclass).
    """
    from src.analyzer.claude_analyzer import _call_claude  # read-only import (격리 boundary)

    prompt = _build_prompt(
        video_title=video_title,
        channel=channel,
        moment_hook=moment_hook,
        moment_summary=moment_summary,
        moment_kind=moment_kind,
    )

    try:
        raw = _call_claude(prompt)
    except Exception as exc:
        logger.warning("메타데이터 생성 Claude 호출 실패 — 기본값 반환: %s", exc)
        return _FALLBACK

    # 코드펜스 제거
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("메타데이터 JSON 파싱 실패 — 기본값 반환: %s (raw: %r)", exc, raw[:200])
        return _FALLBACK

    if not isinstance(data, dict):
        logger.warning("메타데이터 응답이 dict가 아님 — 기본값 반환: %r", type(data).__name__)
        return _FALLBACK

    try:
        return MetaResult.from_dict(data)
    except Exception as exc:
        logger.warning("MetaResult 생성 실패 — 기본값 반환: %s", exc)
        return _FALLBACK
