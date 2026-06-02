"""NotebookLM 스타일 자료 종합 → 쇼츠 (Phase 3B).

여러 URL/PDF/텍스트 자료를 Gemini 2.5 Pro에 한 번에 입력 → 2인 대화형
쇼츠 스크립트 (앵커 + 패널)로 종합.

⚠️ Phase 3B 초안 — 별도 UI 탭 격리. 기존 흐름에 영향 없음.
   실제 PDF 파싱·HTML 다운로드는 단계적으로 보강.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"  # Pro 무료 한도가 낮으므로 Flash 사용


class NotebookLMStyleError(Exception):
    """자료 종합 실패."""


_PROMPT_TEMPLATE = """다음 자료들을 종합하여 30~45초 쇼츠용 2인 대화형 스크립트를 작성하라.

자료:
{sources}

요구사항:
- 8~12씬, 각 씬 3~5초
- 화자는 "anchor"(앵커, 진행) / "reporter"(패널, 분석) 중 하나
- 첫 씬은 anchor의 후킹 문구 (0~3초, 자극적이되 자료 기반)
- 마지막 씬은 anchor의 CTA (좋아요/댓글 유도)
- 자료에서 확인 가능한 사실만 사용, 추측·해석 금지

출력 형식 (JSON 객체만, 다른 텍스트 금지):
{{
  "title": "쇼츠 제목 (1줄, 30자 이내)",
  "scenes": [
    {{"id": 1, "speaker": "anchor", "text": "...", "duration": 3.5}},
    {{"id": 2, "speaker": "reporter", "text": "...", "duration": 4.0}},
    ...
  ]
}}
"""


def synthesize_from_sources(sources: list[str], *, max_sources: int = 5) -> dict:
    """자료 리스트 → 종합 스크립트 JSON dict.

    Args:
        sources: 자료 본문 텍스트(이미 fetch·extract 완료된 문자열) 리스트.
                 PDF/HTML 파싱은 호출자 책임.
        max_sources: 입력 자료 최대 개수 (토큰 한도 보호).

    Returns:
        ``{"title": str, "scenes": [{"id", "speaker", "text", "duration"}, ...]}``

    Raises:
        NotebookLMStyleError: 키 미설정·자료 부족·파싱 실패.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise NotebookLMStyleError("GEMINI_API_KEY 미설정")

    sources = [s.strip() for s in sources if s and s.strip()]
    if not sources:
        raise NotebookLMStyleError("입력 자료가 비어 있습니다")
    if len(sources) > max_sources:
        logger.warning("자료 %d개 → %d개로 자름", len(sources), max_sources)
        sources = sources[:max_sources]

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise NotebookLMStyleError(f"google-genai 미설치: {e}") from e

    sources_block = "\n\n---\n\n".join(
        f"[자료 {i + 1}]\n{s}" for i, s in enumerate(sources)
    )
    prompt = _PROMPT_TEMPLATE.format(sources=sources_block)

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
            ),
        )
    except Exception as e:
        raise NotebookLMStyleError(f"Gemini 호출 실패: {e}") from e

    text = (response.text or "").strip()
    if not text:
        raise NotebookLMStyleError("Gemini 빈 응답")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise NotebookLMStyleError(f"JSON 파싱 실패: {e} | 200자: {text[:200]!r}") from e

    if "scenes" not in data or not isinstance(data["scenes"], list):
        raise NotebookLMStyleError(
            f"scenes 키 누락 또는 잘못된 형식: {list(data.keys())}"
        )
    return data
