"""Feature 011 V2 Phase B — 자막 색 키워드 → hex 매핑.

Stage B 프롬프트가 출력하는 subtitle_color (white/red/yellow/blue) 키워드를
Remotion 컴포넌트에 전달할 hex 값으로 변환한다.

색 의미 (gemini-code 지침):
- white  : 일반 나레이션 (기본)
- red    : 비판·충돌·돌발 발언·핵심 갈등 키워드
- yellow : 강조 키워드·핵심 수치·이슈화 단어
- blue   : 인용·출처·공식 표현
"""
from __future__ import annotations


SUBTITLE_COLOR_HEX: dict[str, str] = {
    "white":  "#FFFFFF",
    "red":    "#FF4444",   # 정치 비판/충돌 — 가독성 위해 어두운 빨강 대신 밝은 빨강
    "yellow": "#FFD93D",   # 강조 — 노란 형광색
    "blue":   "#5DADE2",   # 인용 — 차분한 파랑
}


def get_subtitle_hex(color_keyword: str) -> str:
    """Map keyword to hex. Unknown → fallback white."""
    return SUBTITLE_COLOR_HEX.get((color_keyword or "").strip().lower(), SUBTITLE_COLOR_HEX["white"])


__all__ = ["SUBTITLE_COLOR_HEX", "get_subtitle_hex"]
