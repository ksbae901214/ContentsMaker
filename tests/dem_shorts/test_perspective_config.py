"""Phase 1 TDD: config.py에 perspective 관련 상수 추가 검증."""
from __future__ import annotations


class TestPerspectiveConstants:
    def test_supported_perspectives(self):
        from src.dem_shorts.config import SUPPORTED_PERSPECTIVES
        assert set(SUPPORTED_PERSPECTIVES) == {"dem", "ppp"}

    def test_default_perspective(self):
        from src.dem_shorts.config import DEFAULT_PERSPECTIVE, SUPPORTED_PERSPECTIVES
        assert DEFAULT_PERSPECTIVE in SUPPORTED_PERSPECTIVES

    def test_perspective_top3_mapping(self):
        from src.dem_shorts.config import PERSPECTIVE_TOP_NAMES
        assert "dem" in PERSPECTIVE_TOP_NAMES
        assert "ppp" in PERSPECTIVE_TOP_NAMES
        assert set(PERSPECTIVE_TOP_NAMES["dem"]) == {"이재명", "조국", "정청래"}
        # PPP는 6명 전체가 TOP으로 간주됨 (pinned 시드)
        assert set(PERSPECTIVE_TOP_NAMES["ppp"]) == {
            "한동훈", "김기현", "권성동", "추경호", "나경원", "오세훈"
        }

    def test_perspective_channel_id_mapping(self):
        """현재 프로덕션: ppp만 활성, dem은 NULL (PPP-only 채널 운영)."""
        from src.dem_shorts.config import PERSPECTIVE_CHANNEL_ID
        assert "dem" in PERSPECTIVE_CHANNEL_ID
        assert "ppp" in PERSPECTIVE_CHANNEL_ID

    def test_symmetry_gate_threshold(self):
        """Symmetry Gate 20점 임계값 (SC-013)."""
        from src.dem_shorts.config import SYMMETRY_RISK_DIFF_WARN
        assert SYMMETRY_RISK_DIFF_WARN == 20.0
