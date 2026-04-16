"""YouTube video search for lawmaker speeches.

Uses yt-dlp to search YouTube without requiring an API key.
Results include video metadata: title, URL, duration, view count, upload date.
"""
from __future__ import annotations

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


class VideoSearchError(Exception):
    """Raised when video search fails."""


def search_lawmaker_videos(
    lawmaker_name: str,
    source: str = "all",
    max_results: int = 10,
) -> list[dict]:
    """Search YouTube for lawmaker speech videos using yt-dlp.

    Args:
        lawmaker_name: Name of the lawmaker (e.g., "나경원")
        source: Search source — "natv" for National Assembly TV,
                "news" for news channels, "all" for general search.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with keys:
          title, url, duration_seconds, view_count, upload_date, channel, thumbnail

    Raises:
        VideoSearchError: If yt-dlp is not installed or search fails.
    """
    query = _build_query(lawmaker_name, source, max_results)
    raw_lines = _run_ytdlp_search(query)
    return _parse_results(raw_lines)


def _build_query(name: str, source: str, max_results: int) -> str:
    if source == "natv":
        return f"ytsearch{max_results}:{name} 국회 발언 국회TV NATV"
    if source == "news":
        return f"ytsearch{max_results}:{name} 의원 발언 뉴스"
    return f"ytsearch{max_results}:{name} 국회 발언"


def _run_ytdlp_search(query: str) -> list[str]:
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--quiet",
        query,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise VideoSearchError("yt-dlp 검색 시간 초과 (30초)") from exc
    except FileNotFoundError as exc:
        raise VideoSearchError(
            "yt-dlp가 설치되어 있지 않습니다. 'pip3 install yt-dlp'를 실행하세요."
        ) from exc

    if result.returncode != 0 and not result.stdout.strip():
        raise VideoSearchError(f"yt-dlp 검색 실패: {result.stderr[:200]}")

    return [line for line in result.stdout.strip().split("\n") if line.strip()]


def _parse_results(raw_lines: list[str]) -> list[dict]:
    videos = []
    for line in raw_lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        video_id = data.get("id", "")
        url = (
            data.get("url")
            or data.get("webpage_url")
            or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
        )
        if not url:
            continue

        videos.append({
            "title": data.get("title", ""),
            "url": url,
            "duration_seconds": data.get("duration") or 0,
            "view_count": data.get("view_count") or 0,
            "upload_date": data.get("upload_date", ""),
            "channel": data.get("channel") or data.get("uploader", ""),
            "thumbnail": data.get("thumbnail", ""),
        })

    return videos


def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if seconds <= 0:
        return "--:--"
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_upload_date(date_str: str) -> str:
    """Format YYYYMMDD to YYYY.MM.DD."""
    if len(date_str) == 8:
        return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"
    return date_str


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Search YouTube for lawmaker videos")
    parser.add_argument("--name", required=True, help="Lawmaker name (e.g. 나경원)")
    parser.add_argument("--source", default="all", choices=["all", "natv", "news"])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    try:
        results = search_lawmaker_videos(args.name, args.source, args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except VideoSearchError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
