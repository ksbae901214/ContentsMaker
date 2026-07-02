"""네이버 정치 뉴스 — 지정 KST 범위 수집 → 제목 키워드 빈도(보도량) 기반 인기순 랭킹.

Gemini 단일-호출 클러스터링은 수천 건 입력에서 응답이 잘려 실패하므로, 제목에서
정치 엔티티(인물·정당·기관·키워드)를 추출해 등장 기사 수로 인기 이슈를 랭킹한다.

Usage: python3 scripts/naver_top_political.py <after_iso_kst> <before_iso_kst> [top_n]
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.config import settings  # noqa: F401  — triggers .env / .env.local 로딩
from src.briefing.naver_news_collector import collect_yesterday_news

KST = timezone(timedelta(hours=9))
CACHE = "/tmp/naver_political_news.json"

# 등장 기사 수로 인기 이슈를 가르는 핵심 엔티티 후보 (인물·정당·기관·이슈 키워드).
# 제목에 부분 문자열로 포함되면 매칭 (한국어 조사 부착 무관).
ENTITIES = [
    # 인물
    "이재명", "장동혁", "한동훈", "오세훈", "김문수", "안철수", "홍준표", "이준석",
    "조국", "추경호", "나경원", "권성동", "우원식", "원희룡", "김건희", "윤석열",
    "이낙연", "김동연", "전한길", "우재준", "김재섭", "김용태",
    # 정당·진영
    "국민의힘", "더불어민주당", "민주당", "조국혁신당", "개혁신당", "혁신당",
    # 기관·이슈
    "대통령실", "국회", "검찰", "특검", "헌재", "헌법재판소", "방통위", "감사원",
    "탄핵", "체포", "구속", "영장", "기소", "재판", "선거", "지방선거", "재보궐",
    "예산", "추경", "개헌", "공천", "사퇴", "복지", "부동산", "금리", "관세", "북한",
]

# 너무 흔한/모호한 키워드 — 단독 이슈로 보기 어려움 (보조 라벨로만 사용).
GENERIC = {"국회", "선거", "재판", "정치", "대통령"}


def _clean(title: str) -> str:
    return re.sub(r"<[^>]+>|&[a-z]+;", "", title).strip()


def main() -> int:
    after = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=KST)
    before = datetime.fromisoformat(sys.argv[2]).replace(tzinfo=KST)
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    try:
        cached = json.load(open(CACHE, encoding="utf-8"))
        items = cached["items"]
        print(f"캐시 사용: {len(items)}건 ({CACHE})", file=sys.stderr)
    except Exception:
        print(f"수집 범위(KST): {after} ~ {before}", file=sys.stderr)
        news = collect_yesterday_news(
            queries=["정치", "국회", "대통령", "여당", "야당", "국민의힘", "민주당"],
            after_kst=after, before_kst=before,
        )
        items = [{"title": _clean(n.title), "link": n.link} for n in news]
        json.dump({"items": items}, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"수집 기사: {len(items)}건 (캐시 저장)", file=sys.stderr)

    # 제목 중복 제거 (동일 제목 = 동일 기사 재배포)
    seen, uniq = set(), []
    for it in items:
        t = it["title"]
        if t and t not in seen:
            seen.add(t)
            uniq.append(it)
    print(f"중복 제거 후: {len(uniq)}건", file=sys.stderr)

    # 엔티티별 등장 기사 집계
    ent_articles = defaultdict(list)
    for it in uniq:
        t = it["title"]
        for e in ENTITIES:
            if e in t:
                ent_articles[e].append(it)

    ranked = sorted(ent_articles.items(), key=lambda kv: len(kv[1]), reverse=True)

    out = []
    rank = 0
    for ent, arts in ranked:
        if ent in GENERIC:
            continue
        rank += 1
        if rank > top_n:
            break
        out.append({
            "rank": rank,
            "entity": ent,
            "article_count": len(arts),
            "headlines": [a["title"] for a in arts[:6]],
            "sample_link": arts[0]["link"],
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
