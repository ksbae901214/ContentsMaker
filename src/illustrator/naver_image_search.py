"""Naver Image Search for celebrity-introduction Shorts (Phase 9-2).

Uses the Naver Search API (https://developers.naver.com/docs/serviceapi/search/image/image.md)
to find photos of a named person and download them to a local directory.

Licensing note: returned `link` URLs point to third-party sites. Copyright and
publicity rights belong to the original owners. This module is for personal /
learning use only — downstream code MUST show an attribution overlay in the
final video and MUST NOT upload to public platforms.

Environment:
    NAVER_CLIENT_ID, NAVER_CLIENT_SECRET — required for real calls.
    For tests, pass `transport=httpx.MockTransport(...)`.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


NAVER_API_BASE = "https://openapi.naver.com"
DEFAULT_TIMEOUT_S = 15.0
MAX_DISPLAY = 100  # Naver API hard limit


class NaverImageSearchError(Exception):
    """Raised when the search or download fails."""


@dataclass(frozen=True)
class NaverImage:
    """One image search hit."""
    title: str
    link: str
    thumbnail: str
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "thumbnail": self.thumbnail,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_api_item(cls, item: dict) -> NaverImage:
        return cls(
            title=item.get("title", ""),
            link=item.get("link", ""),
            thumbnail=item.get("thumbnail", ""),
            width=int(item.get("sizewidth", 0) or 0),
            height=int(item.get("sizeheight", 0) or 0),
        )


class NaverImageSearcher:
    """Naver image search + download client."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ):
        self.client_id = client_id or os.environ.get("NAVER_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get(
            "NAVER_CLIENT_SECRET", ""
        )
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout_s,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    # -------- Public API ---------------------------------------------------

    def search(
        self,
        query: str,
        count: int = 5,
        sort: str = "sim",
    ) -> tuple[NaverImage, ...]:
        """Search Naver images. Returns up to `count` results."""
        if not query.strip():
            raise NaverImageSearchError("검색어는 비어 있을 수 없습니다")
        if not self.client_id or not self.client_secret:
            raise NaverImageSearchError(
                "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경변수를 설정하세요"
            )
        if count < 1 or count > MAX_DISPLAY:
            raise NaverImageSearchError(
                f"count는 1-{MAX_DISPLAY} 범위여야 합니다 (현재 {count})"
            )
        if sort not in ("sim", "date"):
            raise NaverImageSearchError(
                f"sort는 'sim' 또는 'date'여야 합니다 (현재 {sort!r})"
            )

        try:
            response = self._client.get(
                f"{NAVER_API_BASE}/v1/search/image.json",
                params={"query": query, "display": count, "sort": sort},
                headers={
                    "X-Naver-Client-Id": self.client_id,
                    "X-Naver-Client-Secret": self.client_secret,
                },
            )
        except httpx.RequestError as exc:
            raise NaverImageSearchError(f"네이버 검색 요청 실패: {exc}") from exc

        if response.status_code >= 400:
            raise NaverImageSearchError(
                f"네이버 검색 HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise NaverImageSearchError("네이버 응답이 JSON이 아닙니다") from exc

        items = payload.get("items", [])
        return tuple(NaverImage.from_api_item(item) for item in items)

    def download(
        self,
        images: tuple[NaverImage, ...],
        output_dir: Path,
        filename_prefix: str = "image",
    ) -> tuple[Path, ...]:
        """Download images + a metadata.json into `output_dir`.

        Returns paths of the downloaded image files (not the metadata).
        Silently skips individual images whose download fails so that one
        broken link does not abort the batch.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        saved: list[Path] = []
        metadata: list[dict] = []

        for idx, img in enumerate(images, start=1):
            ext = _guess_extension(img.link)
            filename = f"{filename_prefix}_{idx:02d}{ext}"
            path = output_dir / filename
            try:
                self._download_one(img.link, path)
            except NaverImageSearchError as exc:
                logger.warning("이미지 다운로드 실패 skip: %s (%s)", img.link, exc)
                continue
            saved.append(path)
            metadata.append({
                **img.to_dict(),
                "saved_as": filename,
            })

        meta_path = output_dir / "metadata.json"
        meta_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return tuple(saved)

    # -------- Internal -----------------------------------------------------

    def _download_one(self, url: str, path: Path) -> None:
        try:
            response = self._client.get(url)
        except httpx.RequestError as exc:
            raise NaverImageSearchError(f"다운로드 실패: {exc}") from exc
        if response.status_code >= 400:
            raise NaverImageSearchError(
                f"다운로드 실패 HTTP {response.status_code}"
            )
        path.write_bytes(response.content)


def _guess_extension(url: str) -> str:
    """Best-effort file extension from URL path."""
    lower = url.lower().split("?")[0]
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if lower.endswith(ext):
            return ext
    return ".jpg"
