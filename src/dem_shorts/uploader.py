"""T086: YouTube 업로더 — Data API v3 resumable upload (FR-036, FR-037, R-13).

업로드 전 검증:
- `operator_confirmed=True` 필수 (FR-037)
- 설명에 "NATV 국회방송" 포함 (FR-029)
- 팩트 링크 ≥2개 (FR-029)
- ⭐ 게이트 통과 재확인 (이중 방어, SC-005)
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.dem_shorts.compliance.gate import get_latest_result
from src.dem_shorts.config import FACT_LINKS_MIN
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH

logger = logging.getLogger(__name__)

NATV_LABEL = "NATV 국회방송"
URL_RE = re.compile(r"https?://[^\s\n]+")
TITLE_MAX_LEN = 100
DESCRIPTION_MAX_LEN = 5000


class UploadError(Exception):
    """Raised when upload validation or API call fails."""


@dataclass(frozen=True)
class UploadRequest:
    """YouTube 업로드 요청.

    2026-04-20: `perspective` 필드 추가 — charter §3.3 channel 1:1 바인딩 강제.
    default는 DEFAULT_PERSPECTIVE(=ppp).
    """

    draft_id: int
    title: str
    description: str
    tags: tuple[str, ...] = ()
    scheduled_publish_at: datetime | None = None
    operator_confirmed: bool = False
    perspective: str = ""  # empty → DEFAULT_PERSPECTIVE 사용


@dataclass(frozen=True)
class UploadResult:
    uploaded_shorts_id: int
    youtube_video_id: str
    youtube_url: str
    scheduled_publish_at: datetime | None


def extract_fact_links_from_description(description: str) -> list[str]:
    """설명에서 http(s) URL 추출."""
    return URL_RE.findall(description)


def _resolve_perspective(req_perspective: str) -> str:
    """perspective 지정이 없으면 DEFAULT_PERSPECTIVE 반환."""
    from src.dem_shorts.config import DEFAULT_PERSPECTIVE, SUPPORTED_PERSPECTIVES
    p = req_perspective or DEFAULT_PERSPECTIVE
    if p not in SUPPORTED_PERSPECTIVES:
        raise UploadError(f"invalid_perspective: {p}")
    return p


def validate_upload_request(req: UploadRequest) -> None:
    """FR-029, FR-037, SC-014: 업로드 요청 검증.

    Raises:
        UploadError: 검증 실패.
    """
    if not req.operator_confirmed:
        raise UploadError("operator_confirmed_required: 운영자가 최종 확정하지 않았습니다")

    # SC-014 perspective ↔ channel_id 1:1 하드블록 (charter §3.3)
    from src.dem_shorts.config import PERSPECTIVE_CHANNEL_ID
    perspective = _resolve_perspective(req.perspective)
    channel_id = (PERSPECTIVE_CHANNEL_ID.get(perspective) or "").strip()
    if not channel_id:
        raise UploadError(
            f"channel_not_configured: perspective={perspective} — "
            f".env에 {perspective.upper()}_CHANNEL_ID 설정 필요 (SC-014 charter §3.3)"
        )

    if not req.title or not req.title.strip():
        raise UploadError("title_required")
    if len(req.title) > TITLE_MAX_LEN:
        raise UploadError(f"title_too_long: {len(req.title)} > {TITLE_MAX_LEN}")

    if not req.description or not req.description.strip():
        raise UploadError("description_required")
    if len(req.description) > DESCRIPTION_MAX_LEN:
        raise UploadError(f"description_too_long: {len(req.description)} > {DESCRIPTION_MAX_LEN}")

    # FR-029: NATV 출처 필수 (문자열 그대로 검색)
    if NATV_LABEL not in req.description:
        raise UploadError(
            f"natv_source_missing: 설명에 '{NATV_LABEL}' 문자열이 반드시 포함되어야 합니다 (FR-029)"
        )

    # FR-029: 팩트 링크 ≥2개
    links = extract_fact_links_from_description(req.description)
    if len(links) < FACT_LINKS_MIN:
        raise UploadError(
            f"fact_links_insufficient: {len(links)}개 (최소 {FACT_LINKS_MIN}개 필요, FR-029)"
        )

    # scheduled_publish_at은 미래 시각
    if req.scheduled_publish_at is not None:
        if req.scheduled_publish_at < datetime.now(timezone.utc):
            raise UploadError("scheduled_publish_at_in_past")


def verify_gate_passed_for_upload(draft_id: int, *, db_path: Path | None = None) -> None:
    """⭐ 업로드 직전 게이트 통과 재확인 (이중 방어, SC-005)."""
    result = get_latest_result(draft_id, db_path=db_path)
    if result is None:
        raise UploadError(f"gate_not_executed: draft {draft_id}")
    if not result.is_passed():
        raise UploadError(
            f"gate_not_passed: draft {draft_id} (overall={result.overall_status})"
        )


def _call_youtube_api(
    video_path: Path,
    title: str,
    description: str,
    tags: tuple[str, ...],
    scheduled_publish_at: datetime | None,
) -> dict:
    """YouTube Data API v3 resumable upload.

    실제 호출은 `google-api-python-client` 필요. 테스트에서는 mock.
    """
    try:
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
    except ImportError as exc:
        raise UploadError(
            f"google-api-python-client not installed: {exc}"
        ) from exc

    token_path = Path("data/.youtube_token.json")
    if not token_path.exists():
        raise UploadError(
            "youtube_auth_missing: run `python3 -m src.main youtube-auth` first"
        )
    creds = Credentials.from_authorized_user_file(
        str(token_path),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    service = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags),
            "categoryId": "25",  # News & Politics
        },
        "status": {
            "privacyStatus": "private" if scheduled_publish_at else "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    if scheduled_publish_at:
        body["status"]["publishAt"] = scheduled_publish_at.isoformat()
        body["status"]["privacyStatus"] = "private"

    media = MediaFileUpload(str(video_path), resumable=True, chunksize=8 * 1024 * 1024)
    request = service.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("youtube upload progress: %d%%", int(status.progress() * 100))

    return response


def upload(
    req: UploadRequest,
    *,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> UploadResult:
    """업로드 파이프라인: 검증 → 게이트 재확인 → YouTube 업로드 → uploaded_shorts 저장."""
    path = db_path or DB_PATH

    # STEP 1: Request 검증
    validate_upload_request(req)

    # STEP 2: ⭐ 게이트 이중 방어
    verify_gate_passed_for_upload(req.draft_id, db_path=path)

    # STEP 3: draft의 rendered_path 확인
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT rendered_path, status FROM shorts_drafts WHERE id=?", (req.draft_id,)
        ).fetchone()
        if not row:
            raise UploadError(f"draft_not_found: {req.draft_id}")
        rendered_path = row["rendered_path"]
        if not rendered_path:
            raise UploadError(f"not_rendered: draft {req.draft_id}은(는) 아직 렌더링되지 않음")
        video_path = Path(rendered_path)
        if not video_path.exists():
            raise UploadError(f"rendered_file_missing: {video_path}")

    # STEP 4: 업로드
    if dry_run:
        yt_id = f"dryrun_{req.draft_id}"
        logger.info("dry run: skipping YouTube API")
    else:
        response = _call_youtube_api(
            video_path,
            req.title,
            req.description,
            req.tags,
            req.scheduled_publish_at,
        )
        yt_id = response.get("id", "")
        if not yt_id:
            raise UploadError(f"upload_failed: no video_id in response {response}")

    # STEP 5: uploaded_shorts 저장
    now = datetime.now(timezone.utc).isoformat()
    fact_links = extract_fact_links_from_description(req.description)
    with get_connection(path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO uploaded_shorts (
                draft_id, final_mp4_path, youtube_video_id, title, description,
                tags, scheduled_publish_at, published_at, fact_links,
                view_count, like_count, comment_count, is_taken_down,
                uploaded_at, metrics_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?)
            """,
            (
                req.draft_id,
                str(video_path),
                yt_id,
                req.title,
                req.description,
                json.dumps(list(req.tags), ensure_ascii=False),
                req.scheduled_publish_at.isoformat() if req.scheduled_publish_at else None,
                None if req.scheduled_publish_at else now,
                json.dumps(fact_links, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.execute(
            "UPDATE shorts_drafts SET status='uploaded', updated_at=? WHERE id=?",
            (now, req.draft_id),
        )
        conn.commit()
        upload_id = cursor.lastrowid

    youtube_url = f"https://youtube.com/shorts/{yt_id}" if not dry_run else f"dryrun://draft/{req.draft_id}"
    return UploadResult(
        uploaded_shorts_id=upload_id,
        youtube_video_id=yt_id,
        youtube_url=youtube_url,
        scheduled_publish_at=req.scheduled_publish_at,
    )
