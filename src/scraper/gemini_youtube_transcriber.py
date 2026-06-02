"""Gemini 멀티모달 영상 → transcript 변환 (Phase 1A).

Whisper STT 대체 — Gemini Files API에 영상을 업로드하고 한 번의 호출로
타임스탬프 포함 transcript를 추출한다. Whisper-large-v3 다운로드(약 3GB)와
로컬 GPU 추론을 회피하여 평균 60초 → 20초로 단축.

폴백 체인 (transcribe_video_or_fallback에서 사용):
  1) yt-dlp VTT 자막 (가장 빠름, 0초)
  2) **Gemini 멀티모달** (이 모듈, 20~40초)
  3) Whisper STT (마지막 안전망, 60~120초)

무료 한도(2026-05 기준):
  - Gemini 2.5 Flash: 10 RPM / 250 req/일 — 영상 1편당 1 req 사용
  - Files API: 누적 2GB / 50 파일 (업로드 후 24h 자동 삭제)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 무료 한도 안전 모델 (Pro 대신 Flash 사용 — transcript 추출은 추론 강도 낮음)
MODEL = "gemini-2.5-flash"
MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100MB 권장 상한 (Files API는 2GB까지 OK)
UPLOAD_POLL_INTERVAL_SEC = 2.0
UPLOAD_TIMEOUT_SEC = 120.0


class GeminiTranscribeError(Exception):
    """Gemini 멀티모달 transcript 추출 실패."""


_PROMPT = """다음 영상에서 모든 음성을 한국어 transcript로 추출하라.

규칙:
- 음성이 실제로 발화된 구간만 포함 (BGM·정적 구간 제외)
- 각 세그먼트는 자연스러운 문장 단위로 분할 (한 문장이 너무 길면 쉼표 단위)
- 추측·요약 금지. 들리는 그대로 옮길 것.

출력 형식 (JSON 배열만, 다른 텍스트 금지):
[
  {"start": 0.0, "end": 3.2, "text": "안녕하세요 시청자 여러분"},
  {"start": 3.2, "end": 6.8, "text": "오늘은 이 뉴스를 다뤄보겠습니다"},
  ...
]

start/end는 초 단위 float. 정확하지 않아도 0.1초 정밀도면 충분.
"""


def gemini_transcribe_video(video_path: Path) -> list[dict]:
    """영상 파일 → transcript 세그먼트 리스트.

    Args:
        video_path: 로컬 영상 파일 경로 (mp4/webm 등).

    Returns:
        ``[{"start": float, "end": float, "text": str}, ...]`` —
        ``_whisper_transcribe`` 와 동일한 스키마.

    Raises:
        GeminiTranscribeError: 키 미설정, 업로드 실패, 빈 응답, JSON 파싱 실패.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiTranscribeError(
            "GEMINI_API_KEY 미설정 — Gemini transcript 비활성화"
        )

    if not video_path.exists():
        raise GeminiTranscribeError(f"영상 파일 없음: {video_path}")

    size = video_path.stat().st_size
    if size > MAX_VIDEO_BYTES:
        raise GeminiTranscribeError(
            f"영상이 너무 큽니다 ({size / 1024 / 1024:.1f}MB > "
            f"{MAX_VIDEO_BYTES / 1024 / 1024:.0f}MB) — Whisper로 폴백 권장"
        )

    try:
        from google import genai
    except ImportError as e:
        raise GeminiTranscribeError(f"google-genai 미설치: {e}") from e

    client = genai.Client(api_key=api_key)

    try:
        uploaded = client.files.upload(file=str(video_path))
    except Exception as e:
        raise GeminiTranscribeError(f"Files API 업로드 실패: {e}") from e

    started = time.time()
    while getattr(uploaded.state, "name", "") == "PROCESSING":
        if time.time() - started > UPLOAD_TIMEOUT_SEC:
            raise GeminiTranscribeError("Files API 처리 타임아웃 (120초)")
        time.sleep(UPLOAD_POLL_INTERVAL_SEC)
        uploaded = client.files.get(name=uploaded.name)

    if getattr(uploaded.state, "name", "") == "FAILED":
        raise GeminiTranscribeError(f"Files API 처리 실패: {uploaded.name}")

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[uploaded, _PROMPT],
        )
    except Exception as e:
        raise GeminiTranscribeError(f"Gemini 분석 실패: {e}") from e
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception as e:
            logger.warning("Files API 삭제 실패(무시): %s", e)

    text = (response.text or "").strip()
    if not text:
        raise GeminiTranscribeError("Gemini 빈 응답")

    segments = _parse_response(text)
    if not segments:
        raise GeminiTranscribeError(
            f"파싱 결과 빈 배열 (raw 200자: {text[:200]!r})"
        )

    logger.info("Gemini transcript %d세그먼트 (%.1fs)", len(segments), time.time() - started)
    return segments


def _parse_response(text: str) -> list[dict]:
    """JSON 배열 추출 — 코드펜스/잡음 제거."""
    candidate = text
    m = re.search(r"```(?:json)?\s*(\[.+?\])\s*```", text, re.DOTALL)
    if m:
        candidate = m.group(1)
    else:
        m = re.search(r"\[\s*\{.+\}\s*\]", text, re.DOTALL)
        if m:
            candidate = m.group(0)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise GeminiTranscribeError(f"JSON 파싱 실패: {e}") from e

    if not isinstance(data, list):
        raise GeminiTranscribeError(f"배열 아님: {type(data).__name__}")

    out: list[dict] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start))
            seg_text = str(item.get("text", "")).strip()
        except (TypeError, ValueError):
            logger.debug("세그먼트 %d 타입 오류 — 스킵", i)
            continue
        if not seg_text or end <= start:
            continue
        out.append({"start": start, "end": end, "text": seg_text})
    return out
