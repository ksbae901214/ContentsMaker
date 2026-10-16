"""V3.0 인물 프로필 렌더러 순수 로직 (041 Phase A2)."""
from __future__ import annotations

import pytest

from scripts.render_profile_v3 import (
    CLIP_MAX_SEC,
    HEADLINE_MAX_LINE,
    build_script,
    config_warnings,
    headline_lines,
    headline_text,
    headline_warnings,
    person_badge,
    photo_for_index,
    rotation_plan,
    source_for_scene,
    source_label,
    validate_config,
)

BASE = {
    "format": "profile_v3",
    "slug": "leehm_profile",
    "category": "political",
    "person": "이해민",
    "person_title": "수석 내정자",
    "headline": ["이해민 수석 내정자", "구글 출신?"],
    "title": "이해민은 누구인가",
    "yt_title": "이해민은 누구인가",
    "fact_sources": [{"title": "이해민 내정", "url": "https://n.news.naver.com/1"}],
    "sources": {
        "interview": {"query": "이해민 인터뷰"},
        "speech": {"query": "이해민 연설"},
        "press": {"query": "이해민 기자회견"},
    },
    "scenes": [
        {"voice": "그는 최근 수석에 내정됐습니다.", "text": "수석 내정"},
        {"voice": "출발은 개발자였습니다.", "text": "개발자 출신"},
    ],
}


class TestHeadline:
    def test_lines_from_list(self):
        assert headline_lines(BASE) == ["이해민 수석 내정자", "구글 출신?"]

    def test_text_is_newline_joined(self):
        """TitleBar 가 \\n 으로 2줄 투톤을 나눈다."""
        assert headline_text(BASE) == "이해민 수석 내정자\n구글 출신?"

    def test_falls_back_to_title(self):
        cfg = {k: v for k, v in BASE.items() if k != "headline"}
        assert headline_lines(cfg) == ["이해민은 누구인가"]

    def test_long_line_warns(self):
        """궁서는 자폭이 넓어 긴 줄이 3줄로 밀리면 인물 배지를 덮는다."""
        cfg = {**BASE, "headline": ["가" * (HEADLINE_MAX_LINE + 1), "짧은 훅?"]}
        assert any("헤드라인" in w for w in headline_warnings(cfg))

    def test_three_lines_warn(self):
        cfg = {**BASE, "headline": ["1열", "2열", "3열"]}
        assert any("2줄" in w for w in headline_warnings(cfg))

    def test_second_line_should_be_question(self):
        cfg = {**BASE, "headline": ["이해민 수석 내정자", "구글 출신이다"]}
        assert any("질문형" in w for w in headline_warnings(cfg))

    def test_ok_headline_is_silent(self):
        assert headline_warnings(BASE) == []


class TestPersonBadge:
    def test_name_and_title(self):
        assert person_badge(BASE) == "이해민 · 수석 내정자"

    def test_name_only(self):
        cfg = {**BASE, "person_title": ""}
        assert person_badge(cfg) == "이해민"


class TestRotation:
    def test_plan_follows_declaration_order(self):
        assert rotation_plan(BASE) == ["interview", "speech", "press"]

    def test_underscore_comment_keys_are_not_sources(self):
        """이 레포 템플릿은 객체 안에 _comment 키를 넣는다 — 소스로 세면 안 된다."""
        cfg = {**BASE, "sources": {
            "_comment_": "설명 문자열",
            "interview": {"query": "q"},
        }}
        assert rotation_plan(cfg) == ["interview"]

    def test_first_pass_is_sequential(self):
        plan = rotation_plan(BASE)
        assert [source_for_scene(BASE, plan, i) for i in range(3)] == plan

    def test_second_pass_is_offset(self):
        """매 순환마다 시작 오프셋을 밀어 같은 순서 반복을 피한다 (지침 §4-3)."""
        plan = rotation_plan(BASE)
        assert [source_for_scene(BASE, plan, i) for i in range(3, 6)] == [
            "speech", "press", "interview"]

    def test_explicit_source_wins(self):
        cfg = {**BASE, "scenes": [{"voice": "v", "text": "t", "source": "press"}]}
        assert source_for_scene(cfg, rotation_plan(cfg), 0) == "press"

    def test_empty_plan_returns_empty(self):
        assert source_for_scene({"scenes": [{}]}, [], 0) == ""


class TestPhotoPool:
    def test_cycles(self):
        photos = ["a.png", "b.png"]
        assert [photo_for_index(photos, i) for i in range(4)] == [
            "a.png", "b.png", "a.png", "b.png"]

    def test_empty_pool(self):
        assert photo_for_index([], 0) is None


class TestValidate:
    def test_ok(self):
        validate_config(BASE)

    def test_wrong_format_rejected(self):
        with pytest.raises(ValueError, match="profile_v3"):
            validate_config({**BASE, "format": "v2_1"})

    def test_person_required(self):
        with pytest.raises(ValueError, match="person"):
            validate_config({k: v for k, v in BASE.items() if k != "person"})

    def test_fact_sources_required(self):
        """나레이션 전체가 채널의 발언이라 팩트 소스가 유일한 방어선이다."""
        cfg = {k: v for k, v in BASE.items() if k != "fact_sources"}
        with pytest.raises(ValueError, match="fact_sources"):
            validate_config(cfg)

    def test_namuwiki_fact_source_blocked(self):
        cfg = {**BASE,
               "fact_sources": [{"title": "x", "url": "https://namu.wiki/w/이해민"}]}
        with pytest.raises(ValueError, match="나무위키"):
            validate_config(cfg)

    def test_fact_gate_off_bypasses(self):
        cfg = {k: v for k, v in BASE.items() if k != "fact_sources"}
        validate_config({**cfg, "fact_gate": "off"})

    def test_scene_voice_required(self):
        cfg = {**BASE, "scenes": [{"text": "자막만"}]}
        with pytest.raises(ValueError, match="voice"):
            validate_config(cfg)


class TestWarnings:
    def test_long_clip_warns(self):
        """인물 B-roll 은 비평 대상이 그 영상이 아니라 인용 목적성이 약하다."""
        cfg = {**BASE, "hook": {"source": "interview",
                                "duration": CLIP_MAX_SEC + 1}}
        assert any("저작권" in w for w in config_warnings(cfg))

    def test_headline_warnings_included(self):
        cfg = {**BASE, "headline": ["1열", "2열", "3열"]}
        assert any("2줄" in w for w in config_warnings(cfg))

    def test_symmetry_gate_stays_silent(self):
        """040 대칭은 인물 1명 포맷에 성립하지 않는다 (A4 연동 확인)."""
        assert not any("[040] 한쪽 진영" in w for w in config_warnings(BASE))

    SUBSCRIBE_CTA = {
        "text": "더 궁금하다면?\n댓글 + 구독",
        "voice": "궁금한 점은 댓글로 남겨주세요.",
    }

    def test_subscribe_cta_not_flagged_as_open_question(self):
        """구독형 CTA 는 V3.0 의 확정 규격이다 — 선택지형 경고가 뜨면 안 된다."""
        cfg = {**BASE, "cta": self.SUBSCRIBE_CTA}
        assert not any("선택지형" in w for w in config_warnings(cfg))

    def test_subscribe_cta_polite_closing_accepted(self):
        cfg = {**BASE, "cta": self.SUBSCRIBE_CTA}
        assert not any("종결" in w for w in config_warnings(cfg))

    def test_blunt_subscribe_cta_still_flagged(self):
        cfg = {**BASE, "cta": {**self.SUBSCRIBE_CTA, "voice": "댓글 달고 구독."}}
        assert any("종결" in w for w in config_warnings(cfg))


class TestUploadPackageChecklist:
    """포맷 체크리스트가 upload_package.md 에 실제로 나와야 한다 (041 A5)."""

    def _md(self, cfg, tmp_path):
        from datetime import datetime

        from scripts.political_upload_package import build_upload_package_md
        return build_upload_package_md(
            cfg, tmp_path / "out.mp4", suggested=datetime(2026, 9, 14, 20, 0))

    def test_profile_v3_checklist_rendered(self, tmp_path):
        md = self._md(BASE, tmp_path)
        assert "fact_sources" in md          # 팩트 매핑 항목
        assert "나무위키" in md               # 라이선스 항목

    def test_profile_v3_format_labelled(self, tmp_path):
        assert "profile_v3" in self._md(BASE, tmp_path)

    def test_v2_checklist_unchanged(self, tmp_path):
        """대조군 — 기존 V2 config 의 패키지에는 V3.0 항목이 없어야 한다."""
        cfg = {k: v for k, v in BASE.items() if k != "format"}
        md = self._md(cfg, tmp_path)
        assert "나무위키" not in md
        assert "profile_v3" not in md


class TestSourceLabel:
    def test_joins_channels(self):
        cfg = {**BASE, "sources": {
            "a": {"query": "q", "channel": "채널A"},
            "b": {"query": "q", "channel": "채널B"},
        }}
        label = source_label(cfg)
        assert "채널A" in label and "채널B" in label

    def test_dedupes(self):
        cfg = {**BASE, "sources": {
            "a": {"query": "q", "channel": "채널A"},
            "b": {"query": "q", "channel": "채널A"},
        }}
        assert source_label(cfg).count("채널A") == 1

    def test_explicit_source_channel_wins(self):
        cfg = {**BASE, "source_channel": "직접 지정"}
        assert "직접 지정" in source_label(cfg)

    def test_empty_without_channels(self):
        assert source_label(BASE) == ""

    def test_ignores_comment_entries(self):
        cfg = {**BASE, "sources": {
            "_comment_": "설명 문자열",
            "a": {"query": "q", "channel": "채널A"},
        }}
        assert source_label(cfg) == "출처: 채널A"


class TestBuildScript:
    def test_title_is_two_line_headline(self):
        script = build_script(BASE, hook_dur=0.0)
        assert script.metadata.title == "이해민 수석 내정자\n구글 출신?"

    def test_hook_scene_has_no_voice(self):
        cfg = {**BASE, "hook": {"source": "interview", "duration": 4.0}}
        script = build_script(cfg, hook_dur=4.0)
        assert script.scenes[0].voice_text == ""
        assert script.scenes[0].duration == 4.0

    def test_scene_count_with_hook(self):
        cfg = {**BASE, "hook": {"source": "interview", "duration": 4.0}}
        script = build_script(cfg, hook_dur=4.0)
        assert len(script.scenes) == len(BASE["scenes"]) + 1

    def test_scene_count_without_hook(self):
        script = build_script(BASE, hook_dur=0.0)
        assert len(script.scenes) == len(BASE["scenes"])

    def test_tts_script_joins_voices(self):
        script = build_script(BASE, hook_dur=0.0)
        assert "출발은 개발자였습니다." in script.audio.tts_script
