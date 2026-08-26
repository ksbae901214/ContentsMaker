"""039 Phase 4 — 렌더 결과를 YouTube/TikTok 에 올리는 CLI.

여태 `upload_video()` 호출부는 `app/api/generate/route.ts` 안에만 있어서 CLI
경로에서는 업로드가 불가능했다. 이 모듈이 그 구멍을 메운다.

**두 가지 자동화 한계를 코드로 명시한다** (숨기면 '올렸겠지' 하고 넘어간다):
  1. **TikTok 은 초안까지만.** `tiktok_uploader` 가 `privacy_level: "SELF_ONLY"`
     로 고정돼 있고, Content Posting API 의 공개 게시는 심사 통과 앱만 쓸 수
     있다. 폰에서 1탭 게시가 필요하다.
  2. **고정댓글은 '작성'까지만.** YouTube Data API v3 에 댓글 **고정** 엔드포인트가
     없다. 댓글은 자동으로 달리지만 고정은 스튜디오에서 눌러야 한다.

메타데이터는 config 에서 만드는 것이 기본이고, 사람이 `upload_package.md` 를
고쳤다면 그쪽이 이긴다 — 검수자의 수정이 최종이어야 한다.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scripts.auto_daily.slots import KST

logger = logging.getLogger(__name__)

YOUTUBE_TITLE_MAX = 100
#: 25 = News & Politics, 24 = Entertainment
_CATEGORY_IDS = {"political": "25", "economic": "25", "society": "25",
                 "entertainment": "24"}
DEFAULT_CATEGORY_ID = "25"
TARGETS_ALL = ("youtube", "tiktok")

_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})")


@dataclass(frozen=True)
class UploadMetadata:
    title: str
    description: str
    tags: list[str]
    pinned_comment: str
    category_id: str


@dataclass(frozen=True)
class PublishOutcome:
    """업로드 결과. 실패해도 예외가 아니라 여기 담아 돌려준다."""

    youtube_url: str | None = None
    tiktok_publish_id: str | None = None
    comment_id: str | None = None
    errors: tuple[str, ...] = ()

    @property
    def tiktok_needs_manual_publish(self) -> bool:
        """초안으로만 올라간다 — 폰에서 게시를 눌러야 공개된다."""
        return self.tiktok_publish_id is not None

    @property
    def comment_needs_manual_pin(self) -> bool:
        """댓글은 달렸지만 고정은 API 로 못 한다."""
        return self.comment_id is not None


def youtube_category_id(category: str) -> str:
    return _CATEGORY_IDS.get(category, DEFAULT_CATEGORY_ID)


def video_id_from_url(url: str) -> str | None:
    m = _VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else None


# ── 메타데이터 ──────────────────────────────────────────────────────
def metadata_from_config(cfg: dict) -> UploadMetadata:
    """config → 업로드 메타데이터. 038 패키지 생성기와 같은 함수를 쓴다."""
    from scripts.political_upload_package import (
        build_description, build_hashtags, resolve_pinned_comment,
        sanitize_yt_title,
    )
    from scripts.shorts_category import resolve_config_category

    title, extracted = sanitize_yt_title(cfg.get("yt_title") or cfg["title"])
    hashtags = build_hashtags(cfg)
    for tag in extracted:
        if tag not in hashtags:
            hashtags.append(tag)
    return UploadMetadata(
        title=title[:YOUTUBE_TITLE_MAX],
        description=build_description(cfg, hashtags),
        tags=[t.lstrip("#") for t in hashtags if t.strip("#")],
        pinned_comment=resolve_pinned_comment(cfg),
        category_id=youtube_category_id(resolve_config_category(cfg)),
    )


def _section(text: str, heading: str) -> str:
    """`## heading` 아래 본문. ``` 코드펜스는 벗겨서 돌려준다."""
    m = re.search(rf"^##\s*{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
                  text, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    body = m.group(1).strip()
    fenced = re.search(r"```\s*\n(.*?)\n?```", body, re.DOTALL)
    return (fenced.group(1) if fenced else body).strip()


def parse_upload_package(text: str, *, category: str = "political") -> UploadMetadata:
    """검수자가 손댄 `upload_package.md` 를 읽는다 — 사람의 수정이 최종이다."""
    titles = _section(text, "제목 (A/B)")
    m = re.search(r"^-\s*A:\s*(.+)$", titles, re.MULTILINE)
    if not m:
        raise ValueError("upload_package.md 에서 '## 제목 (A/B)' 의 A안을 찾지 못했습니다")

    raw_tags = _section(text, "해시태그").split()
    return UploadMetadata(
        title=m.group(1).strip()[:YOUTUBE_TITLE_MAX],
        description=_section(text, "설명"),
        tags=[t.lstrip("#") for t in raw_tags if t.startswith("#")],
        pinned_comment=_section(text, "고정댓글"),
        category_id=youtube_category_id(category),
    )


# ── 실제 업로드 ─────────────────────────────────────────────────────
def _default_youtube_upload(**kwargs) -> str:
    from src.upload.youtube_uploader import upload_video
    return upload_video(**kwargs)


def _default_tiktok_upload(video_path: Path, title: str) -> str:
    from src.upload.tiktok_uploader import upload_video
    return upload_video(video_path=video_path, title=title)


def _default_comment_poster(video_id: str, text: str) -> str:
    """채널 계정으로 최상위 댓글 작성. **고정은 API 로 불가능하다.**"""
    from googleapiclient.discovery import build

    from src.upload.youtube_uploader import _get_credentials
    youtube = build("youtube", "v3", credentials=_get_credentials())
    response = youtube.commentThreads().insert(
        part="snippet",
        body={"snippet": {"videoId": video_id, "topLevelComment": {
            "snippet": {"textOriginal": text}}}},
    ).execute()
    return response["id"]


def record_publish(log_path: Path, entry: dict) -> None:
    """publish_log.jsonl 에 한 줄 추가. 기록 실패로 업로드를 되돌리지 않는다."""
    log_path = Path(log_path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {**entry, "recorded_at": datetime.now(KST).isoformat()}
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("업로드 이력 기록 실패: %s", exc)


def publish(video_path: Path, metadata: UploadMetadata, *,
            targets: tuple[str, ...] = TARGETS_ALL,
            privacy: str = "public",
            youtube_upload=None, tiktok_upload=None, comment_poster=None,
            log_path: Path | None = None, slug: str = "") -> PublishOutcome:
    """플랫폼별 업로드. **한 플랫폼이 실패해도 나머지는 계속 간다.**"""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    errors: list[str] = []
    youtube_url = comment_id = tiktok_id = None

    if "youtube" in targets:
        youtube_url, comment_id, yt_errors = _publish_youtube(
            video_path, metadata, privacy,
            youtube_upload or _default_youtube_upload,
            comment_poster or _default_comment_poster)
        errors.extend(yt_errors)

    if "tiktok" in targets:
        try:
            tiktok_id = (tiktok_upload or _default_tiktok_upload)(
                video_path=video_path, title=metadata.title)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"TikTok 업로드 실패: {exc}")

    outcome = PublishOutcome(youtube_url=youtube_url, tiktok_publish_id=tiktok_id,
                             comment_id=comment_id, errors=tuple(errors))
    if log_path is not None:
        record_publish(log_path, {
            "slug": slug, "title": metadata.title, "video": str(video_path),
            "youtube_url": youtube_url, "tiktok_publish_id": tiktok_id,
            "platform": ",".join(targets), "errors": list(errors),
        })
    return outcome


def _publish_youtube(video_path: Path, metadata: UploadMetadata, privacy: str,
                     uploader, poster) -> tuple[str | None, str | None, list[str]]:
    errors: list[str] = []
    try:
        url = uploader(video_path=video_path, title=metadata.title,
                       description=metadata.description, tags=metadata.tags,
                       category_id=metadata.category_id, privacy=privacy)
    except Exception as exc:  # noqa: BLE001 — 틱톡은 계속 시도해야 한다
        return None, None, [f"YouTube 업로드 실패: {exc}"]

    comment_id = None
    video_id = video_id_from_url(url)
    if metadata.pinned_comment and video_id:
        try:
            comment_id = poster(video_id, metadata.pinned_comment)
        except Exception as exc:  # noqa: BLE001 — 댓글 실패로 업로드를 되돌리지 않는다
            errors.append(f"고정댓글 작성 실패: {exc}")
    return url, comment_id, errors
