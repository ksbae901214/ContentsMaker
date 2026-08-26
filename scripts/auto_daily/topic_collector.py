"""039 Phase 1 — 소재 수집 오케스트레이션 (수집 → 반응 측정 → 클러스터 → 랭킹).

카테고리에 따라 반응 지표가 갈린다:
  - 정치·경제·사회 → 네이버 검색 API + cbox **댓글 수**
  - 연예 → 엔터 **조회수 랭킹** (2020년 댓글창 폐지로 댓글이 진짜 0)

수집 실패는 예외를 올리지 않고 빈 리스트로 떨어진다. 소재 수집이 죽었다고
슬롯 전체가 실패하면 그날 3편이 통째로 날아간다 — 판단은 runner 가 한다.
"""
from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from scripts.auto_daily.naver_metrics import Article, article_ids
from scripts.auto_daily.naver_metrics import comment_counts as _comment_counts
from scripts.auto_daily.naver_metrics import entertainment_ranking as _ent_ranking
from scripts.auto_daily.slots import SlotSpec, resolve_window
from scripts.auto_daily.topic_ranker import (
    TopicCluster, cluster_articles, rank_topics, topics_payload,
)

logger = logging.getLogger(__name__)

TOPICS_FILENAME = "topics.json"
ENTERTAINMENT = "entertainment"


def _clean_title(title: str) -> str:
    """네이버 응답의 <b> 태그 + HTML entity 제거."""
    return html.unescape(re.sub(r"<[^>]+>", "", title or "")).strip()


def _collect_news_articles(slot: SlotSpec, now: datetime, news_collector,
                           comment_counts, http_get) -> list[Article]:
    """검색 API 수집 → 제휴 기사만 남김 → 댓글 수 부착."""
    after, before = resolve_window(slot, now)
    items = news_collector(list(slot.queries), after_kst=after, before_kst=before)

    # 비제휴 기사는 댓글창이 없어 반응을 잴 수 없다 — 후보에서 뺀다.
    partners = [it for it in items if article_ids(getattr(it, "link", ""))]
    if not partners:
        return []

    links = [it.link for it in partners]
    counts = comment_counts(links, category=slot.category, http_get=http_get)
    return [Article(title=_clean_title(it.title), link=it.link,
                    metric=int(counts.get(it.link, 0)),
                    pub_date=getattr(it, "pub_date", ""))
            for it in partners]


def _collect_entertainment_articles(now: datetime, entertainment_ranking,
                                    http_get) -> list[Article]:
    articles = entertainment_ranking(f"{now:%Y%m%d}", http_get=http_get)
    return [Article(title=_clean_title(a.title), link=a.link,
                    metric=a.metric, pub_date=a.pub_date) for a in articles]


def collect_topics(slot: SlotSpec, now: datetime, *,
                   news_collector=None, entertainment_ranking=None,
                   comment_counts=None, http_get=None,
                   top_n: int = 5) -> list[TopicCluster]:
    """슬롯의 소재 후보를 반응 순으로 최대 top_n 개.

    주입 인자는 전부 테스트/재시도용 — 미지정 시 실제 네이버 호출로 간다.
    """
    comment_counts = comment_counts or _comment_counts
    try:
        if slot.category == ENTERTAINMENT:
            articles = _collect_entertainment_articles(
                now, entertainment_ranking or _ent_ranking, http_get)
        else:
            if news_collector is None:
                from src.briefing.naver_news_collector import collect_yesterday_news
                news_collector = collect_yesterday_news
            articles = _collect_news_articles(
                slot, now, news_collector, comment_counts, http_get)
    except Exception as exc:  # noqa: BLE001 — 수집 실패로 슬롯을 죽이지 않는다
        logger.warning("[%s] 소재 수집 실패: %s", slot.name, exc)
        return []

    logger.info("[%s] 후보 기사 %d건 수집", slot.name, len(articles))
    return rank_topics(cluster_articles(articles, category=slot.category),
                       top_n=top_n)


def write_topics(slot: SlotSpec, clusters: list[TopicCluster], out_dir: Path,
                 *, now: datetime) -> Path:
    """topics.json 저장. 다음 단계(source_finder)가 이 파일을 읽는다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / TOPICS_FILENAME
    payload = topics_payload(slot, clusters, now=now)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path
