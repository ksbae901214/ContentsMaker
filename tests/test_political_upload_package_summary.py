"""3줄요약·채팅용 블록 생성 (038) 테스트 — scripts/political_upload_package.py."""
from __future__ import annotations

from scripts.political_upload_package import (
    build_chat_ready_block, build_three_line_summary,
)


def v21_cfg(**over) -> dict:
    """훅이 top-level `hook` 블록인 v2.1 스타일 config."""
    cfg = {
        "slug": "test_v21",
        "title": "테스트 제목",
        "yt_title": "테스트 제목 15자 이상 채움",
        "hashtags": ["#테스트"],
        "hook": {"source": "a", "start_sec": 0.0, "duration": 5.0,
                  "text": "훅 자막\n첫 줄"},
        "scenes": [
            {"type": "body", "text": "중간 자막 1", "voice": "중간 나레이션 1"},
            {"type": "body", "text": "가장 긴 정보 밀도 높은 중간 자막입니다",
             "voice": "가장 긴 나레이션"},
            {"type": "body", "text": "마지막 자막", "voice": "마지막 나레이션"},
        ],
    }
    cfg.update(over)
    return cfg


def v22_cfg(**over) -> dict:
    """훅이 top-level 블록 없이 scenes[0](clip)인 v2.2 스타일 config."""
    cfg = {
        "slug": "test_v22",
        "title": "테스트 제목",
        "yt_title": "테스트 제목 15자 이상 채움",
        "hashtags": ["#테스트"],
        "scenes": [
            {"mode": "clip", "text": "훅 클립 자막"},
            {"mode": "clip", "text": "본문 클립 자막 조금 더 긺"},
            {"mode": "tts", "text": "마지막 정리 자막", "voice": "마지막 정리 나레이션"},
        ],
    }
    cfg.update(over)
    return cfg


class TestBuildThreeLineSummary:
    def test_v21_uses_hook_block_as_line1(self):
        summary = build_three_line_summary(v21_cfg())
        lines = summary.split("\n")
        assert len(lines) == 3
        assert "훅 자막 첫 줄" in lines[0]

    def test_v22_uses_scene0_as_line1(self):
        summary = build_three_line_summary(v22_cfg())
        lines = summary.split("\n")
        assert len(lines) == 3
        assert "훅 클립 자막" in lines[0]

    def test_excludes_cta_scene_from_last_line(self):
        cfg = v21_cfg()
        cfg["scenes"].append({
            "type": "body", "_cta": True,
            "text": "이거 누구 잘못?\n① 조국  ② 이준석",
            "voice": "1번 조국, 2번 이준석. 댓글로 알려주세요.",
        })
        summary = build_three_line_summary(cfg)
        assert "누구 잘못" not in summary

    def test_excludes_scene_cta_marker_from_last_line(self):
        """top-level `_cta` 플래그 없이 씬으로 직접 쓴 CTA(①/② 마커)도 제외."""
        cfg = v22_cfg()
        cfg["scenes"].append({
            "mode": "tts", "text": "어느 쪽?\n① 약하다  ② 적당하다",
            "voice": "1번 약하다, 2번 적당하다. 댓글로 알려주세요.",
        })
        summary = build_three_line_summary(cfg)
        assert "약하다" not in summary or "적당하다" not in summary

    def test_lines_are_numbered(self):
        summary = build_three_line_summary(v21_cfg())
        lines = summary.split("\n")
        assert lines[0].startswith("1. ")
        assert lines[1].startswith("2. ")
        assert lines[2].startswith("3. ")

    def test_flattens_newlines_in_scene_text(self):
        summary = build_three_line_summary(v21_cfg())
        assert "\n" not in summary.split("\n")[0][3:]

    def test_no_scenes_falls_back_to_title(self):
        cfg = {"slug": "x", "title": "폴백 제목", "scenes": []}
        assert build_three_line_summary(cfg) == "폴백 제목"


class TestBuildChatReadyBlock:
    def test_contains_title_summary_hashtags(self):
        block = build_chat_ready_block(v21_cfg())
        assert "제목:" in block
        assert "3줄요약:" in block
        assert "해시태그:" in block
        assert "#테스트" in block

    def test_uses_sanitized_yt_title(self):
        cfg = v21_cfg(yt_title="테스트 #해시태그포함제목입니다요")
        block = build_chat_ready_block(cfg)
        title_line = next(ln for ln in block.split("\n") if ln.startswith("제목:"))
        assert "#" not in title_line
