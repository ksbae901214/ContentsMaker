#!/usr/bin/env python3
"""민생 심판 정치쇼츠 재렌더 — 씬 내용별 YouTube 뉴스 영상을 배경으로 삽입.

- 기존 그라데이션 렌더의 script/audio/timings를 그대로 재사용 (재TTS 없음).
- 씬 내용을 4개 주제로 묶어 주제별 YouTube 뉴스를 ytsearch1로 1편씩 다운로드.
- 각 씬을 해당 주제 원본의 서로 다른 구간에서 9:16(center-crop)으로 컷.
- scene_videos로 재렌더 (자막은 영상 위에 그대로 오버레이).
- 다운로드/컷 실패 씬은 자동으로 그라데이션 배경 유지.
"""
import glob
import json
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.scraper.youtube_news_searcher import (
    YouTubeNewsSearchError,
    cut_scene_clip,
    get_video_duration_sec,
    search_and_download_news_clips,
)
from src.video.renderer import render_video

BASE = Path("data/political_pro/20260701_민생심판")


def _find(pattern: str) -> Path:
    hits = sorted(glob.glob(str(BASE / pattern)))
    if not hits:
        raise FileNotFoundError(f"파일 없음: {pattern}")
    return Path(hits[0])


# 씬 id → 주제
SCENE_THEME = {
    0: "price", 1: "price", 4: "price", 5: "price", 10: "price",
    2: "cash", 3: "cash", 11: "cash",
    6: "fx", 7: "fx",
    8: "debt", 9: "debt",
}
THEME_QUERY = {
    "price": "마트 물가 상승 장바구니 서민 부담 뉴스",
    "cash": "민생지원금 추경 현금 지원 뉴스",
    "fx": "원달러 환율 급등 원화 약세 뉴스",
    "debt": "국가부채 나랏빚 급증 국가채무 뉴스",
}


def main() -> None:
    script_json = _find("*_political_pro.json")
    audio_path = _find("*_aligned.mp3")
    timing_json = _find("*.timing.json")

    script = ShortsScript.from_dict(json.loads(script_json.read_text(encoding="utf-8")))
    timings = json.loads(timing_json.read_text(encoding="utf-8"))
    print(f"[1/4] 재사용 로드: {len(script.scenes)}개 씬, audio={audio_path.name}")

    # 주제별 원본 1편씩 다운로드
    themes = list(THEME_QUERY.keys())
    queries = [THEME_QUERY[t] for t in themes]
    src_dir = BASE / "yt_sources"
    downloaded = search_and_download_news_clips(
        queries, out_dir=src_dir, max_duration_sec=300
    )
    src_by_theme = {t: downloaded[i] for i, t in enumerate(themes)}
    ok = [t for t, p in src_by_theme.items() if p and Path(p).exists()]
    print(f"[2/4] 다운로드 성공 주제: {ok}")

    # 씬별 컷
    scenes_dir = BASE / "yt_scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    theme_count: dict[str, int] = {}
    scene_videos: list[dict] = []
    for s in script.scenes:
        theme = SCENE_THEME.get(s.id)
        src = src_by_theme.get(theme) if theme else None
        if not src or not Path(src).exists():
            continue
        total = get_video_duration_sec(Path(src))
        dur = max(0.6, float(s.duration))
        k = theme_count.get(theme, 0)
        theme_count[theme] = k + 1
        # 같은 원본을 쓰는 씬들은 구간을 벌려 서로 다른 장면이 나오게
        offset = min(total * 0.10 + k * (dur + 3.0), max(0.0, total - dur - 0.5))
        out = scenes_dir / f"scene_{s.id:02d}.mp4"
        try:
            cut_scene_clip(
                Path(src), output=out, start_sec=offset,
                duration_sec=dur, crop_mode="crop",
            )
            scene_videos.append({"scene_id": s.id, "video_path": str(out)})
        except YouTubeNewsSearchError as e:
            print(f"  씬 {s.id} 컷 실패: {e}")

    print(f"[3/4] 배경 삽입 씬: {len(scene_videos)}/{len(script.scenes)}")
    if not scene_videos:
        raise SystemExit("배경 클립 0개 — YouTube 다운로드 전부 실패. 재렌더 중단.")

    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=scene_videos,
        scene_timings=timings,
        output_dir=BASE,
        use_bgm=True,
        enable_transitions=False,
        enable_sfx=False,
    )
    print(f"[4/4] ✅ 재렌더 완료(영상 배경): {mp4}")


if __name__ == "__main__":
    main()
