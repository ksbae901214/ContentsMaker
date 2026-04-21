"""Naver 웹·백과·뉴스 검색 폴백 (2026-04-21).

나무위키에 문서가 없거나 요약이 너무 짧을 때 네이버 검색 API로
인물 정보를 보강한다. 반환값은 CelebrityInfo 호환 필드.

엔드포인트 (모두 NAVER_CLIENT_ID/SECRET 인증):
- encyc: /v1/search/encyc.json  → 백과사전 (최우선, 인물 정보 풍부)
- news:  /v1/search/news.json   → 최근 뉴스 (fallback)
- webkr: /v1/search/webkr.json  → 웹문서 (최후 fallback)

하루 쿼터: 각 25,000건 — celebrity 1건당 2~3 API call = 여유.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

NAVER_API_BASE = "https://openapi.naver.com"
DEFAULT_TIMEOUT_S = 10.0
_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_MAP = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'",
}


class NaverTextSearchError(Exception):
    """네이버 텍스트 검색 실패."""


@dataclass(frozen=True)
class NaverTextResult:
    title: str
    description: str
    link: str


def _clean(text: str) -> str:
    """네이버 API가 `<b>` 태그와 HTML 엔티티를 포함하므로 정리."""
    t = _TAG_RE.sub("", text or "")
    for ent, rep in _HTML_ENTITY_MAP.items():
        t = t.replace(ent, rep)
    return t.strip()


class NaverTextSearcher:
    """네이버 검색 API 기반 텍스트 검색기."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ):
        self.client_id = client_id or os.environ.get("NAVER_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("NAVER_CLIENT_SECRET", "")
        self._client = httpx.Client(
            base_url=NAVER_API_BASE,
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            },
            transport=transport,
            timeout=timeout_s,
        )

    def close(self) -> None:
        self._client.close()

    def _search(
        self, endpoint: str, query: str, display: int = 5
    ) -> list[NaverTextResult]:
        if not self.client_id or not self.client_secret:
            raise NaverTextSearchError(
                "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다"
            )
        if not query or not query.strip():
            raise NaverTextSearchError("검색어 비어 있음")
        try:
            r = self._client.get(
                f"/v1/search/{endpoint}.json",
                params={"query": query, "display": display},
            )
        except httpx.RequestError as e:
            raise NaverTextSearchError(f"네이버 요청 실패: {e}") from e
        if r.status_code != 200:
            raise NaverTextSearchError(
                f"네이버 응답 {r.status_code}: {r.text[:200]}"
            )
        try:
            items = r.json().get("items", [])
        except Exception as e:
            raise NaverTextSearchError("네이버 응답 JSON 파싱 실패") from e
        return [
            NaverTextResult(
                title=_clean(it.get("title", "")),
                description=_clean(it.get("description", "")),
                link=it.get("link", ""),
            )
            for it in items
        ]

    def search_encyc(self, query: str, display: int = 5) -> list[NaverTextResult]:
        """백과사전 검색 — 인물 정보에 가장 적합."""
        return self._search("encyc", query, display=display)

    def search_news(self, query: str, display: int = 5) -> list[NaverTextResult]:
        return self._search("news", query, display=display)

    def search_webkr(self, query: str, display: int = 5) -> list[NaverTextResult]:
        return self._search("webkr", query, display=display)


def fetch_celebrity_text_fallback(
    name: str,
    searcher: NaverTextSearcher | None = None,
    qualifier: str | None = None,
) -> str:
    """나무위키 요약이 불충분할 때 호출. 백과 → 뉴스 → 웹문서 순으로 시도해
    첫 의미 있는 텍스트 블록을 합성 요약으로 반환.

    qualifier: 동명이인 구분용 (예: "정치인", "배우"). 주어지면 `{name} {qualifier}`로
        검색해 정확도 향상.

    Returns 빈 문자열 if all attempts failed or no results.
    """
    own = False
    if searcher is None:
        searcher = NaverTextSearcher()
        own = True
    query = f"{name} {qualifier}".strip() if qualifier else name
    try:
        for fn_name in ("search_encyc", "search_news", "search_webkr"):
            try:
                fn = getattr(searcher, fn_name)
                results = fn(query, display=5)
            except NaverTextSearchError as e:
                logger.warning("네이버 %s 실패: %s", fn_name, e)
                continue
            # 인물명이 title에 실제 포함된 결과만 (동명이인·광고 제거)
            relevant = [r for r in results if name in r.title or name in r.description]
            if not relevant:
                relevant = results[:2]
            if relevant:
                pieces = []
                for r in relevant[:3]:
                    title = r.title.strip()
                    desc = r.description.strip()
                    if title and desc:
                        pieces.append(f"{title} — {desc}")
                    elif desc:
                        pieces.append(desc)
                if pieces:
                    return " / ".join(pieces)[:800]
    finally:
        if own:
            searcher.close()
    return ""
