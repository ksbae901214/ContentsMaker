"""V3 격리 모드 전역 상수.

모든 경로는 PROJECT_ROOT 기준 상대 경로. 모듈 어디서나 동일한 절대 경로를 받아 사용.
변경 시 spec.md FR-004, FR-036 영향 — 단순 상수 변경 불가.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final

# 프로젝트 루트 (.../ContentsMaker)
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT: Final[Path] = _THIS_FILE.parent.parent.parent

# V3 격리 출력 디렉토리 (FR-004)
JPOLITICS_OUTPUT_DIR: Final[Path] = PROJECT_ROOT / "data" / "jpolitics"
POLITICIAN_CARDS_DIR: Final[Path] = PROJECT_ROOT / "data" / "politician_cards"
POLITICIAN_PHOTOS_DIR: Final[Path] = POLITICIAN_CARDS_DIR / "photos"
JPOLITICS_REFERENCE_DIR: Final[Path] = PROJECT_ROOT / "data" / "jpolitics_reference"

# Remotion V3 격리 패키지
REMOTION_V3_DIR: Final[Path] = PROJECT_ROOT / "src" / "video" / "remotion_v3"
REMOTION_V3_PUBLIC_DIR: Final[Path] = REMOTION_V3_DIR / "public"

# 영상 길이 제약 (FR-016)
MAX_SCENE_DURATION: Final[float] = 5.0
MIN_VIDEO_DURATION: Final[float] = 30.0
MAX_VIDEO_DURATION: Final[float] = 60.0

# TTS 락인 (FR-021, FR-036)
TTS_VOICE: Final[str] = "ko-KR-InJoonNeural"
TTS_RATE: Final[str] = "+22%"
INTER_SCENE_GAP_MS: Final[int] = 300

# 영상 해상도 (헌법 III)
VIDEO_WIDTH: Final[int] = 1080
VIDEO_HEIGHT: Final[int] = 1920
VIDEO_FPS: Final[int] = 30

# 색상 (FR-024)
PARTY_COLORS: Final[dict[str, str]] = {
    "더불어민주당": "#004EA2",
    "국민의힘": "#E61E2B",
    "조국혁신당": "#0073CF",
    "개혁신당": "#FF7920",
    "정의당": "#F9DD24",
    "진보당": "#D6001C",
    "기본소득당": "#00B05E",
    "무소속": "#888888",
    "기타": "#888888",
}
DEFAULT_PARTY_COLOR: Final[str] = "#888888"
