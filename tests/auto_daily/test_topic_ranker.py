"""039 Phase 1 — 소재 클러스터링·랭킹 테스트.

핵심 규칙 (`[[shorts-topic-selection-by-comments]]`):
  기사 **건수**가 아니라 클러스터별 **총 댓글 수**로 순위를 매긴다.
"""
import json

import pytest

from scripts.auto_daily.naver_metrics import Article
from scripts.auto_daily.topic_ranker import (
    ENTITIES_BY_CATEGORY, TopicCluster, cluster_articles, rank_topics,
    topics_payload,
)


def _a(title, metric=0, oid="001", aid="1"):
    return Article(title=title, link=f"https://n.news.naver.com/mnews/article/{oid}/{aid}",
                   metric=metric)


# ── 클러스터링 ──────────────────────────────────────────────────────
def test_같은_엔티티_기사끼리_묶인다():
    arts = [_a("이재명 부동산 대책 발표"), _a("이재명, 종부세 언급"), _a("장동혁 사퇴 요구")]
    clusters = cluster_articles(arts, category="political")
    anchors = {c.anchor for c in clusters}
    assert "이재명" in anchors and "장동혁" in anchors


def test_클러스터_총댓글은_소속기사_합이다():
    arts = [_a("이재명 A", 100, aid="1"), _a("이재명 B", 250, aid="2")]
    cluster = cluster_articles(arts, category="political")[0]
    assert cluster.total_metric == 350
    assert cluster.article_count == 2


def test_기사건수가_많아도_댓글이_적으면_순위가_낮다():
    """실패 사례 재현 — 최저임금 3건 12댓글 vs 부동산 1건 3936댓글."""
    arts = [
        _a("최저임금 확정 A", 4, aid="1"), _a("최저임금 확정 B", 4, aid="2"),
        _a("최저임금 확정 C", 4, aid="3"),
        _a("부동산 세제개편 확정", 3936, aid="4"),
    ]
    ranked = rank_topics(cluster_articles(arts, category="economic"), top_n=2)
    assert ranked[0].anchor == "부동산"
    assert ranked[0].total_metric == 3936


def test_알려진_엔티티가_없으면_토큰중복으로_묶는다():
    """연예는 인물명을 미리 등록할 수 없다 — 제목 토큰 겹침으로 대체."""
    arts = [
        _a("배우 홍길동 열애설 인정", 10, aid="1"),
        _a("홍길동 소속사 열애설 공식 인정", 20, aid="2"),
        _a("가수 아무개 신곡 공개", 5, aid="3"),
    ]
    clusters = cluster_articles(arts, category="entertainment")
    sizes = sorted(c.article_count for c in clusters)
    assert sizes == [1, 2]


def test_한_기사가_두_클러스터에_중복되지_않는다():
    arts = [_a("이재명 장동혁 회동", 50)]
    clusters = cluster_articles(arts, category="political")
    assert sum(c.article_count for c in clusters) == 1


def test_흔한_단어는_클러스터_앵커가_되지_않는다():
    arts = [_a("국회 본회의 개최", 5, aid="1"), _a("국회 일정 공개", 5, aid="2")]
    clusters = cluster_articles(arts, category="political")
    assert all(c.anchor != "국회" for c in clusters)


def test_빈_입력은_빈_클러스터():
    assert cluster_articles([], category="political") == []


def test_중복제목_기사는_한_번만_센다():
    """동일 제목 = 동일 기사 재배포. 두 번 세면 댓글이 부풀려진다."""
    arts = [_a("이재명 종부세 확정", 100, aid="1"), _a("이재명 종부세 확정", 100, aid="2")]
    assert cluster_articles(arts, category="political")[0].total_metric == 100


# ── 랭킹 + 프레임 게이트 ────────────────────────────────────────────
def test_top_n으로_자른다():
    arts = [_a(f"이슈{i} 확정", i * 10, aid=str(i)) for i in range(1, 8)]
    assert len(rank_topics(cluster_articles(arts, category="political"), top_n=3)) == 3


def test_결과프레임_소재가_공방형보다_위로_온다():
    """035 — 공방형은 1,100대 천장. 댓글이 비슷하면 결과어 쪽을 올린다."""
    arts = [
        _a("이재명 직격 한동훈 정면충돌", 1000, aid="1"),
        _a("장동혁 대표직 사퇴", 1000, aid="2"),
    ]
    ranked = rank_topics(cluster_articles(arts, category="political"), top_n=2)
    assert ranked[0].has_outcome is True


def test_공방형_클러스터는_경고를_단다():
    arts = [_a("이재명 직격 장동혁 공방", 500)]
    cluster = rank_topics(cluster_articles(arts, category="political"), top_n=1)[0]
    assert cluster.warnings


def test_결과형은_경고가_없다():
    arts = [_a("장동혁 대표직 사퇴", 500)]
    cluster = rank_topics(cluster_articles(arts, category="political"), top_n=1)[0]
    assert cluster.warnings == ()


def test_반응이_0인_클러스터는_제외한다():
    arts = [_a("아무도 안 본 기사 확정", 0)]
    assert rank_topics(cluster_articles(arts, category="political"), top_n=5) == []


# ── 카테고리 엔티티 ─────────────────────────────────────────────────
def test_정치_엔티티는_기존_스크립트를_재사용한다():
    from scripts.naver_top_political import ENTITIES
    assert set(ENTITIES) <= set(ENTITIES_BY_CATEGORY["political"])


def test_경제_엔티티에_핵심어가_있다():
    econ = ENTITIES_BY_CATEGORY["economic"]
    for w in ("금리", "환율", "부동산", "한국은행"):
        assert w in econ


def test_모든_카테고리에_엔티티_항목이_있다():
    from scripts.shorts_category import CATEGORIES
    assert set(ENTITIES_BY_CATEGORY) == set(CATEGORIES)


# ── 직렬화 ──────────────────────────────────────────────────────────
def test_topics_payload는_json으로_저장가능하다():
    from datetime import datetime
    from scripts.auto_daily.slots import KST, slot_for_name

    arts = [_a("장동혁 대표직 사퇴", 800)]
    ranked = rank_topics(cluster_articles(arts, category="political"), top_n=3)
    payload = topics_payload(slot_for_name("morning"), ranked,
                             now=datetime(2026, 8, 26, 7, 0, tzinfo=KST))
    text = json.dumps(payload, ensure_ascii=False)
    assert "장동혁" in text
    assert payload["slot"] == "morning"
    assert payload["category"] == "political"
    assert payload["window"]["after"].startswith("2026-08-25")


def test_TopicCluster는_불변이다():
    c = TopicCluster(anchor="x", articles=(), total_metric=0,
                     has_outcome=False, warnings=())
    with pytest.raises(Exception):
        c.anchor = "y"  # type: ignore[misc]
