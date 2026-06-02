"""정치 발언 팩트체크 (Phase 4) — Gemini Grounding with Google Search.

정치_pro 모드의 transcript에서 추출한 사실 주장에 대해 자동 출처 검증을
수행. 검수 UI에 🟢/🟡/🔴 배지를 표시하고, 영상 description에 출처 자동 첨부.

무료 한도 안전:
  - Gemini 2.5 Flash + grounding tool: 100 grounded queries/일 (free tier)
  - 영상 1편당 5~10 claim 검증 → 일 10편 처리 가능
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class FactCheckResult:
    """단일 주장 검증 결과."""
    claim: str
    verdict: str  # "verified" / "partial" / "unverified"
    confidence: float  # 0.0 ~ 1.0
    sources: tuple[str, ...]
    summary: str

    @property
    def badge(self) -> str:
        """UI 표시용 색 배지."""
        return {
            "verified": "🟢",
            "partial": "🟡",
            "unverified": "🔴",
        }.get(self.verdict, "⚪")


class FactCheckError(Exception):
    """팩트체크 호출 실패."""


_EXTRACT_CLAIMS_PROMPT = """다음 영상 transcript에서 사실 검증이 필요한 주장만 추출하라.

transcript:
{transcript}

규칙:
- 의견·감정·수사적 표현 제외
- 구체적 숫자·날짜·인용·통계가 포함된 문장 우선
- 최대 8개

출력 형식 (JSON 배열만):
["주장 1", "주장 2", ...]
"""

_VERIFY_PROMPT = """다음 정치 관련 주장을 Google 검색으로 검증하라.

주장: "{claim}"

다음 JSON 형식으로만 답하라:
{{
  "verdict": "verified" | "partial" | "unverified",
  "confidence": 0.0~1.0 float,
  "summary": "검증 결과 한 줄 요약 (한국어, 50자 이내)"
}}

- verified: 신뢰할 만한 출처에서 명확히 확인됨
- partial: 부분적으로 사실이나 맥락이 다르거나 일부 오류
- unverified: 출처를 찾지 못했거나 반대되는 정보가 존재
"""


def extract_claims(transcript_text: str) -> list[str]:
    """transcript 텍스트에서 검증 대상 주장 추출.

    Args:
        transcript_text: 합쳐진 transcript (줄바꿈 구분).

    Returns:
        최대 8개의 주장 문자열 리스트.

    Raises:
        FactCheckError: 키 미설정·파싱 실패.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise FactCheckError("GEMINI_API_KEY 미설정")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise FactCheckError(f"google-genai 미설치: {e}") from e

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_EXTRACT_CLAIMS_PROMPT.format(transcript=transcript_text[:8000]),
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
    except Exception as e:
        raise FactCheckError(f"주장 추출 실패: {e}") from e

    text = (response.text or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise FactCheckError(f"JSON 파싱 실패: {e}") from e
    if not isinstance(data, list):
        raise FactCheckError(f"배열 아님: {type(data).__name__}")
    return [str(x).strip() for x in data if str(x).strip()][:8]


def verify_claim(claim: str) -> FactCheckResult:
    """단일 주장 검증 (Grounding tool 사용).

    Raises:
        FactCheckError: API 실패·잘못된 응답.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise FactCheckError("GEMINI_API_KEY 미설정")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise FactCheckError(f"google-genai 미설치: {e}") from e

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_VERIFY_PROMPT.format(claim=claim),
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception as e:
        raise FactCheckError(f"검증 실패: {e}") from e

    text = (response.text or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise FactCheckError(f"JSON 파싱 실패: {e}") from e

    verdict = str(data.get("verdict", "unverified")).lower()
    if verdict not in ("verified", "partial", "unverified"):
        verdict = "unverified"

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    sources = tuple(_extract_grounding_sources(response))

    return FactCheckResult(
        claim=claim,
        verdict=verdict,
        confidence=max(0.0, min(1.0, confidence)),
        sources=sources,
        summary=str(data.get("summary", "")).strip()[:200],
    )


def verify_transcript(transcript_text: str) -> list[FactCheckResult]:
    """transcript 전체 → 주장 추출 + 각각 검증."""
    claims = extract_claims(transcript_text)
    results: list[FactCheckResult] = []
    for c in claims:
        try:
            results.append(verify_claim(c))
        except FactCheckError as e:
            logger.warning("주장 검증 실패 (skip): %s | %s", c[:60], e)
    return results


def _extract_grounding_sources(response) -> list[str]:
    """grounding metadata에서 출처 URL 추출."""
    try:
        cand = response.candidates[0]
        meta = cand.grounding_metadata
        chunks = meta.grounding_chunks or []
        urls: list[str] = []
        for ch in chunks:
            web = getattr(ch, "web", None)
            if web and getattr(web, "uri", None):
                urls.append(web.uri)
        return urls[:5]
    except (AttributeError, IndexError):
        return []
