"""상위 N개 이슈에 대해 generate_three_plans 호출 + 결과 저장.

각 이슈의 대표 클립(조회수 최대)에서 자막 추출 → generate_three_plans → JSON 저장.

자막 없는 영상은 plan 생성 스킵하고 manual_required=True 표시.
사용자가 웹 UI에서 보고 직접 처리하도록 안내.
"""
from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from src.briefing.models import BriefingResult, RankedIssue
from src.config.settings import DATA_DIR

logger = logging.getLogger(__name__)

BRIEFING_DATA_DIR = DATA_DIR / "daily_briefing"


class PlanRunnerError(Exception):
    """Raised when plan 생성 파이프라인 실패."""


_KEYWORD_STOPWORDS = {
    "정치", "국회", "대통령", "선거", "오늘", "이번",
    "방송", "라이브", "live", "LIVE", "Live",
    "뉴스", "속보", "분석", "현장", "독점", "단독",
    "MBC", "KBS", "SBS", "JTBC", "TV", "tv",
    "Full", "VOD", "다시보기", "다시", "보기",
}


def _extract_keywords_from_titles(titles: list[str]) -> list[str]:
    """영상 제목들에서 정치 키워드(인물·사건명) 후보 추출.

    한국어 명사 형태(한글 2~6자 연속)를 빈도순 정렬, stopword 제외, 상위 8개 반환.
    네이버 검색 어제 기사 도달률 향상용 (광범위 쿼리는 발행량 많아 도달 어려움).
    """
    import re
    from collections import Counter
    counter: Counter[str] = Counter()
    for t in titles:
        for tok in re.findall(r"[가-힣]{2,6}", t or ""):
            if tok in _KEYWORD_STOPWORDS:
                continue
            counter[tok] += 1
    # 빈도 ≥ 2 인 키워드 우선 (여러 영상 공통이면 어제 핫 이슈)
    common = [k for k, c in counter.most_common() if c >= 2][:6]
    # 빈도 1인 것도 보충 (다양성)
    rare = [k for k, c in counter.most_common() if c == 1][:2]
    return common + rare


def _try_get_transcript(youtube_url: str) -> list[dict] | None:
    """yt-dlp로 VTT 자막만 다운로드 시도 (영상 다운로드 X — 비용 절감).

    자막 없으면 None 반환 (호출자가 manual_required로 처리).
    """
    from src.scraper.youtube_downloader import download_subtitles, parse_vtt_subtitles
    try:
        with tempfile.TemporaryDirectory(prefix="briefing_subs_") as td:
            out_dir = Path(td)
            vtt = download_subtitles(youtube_url, out_dir, lang="ko")
            if vtt is None:
                return None
            transcript = parse_vtt_subtitles(vtt)
            return transcript if transcript else None
    except Exception as e:
        logger.warning("자막 다운로드 실패 (%s): %s", youtube_url, e)
        return None


def run_briefing(
    *,
    top_n: int = 5,
    date_str: str | None = None,
    channels: list[dict] | None = None,
    transcript_fetcher=None,  # 테스트 주입
    plan_generator=None,       # 테스트 주입
    youtube_service=None,      # 테스트 주입 (Phase 1 collector로 전달)
    news_http_get=None,        # 테스트 주입 (Phase 1 collector로 전달)
    gemini_caller=None,        # 테스트 주입 (Phase 2 clusterer로 전달)
) -> BriefingResult:
    """매일 브리핑 실행 — Phase 1+2+3 통합.

    Args:
        top_n: 상위 N개 이슈만 plan 생성. 나머지는 점수만 보존.
        date_str: KST 기준 "어제" YYYY-MM-DD. None이면 자동 계산.
        channels: 모니터링 채널 목록. None이면 channel_config.load_channels() 사용.

    Returns:
        BriefingResult — 결과 객체. 결과는 data/daily_briefing/{date}/ 에 자동 저장.
    """
    from src.briefing.channel_config import load_channels
    from src.briefing.issue_clusterer import cluster_issues
    from src.briefing.naver_news_collector import collect_yesterday_news
    from src.briefing.scorer import rank_clusters
    from src.briefing.youtube_collector import (
        collect_yesterday_videos,
        yesterday_kst_range,
    )

    if channels is None:
        channels = load_channels()
    after_kst, before_kst = yesterday_kst_range()

    if date_str is None:
        date_str = after_kst.date().isoformat()  # YYYY-MM-DD (어제)

    logger.info("브리핑 시작 — date=%s, 채널 %d개", date_str, len(channels))

    # Phase 1: 수집
    videos = collect_yesterday_videos(
        channels,
        after_kst=after_kst,
        before_kst=before_kst,
        youtube_service=youtube_service,
    )
    logger.info("YouTube 수집: %d 영상", len(videos))

    # 네이버 뉴스 — 광범위 쿼리("정치")는 발행량 많아 1100건 내 어제 미도달.
    # 영상 제목에서 명사 추출해 좁은 키워드로 검색하면 어제 기사 잡힐 확률↑.
    try:
        dynamic_queries = _extract_keywords_from_titles([v.title for v in videos])
        # 기본 쿼리 + 영상 기반 동적 쿼리 합침 (중복 제거)
        all_queries = list(dict.fromkeys(["정치", "국회"] + dynamic_queries))[:12]
        logger.info("네이버 검색 쿼리: %s", all_queries)
        news = collect_yesterday_news(
            queries=all_queries,
            after_kst=after_kst, before_kst=before_kst,
            http_get=news_http_get,
        )
    except Exception as e:
        logger.warning("네이버 뉴스 수집 실패 (skip): %s", e)
        news = []
    logger.info("네이버 뉴스 수집: %d 기사", len(news))

    # Phase 2: 클러스터링 + 점수화
    clusters = cluster_issues(videos, news, gemini_caller=gemini_caller)
    ranked = rank_clusters(clusters)

    # Phase 3: 상위 N개에 대해 generate_three_plans
    fetch = transcript_fetcher if transcript_fetcher is not None else _try_get_transcript
    if plan_generator is None:
        from src.analyzer.political_planner import generate_three_plans
        plan_generator = generate_three_plans

    target_dir = BRIEFING_DATA_DIR / date_str
    plans_dir = target_dir / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    # 1차 패스 — 모든 rank 시도. 일시적 오류(Gemini 503 등) rank는 retry 큐에 적재.
    retry_queue: list[RankedIssue] = []
    for ri in ranked[:top_n]:
        cluster = ri.cluster
        top_v = cluster.top_video
        if top_v is None:
            logger.info("rank=%d 대표 영상 없음(뉴스만) — plan 스킵", ri.rank)
            continue
        try:
            transcript = fetch(top_v.url)
        except Exception as e:
            logger.warning("rank=%d transcript 실패: %s", ri.rank, e)
            transcript = None
        if not transcript:
            manual_path = plans_dir / f"{ri.rank:02d}_manual_required.json"
            manual_path.write_text(json.dumps({
                "rank": ri.rank,
                "topic": cluster.topic,
                "youtube_url": top_v.url,
                "reason": "자막 없음 — 영상 다운로드 + Whisper 필요",
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        video_duration = float(transcript[-1].get("end", 60.0)) if transcript else 60.0

        try:
            result = plan_generator(
                youtube_url=top_v.url,
                transcript=transcript,
                video_title=top_v.title,
                video_duration_sec=video_duration,
                video_channel=top_v.channel_title,
                output_dir=plans_dir / f"{ri.rank:02d}",
                use_hybrid=True,
            )
            logger.info("rank=%d (%s): %d plans 생성", ri.rank, cluster.topic,
                        len(result.plans) if hasattr(result, "plans") else 0)
        except Exception as e:
            msg = str(e)
            transient = any(t in msg for t in (
                "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                "DEADLINE", "TIMEOUT", "timeout",
            ))
            logger.warning("rank=%d plan 생성 실패 (transient=%s): %s",
                           ri.rank, transient, e)
            if transient:
                retry_queue.append(ri)

    # 2차 패스 — 일시적 오류로 실패한 rank들 30초 대기 후 재시도 (high demand 회복 시간).
    if retry_queue:
        import time as _time
        wait_sec = 30.0
        logger.info(
            "🔁 일시적 오류로 %d개 rank 재시도 — %.0fs 대기 후 진행 (Gemini high demand 회복)",
            len(retry_queue), wait_sec,
        )
        _time.sleep(wait_sec)
        for ri in retry_queue:
            cluster = ri.cluster
            top_v = cluster.top_video
            if top_v is None:
                continue
            transcript = fetch(top_v.url)
            if not transcript:
                continue
            video_duration = float(transcript[-1].get("end", 60.0))
            try:
                result = plan_generator(
                    youtube_url=top_v.url,
                    transcript=transcript,
                    video_title=top_v.title,
                    video_duration_sec=video_duration,
                    video_channel=top_v.channel_title,
                    output_dir=plans_dir / f"{ri.rank:02d}",
                    use_hybrid=True,
                )
                logger.info("✅ rank=%d 재시도 성공: %d plans", ri.rank,
                            len(result.plans) if hasattr(result, "plans") else 0)
            except Exception as e:
                logger.warning("❌ rank=%d 재시도도 실패: %s", ri.rank, e)
                # manual_required 표시
                manual_path = plans_dir / f"{ri.rank:02d}_retry_failed.json"
                manual_path.write_text(json.dumps({
                    "rank": ri.rank,
                    "topic": cluster.topic,
                    "youtube_url": top_v.url,
                    "reason": f"Gemini/Claude 일시적 오류 — 재시도도 실패: {str(e)[:200]}",
                }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 최종 BriefingResult 저장
    briefing = BriefingResult(
        date=date_str,
        generated_at=datetime.utcnow().isoformat() + "Z",
        ranked_issues=tuple(ranked),
        channel_count=len(channels),
        raw_video_count=len(videos),
        raw_news_count=len(news),
    )
    (target_dir / "issues.json").write_text(
        json.dumps(briefing.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("브리핑 완료: %s", target_dir)
    return briefing


def load_briefing(date_str: str) -> BriefingResult | None:
    """저장된 브리핑 결과 로드. 없으면 None."""
    path = BRIEFING_DATA_DIR / date_str / "issues.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return BriefingResult.from_dict(data)
