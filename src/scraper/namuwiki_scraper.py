"""Namuwiki scraper for celebrity-introduction Shorts (Phase 9-1).

Fetches a person's article from https://namu.wiki/w/{name}, parses the
summary / birth date / profession / career highlights / trivia sections, and
returns a CelebrityInfo.

Content on Namuwiki is licensed CC BY-NC-SA 3.0 — this scraper preserves the
`source_url` for downstream attribution. The Claude analyzer must REWRITE the
extracted text for the final narration; verbatim quoting is forbidden by both
the license (non-commercial) and fair-use norms.

Safeguards:
- Rate limit (default 2s between requests) — respects server load.
- User-Agent header — Namuwiki refuses empty UA.
- On-disk cache (`data/cache/namuwiki/`) — re-runs skip the network.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from src.scraper.celebrity_models import CelebrityInfo, CelebrityInfoError


NAMUWIKI_BASE = "https://namu.wiki"
DEFAULT_UA = "ContentsMaker/0.1 (https://github.com/ksbae901214/ContentsMaker)"
DEFAULT_TIMEOUT_S = 15.0
DEFAULT_RATE_LIMIT_S = 2.0


class NamuwikiScraperError(Exception):
    """Raised when scraping or parsing fails."""


class NamuwikiScraper:
    """Fetches and parses a Namuwiki person article."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        rate_limit_s: float = DEFAULT_RATE_LIMIT_S,
        user_agent: str = DEFAULT_UA,
        transport: httpx.BaseTransport | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ):
        if cache_dir is None:
            from src.config.settings import DATA_DIR
            cache_dir = DATA_DIR / "cache" / "namuwiki"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_s = max(0.0, rate_limit_s)
        self.user_agent = user_agent
        self._client = httpx.Client(
            base_url=NAMUWIKI_BASE,
            headers={
                "User-Agent": user_agent,
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
            transport=transport,
            timeout=timeout_s,
            follow_redirects=True,
        )
        self._last_request_at: float = 0.0

    # -------- Public API ---------------------------------------------------

    def fetch_person(self, name: str) -> CelebrityInfo:
        """Return CelebrityInfo for `name`, using cache when available."""
        if not name or not name.strip():
            raise NamuwikiScraperError("이름은 비어 있을 수 없습니다")

        name = name.strip()
        cached = self._load_cache(name)
        if cached is not None:
            return cached

        html = self._fetch_html(name)
        info = self._parse_html(name, html)
        self._save_cache(name, info)
        return info

    def close(self) -> None:
        self._client.close()

    # -------- Internal helpers --------------------------------------------

    def _cache_path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() else "_" for c in name)[:60]
        return self.cache_dir / f"{safe}.json"

    def _load_cache(self, name: str) -> CelebrityInfo | None:
        path = self._cache_path(name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CelebrityInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError, CelebrityInfoError):
            return None

    def _save_cache(self, name: str, info: CelebrityInfo) -> None:
        path = self._cache_path(name)
        path.write_text(
            json.dumps(info.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _respect_rate_limit(self) -> None:
        if self.rate_limit_s <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self.rate_limit_s - elapsed
        if wait > 0:
            time.sleep(wait)

    def _fetch_html(self, name: str) -> str:
        self._respect_rate_limit()
        path = f"/w/{quote(name, safe='')}"
        try:
            response = self._client.get(path)
        except httpx.RequestError as exc:
            raise NamuwikiScraperError(f"요청 실패: {exc}") from exc
        finally:
            self._last_request_at = time.monotonic()

        if response.status_code == 404:
            raise NamuwikiScraperError(
                f"'{name}' 문서를 찾을 수 없습니다 (HTTP 404)"
            )
        if response.status_code >= 400:
            raise NamuwikiScraperError(
                f"요청 실패: HTTP {response.status_code}"
            )
        return response.text

    def _parse_html(self, name: str, html: str) -> CelebrityInfo:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(".wiki-heading-content") or soup.body
        if container is None:
            raise NamuwikiScraperError(f"'{name}' 페이지 구조를 파싱할 수 없습니다")

        summary = self._extract_summary(container)
        if not summary:
            raise NamuwikiScraperError(f"'{name}' 페이지에서 요약을 찾을 수 없습니다")

        birth_date, profession = self._extract_table_fields(container)
        career_highlights = self._extract_section_list(container, ("경력", "이력"))
        trivia = self._extract_section_list(container, ("여담", "기타", "에피소드"))
        source_url = f"{NAMUWIKI_BASE}/w/{quote(name, safe='')}"

        return CelebrityInfo(
            name=name,
            summary=summary,
            source_url=source_url,
            birth_date=birth_date,
            profession=profession,
            career_highlights=career_highlights,
            trivia=trivia,
        )

    @staticmethod
    def _extract_summary(container) -> str:
        first_p = container.find("p")
        if first_p is None:
            return ""
        return first_p.get_text(strip=True)

    @staticmethod
    def _extract_table_fields(container) -> tuple[str, str]:
        birth = ""
        profession = ""
        for row in container.select("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True)
            value = td.get_text(strip=True)
            if "출생" in label or "생년" in label:
                birth = value
            elif "직업" in label or "직종" in label:
                profession = value
        return birth, profession

    @staticmethod
    def _extract_section_list(container, keywords: tuple[str, ...]) -> tuple[str, ...]:
        """Find <h2>/<h3> whose text matches any keyword, then collect
        its following <ul>/<ol> list items."""
        for heading in container.find_all(["h2", "h3"]):
            heading_text = heading.get_text(strip=True)
            if not any(kw in heading_text for kw in keywords):
                continue
            target_list = heading.find_next(["ul", "ol"])
            if target_list is None:
                continue
            items = [
                li.get_text(" ", strip=True)
                for li in target_list.find_all("li", recursive=False)
            ]
            return tuple(item for item in items if item)
        return ()
