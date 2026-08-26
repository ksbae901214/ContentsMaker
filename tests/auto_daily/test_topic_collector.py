"""039 Phase 1 — 수집 오케스트레이션 테스트 (네트워크 없음, 전부 주입)."""
import json
from datetime import datetime

from src.briefing.models import NewsItem

from scripts.auto_daily.slots import KST, slot_for_name
from scripts.auto_daily.topic_collector import collect_topics, write_topics

NOW = datetime(2026, 8, 26, 7, 0, tzinfo=KST)


def _news(title, oid="001", aid="0000000001"):
    return NewsItem(title=title,
                    link=f"https://n.news.naver.com/mnews/article/{oid}/{aid}",
                    description="", pub_date="")


def test_정치슬롯은_댓글수를_지표로_쓴다():
    collected = {}

    def fake_collector(queries, after_kst, before_kst):
        collected["queries"] = queries
        collected["after"] = after_kst
        return [_news("장동혁 대표직 사퇴", aid="0000000001"),
                _news("이재명 종부세 확정", aid="0000000002")]

    def fake_counts(links, category, http_get=None, workers=6):
        return {links[0]: 900, links[1]: 100}

    topics = collect_topics(slot_for_name("morning"), NOW,
                            news_collector=fake_collector,
                            comment_counts=fake_counts, top_n=5)
    assert topics[0].total_metric == 900
    assert collected["after"] == datetime(2026, 8, 25, 0, 0, tzinfo=KST)
    assert "국회" in collected["queries"]


def test_정치슬롯은_카테고리를_댓글조회에_넘긴다():
    """cbox templateId 가 카테고리별로 달라 잘못 넘기면 0이 돌아온다."""
    seen = {}

    def fake_counts(links, category, http_get=None, workers=6):
        seen["category"] = category
        return dict.fromkeys(links, 5)

    collect_topics(slot_for_name("noon"), NOW,
                   news_collector=lambda q, after_kst, before_kst: [_news("금리 동결 확정")],
                   comment_counts=fake_counts)
    assert seen["category"] == "economic"


def test_연예슬롯은_댓글대신_조회수랭킹을_쓴다():
    """네이버가 2020년 연예 댓글창을 폐지했다 — 댓글 조회는 아예 하지 않는다."""
    called = {"comments": False}

    def fake_counts(links, category, http_get=None, workers=6):
        called["comments"] = True
        return {}

    def fake_ranking(date_str, http_get=None):
        from scripts.auto_daily.naver_metrics import Article
        assert date_str == "20260826"
        return [Article(title="9년 만에 복귀", link="https://n.news.naver.com/mnews/article/076/0000000001",
                        metric=150000)]

    topics = collect_topics(slot_for_name("evening"),
                            datetime(2026, 8, 26, 18, 0, tzinfo=KST),
                            entertainment_ranking=fake_ranking,
                            comment_counts=fake_counts)
    assert called["comments"] is False
    assert topics[0].total_metric == 150000


def test_수집이_비면_빈리스트다():
    topics = collect_topics(slot_for_name("morning"), NOW,
                            news_collector=lambda q, after_kst, before_kst: [],
                            comment_counts=lambda links, category, **kw: {})
    assert topics == []


def test_수집기_예외는_빈리스트로_떨어진다():
    """소재 수집 실패가 슬롯 전체를 죽이면 안 된다 — 다음 단계가 판단한다."""
    def boom(queries, after_kst, before_kst):
        raise OSError("naver down")

    assert collect_topics(slot_for_name("morning"), NOW, news_collector=boom) == []


def test_비제휴_기사는_후보에서_빠진다():
    """댓글창이 없어 반응을 잴 수 없다."""
    def fake_collector(queries, after_kst, before_kst):
        return [NewsItem(title="비제휴 기사 확정", link="https://www.chosun.com/x",
                         description="", pub_date="")]

    assert collect_topics(slot_for_name("morning"), NOW,
                          news_collector=fake_collector,
                          comment_counts=lambda links, category, **kw: {}) == []


def test_제목의_HTML태그가_제거된다():
    def fake_collector(queries, after_kst, before_kst):
        return [_news("<b>장동혁</b> 사퇴 &amp; 후폭풍")]

    topics = collect_topics(slot_for_name("morning"), NOW,
                            news_collector=fake_collector,
                            comment_counts=lambda links, category, **kw: dict.fromkeys(links, 10))
    assert topics[0].headline == "장동혁 사퇴 & 후폭풍"


def test_topics_json을_파일로_쓴다(tmp_path):
    def fake_collector(queries, after_kst, before_kst):
        return [_news("장동혁 대표직 사퇴")]

    topics = collect_topics(slot_for_name("morning"), NOW,
                            news_collector=fake_collector,
                            comment_counts=lambda links, category, **kw: dict.fromkeys(links, 500))
    out = write_topics(slot_for_name("morning"), topics, tmp_path, now=NOW)

    assert out == tmp_path / "topics.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["category"] == "political"
    assert payload["topics"][0]["total_metric"] == 500


def test_write_topics는_디렉터리를_만든다(tmp_path):
    target = tmp_path / "20260826_morning"
    write_topics(slot_for_name("morning"), [], target, now=NOW)
    assert (target / "topics.json").exists()
