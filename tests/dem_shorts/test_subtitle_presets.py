"""QW-03: 자막 외곽선 강화 (B안: 시그니처 색 유지 + 6px + 약한 drop shadow).

정치 유튜브 가독성 패턴: 모든 프리셋 stroke_width≥6, drop_shadow 필드 신규.
출처: docs/dem-shorts/political-youtube-style-plan.md §8.2 QW-03.
"""
from __future__ import annotations

import pytest

from src.dem_shorts.editor.subtitle_presets import (
    PRESETS,
    SubtitlePreset,
    get_preset,
    list_preset_ids,
    preset_to_dict,
)


class TestStrokeWidthQw03:
    """B안 + 6px: 모든 프리셋의 외곽선 두께가 6px 이상이어야 한다."""

    @pytest.mark.parametrize("preset_id", list(PRESETS.keys()))
    def test_stroke_width_at_least_6px(self, preset_id: str):
        preset = PRESETS[preset_id]
        assert preset.stroke_width >= 6, (
            f"preset '{preset_id}' stroke_width={preset.stroke_width}, "
            f"QW-03 요구 6px 이상 (정치 유튜브 가독성)"
        )

    def test_default_preset_stroke_width_6(self):
        """default 프리셋은 정확히 6 (안전한 중간값)."""
        assert PRESETS["default"].stroke_width == 6


class TestStrokeColorQw03:
    """B안: 시그니처 색을 강제로 검정으로 바꾸지 않는다."""

    def test_leejaemyung_keeps_signature_blue(self):
        """leejaemyung 프리셋은 민주 블루 시그니처 색을 유지한다."""
        assert PRESETS["leejaemyung"].stroke_color == "#1A237E"

    def test_youth_keeps_signature_teal(self):
        """youth 프리셋은 청록 시그니처 색을 유지한다."""
        assert PRESETS["youth"].stroke_color == "#00695C"

    def test_default_uses_black(self):
        """default 프리셋(시그니처 없음)은 검정 외곽선."""
        assert PRESETS["default"].stroke_color == "#000000"


class TestDropShadowField:
    """drop_shadow 필드 신규 추가: 약한 drop shadow 통일."""

    @pytest.mark.parametrize("preset_id", list(PRESETS.keys()))
    def test_preset_has_drop_shadow_field(self, preset_id: str):
        preset = PRESETS[preset_id]
        assert hasattr(preset, "drop_shadow"), (
            f"preset '{preset_id}'는 drop_shadow 필드를 가져야 한다 (QW-03)"
        )
        assert isinstance(preset.drop_shadow, str)
        assert len(preset.drop_shadow) > 0

    @pytest.mark.parametrize("preset_id", list(PRESETS.keys()))
    def test_drop_shadow_default_is_soft(self, preset_id: str):
        """Q3 결정: 약한 drop shadow (`3px 3px 8px rgba(0,0,0,0.7)`) 통일."""
        preset = PRESETS[preset_id]
        assert preset.drop_shadow == "3px 3px 8px rgba(0,0,0,0.7)", (
            f"preset '{preset_id}' drop_shadow={preset.drop_shadow}, "
            f"QW-03 Q3=약한 그림자 통일 위반"
        )


class TestPresetToDict:
    """Remotion으로 직렬화될 때 dropShadow 키가 포함되어야 한다."""

    @pytest.mark.parametrize("preset_id", list(PRESETS.keys()))
    def test_preset_to_dict_includes_drop_shadow(self, preset_id: str):
        d = preset_to_dict(PRESETS[preset_id])
        assert "dropShadow" in d, (
            f"preset_to_dict('{preset_id}')에 dropShadow 키 없음 — Remotion에 전달 안 됨"
        )
        assert d["dropShadow"] == PRESETS[preset_id].drop_shadow

    @pytest.mark.parametrize("preset_id", list(PRESETS.keys()))
    def test_preset_to_dict_keeps_existing_keys(self, preset_id: str):
        """기존 키들 회귀 방지."""
        d = preset_to_dict(PRESETS[preset_id])
        for required in (
            "id",
            "fontFamily",
            "baseFontSize",
            "color",
            "highlightColor",
            "strokeColor",
            "strokeWidth",
            "background",
            "textAlign",
            "paddingPx",
            "position",
            "maxLines",
            "lineHeight",
            "bold",
        ):
            assert required in d, f"preset_to_dict에 '{required}' 키 사라짐"


class TestGetPreset:
    """get_preset() 회귀: unknown id는 default로 fallback."""

    def test_known_preset(self):
        assert get_preset("leejaemyung").id == "leejaemyung"

    def test_unknown_preset_falls_back_to_default(self):
        assert get_preset("nonexistent_xyz").id == "default"


class TestListPresetIds:
    def test_contains_all_5_presets(self):
        ids = set(list_preset_ids())
        assert {"leejaemyung", "jungcheongrae", "youth", "hotissue", "default"} == ids
