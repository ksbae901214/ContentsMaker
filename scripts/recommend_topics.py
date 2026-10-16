"""쇼츠 소재 추천 CLI (044) — 네이버 '댓글 많은 뉴스' + 연예 조회수 랭킹 → 우리 채널 기준 점수.

사용:
  PYTHONPATH=. .venv311/bin/python scripts/recommend_topics.py [--days 2] [--top 5]

수집 경로는 `naver-news-access-method` 메모리 그대로다 — 브라우저 자동화는
차단되므로 curl 수준 HTTP + cp949 디코딩 + cbox 댓글 API. API 키 불필요.
점수 공식·근거는 `scripts/topic_scoring.py`.

리포트는 `data/topic_recommendations/<stamp>.md` + `.json` 으로 남는다.
JSON 은 나중에 '추천 순위 vs 실제 조회수'를 대조해 HIT_RATE 를 보정하는 근거다.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.channel_trends import followup_candidates
from scripts.topic_scoring import (
    Article, Recommendation, cluster_articles, recommend,
)

KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
MEMO_URL = "https://news.naver.com/main/ranking/popularMemo.naver?date={date}"
CBOX_URL = ("https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json"
            "?ticket=news&templateId=default_society&pool=cbox5&lang=ko&country=KR"
            "&objectId=news{oid},{aid}&pageSize=1&indexSize=1&page=1&sort=NEW")
ENT_URL = "https://api-gw.entertain.naver.com/ranking/most-viewed?date={date}"
ENT_REFERER = "https://entertain.naver.com/ranking"
CBOX_THREADS = 6            # 메모리 실측: 6스레드까지 차단 없음
OUT_DIR = Path("data/topic_recommendations")
ANALYTICS_DIR = Path("data/channel_analytics")

_MEMO_RE = re.compile(
    r'href="https://n\.news\.naver\.com/article/(\d+)/(\d+)\?ntype=RANKING"'
    r'[^>]*class="list_title[^"]*"[^>]*>([^<]+)<')


# ── 파서 (순수) ────────────────────────────────────────────────────
def parse_popular_memo(page: str) -> list[tuple[str, str, str, str]]:
    """랭킹 HTML → [(oid, aid, title, url)] (중복 제거, 등장 순)."""
    seen: set[tuple[str, str]] = set()
    out = []
    for oid, aid, title in _MEMO_RE.findall(page):
        if (oid, aid) in seen:
            continue
        seen.add((oid, aid))
        out.append((oid, aid, html.unescape(title).strip(),
                    f"https://n.news.naver.com/article/{oid}/{aid}"))
    return out


def parse_cbox_total(text: str) -> int:
    """cbox JSONP → 총 댓글 수. 실패하면 0 (추천에서 자연히 밀려난다)."""
    try:
        body = json.loads(text[text.index("(") + 1: text.rindex(")")])
        return int(body["result"]["count"]["total"])
    except (ValueError, KeyError, TypeError):
        return 0


def parse_entertainment(data: dict) -> list[Article]:
    """연예 조회수 랭킹 JSON → Article (조회수 없는 항목 제외)."""
    try:
        items = data["result"]["articles"]
    except (KeyError, TypeError):
        return []
    return [Article(title=a["title"], demand=int(a["count"]), url=a.get("url", ""))
            for a in items if a.get("title") and a.get("count")]


# ── 리포트 (순수) ──────────────────────────────────────────────────
def _rec_lines(i: int, r: Recommendation, unit: str) -> list[str]:
    flags = "".join([" · 💰내 돈" if r.money else "",
                     " · 🔁후속편" if r.followup else ""])
    lines = [
        f"### {i}. {r.label}",
        f"- **{r.tier}등급** ({r.tier_note}) · {r.category}{flags}",
        f"- {unit} {r.demand:,} · 기사 {r.article_count}건 · 점수 {r.score:,.0f}",
        f"- 각도: {r.angle_hint}",
        f"- 버전: {r.version_hint}",
    ]
    if r.hits:
        lines.append(f"- 판정 근거: {', '.join(r.hits)}")
    lines += [f"  - [{t}]({u})" for t, u in zip(r.titles, r.urls)]
    return lines + [""]


def build_report_md(news: list[Recommendation], ent: list[Recommendation], *,
                    dates: list[str], article_count: int,
                    followup_titles: list[str]) -> str:
    lines = [
        f"# 쇼츠 소재 추천 — {', '.join(dates)}",
        "",
        f"네이버 댓글 많은 뉴스 {article_count}건 기준. "
        "점수 = 반응(댓글·조회) × 039 등급 실측 돌파율 × 내 돈 1.5 × 후속편 2.0. "
        "당내 정치(DEAD)는 제외.",
        "",
    ]
    if followup_titles:
        lines += ["**후속편 기준 (채널에서 최근 터진 편)**", ""]
        lines += [f"- {t}" for t in followup_titles] + [""]
    if not news and not ent:
        return "\n".join(lines + ["추천할 소재가 없습니다.", ""])
    lines += ["## 뉴스 (댓글 기준)", ""]
    for i, r in enumerate(news, 1):
        lines += _rec_lines(i, r, "댓글")
    if ent:
        lines += ["## 연예 (조회수 기준 — 연예 기사는 댓글창이 없다)", ""]
        for i, r in enumerate(ent, 1):
            lines += _rec_lines(i, r, "조회")
    lines += ["---", "육성 영상 유무는 자동 판정하지 않는다 — 버전은 소스 확인 후 확정.", ""]
    return "\n".join(lines)


# ── 수집 (네트워크) ────────────────────────────────────────────────
def _get(url: str, referer: str | None = None, timeout: float = 15.0) -> bytes:
    headers = {"User-Agent": UA, **({"Referer": referer} if referer else {})}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                timeout=timeout) as resp:
        return resp.read()


def fetch_news(dates: list[str]) -> list[Article]:
    """날짜별 '댓글 많은' 랭킹 → cbox 로 실제 댓글 수를 붙인 Article."""
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for d in dates:
        try:
            page = _get(MEMO_URL.format(date=d)).decode("cp949", errors="replace")
        except OSError as e:
            print(f"   ⚠️ 랭킹 {d} 수집 실패: {e}", file=sys.stderr)
            continue
        for oid, aid, title, url in parse_popular_memo(page):
            found.setdefault((oid, aid), (title, url))

    def count(key: tuple[str, str]) -> int:
        oid, aid = key
        try:
            return parse_cbox_total(_get(CBOX_URL.format(oid=oid, aid=aid),
                                         referer=found[key][1]).decode("utf-8"))
        except OSError:
            return 0

    keys = list(found)
    with ThreadPoolExecutor(max_workers=CBOX_THREADS) as pool:
        totals = list(pool.map(count, keys))
    return [Article(title=found[k][0], demand=n, url=found[k][1])
            for k, n in zip(keys, totals) if n > 0]


def fetch_entertainment(dates: list[str]) -> list[Article]:
    out: dict[str, Article] = {}
    for d in dates:
        try:
            data = json.loads(_get(ENT_URL.format(date=d), referer=ENT_REFERER))
        except (OSError, json.JSONDecodeError) as e:
            print(f"   ⚠️ 연예 랭킹 {d} 수집 실패: {e}", file=sys.stderr)
            continue
        for a in parse_entertainment(data):
            if a.url not in out or out[a.url].demand < a.demand:
                out[a.url] = a
    return list(out.values())


def channel_followup_titles(analytics_dir: Path, today: str) -> list[str]:
    """최신 채널 스냅샷에서 후속편 후보 제목 (없으면 빈 목록)."""
    snaps = sorted(analytics_dir.glob("*_snapshot.json"))
    if not snaps:
        return []
    entries = json.loads(snaps[-1].read_text(encoding="utf-8")).get("entries", [])
    views = sorted(e["view_count"] for e in entries if e.get("view_count") is not None)
    if not views:
        return []
    median = views[len(views) // 2]
    return [c["title"] for c in followup_candidates(entries, today, median)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=2, help="오늘 포함 최근 N일 (KST)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    now = datetime.now(KST)
    dates = [(now - timedelta(days=i)).strftime("%Y%m%d") for i in range(args.days)]
    print(f"📡 네이버 댓글 많은 뉴스 수집: {', '.join(dates)}", flush=True)
    news_articles = fetch_news(dates)
    print(f"   댓글 집계 {len(news_articles)}건", flush=True)
    ent_articles = fetch_entertainment(dates)
    print(f"   연예 {len(ent_articles)}건", flush=True)

    follow = channel_followup_titles(ANALYTICS_DIR, dates[0])
    news = recommend(cluster_articles(news_articles), category="news",
                     followup_titles=follow, top=args.top)
    ent = recommend(cluster_articles(ent_articles), category="entertainment",
                    followup_titles=follow, top=min(3, args.top))
    md = build_report_md(news, ent, dates=dates, article_count=len(news_articles),
                         followup_titles=follow)

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    (args.out / f"{stamp}.md").write_text(md, encoding="utf-8")
    (args.out / f"{stamp}.json").write_text(json.dumps(
        {"dates": dates, "news": [asdict(r) for r in news],
         "entertainment": [asdict(r) for r in ent]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(md)
    print(f"📁 {args.out / f'{stamp}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
