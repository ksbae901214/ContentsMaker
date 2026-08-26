"""039 Phase 1 — 네이버 반응 지표 수집 (cbox 댓글 수 / 엔터 조회수).

**브라우저 자동화를 쓰지 않는다.** `news.naver.com` 은 확장 서버측 분류로 하드
차단돼 있어 우회 경로가 없다 (`[[naver-news-access-method]]`). 전부 HTTP 직호출.

두 지표를 쓰는 이유가 다르다:
  - 정치·경제·사회: cbox 댓글 수. 보도량은 언론사 관심도지 시청자 반응이 아니다
    (`[[shorts-topic-selection-by-comments]]`).
  - 연예: 네이버가 2020년 연예 뉴스 댓글창을 **폐지**해 댓글이 진짜로 0이다.
    조회수 랭킹으로 대체한다 (`[[naver-entertainment-no-comments]]`).
"""
from __future__ import annotations

import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib import parse, request

logger = logging.getLogger(__name__)

CBOX_URL = "https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json"
ENTERTAINMENT_RANKING_URL = "https://api-gw.entertain.naver.com/ranking/most-viewed"
_ENT_REFERER = "https://entertain.naver.com/ranking"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

#: cbox 는 카테고리별 templateId 를 요구한다. 연예는 목록에 없다(댓글창 폐지).
_TEMPLATE_IDS = {
    "political": "default_politics",
    "economic": "default_economy",
    "society": "default_society",
}
_DEFAULT_TEMPLATE = "default_politics"

#: 제휴 기사만 댓글창이 있다. hotissue 같은 중간 경로는 제외해야 한다.
_ARTICLE_RE = re.compile(
    r"^https://n\.news\.naver\.com/(?:mnews/)?article/(\d{3})/(\d{10})(?:[?#]|$)"
)
_JSONP_RE = re.compile(r"^[^(]*\((.*)\);?\s*$", re.DOTALL)


@dataclass(frozen=True)
class Article:
    """소재 후보 기사 한 건. `metric` 은 카테고리에 따라 댓글 수 또는 조회수."""

    title: str
    link: str
    metric: int = 0
    pub_date: str = ""

    def to_dict(self) -> dict:
        return {"title": self.title, "link": self.link,
                "metric": self.metric, "pub_date": self.pub_date}


def template_id_for(category: str) -> str:
    return _TEMPLATE_IDS.get(category, _DEFAULT_TEMPLATE)


def article_ids(link: str) -> tuple[str, str] | None:
    """제휴 기사 링크에서 (oid, aid). 비제휴면 None — 댓글창 자체가 없다."""
    m = _ARTICLE_RE.match(link or "")
    return (m.group(1), m.group(2)) if m else None


def parse_jsonp(text: str) -> dict:
    """`jQuery123({...});` 래퍼를 벗겨 dict 로. 순수 JSON 도 받는다."""
    body = text.strip()
    m = _JSONP_RE.match(body)
    if m:
        body = m.group(1)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"cbox 응답을 JSON 으로 읽을 수 없음: {body[:80]!r}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"cbox 응답이 객체가 아님: {type(parsed).__name__}")
    return parsed


def _http_get(url: str, headers: dict) -> str:
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=10.0) as resp:
        return resp.read().decode("utf-8", errors="replace")


def comment_count(oid: str, aid: str, *, category: str = "political",
                  http_get=None) -> int:
    """기사 한 건의 총 댓글 수. **실패는 0 으로 떨어진다.**

    한 기사 조회가 죽었다고 랭킹 전체를 날리면 슬롯이 통째로 실패한다.
    """
    get = http_get or _http_get
    query = parse.urlencode({
        "ticket": "news", "templateId": template_id_for(category),
        "pool": "cbox5", "lang": "ko", "country": "KR",
        "objectId": f"news{oid},{aid}",
        "pageSize": 1, "indexSize": 1, "page": 1, "sort": "NEW",
    })
    article_url = f"https://n.news.naver.com/mnews/article/{oid}/{aid}"
    try:
        payload = parse_jsonp(get(f"{CBOX_URL}?{query}",
                                  {"User-Agent": _UA, "Referer": article_url}))
        return int(payload["result"]["count"]["total"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.debug("댓글 수 조회 실패 (%s/%s): %s", oid, aid, exc)
        return 0


def comment_counts(links: list[str], *, category: str = "political",
                   http_get=None, workers: int = 6) -> dict[str, int]:
    """링크별 댓글 수. 비제휴 링크는 0.

    동시 6스레드까지 차단되지 않는 것이 실측됐다 (`[[naver-news-access-method]]`).
    """
    targets = {link: ids for link in links if (ids := article_ids(link))}

    def fetch(item):
        link, (oid, aid) = item
        return link, comment_count(oid, aid, category=category, http_get=http_get)

    counts = dict.fromkeys(links, 0)
    if targets:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as pool:
            counts.update(dict(pool.map(fetch, targets.items())))
    return counts


def _strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def entertainment_ranking(date_str: str, *, http_get=None) -> list[Article]:
    """연예 조회수 랭킹. 실패는 빈 리스트 — evening 슬롯이 폴백으로 넘어간다.

    응답은 UTF-8 JSON 이라 cp949 디코딩이 필요 없다 (news.naver 랭킹 HTML과 다름).
    """
    get = http_get or _http_get
    url = f"{ENTERTAINMENT_RANKING_URL}?{parse.urlencode({'date': date_str})}"
    try:
        payload = json.loads(get(url, {"User-Agent": _UA, "Referer": _ENT_REFERER}))
    except (OSError, ValueError) as exc:
        logger.warning("연예 랭킹 조회 실패 (%s): %s", date_str, exc)
        return []

    articles = []
    for row in payload.get("result", []) or []:
        oid, aid = row.get("officeId", ""), row.get("articleId", "")
        if not (oid and aid):
            continue
        articles.append(Article(
            title=_strip_tags(row.get("titleWithStrong") or row.get("title", "")),
            link=f"https://n.news.naver.com/mnews/article/{oid}/{aid}",
            metric=int(row.get("readCount", 0) or 0),
        ))
    return sorted(articles, key=lambda a: a.metric, reverse=True)
