"""V3 모먼트 직캠 전역 상수 (Feature 027)."""

from src.config.settings import DATA_DIR  # read-only import (격리 boundary)

JPOLITICS_DATA_DIR = DATA_DIR / "jpolitics"

# 모먼트 종류 — 벤치마크 실측에서 도출 (조회수 상위 쇼츠의 소재 유형)
MOMENT_KINDS = (
    "laughter",   # 웃음 터진 순간 (YTN 박범계 26만뷰 유형)
    "clash",      # 여야 충돌·설전 (추미애-나경원 유형)
    "outburst",   # 언성·호통·일갈
    "gaffe",      # 실언·어이없는 순간 (겸손은힘들다 방명록 유형)
    "silence",    # 정적·말문 막힘
    "other",      # 기타 강한 감정 모먼트
)

# 클립 길이 제약 — 벤치마크 34~58초, 쇼츠 한도 60초
MIN_MOMENT_SECONDS = 5.0
MAX_MOMENT_SECONDS = 60.0

# 기본 검출 상한 (후보 개수)
DEFAULT_TOP_N = 5
