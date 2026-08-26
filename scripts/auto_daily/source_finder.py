"""039 Phase 2 — 원본 클립 탐색 + 채널 정책 필터.

**왜 채널 정책이 필요한가**: 037-3 은 "원본에 박힌 자막 카드도 눈으로 확인"하고,
카드가 소재와 무관한 채널(뉴스 낭독 + 무관한 스트리밍 화면)이나 서술이 단정적인
채널은 소스에서 빼라고 한다. 무인 운영에는 그 눈이 없다. 대신 사람이 한 번
등록해둔 화이트리스트를 기계가 지킨다 — **정책 파일이 없으면 전부 막는다.**
저작권 스트라이크는 되돌릴 수 없으므로 기본값이 '거부'여야 한다.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

POLICY_PATH = PROJECT_ROOT / "data" / "auto_daily" / "channel_policy.json"
DEFAULT_MAX_DURATION = 900      # 15분 — config 의 dur_max 와 같은 축
DEFAULT_MIN_DURATION = 30
DEFAULT_TOP_N = 5
#: 403/포맷없음은 챌린지 솔버 부재다 (`[[ytdlp-youtube-403-ejs]]`).
EJS_ARGS = ("--remote-components", "ejs:github")


@dataclass(frozen=True)
class SourceCandidate:
    """검색으로 찾은 원본 영상 한 건."""

    video_id: str
    title: str
    channel: str
    duration: int
    url: str

    def to_dict(self) -> dict:
        return {"video_id": self.video_id, "title": self.title,
                "channel": self.channel, "duration": self.duration, "url": self.url}


@dataclass(frozen=True)
class ChannelPolicy:
    """어떤 채널의 영상을 원본으로 쓸지. 부분 문자열로 판정한다."""

    allow: tuple[str, ...]
    deny: tuple[str, ...]
    require_allowlist: bool

    def is_allowed(self, channel: str) -> bool:
        if not channel:
            return False
        if any(d and d in channel for d in self.deny):
            return False            # 블랙리스트가 화이트리스트를 이긴다
        if not self.require_allowlist:
            return True
        return any(a and a in channel for a in self.allow)


def load_policy(path: Path | None = None) -> ChannelPolicy:
    """정책 파일 로드. **없거나 깨졌으면 전부 거부**하는 기본값으로 떨어진다."""
    target = Path(path) if path is not None else POLICY_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("채널 정책을 읽지 못해 전부 거부한다 (%s): %s", target, exc)
        return ChannelPolicy(allow=(), deny=(), require_allowlist=True)
    return ChannelPolicy(
        allow=tuple(raw.get("allow", []) or []),
        deny=tuple(raw.get("deny", []) or []),
        require_allowlist=bool(raw.get("require_allowlist", True)),
    )


def search_candidates(query: str, *, limit: int = 8,
                      runner=subprocess.run) -> list[SourceCandidate]:
    """`ytsearch{N}:` 검색 결과. 실패는 빈 리스트 — 다음 소재로 넘어간다."""
    cmd = ["yt-dlp", f"ytsearch{limit}:{query}", "--dump-json",
           "--flat-playlist", "--no-warnings", *EJS_ARGS]
    try:
        result = runner(cmd, capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        logger.warning("yt-dlp 검색 실패 (%s): %s", query, exc)
        return []
    if getattr(result, "returncode", 1) != 0:
        logger.warning("yt-dlp 검색 종료코드 %s (%s)", result.returncode, query)
        return []

    candidates = []
    for line in (result.stdout or "").splitlines():
        row = _parse_row(line)
        if row is not None:
            candidates.append(row)
    return candidates


def _parse_row(line: str) -> SourceCandidate | None:
    try:
        row = json.loads(line)
    except ValueError:
        return None                 # 진행 로그가 섞여 나온다 — 조용히 건너뛴다
    video_id = row.get("id") or ""
    if not video_id:
        return None
    return SourceCandidate(
        video_id=video_id,
        title=row.get("title") or "",
        channel=row.get("channel") or row.get("uploader") or "",
        duration=int(row.get("duration") or 0),
        url=row.get("url") or f"https://www.youtube.com/watch?v={video_id}",
    )


def pick_candidates(candidates: list[SourceCandidate], policy: ChannelPolicy, *,
                    max_duration: int = DEFAULT_MAX_DURATION,
                    min_duration: int = DEFAULT_MIN_DURATION,
                    top_n: int = DEFAULT_TOP_N) -> list[SourceCandidate]:
    """정책·길이 필터를 통과한 후보. 검색 순서(관련도)를 유지한다."""
    picked, seen = [], set()
    for c in candidates:
        if c.video_id in seen:
            continue
        # duration 0 = 라이브·프리미어. 컷 계획을 세울 수 없다.
        if not (min_duration <= c.duration <= max_duration):
            continue
        if not policy.is_allowed(c.channel):
            logger.info("채널 미등록으로 제외: %s (%s)", c.channel, c.title)
            continue
        seen.add(c.video_id)
        picked.append(c)
        if len(picked) >= top_n:
            break
    return picked


def download_source(url: str, out_path: Path, *,
                    runner=subprocess.run) -> Path | None:
    """원본 영상 다운로드. 실패하거나 파일이 안 생기면 None."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["yt-dlp", url, "-f", "bv*[height<=1080]+ba/b", "--merge-output-format",
           "mp4", "-o", str(out_path), "--no-warnings", *EJS_ARGS]
    try:
        result = runner(cmd, capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        logger.warning("원본 다운로드 실패 (%s): %s", url, exc)
        return None
    if getattr(result, "returncode", 1) != 0 or not out_path.exists():
        return None
    return out_path
