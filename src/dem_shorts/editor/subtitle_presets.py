"""T066: 자막 프리셋 5종 (FR-021).

쇼츠 자막 스타일을 인물·주제별로 차별화. Remotion composition이 이 설정을 prop으로 받아 렌더.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitlePreset:
    """Remotion 자막 블록 스타일.

    QW-03 (B안): stroke_color는 프리셋별 시그니처 색 유지, stroke_width는
    모든 프리셋 6px 이상으로 통일, drop_shadow는 약한 기본값 통일.
    """

    id: str  # leejaemyung/jungcheongrae/youth/hotissue/default
    font_family: str
    base_font_size: int  # px (1080x1920 기준)
    color: str  # 기본 텍스트 색
    highlight_color: str  # 강조 키워드 색
    stroke_color: str  # 외곽선 색 (B안: 시그니처 색 유지)
    stroke_width: int  # px (QW-03: 6 이상)
    background: str  # 자막 박스 배경 (rgba 또는 'none')
    text_align: str  # "left"/"center"/"right"
    padding_px: int  # 자막 박스 안쪽 여백
    position: str  # "bottom"/"center"/"top"
    max_lines: int  # 한 블록 최대 줄 수
    line_height: float  # 배수
    bold: bool
    drop_shadow: str = "3px 3px 8px rgba(0,0,0,0.7)"  # QW-03 Q3=약


# FR-021: 5개 프리셋. 색상/폰트/위치는 인물 이미지와의 시각적 일관성을 위해 정의.
PRESETS: dict[str, SubtitlePreset] = {
    "leejaemyung": SubtitlePreset(
        id="leejaemyung",
        font_family="Pretendard, -apple-system, sans-serif",
        base_font_size=72,
        color="#FFFFFF",
        highlight_color="#FFD54F",  # 민생 경제 강조 노란색
        stroke_color="#1A237E",  # 민주당 블루 계열 (B안: 시그니처 유지)
        stroke_width=6,
        background="rgba(26,35,126,0.65)",
        text_align="center",
        padding_px=24,
        position="bottom",
        max_lines=2,
        line_height=1.2,
        bold=True,
    ),
    "jungcheongrae": SubtitlePreset(
        id="jungcheongrae",
        font_family="Pretendard, -apple-system, sans-serif",
        base_font_size=72,
        color="#FFFFFF",
        highlight_color="#FF7043",  # 법사위 날카로운 강조
        stroke_color="#000000",
        stroke_width=6,
        background="rgba(0,0,0,0.75)",
        text_align="center",
        padding_px=24,
        position="bottom",
        max_lines=2,
        line_height=1.15,
        bold=True,
    ),
    "youth": SubtitlePreset(
        id="youth",
        font_family="Pretendard, -apple-system, sans-serif",
        base_font_size=68,
        color="#FFFFFF",
        highlight_color="#26C6DA",  # 청년 상쾌한 청록색
        stroke_color="#00695C",  # B안: 시그니처 청록 유지
        stroke_width=6,
        background="rgba(0,121,107,0.55)",
        text_align="center",
        padding_px=20,
        position="bottom",
        max_lines=2,
        line_height=1.25,
        bold=True,
    ),
    "hotissue": SubtitlePreset(
        id="hotissue",
        font_family="Pretendard, -apple-system, sans-serif",
        base_font_size=76,
        color="#FFEB3B",
        highlight_color="#F44336",  # 이슈 강조 빨강
        stroke_color="#000000",
        stroke_width=6,
        background="rgba(0,0,0,0.8)",
        text_align="center",
        padding_px=26,
        position="center",  # 이슈는 중앙 배치로 시선 집중
        max_lines=3,
        line_height=1.15,
        bold=True,
    ),
    "default": SubtitlePreset(
        id="default",
        font_family="Pretendard, -apple-system, sans-serif",
        base_font_size=64,
        color="#FFFFFF",
        highlight_color="#FFC107",
        stroke_color="#000000",
        stroke_width=6,
        background="rgba(0,0,0,0.6)",
        text_align="center",
        padding_px=20,
        position="bottom",
        max_lines=2,
        line_height=1.2,
        bold=True,
    ),
}


def get_preset(preset_id: str) -> SubtitlePreset:
    """Lookup preset by id, fall back to 'default' if unknown."""
    return PRESETS.get(preset_id, PRESETS["default"])


def list_preset_ids() -> list[str]:
    return list(PRESETS.keys())


def preset_to_dict(preset: SubtitlePreset) -> dict:
    """JSON serializable dict (Remotion prop payload)."""
    return {
        "id": preset.id,
        "fontFamily": preset.font_family,
        "baseFontSize": preset.base_font_size,
        "color": preset.color,
        "highlightColor": preset.highlight_color,
        "strokeColor": preset.stroke_color,
        "strokeWidth": preset.stroke_width,
        "background": preset.background,
        "textAlign": preset.text_align,
        "paddingPx": preset.padding_px,
        "position": preset.position,
        "maxLines": preset.max_lines,
        "lineHeight": preset.line_height,
        "bold": preset.bold,
        "dropShadow": preset.drop_shadow,
    }
