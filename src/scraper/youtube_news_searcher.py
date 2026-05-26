"""YouTube 뉴스 자동 검색·다운로드 (Feature 023 — 정치쇼츠 topic 모드).

주제 입력 모드에서 ShortsPlan.youtube_search_keywords 배열을 받아
각 키워드별로 yt-dlp `ytsearch1`로 한 영상씩 다운로드하고,
ffmpeg으로 씬별 9:16 클립으로 자른다.

스타벅스 5·18 영상 작업에서 검증된 패턴 (2026-05-26).
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class YouTubeNewsSearchError(Exception):
    """Raised when YouTube news search or download fails."""


# 9:16 크롭 + 영상만(오디오 제거): scale로 높이 1920 맞춤 + 중앙 1080폭 크롭
_VF_9x16_CROP = "scale=-2:1920,crop=1080:1920"


def search_and_download_news_clips(
    keywords: list[str],
    *,
    out_dir: Path,
    max_duration_sec: int = 300,
) -> list[Path]:
    """키워드 배열로 YouTube 뉴스 클립 다운로드.

    각 키워드별로 ``ytsearch1``로 한 영상 다운로드. 실패 시 해당 인덱스에는
    None 대신 빈 리스트가 아닌 길이 N 결과의 ``None``이 들어가지 않도록 — 호출자가
    실패 위치를 알 수 있도록 ``None``을 채워서 N 길이를 보존한다.

    Args:
        keywords: 검색어 배열 (씬별 1개).
        out_dir: 다운로드 디렉토리.
        max_duration_sec: 검색 영상 최대 길이(초). 너무 긴 영상 회피.

    Returns:
        각 키워드별 다운로드 경로 (실패한 인덱스는 None). 길이는 keywords와 동일.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []

    for i, kw in enumerate(keywords):
        kw = (kw or "").strip()
        if not kw:
            logger.warning("키워드 #%d 비어있음 — 스킵", i)
            results.append(None)  # type: ignore[arg-type]
            continue

        try:
            path = _download_single(kw, out_dir, idx=i, max_duration_sec=max_duration_sec)
            results.append(path)
            logger.info("✅ 검색 클립 #%d 다운로드 완료: %s", i, path.name)
        except YouTubeNewsSearchError as e:
            logger.warning("❌ 검색 클립 #%d (%r) 다운로드 실패: %s", i, kw, e)
            results.append(None)  # type: ignore[arg-type]

    return results


def _download_single(
    keyword: str,
    out_dir: Path,
    *,
    idx: int,
    max_duration_sec: int,
) -> Path:
    """단일 키워드 → yt-dlp ytsearch1 다운로드 → mp4 경로 반환."""
    template = str(out_dir / f"search{idx:02d}_%(title).40s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--default-search", "ytsearch1",
        "--match-filters", f"duration<={max_duration_sec}",
        "-f", "best[height<=720]/best",
        "--no-playlist",
        "--print", "after_move:filepath",
        "--no-simulate",
        "--quiet",
        "-o", template,
        keyword,
    ]
    logger.info("yt-dlp 검색 #%d: %r", idx, keyword)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired as e:
        raise YouTubeNewsSearchError(
            f"yt-dlp 시간 초과 (180s) — 키워드: {keyword!r}"
        ) from e

    if result.returncode != 0:
        raise YouTubeNewsSearchError(
            f"yt-dlp exit {result.returncode}: {(result.stderr or '')[:200]}"
        )

    # 1차: stdout의 after_move:filepath 라인 신뢰
    for line in (result.stdout or "").splitlines():
        candidate = Path(line.strip())
        if candidate.exists() and candidate.suffix.lower() in (".mp4", ".webm", ".mkv"):
            return candidate

    # 2차: glob 폴백
    pattern = f"search{idx:02d}_*"
    matches = sorted(out_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
    if matches:
        return matches[-1]

    raise YouTubeNewsSearchError(
        f"다운로드된 영상 파일을 찾을 수 없음 — 키워드: {keyword!r}"
    )


def cut_scene_clip(
    source: Path,
    *,
    output: Path,
    start_sec: float,
    duration_sec: float,
    crop_9x16: bool = True,
) -> Path:
    """소스 영상에서 ``start_sec`` 부터 ``duration_sec`` 만큼 잘라 9:16로 크롭.

    Args:
        source: 다운로드된 원본 영상 경로.
        output: 출력 파일 경로 (.mp4).
        start_sec: 시작 시간 (초).
        duration_sec: 자를 길이 (초).
        crop_9x16: True면 1080x1920 9:16 중앙 크롭. False면 원본 비율 유지.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0.0, start_sec)),
        "-i", str(source),
        "-t", str(max(0.5, duration_sec)),
    ]
    if crop_9x16:
        cmd += ["-vf", _VF_9x16_CROP]
    cmd += [
        "-c:v", "libx264", "-preset", "fast",
        "-an",  # 오디오 제거 (TTS가 메인)
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise YouTubeNewsSearchError(
            f"ffmpeg cut 실패 (exit {result.returncode}): {(result.stderr or '')[:200]}"
        )
    if not output.exists():
        raise YouTubeNewsSearchError(f"cut 출력 파일 없음: {output}")
    return output


def get_video_duration_sec(path: Path) -> float:
    """ffprobe로 영상 길이 측정."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "csv=p=0",
                "-show_entries", "format=duration",
                "-i", str(path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        return float((result.stdout or "0").strip() or 0)
    except Exception as e:
        logger.warning("ffprobe duration 측정 실패: %s", e)
        return 0.0


def build_scene_clips(
    scene_durations: list[float],
    *,
    keywords: list[str],
    out_dir: Path,
    crop_9x16: bool = True,
) -> list[Path | None]:
    """주제 모드용 통합 함수 — 검색 + 다운로드 + 씬별 cut.

    Args:
        scene_durations: 씬별 길이 (초). 길이가 keywords와 다르면 짧은 쪽 기준.
        keywords: 씬별 검색어. 길이가 scene_durations와 다르면 짧은 쪽 기준.
        out_dir: 작업 디렉토리. ``out_dir/sources/``에 원본 다운로드, ``out_dir/scenes/``에 cut 결과.
        crop_9x16: 9:16 크롭 여부.

    Returns:
        씬별 클립 경로 (실패는 None). 길이는 min(len(scene_durations), len(keywords))과 동일.
    """
    sources_dir = out_dir / "sources"
    scenes_dir = out_dir / "scenes"
    sources_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    n = min(len(scene_durations), len(keywords))
    if n == 0:
        return []

    # 1) 키워드별 검색·다운로드
    downloaded = search_and_download_news_clips(
        keywords[:n], out_dir=sources_dir,
    )

    # 2) 씬별 cut (각 소스의 다양한 구간 사용 — 5초 간격 offset)
    clips: list[Path | None] = []
    for i, src in enumerate(downloaded):
        if src is None or not src.exists():
            clips.append(None)
            continue

        total_dur = get_video_duration_sec(src)
        # 씬마다 다른 구간 선택 — 너무 앞·뒤 회피하고 중간 영역에서 시작
        offset = min(max(0.0, total_dur * 0.15), max(0.0, total_dur - scene_durations[i] - 1.0))
        out_path = scenes_dir / f"s{i:02d}.mp4"
        try:
            cut_scene_clip(
                src,
                output=out_path,
                start_sec=offset,
                duration_sec=scene_durations[i],
                crop_9x16=crop_9x16,
            )
            clips.append(out_path)
        except YouTubeNewsSearchError as e:
            logger.warning("씬 #%d cut 실패: %s", i, e)
            clips.append(None)

    return clips


def safe_search_keyword(text: str, *, max_chars: int = 80) -> str:
    """LLM 응답을 yt-dlp 검색어로 안전하게 정리.

    - 양 끝 공백·따옴표 제거
    - 줄바꿈 → 공백
    - 길이 제한
    """
    cleaned = re.sub(r"\s+", " ", (text or "").strip().strip("\"'"))
    return cleaned[:max_chars]


__all__ = [
    "YouTubeNewsSearchError",
    "search_and_download_news_clips",
    "cut_scene_clip",
    "get_video_duration_sec",
    "build_scene_clips",
    "safe_search_keyword",
]
