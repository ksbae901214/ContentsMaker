"""중앙화된 설정값 (원칙 VI: 매직 넘버 금지).

환경 변수는 .env에서, 상수는 본 모듈에서 관리.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # /Users/kyusik/ContentsMaker
DATA_DIR = PROJECT_ROOT / "data" / "dem_shorts"

# ── NATV / YouTube ─────────────────────────────────────────────
NATV_CHANNEL_HANDLE = os.getenv("NATV_CHANNEL_HANDLE", "@NATV_korea")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_OAUTH_CLIENT = os.getenv("YOUTUBE_OAUTH_CLIENT", "")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# ── Polling / batch schedule ───────────────────────────────────
POLL_INTERVAL_MIN = 30  # FR-001
POLL_RETRY_ATTEMPTS = 3
POLL_RETRY_BACKOFF_MIN = (5, 15, 60)  # B-01

# ── Video constraints ──────────────────────────────────────────
MAX_VIDEO_DURATION_SEC = 6 * 3600  # FR-002: 6시간 초과 자동 제외
CUT_MAX_SEC = 60.0  # FR-018
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_FPS = 30

# ── Compliance thresholds ──────────────────────────────────────
COMMENTARY_MIN_CHARS = 50  # FR-024, 게이트 item_1
ORIGINAL_RATIO_MAX = 0.50  # 게이트 item_2
COMMENTARY_RATIO_MIN = 0.30  # 게이트 item_2
FACT_LINKS_MIN = 2  # FR-029
RISK_SCORE_BLOCK = 61.0  # FR-026
RISK_SCORE_WARN = 31.0
TEMPLATE_REPEAT_MAX = 3  # 게이트 item_6

# ── Election guard (R-10) ──────────────────────────────────────
PRESIDENTIAL_GUARD_DAYS = 180
GENERAL_ELECTION_GUARD_DAYS = 120
RISK_SCORE_BLOCK_ELECTION = 30.0  # FR-031: 선거기간 중 편향 임계값 하향

# ── Speaker identification ─────────────────────────────────────
SPEAKER_CONFIDENCE_MIN = 0.7  # FR-014

# ── Dem-score weights (R-05) ───────────────────────────────────
DEM_SCORE_PER_PERSON = 10
DEM_SCORE_PER_PERSON_CAP = 40
DEM_SCORE_TOP_WHITELIST = 20
DEM_SCORE_TOP3_BONUS = 15  # 이재명·조국·정청래 각각
DEM_SCORE_TOP3_CAP = 30
DEM_SCORE_FEMALE_YOUTH_BONUS = 10
DEM_SCORE_ISSUE_KEYWORD = 5
DEM_SCORE_ISSUE_KEYWORD_CAP = 20
DEM_SCORE_OVER_6H_PENALTY = 10
DEM_SCORE_REPEAT_PENALTY_MAX = 30

# ── Ranking (R-06) ─────────────────────────────────────────────
RANKING_TOP_N = 20  # FR-009: 상위 20명만 auto 등급
RANKING_PENDING_WEEKS = 2  # 2주 연속 대기 시 삭제
RANKING_SOURCE_WEIGHTS = {
    "naver_news": 0.30,
    "google_trends": 0.25,
    "youtube_metrics": 0.25,
    "wikipedia_pageviews": 0.10,
    "naver_datalab": 0.10,
}

# ── Render (R-14) ──────────────────────────────────────────────
RENDER_CRF = 23
RENDER_AUDIO_BITRATE = "128k"
ORIGINAL_AUDIO_DB = -12  # 원본 음성 다운
TTS_AUDIO_DB = 0  # TTS 오버레이 레벨
BGM_AUDIO_DB = -18  # BGM 레벨

# ── STT / Diarization ──────────────────────────────────────────
WHISPER_MODEL = "large-v3"
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"

# ── Party Perspective Axis (010, 2026-04-20) ───────────────────
# Spec: specs/007-dem-shorts-studio/spec.md (v2)
# Charter: docs/politics-bias-charter.md
SUPPORTED_PERSPECTIVES = ("dem", "ppp")
# 2026-04-20 채널 방향 확정 (@국회직캠-d6r = 야당 관점):
# DEFAULT_PERSPECTIVE='ppp'로 변경. dem perspective는 명시 인자로만 동작 (로컬 렌더 전용).
DEFAULT_PERSPECTIVE = "ppp"

# FR-006: perspective별 pinned 시드 이름 목록 (scoring TOP 가중치에 사용)
PERSPECTIVE_TOP_NAMES: dict[str, tuple[str, ...]] = {
    "dem": ("이재명", "조국", "정청래"),
    "ppp": ("한동훈", "김기현", "권성동", "추경호", "나경원", "오세훈"),
}

# perspective ↔ channel_id 1:1 고정 매핑 (charter §3.3, SC-014)
# .env의 DEM_CHANNEL_ID / PPP_CHANNEL_ID 우선. 비어 있으면 NULL (업로드 비활성).
# 현재 Q6 결정: ppp만 활성, dem은 로컬 렌더 전용.
PERSPECTIVE_CHANNEL_ID: dict[str, str] = {
    "dem": os.getenv("DEM_CHANNEL_ID", ""),
    "ppp": os.getenv("PPP_CHANNEL_ID", ""),
}

# perspective 라벨 (UI·리포트 표시용)
PERSPECTIVE_LABELS: dict[str, str] = {
    "dem": "민주당 관점",
    "ppp": "국민의힘 관점",
}

# Symmetry Gate (FR-025 item 11, SC-013) — 양 perspective risk_score 차이 임계값
SYMMETRY_RISK_DIFF_WARN = 20.0  # 경고 임계
SYMMETRY_WARN_TO_FAIL_DAYS = 30  # warn 기간 후 fail 승격
