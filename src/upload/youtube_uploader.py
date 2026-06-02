"""YouTube Data API v3 uploader.

Handles OAuth authentication and video upload to YouTube.
First-time auth requires browser interaction via `youtube-auth` command.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

TOKEN_PATH = PROJECT_ROOT / "data" / ".youtube_token.json"
CREDENTIALS_PATH = PROJECT_ROOT / "data" / ".youtube_credentials.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class UploadError(Exception):
    """Raised when YouTube upload fails."""


def is_authenticated() -> bool:
    """Check if YouTube OAuth token exists."""
    return TOKEN_PATH.exists()


def authenticate():
    """Run OAuth flow to get YouTube upload token.

    Opens browser for Google sign-in. Saves token to TOKEN_PATH.
    Requires credentials.json from Google Cloud Console.
    """
    if not CREDENTIALS_PATH.exists():
        raise UploadError(
            "YouTube API 인증 파일이 필요합니다.\n"
            "1. Google Cloud Console → APIs → YouTube Data API v3 활성화\n"
            "2. OAuth 2.0 Client ID 생성 (Desktop app)\n"
            "3. JSON 다운로드 → data/.youtube_credentials.json 에 저장"
        )

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH), SCOPES
    )
    credentials = flow.run_local_server(port=8090)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(credentials.to_json())
    logger.info("YouTube 인증 완료: %s", TOKEN_PATH)
    print("✅ YouTube 인증 완료! 이제 영상 업로드가 가능합니다.")


def _get_credentials():
    """Load saved credentials, refreshing if expired."""
    if not TOKEN_PATH.exists():
        raise UploadError(
            "YouTube 인증이 필요합니다.\n"
            "실행: python3 -m src.main youtube-auth"
        )

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())

    return creds


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "22",  # People & Blogs
    privacy: str = "public",
) -> str:
    """Upload a video to YouTube.

    Returns the video URL.
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if not video_path.exists():
        raise UploadError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": category_id,
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    logger.info("YouTube 업로드 시작: %s", title)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("업로드 진행: %d%%", int(status.progress() * 100))

    video_id = response["id"]
    video_url = f"https://youtube.com/shorts/{video_id}"
    logger.info("YouTube 업로드 완료: %s", video_url)

    return video_url
