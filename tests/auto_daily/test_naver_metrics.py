"""039 Phase 1 — 네이버 반응 지표 수집 테스트 (cbox 댓글 / 엔터 조회수).

HTTP는 전부 주입한다. 네트워크를 타는 테스트는 없다.
"""
import pytest

from scripts.auto_daily.naver_metrics import (
    ENTERTAINMENT_RANKING_URL, article_ids, comment_count, comment_counts,
    entertainment_ranking, parse_jsonp, template_id_for,
)

_JSONP = 'jQuery1234({"success":true,"result":{"count":{"total":3936,"comment":30}}});'


# ── 기사 ID 파싱 ────────────────────────────────────────────────────
@pytest.mark.parametrize("link,expected", [
    ("https://n.news.naver.com/mnews/article/001/0012345678", ("001", "0012345678")),
    ("https://n.news.naver.com/article/025/0003456789?ntype=RANKING", ("025", "0003456789")),
    ("https://n.news.naver.com/mnews/article/469/0000812345?sid=100", ("469", "0000812345")),
])
def test_제휴기사_링크에서_oid_aid를_뽑는다(link, expected):
    assert article_ids(link) == expected


@pytest.mark.parametrize("link", [
    "https://www.chosun.com/politics/2026/08/26/ABCDEF/",   # 비제휴 — 댓글창 없음
    "https://news.naver.com/main/ranking/popularDay.naver",
    "https://n.news.naver.com/mnews/hotissue/article/001/0012345678",
    "",
])
def test_비제휴_링크는_None을_돌려준다(link):
    assert article_ids(link) is None


# ── JSONP ───────────────────────────────────────────────────────────
def test_JSONP_래퍼를_벗겨_dict로_만든다():
    assert parse_jsonp(_JSONP)["result"]["count"]["total"] == 3936


def test_순수_JSON도_파싱한다():
    assert parse_jsonp('{"success":true}')["success"] is True


def test_망가진_응답은_ValueError():
    with pytest.raises(ValueError):
        parse_jsonp("<!DOCTYPE html><html>차단</html>")


# ── 댓글 수 ─────────────────────────────────────────────────────────
def test_댓글수를_읽어온다():
    calls = []

    def fake_get(url, headers):
        calls.append((url, headers))
        return _JSONP

    assert comment_count("001", "0012345678", http_get=fake_get) == 3936
    url, headers = calls[0]
    assert "objectId=news001%2C0012345678" in url or "objectId=news001,0012345678" in url
    # Referer 없으면 cbox가 거부한다
    assert headers["Referer"].endswith("/article/001/0012345678")


def test_카테고리별_templateId를_쓴다():
    seen = []

    def fake_get(url, headers):
        seen.append(url)
        return _JSONP

    comment_count("001", "1", category="economic", http_get=fake_get)
    assert f"templateId={template_id_for('economic')}" in seen[0]


@pytest.mark.parametrize("category,expected", [
    ("political", "default_politics"),
    ("economic", "default_economy"),
    ("society", "default_society"),
])
def test_templateId_매핑(category, expected):
    assert template_id_for(category) == expected


def test_HTTP_실패는_0으로_떨어진다():
    """한 기사 조회 실패가 전체 랭킹을 죽이면 안 된다."""
    def boom(url, headers):
        raise OSError("timeout")

    assert comment_count("001", "1", http_get=boom) == 0


def test_응답에_count가_없으면_0():
    assert comment_count("001", "1", http_get=lambda u, h: '{"success":false}') == 0


def test_여러_기사를_한번에_조회한다():
    links = [
        "https://n.news.naver.com/mnews/article/001/0000000001",
        "https://n.news.naver.com/mnews/article/002/0000000002",
        "https://www.chosun.com/not-naver",          # 스킵 대상
    ]
    counts = {"0000000001": 10, "0000000002": 25}

    def fake_get(url, headers):
        for k, v in counts.items():
            if k in url:
                return f'({{"result":{{"count":{{"total":{v}}}}}}});'
        return '{"result":{"count":{"total":0}}}'

    got = comment_counts(links, http_get=fake_get, workers=2)
    assert got["https://n.news.naver.com/mnews/article/001/0000000001"] == 10
    assert got["https://n.news.naver.com/mnews/article/002/0000000002"] == 25
    assert got["https://www.chosun.com/not-naver"] == 0


# ── 연예 랭킹 (댓글창 폐지 → 조회수) ────────────────────────────────
_ENT_JSON = {
    "result": [
        {"articleId": "0002233445", "officeId": "076",
         "titleWithStrong": "9년 만에 <strong>복귀</strong>", "readCount": 152000},
        {"articleId": "0002233446", "officeId": "311",
         "titleWithStrong": "하차 통보", "readCount": 98000},
    ]
}


def test_연예랭킹은_조회수_기준이다():
    def fake_get(url, headers):
        assert url.startswith(ENTERTAINMENT_RANKING_URL)
        assert "date=20260826" in url
        assert headers["Referer"].startswith("https://entertain.naver.com")
        import json
        return json.dumps(_ENT_JSON)

    arts = entertainment_ranking("20260826", http_get=fake_get)
    assert [a.metric for a in arts] == [152000, 98000]
    assert arts[0].title == "9년 만에 복귀"          # HTML 태그 제거
    assert arts[0].link.endswith("/article/076/0002233445")


def test_연예랭킹_실패는_빈리스트():
    def boom(url, headers):
        raise OSError("blocked")

    assert entertainment_ranking("20260826", http_get=boom) == []


def test_연예랭킹은_조회수_내림차순으로_정렬한다():
    import json

    payload = {"result": [
        {"articleId": "1", "officeId": "076", "titleWithStrong": "낮음", "readCount": 10},
        {"articleId": "2", "officeId": "076", "titleWithStrong": "높음", "readCount": 900},
    ]}
    arts = entertainment_ranking("20260826", http_get=lambda u, h: json.dumps(payload))
    assert [a.title for a in arts] == ["높음", "낮음"]
