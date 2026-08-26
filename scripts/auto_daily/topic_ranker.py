"""039 Phase 1 — 소재 후보 클러스터링 + 랭킹.

**순위는 기사 건수가 아니라 클러스터별 총 반응 수로 매긴다**
(`[[shorts-topic-selection-by-comments]]`). 보도량으로 뽑았다가 최저임금(3건
12댓글)을 1순위로 올리고 부동산 세제개편(41건 3,936댓글)을 놓친 실패가 있다.
보도량은 언론사 관심도지 시청자 반응이 아니다.

**게이트는 랭킹 다음에 적용한다** — 순서가 반대면 반응 없는 소재가 게이트만
통과하고 올라온다.

클러스터링은 2단이다:
  1. 알려진 엔티티(인물·정당·기관·이슈어) 부분 문자열 매칭 — 정치·경제는 명단이
     안정적이라 이쪽이 정확하다.
  2. 명단에 없으면 제목 토큰 겹침 — 연예는 인물명을 미리 등록할 수 없다.
     형태소 분석 없이 한글 2자 이상 토큰을 쓰되, **너무 흔한 토큰은 제외**한다
     ('확정'처럼 전 기사에 깔린 단어로 묶으면 전부 한 덩어리가 된다).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from scripts.auto_daily.naver_metrics import Article
from scripts.auto_daily.slots import SlotSpec, resolve_window
from scripts.naver_top_political import ENTITIES as _POLITICAL_ENTITIES
from scripts.naver_top_political import GENERIC as _POLITICAL_GENERIC
from scripts.political_upload_package import has_outcome_frame, lint_topic_frame
from scripts.shorts_category import CATEGORIES

_ECONOMIC_ENTITIES = (
    "금리", "환율", "물가", "부동산", "전세", "월세", "종부세", "재산세",
    "최저임금", "실업", "고용", "수출", "관세", "증시", "코스피", "코스닥",
    "가상자산", "비트코인", "대출", "예금", "연금", "국민연금", "건강보험",
    "한국은행", "기획재정부", "금융위", "금감원", "공정위", "국세청",
    "삼성전자", "SK하이닉스", "현대차", "LG", "카카오", "네이버", "쿠팡",
    "반도체", "배터리", "조선", "철강", "유가", "세제개편", "추경", "예산",
)

# 사회는 이번 슬롯에 없지만 카테고리 축이 4종이라 표를 비워두지 않는다.
_SOCIETY_ENTITIES = (
    "경찰", "검찰", "법원", "대법원", "소방", "교육청", "학교", "병원",
    "재판", "판결", "무죄", "유죄", "구속", "영장", "고소", "고발",
    "사고", "화재", "참사", "실종", "피해자", "유족", "산재", "학폭",
)

# **연예는 인물명을 등록하지 않는다** — 매일 바뀐다. 소속사·방송사·플랫폼처럼
# 안정적인 고유명사만 두고, 인물 클러스터링은 토큰 겹침에 맡긴다.
_ENTERTAINMENT_ENTITIES = (
    "하이브", "SM", "JYP", "YG", "카카오엔터", "넷플릭스", "티빙", "쿠팡플레이",
    "디즈니플러스", "웨이브", "KBS", "MBC", "SBS", "JTBC", "tvN", "ENA",
)

ENTITIES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "political": tuple(_POLITICAL_ENTITIES),
    "economic": _ECONOMIC_ENTITIES,
    "society": _SOCIETY_ENTITIES,
    "entertainment": _ENTERTAINMENT_ENTITIES,
}
assert set(ENTITIES_BY_CATEGORY) == set(CATEGORIES), "카테고리 축이 갈라졌다"

#: 단독으로는 이슈가 못 되는 말 — 클러스터 앵커로 쓰지 않는다.
GENERIC_ANCHORS = set(_POLITICAL_GENERIC) | {
    "기자", "속보", "단독", "오늘", "내일", "어제", "관련", "이번", "지난",
    "우리", "그것", "발표", "논란", "상황", "입장", "가능", "예정",
}

_TOKEN_RE = re.compile(r"[가-힣]{2,}")
#: 토큰 겹침으로 묶는 최소 개수. 1개면 '확정' 하나로 남남이 붙는다.
_MIN_SHARED_TOKENS = 2


@dataclass(frozen=True)
class TopicCluster:
    """한 소재(이슈) 후보. `total_metric` 이 랭킹의 유일한 1차 기준."""

    anchor: str
    articles: tuple[Article, ...]
    total_metric: int
    has_outcome: bool
    warnings: tuple[str, ...]

    @property
    def article_count(self) -> int:
        return len(self.articles)

    @property
    def headline(self) -> str:
        """대표 제목 = 반응이 가장 큰 기사."""
        return max(self.articles, key=lambda a: a.metric).title if self.articles else ""

    def to_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "headline": self.headline,
            "total_metric": self.total_metric,
            "article_count": self.article_count,
            "has_outcome": self.has_outcome,
            "warnings": list(self.warnings),
            "articles": [a.to_dict() for a in self.articles],
        }


def _dedupe(articles: list[Article]) -> list[Article]:
    """동일 제목 = 동일 기사 재배포. 두 번 세면 반응이 부풀려진다."""
    seen, out = set(), []
    for a in articles:
        if a.title and a.title not in seen:
            seen.add(a.title)
            out.append(a)
    return out


def _tokens(title: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(title) if t not in GENERIC_ANCHORS}


def _group_by_entity(articles: list[Article], entities: tuple[str, ...],
                     ) -> tuple[list[tuple[str, list[Article]]], list[Article]]:
    """엔티티별로 묶고 (묶음, 남은 기사) 를 돌려준다. 기사는 한 곳에만 속한다."""
    matches = {
        e: [a for a in articles if e in a.title]
        for e in entities if e not in GENERIC_ANCHORS
    }
    taken: set[int] = set()
    groups = []
    # 많이 걸린 엔티티부터 — 동률이면 명단 순서(고정)라 결과가 재현된다.
    for entity, hits in sorted(matches.items(), key=lambda kv: -len(kv[1])):
        fresh = [a for a in hits if id(a) not in taken]
        if fresh:
            taken.update(id(a) for a in fresh)
            groups.append((entity, fresh))
    return groups, [a for a in articles if id(a) not in taken]


def _distinctive(articles: list[Article]) -> set[str]:
    """전체의 40% 이상(최소 3건)에 깔린 토큰은 변별력이 없으니 뺀다."""
    counts: dict[str, int] = {}
    for a in articles:
        for t in _tokens(a.title):
            counts[t] = counts.get(t, 0) + 1
    ceiling = max(3, int(len(articles) * 0.4))
    return {t for t, c in counts.items() if c < ceiling}


def _group_by_tokens(articles: list[Article]) -> list[tuple[str, list[Article]]]:
    """토큰 겹침 클러스터링 — 엔티티 명단이 없는 카테고리(연예)용."""
    distinctive = _distinctive(articles)
    groups: list[tuple[set[str], list[Article]]] = []
    for a in articles:
        keys = _tokens(a.title) & distinctive
        for shared, members in groups:
            if len(keys & shared) >= _MIN_SHARED_TOKENS:
                members.append(a)
                shared |= keys
                break
        else:
            groups.append((set(keys), [a]))
    return [(_pick_anchor(members, shared), members) for shared, members in groups]


def _pick_anchor(articles: list[Article], distinctive: set[str]) -> str:
    """변별력 있는 토큰 > 아무 토큰 > 제목 앞부분. 흔한 말은 앵커가 못 된다."""
    for pool in (sorted(distinctive), sorted(_tokens(articles[0].title))):
        if pool:
            return max(pool, key=len)
    return articles[0].title[:20]


def cluster_articles(articles: list[Article], *, category: str) -> list[TopicCluster]:
    """기사 목록 → 소재 클러스터. 반응 합계와 프레임 판정을 함께 계산한다."""
    unique = _dedupe(list(articles))
    if not unique:
        return []
    entity_groups, leftover = _group_by_entity(
        unique, ENTITIES_BY_CATEGORY.get(category, ()))
    groups = entity_groups + (_group_by_tokens(leftover) if leftover else [])

    clusters = []
    for anchor, members in groups:
        head = max(members, key=lambda a: a.metric).title
        clusters.append(TopicCluster(
            anchor=anchor,
            articles=tuple(members),
            total_metric=sum(a.metric for a in members),
            has_outcome=has_outcome_frame(head, category),
            warnings=tuple(lint_topic_frame(head, category)),
        ))
    return clusters


def rank_topics(clusters: list[TopicCluster], *, top_n: int = 5) -> list[TopicCluster]:
    """반응 우선, 동률이면 결과 프레임을 올린다.

    035 실측 — 결과 없는 공방형은 조회수 1,100대에서 멈춘다. 반응이 같다면
    결과가 난 사건 쪽이 완주율에서 이긴다.
    """
    alive = [c for c in clusters if c.total_metric > 0]
    ordered = sorted(alive, key=lambda c: (-c.total_metric, not c.has_outcome))
    if len(ordered) > 1 and ordered[0].total_metric == ordered[1].total_metric:
        ordered = sorted(alive, key=lambda c: (not c.has_outcome, -c.total_metric))
    return ordered[:top_n]


def topics_payload(slot: SlotSpec, clusters: list[TopicCluster],
                   *, now: datetime) -> dict:
    """topics.json 본문. 다음 단계(source_finder)가 그대로 읽는다."""
    after, before = resolve_window(slot, now)
    return {
        "slot": slot.name,
        "category": slot.category,
        "generated_at": now.isoformat(),
        "window": {"after": after.isoformat(), "before": before.isoformat()},
        "metric": "comment_count" if slot.category != "entertainment" else "read_count",
        "topics": [c.to_dict() for c in clusters],
    }
