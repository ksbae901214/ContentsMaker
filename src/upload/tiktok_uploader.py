"""TikTok Content Posting API uploader.

Uploads videos as Draft to TikTok. User must publish from TikTok app.
Requires TikTok Developer app approval + OAuth credentials.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import urllib.request
import urllib.parse

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

TOKEN_PATH = PROJECT_ROOT / "data" / ".tiktok_token.json"
CREDENTIALS_PATH = PROJECT_ROOT / "data" / ".tiktok_credentials.json"

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_UPLOAD_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_UPLOAD_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


class TikTokUploadError(Exception):
    """Raised when TikTok upload fails."""


def is_authenticated() -> bool:
    """Check if TikTok OAuth token exists."""
    return TOKEN_PATH.exists()


def _load_credentials() -> dict:
    """Load TikTok app credentials."""
    if not CREDENTIALS_PATH.exists():
        raise TikTokUploadError(
            "TikTok API 인증 파일이 필요합니다.\n"
            "1. https://developers.tiktok.com 에서 앱 등록\n"
            "2. Content Posting API 신청 + 심사 완료\n"
            "3. Client Key/Secret을 data/.tiktok_credentials.json에 저장:\n"
            '   {"client_key": "...", "client_secret": "...", "redirect_uri": "http://localhost:8091/callback"}'
        )
    return json.loads(CREDENTIALS_PATH.read_text())


def authenticate():
    """Run OAuth flow for TikTok.

    Opens browser for TikTok sign-in. Saves token to TOKEN_PATH.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler

    creds = _load_credentials()
    client_key = creds["client_key"]
    client_secret = creds["client_secret"]
    redirect_uri = creds.get("redirect_uri", "http://localhost:8091/callback")

    scope = "user.info.basic,video.publish"
    state = "contentsmaker"

    auth_url = (
        f"{TIKTOK_AUTH_URL}?"
        f"client_key={client_key}&"
        f"scope={scope}&"
        f"response_type=code&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"state={state}"
    )

    print(f"\n브라우저에서 TikTok 로그인을 진행하세요:")
    print(f"{auth_url}\n")

    import webbrowser
    webbrowser.open(auth_url)

    auth_code = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            auth_code = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>TikTok Auth Complete! Close this tab.</h1>")

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("localhost", 8091), CallbackHandler)
    server.timeout = 120
    server.handle_request()

    if not auth_code:
        raise TikTokUploadError("TikTok 인증 실패: 인증 코드를 받지 못했습니다.")

    # Exchange code for token
    token_data = json.dumps({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }).encode()

    req = urllib.request.Request(
        TIKTOK_TOKEN_URL,
        data=token_data,
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())

    if "access_token" not in resp:
        raise TikTokUploadError(f"토큰 교환 실패: {resp}")

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(resp))
    logger.info("TikTok 인증 완료: %s", TOKEN_PATH)
    print("✅ TikTok 인증 완료! 이제 영상 업로드가 가능합니다.")


def _get_access_token() -> str:
    """Load saved access token."""
    if not TOKEN_PATH.exists():
        raise TikTokUploadError(
            "TikTok 인증이 필요합니다.\n"
            "실행: python3 -m src.main tiktok-auth"
        )

    token_data = json.loads(TOKEN_PATH.read_text())

    # Check if refresh needed
    if token_data.get("expires_in", 0) < time.time() - token_data.get("_saved_at", 0):
        if token_data.get("refresh_token"):
            _refresh_token(token_data)
            token_data = json.loads(TOKEN_PATH.read_text())

    return token_data["access_token"]


def _refresh_token(token_data: dict):
    """Refresh expired token."""
    creds = _load_credentials()
    refresh_data = json.dumps({
        "client_key": creds["client_key"],
        "client_secret": creds["client_secret"],
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
    }).encode()

    req = urllib.request.Request(
        TIKTOK_TOKEN_URL,
        data=refresh_data,
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())

    if "access_token" in resp:
        resp["_saved_at"] = time.time()
        TOKEN_PATH.write_text(json.dumps(resp))


def upload_video(
    video_path: Path,
    title: str,
) -> str:
    """Upload video to TikTok as Draft.

    User must open TikTok app to publish.
    Returns publish_id for status tracking.
    """
    if not video_path.exists():
        raise TikTokUploadError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    access_token = _get_access_token()
    file_size = video_path.stat().st_size

    # Step 1: Initialize upload
    init_data = json.dumps({
        "post_info": {
            "title": title[:150],
            "privacy_level": "SELF_ONLY",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        },
    }).encode()

    req = urllib.request.Request(
        TIKTOK_UPLOAD_INIT_URL,
        data=init_data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )

    logger.info("TikTok 업로드 초기화: %s", title)
    resp = json.loads(urllib.request.urlopen(req).read())

    if resp.get("error", {}).get("code") != "ok":
        raise TikTokUploadError(f"업로드 초기화 실패: {resp}")

    upload_url = resp["data"]["upload_url"]
    publish_id = resp["data"]["publish_id"]

    # Step 2: Upload video file
    video_bytes = video_path.read_bytes()
    upload_req = urllib.request.Request(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
        },
        method="PUT",
    )

    logger.info("TikTok 영상 업로드 중 (%.1f MB)...", file_size / (1024 * 1024))
    urllib.request.urlopen(upload_req)

    logger.info("TikTok Draft 업로드 완료 (publish_id: %s)", publish_id)
    return publish_id
