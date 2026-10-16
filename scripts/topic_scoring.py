"""소재 추천 점수 (044) — '사람들이 반응하나' × '우리 채널에서 터지나'.

    score = √demand × HIT_RATE[039 등급] × (내 돈 1.5) × (후속편 2.0)

- demand: 뉴스는 이슈 묶음의 네이버 댓글 총합(`shorts-topic-selection-by-comments`
  메모리 — 보도량이 아니라 반응), 연예는 기사 조회수(댓글창 폐지). 척도가 달라
  두 목록은 섞지 않는다.
- √demand: 뜨거움은 체감 수익이다. 039 실측상 정치 소재는 아무리 큰 이슈여도
  1,300 밴드에 갇힌다(인지도는 변수 아님). 선형이면 댓글 37,700 골프 공방(C)이
  3,517 단체관람 취소(A)와 동점이 됐다. 제곱근이면 C 가 A 를 이기려면 반응이
  (0.75/0.07)² ≈ 115배여야 한다 — 정치를 막는 게 아니라 '뜨겁다는 이유만으로'
  올라오지 않게 한다.
- HIT_RATE: 039 실측 돌파율(3,000회+) — A 75% / B 25% / C 7% / DEAD 0%.
  표본이 작다(A 는 8~11편, 박위 3편 포함). 추천 리포트를 남겨 실제 조회수와
  대조하며 보정할 것.
- 내 돈: 044 정점 구간의 금감원 세종 이전(3,862)·금리 인상(2,496) 계열.
- 후속편: 039 증폭기(박위 55,523 → 7,002 → 6,208). 채널 리포트의 후속 후보와
  핵심어가 겹치면 붙인다.

순수 함수만 둔다 — 수집(네트워크)은 `scripts/recommend_topics.py`.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from scripts.shorts_breakout import (
    COST_WORDS, POLITICIAN, POLITICIAN_MARKERS, SUBJECT_KEY, TIER_A, TIER_B,
    TIER_C, TIER_DEAD, UNSETTLED_WORDS, evaluate,
)
from scripts.shorts_category import UNKNOWN, classify_category
from scripts.shorts_symmetry import LEFT_MARKERS, RIGHT_MARKERS

HIT_RATE = {TIER_A: 0.75, TIER_B: 0.25, TIER_C: 0.07, TIER_DEAD: 0.0}
MONEY_BOOST = 1.5
FOLLOWUP_BOOST = 2.0
MIN_SHARED_TOKENS = 2       # 한 단어만 겹치면('대통령') 다른 이슈다
TOP_TITLES = 3              # 판정·표시에 쓰는 대표 기사 수

MONEY_WORDS = (
    "세금", "월급", "연봉", "금리", "대출", "집값", "전세", "월세", "연금",
    "보험료", "물가", "요금", "수당", "환급", "지원금",
    "이전", "파업", "해고", "구조조정", "직장인", "자영업", "서민",
)

# 040 사용자 확정(2026-09-04): 범죄 소재는 편성 제외. 사건형 강력범죄만 —
# 학대 판결·갑질처럼 '대가를 치른 사람' 소재까지 막으면 A 등급이 사라진다.
CRIME_WORDS = ("살해", "살인", "시신", "흉기", "토막", "납치", "성폭행", "강간",
               "성착취", "묻지마")

_PARTICLES = ("에서", "으로", "까지", "부터", "에게", "한테", "은", "는",
              "이", "가", "을", "를", "의", "에", "도", "로", "과", "와", "만")
_STOP = {"단독", "속보", "종합", "영상", "포토", "기자", "오늘", "어제", "결국",
         "논란", "의혹", "그리고", "하지만", "이번", "지금",
         "알고", "보니", "정체", "충격", "이유",   # '알고 보니'로 크리스·톰 크루즈가 묶였다
         "공개", "만에"}   # '공개'·'만에'로 탑 묶음에 조세호·김용지가 섞였다

# 직함 없이 이름만 나오는 공인 — 039 판정기는 직함으로만 정치인을 알아본다.
# 뉴스 제목은 "박지원 \"…\"" 처럼 이름만 쓰는 게 기본이라, 이게 없으면 정치인이
# 민간인 A 등급으로 올라온다(2026-10-12 첫 실행: 안규백·정동영·박지원·추미애).
# 040 진영 사전을 재사용하고, 사전에 없던 이름·사법부 직함을 더한다. 낡는 목록이다.
PUBLIC_FIGURES = tuple(
    m for m in LEFT_MARKERS + RIGHT_MARKERS if not m.isascii()
) + ("정동영", "박지원", "주진우", "김의겸", "정봉주", "김여정", "김정은",
     "조희대", "대법원장", "대법관", "감사원장", "검찰총장", "청와대", "靑", "李")
# 후속편 매칭에서 무시할 흔한 단어 — '사과'가 겹친다고 같은 인물이 아니다
_FOLLOWUP_STOP = (_STOP | set(COST_WORDS) | set(UNSETTLED_WORDS)
                  | set(POLITICIAN_MARKERS))
_BRACKET_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|#\S+")
_SPLIT_RE = re.compile(r"[^0-9A-Za-z가-힣一-鿿]+")


@dataclass(frozen=True)
class Article:
    title: str
    demand: int             # 뉴스 = 댓글 수, 연예 = 조회수
    url: str


@dataclass(frozen=True)
class TopicCluster:
    label: str              # 수요가 가장 큰 기사 제목
    demand: int
    articles: tuple[Article, ...]
    tokens: frozenset[str]  # 대표 기사 핵심어 (묶기 기준)


@dataclass(frozen=True)
class Recommendation:
    label: str
    category: str
    tier: str
    tier_note: str
    demand: int
    score: float
    money: bool
    followup: bool
    hits: tuple[str, ...]
    titles: tuple[str, ...]
    urls: tuple[str, ...]
    article_count: int
    version_hint: str
    angle_hint: str


def _strip_particle(word: str) -> str:
    for p in _PARTICLES:
        if word.endswith(p) and len(word) - len(p) >= 2:
            return word[: -len(p)]
    return word


def title_tokens(title: str) -> frozenset[str]:
    """제목 → 핵심어 집합 (괄호·해시태그 제거, 조사 1개 제거, 2자 이상)."""
    words = _SPLIT_RE.split(_BRACKET_RE.sub(" ", title))
    toks = (_strip_particle(w) for w in words if w)
    return frozenset(t for t in toks if len(t) >= 2 and t not in _STOP)


def cluster_articles(articles: list[Article]) -> list[TopicCluster]:
    """같은 이슈 기사 묶기 — 수요 큰 기사부터, 대표 기사와 핵심어 2개+ 겹치면 합류."""
    seeds: list[tuple[frozenset[str], list[Article]]] = []
    for art in sorted(articles, key=lambda a: a.demand, reverse=True):
        toks = title_tokens(art.title)
        home = next((members for seed, members in seeds
                     if len(seed & toks) >= MIN_SHARED_TOKENS), None)
        if home is None:
            seeds.append((toks, [art]))
        else:
            home.append(art)
    clusters = [TopicCluster(label=members[0].title,
                             demand=sum(a.demand for a in members),
                             articles=tuple(members), tokens=seed)
                for seed, members in seeds]
    return sorted(clusters, key=lambda c: c.demand, reverse=True)


def score_topic(demand: int, tier: str, money: bool = False,
                followup: bool = False) -> float:
    return (math.sqrt(max(demand, 0)) * HIT_RATE[tier]
            * (MONEY_BOOST if money else 1.0)
            * (FOLLOWUP_BOOST if followup else 1.0))


def _pseudo_config(cluster: TopicCluster, category: str) -> dict:
    """039 판정기(config 입력)에 넣을 가짜 config.

    - 공인 이름이 있으면 당사자 = 정치인으로 못박는다(`PUBLIC_FIGURES`).
    - 사회·연예는 **대가 어휘가 있을 때만** 당사자(persons)가 있다고 본다.
      뉴스 묶음에선 실명을 확인할 길이 없어, 대가도 없는 소재(스타벅스 1위 탈환)가
      A 로 올라왔다. persons 가 비면 판정기가 '기관'으로 보고 C 를 준다 — 039 ②
      (대가 있음 36% vs 없음 7%)와 같은 방향이다.
    """
    title = " / ".join(a.title for a in cluster.articles[:TOP_TITLES])
    if category == "news":
        guessed = classify_category(title)
        category = "society" if guessed == UNKNOWN else guessed
    cfg = {"title": title, "category": category, "persons": []}
    if any(name in title for name in PUBLIC_FIGURES):
        return {**cfg, SUBJECT_KEY: POLITICIAN}
    if category in ("society", "entertainment") and any(w in title for w in COST_WORDS):
        return {**cfg, "persons": [cluster.label]}
    return cfg


def _is_followup(cluster: TopicCluster, followup_tokens: list[frozenset[str]]) -> bool:
    mine = cluster.tokens - _FOLLOWUP_STOP
    return any(mine & (t - _FOLLOWUP_STOP) for t in followup_tokens)


def _version_hint(category: str, tier: str, money: bool) -> str:
    if category == "entertainment":
        return "육성 있으면 V2.2 (+V2.1) / 없으면 V4.0 (연예 허용 2026-10-12)"
    if category != "political":
        return "V2.2 (+V2.1 병행) — V4.0 은 정치·연예 전용"
    if tier == TIER_B or money:
        return "증거(육성·캡처)로 모순을 치면 V5.0 / 육성 있으면 V2.2 / 없으면 V4.0"
    return "육성 있으면 V2.2 (+V2.1) / 없으면 V4.0"


def _angle_hint(category: str, tier: str) -> str:
    if tier == TIER_A:
        return "당사자가 잃은 것(사과·취소·하차)을 훅으로"
    if tier == TIER_B:
        return "'과거 발언 vs 현재 행동' 대조 — 양쪽 진영에 같은 잣대(040)"
    if category == "political":
        return "정치인 공방 말고 이 사건으로 잃거나 다친 사람을 주인공으로(044)"
    return "당사자가 치른 대가가 아직 없다 — 결말이 난 뒤 다룰 것"


def recommend(clusters: list[TopicCluster], *, category: str,
              followup_titles: list[str] | None = None,
              top: int = 5) -> list[Recommendation]:
    """묶음 → 점수순 추천 (DEAD·강력범죄 제외). category: "news" 또는 "entertainment"."""
    follow = [title_tokens(t) for t in (followup_titles or [])]
    recs = []
    for c in clusters:
        cfg = _pseudo_config(c, category)
        if any(w in cfg["title"] for w in CRIME_WORDS):
            continue
        verdict = evaluate(cfg)
        if verdict.tier == TIER_DEAD:
            continue
        money = any(w in cfg["title"] for w in MONEY_WORDS)
        followup = _is_followup(c, follow)
        recs.append(Recommendation(
            label=c.label, category=cfg["category"], tier=verdict.tier,
            tier_note=verdict.note, demand=c.demand,
            score=score_topic(c.demand, verdict.tier, money, followup),
            money=money, followup=followup, hits=verdict.hits,
            titles=tuple(a.title for a in c.articles[:TOP_TITLES]),
            urls=tuple(a.url for a in c.articles[:TOP_TITLES]),
            article_count=len(c.articles),
            version_hint=_version_hint(cfg["category"], verdict.tier, money),
            angle_hint=_angle_hint(cfg["category"], verdict.tier),
        ))
    return sorted(recs, key=lambda r: r.score, reverse=True)[:top]
