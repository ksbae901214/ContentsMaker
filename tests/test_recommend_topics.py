"""044 소재 추천 CLI — 파서·리포트 순수 로직 (scripts/recommend_topics.py)."""
from __future__ import annotations

from scripts.recommend_topics import (
    build_report_md, parse_cbox_total, parse_entertainment, parse_popular_memo,
)
from scripts.topic_scoring import Article, cluster_articles, recommend

MEMO_HTML = """
<a href="https://n.news.naver.com/article/025/0003557055?ntype=RANKING" class="list_title nclicks('RBP.drnknws')">&quot;딸 논문 대필&quot; 김민석·한동훈</a>
<a href="https://n.news.naver.com/article/648/0000051472?ntype=RANKING" class="list_title nclicks('RBP.drnknws')">SK하닉 상장</a>
<a href="https://n.news.naver.com/article/025/0003557055?ntype=RANKING" class="list_title">&quot;딸 논문 대필&quot; 김민석·한동훈</a>
"""


class TestParsePopularMemo:
    def test_extracts_unique_articles_with_unescaped_titles(self):
        out = parse_popular_memo(MEMO_HTML)
        assert out == [
            ("025", "0003557055", '"딸 논문 대필" 김민석·한동훈',
             "https://n.news.naver.com/article/025/0003557055"),
            ("648", "0000051472", "SK하닉 상장",
             "https://n.news.naver.com/article/648/0000051472"),
        ]

    def test_empty_html(self):
        assert parse_popular_memo("") == []


class TestParseCboxTotal:
    def test_jsonp(self):
        text = '_callback({"success":true,"result":{"count":{"total":733}}});'
        assert parse_cbox_total(text) == 733

    def test_failure_returns_zero(self):
        assert parse_cbox_total('_callback({"success":false})') == 0
        assert parse_cbox_total("garbage") == 0


class TestParseEntertainment:
    def test_articles_by_views(self):
        data = {"result": {"articles": [
            {"title": "김호영 유튜브 법적 대응", "count": 647794,
             "url": "https://m.entertain.naver.com/article/117/0004113946"},
            {"title": "없는 조회수", "url": "u"},
        ]}}
        out = parse_entertainment(data)
        assert out == [Article(title="김호영 유튜브 법적 대응", demand=647794,
                               url="https://m.entertain.naver.com/article/117/0004113946")]

    def test_bad_shape(self):
        assert parse_entertainment({}) == []


class TestBuildReport:
    def test_sections_and_fields(self):
        news = recommend(cluster_articles(
            [Article("교사 폭행 학부모 결국 사과", 1200, "https://n/1")]),
            category="news")
        ent = recommend(cluster_articles(
            [Article("배우 갑질 결국 하차", 500_000, "https://e/1")]),
            category="entertainment")
        md = build_report_md(news, ent, dates=["20261011", "20261012"],
                             article_count=393, followup_titles=["박위 사과"])
        assert "# 쇼츠 소재 추천" in md
        assert "교사 폭행 학부모 결국 사과" in md
        assert "A등급" in md
        assert "댓글 1,200" in md
        assert "## 연예" in md
        assert "조회 500,000" in md
        assert "https://n/1" in md
        assert "박위 사과" in md

    def test_empty_lists(self):
        md = build_report_md([], [], dates=["20261012"], article_count=0,
                             followup_titles=[])
        assert "추천할 소재가 없습니다" in md
