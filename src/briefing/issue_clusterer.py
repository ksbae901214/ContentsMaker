"""Gemini로 영상+뉴스 제목을 같은 이슈끼리 묶기.

폴백 전략 (Gemini 응답 실패 시):
    각 영상/기사를 단일-멤버 클러스터로 만듦 (클러스터링 효과 없음, 점수만 작동).

응답 JSON 형식 (prompts/cluster.txt 참조):
    {"clusters": [{"topic": "...", "member_ids": ["video_1", "news_2", ...]}, ...]}
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.briefing.models import IssueCluster, NewsItem, VideoMeta

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "cluster.txt"


class IssueClustererError(Exception):
    """Raised when 클러스터링 실패 (폴백 사용됨)."""


def _build_prompt(videos: list[VideoMeta], news: list[NewsItem]) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    lines: list[str] = ["", "# 입력", ""]
    for i, v in enumerate(videos):
        lines.append(f"- VIDEO: [id=video_{i}] {v.title}")
    for j, n in enumerate(news):
        desc = (n.description or "")[:80]
        lines.append(f"- NEWS: [id=news_{j}] {n.title} ({desc})")
    return template + "\n".join(lines)


def _fallback_singleton_clusters(
    videos: list[VideoMeta], news: list[NewsItem]
) -> list[IssueCluster]:
    """폴백: 각 영상이 자기 토픽인 단일 클러스터.

    뉴스만 있는 단일 클러스터는 만들지 않음 — 대표 영상이 없으면 plan을 못 만드므로
    UI에 노이즈만 늘림 (2026-05-21 fix: 1100개 카드 렌더링 freeze 방지).
    Gemini 클러스터링 정상 동작 시에는 영상+기사가 같은 토픽으로 묶일 수 있음.
    """
    clusters: list[IssueCluster] = []
    for v in videos:
        clusters.append(IssueCluster(topic=v.title[:25], videos=(v,)))
    return clusters


def cluster_issues(
    videos: list[VideoMeta],
    news: list[NewsItem],
    *,
    gemini_caller=None,  # 주입용 (테스트)
) -> list[IssueCluster]:
    """영상+뉴스를 같은 이슈끼리 묶음.

    Args:
        videos / news: 어제 수집된 항목들.
        gemini_caller: callable(prompt: str) -> str (테스트 주입). None이면 실제 Gemini.

    Returns:
        IssueCluster 리스트. 멤버 합집합 = 입력 전체 (누락 없음).
    """
    if not videos and not news:
        return []

    if gemini_caller is None:
        from src.analyzer.gemini_backend import call_gemini
        gemini_caller = call_gemini

    prompt = _build_prompt(videos, news)
    try:
        raw = gemini_caller(prompt)
        data = json.loads(raw)
    except Exception as e:
        logger.warning(
            "Gemini 클러스터링 실패 — 단일-멤버 폴백 사용: %s", e,
        )
        return _fallback_singleton_clusters(videos, news)

    id_to_video = {f"video_{i}": v for i, v in enumerate(videos)}
    id_to_news = {f"news_{j}": n for j, n in enumerate(news)}

    clusters: list[IssueCluster] = []
    used_ids: set[str] = set()

    raw_clusters = data.get("clusters", [])
    if not isinstance(raw_clusters, list):
        logger.warning("Gemini 응답에 'clusters' 배열 없음 — 폴백")
        return _fallback_singleton_clusters(videos, news)

    for cl in raw_clusters:
        topic = str(cl.get("topic", "")).strip()
        member_ids = cl.get("member_ids", [])
        if not topic or not isinstance(member_ids, list) or not member_ids:
            continue
        cl_videos: list[VideoMeta] = []
        cl_news: list[NewsItem] = []
        for mid in member_ids:
            if mid in id_to_video:
                cl_videos.append(id_to_video[mid])
                used_ids.add(mid)
            elif mid in id_to_news:
                cl_news.append(id_to_news[mid])
                used_ids.add(mid)
        if not cl_videos and not cl_news:
            continue
        clusters.append(IssueCluster(
            topic=topic,
            videos=tuple(cl_videos),
            news=tuple(cl_news),
        ))

    # 누락된 영상은 단일 클러스터로 추가 (정합성).
    # 누락된 뉴스는 만들지 않음 — 영상 없는 클러스터는 plan 못 만들고 UI 노이즈만 늘림.
    for vid_id, v in id_to_video.items():
        if vid_id not in used_ids:
            clusters.append(IssueCluster(topic=v.title[:25], videos=(v,)))

    return clusters
