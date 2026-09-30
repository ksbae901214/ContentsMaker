"""V4.0 사진 슬라이드 뉴스 카드 — config 게이트·라벨 (042 Phase A)."""
from __future__ import annotations

import pytest

from scripts.render_news_v4 import (
    MIN_PHOTOS,
    config_warnings,
    headline_text,
    photo_credit_label,
    tag_badge,
    validate_config,
    with_caption_text,
)

BASE = {
    "format": "news_v4",
    "slug": "20260930_hdh_assassins_news_v4",
    "category": "political",
    "headline": ["영화 암살자들", "한동훈 직격탄"],
    "tag": "페이스북 직격 비판",
    "title": "영화 암살자들 한동훈 직격탄",
    "yt_title": "영화 암살자들 한동훈 직격탄",
    "persons": ["한동훈"],
    "fact_sources": [{"title": "한동훈 페이스북", "url": "https://n.news.naver.com/1"}],
    "photos": [
        {"path": "a.jpg", "credit": "연합뉴스"},
        {"path": "fb.png", "credit": "한동훈 페이스북", "fit": "contain"},
        {"path": "c.jpg", "credit": "뉴스1"},
        {"path": "d.jpg", "credit": "연합뉴스"},
    ],
    "scenes": [
        {"voice": "영화 암살자들이 역사 왜곡 논란에 휩싸였습니다."},
        {"voice": "한동훈 무소속 의원이 페이스북을 통해 쓴소리를 날렸습니다."},
    ],
}


def _without(key):
    return {k: v for k, v in BASE.items() if k != key}


class TestValidate:
    def test_base_passes(self):
        validate_config(BASE)

    def test_wrong_format_rejected(self):
        with pytest.raises(ValueError, match="news_v4"):
            validate_config({**BASE, "format": "profile_v3"})

    def test_missing_format_rejected(self):
        """미지정 = v2_1 — 이 렌더러로 V2 config 를 돌리면 안 된다."""
        with pytest.raises(ValueError, match="news_v4"):
            validate_config(_without("format"))

    @pytest.mark.parametrize("key", ["slug", "photos", "scenes"])
    def test_required_keys(self, key):
        with pytest.raises(ValueError, match=key):
            validate_config(_without(key))

    def test_political_only(self):
        """사용자 확정 2026-09-30 — V4.0 은 정치만."""
        with pytest.raises(ValueError, match="정치"):
            validate_config({**BASE, "category": "economic"})

    def test_category_default_is_political(self):
        validate_config(_without("category"))

    def test_photo_credit_required(self):
        """출처 표기는 저작권 방어선 — 하단 출처 줄이 credit 으로 조립된다."""
        photos = [*BASE["photos"][:3], {"path": "x.jpg"}]
        with pytest.raises(ValueError, match="credit"):
            validate_config({**BASE, "photos": photos})

    def test_photo_path_required(self):
        photos = [*BASE["photos"][:3], {"credit": "뉴스1"}]
        with pytest.raises(ValueError, match="path"):
            validate_config({**BASE, "photos": photos})

    def test_photo_fit_value(self):
        photos = [*BASE["photos"][:3], {"path": "x.jpg", "credit": "뉴스1", "fit": "fill"}]
        with pytest.raises(ValueError, match="fit"):
            validate_config({**BASE, "photos": photos})

    def test_empty_voice_rejected(self):
        with pytest.raises(ValueError, match="voice"):
            validate_config({**BASE, "scenes": [{"voice": ""}]})

    def test_color_checked(self):
        scenes = [{"voice": "문장입니다.", "color": "green"}]
        with pytest.raises(ValueError, match="color"):
            validate_config({**BASE, "scenes": scenes})

    def test_fact_sources_required(self):
        """나레이션 100% 가 채널 자신의 서술 — 041 과 같은 법적 요건."""
        with pytest.raises(ValueError, match="fact_sources"):
            validate_config(_without("fact_sources"))

    def test_fact_gate_off_bypasses(self):
        validate_config({**_without("fact_sources"), "fact_gate": "off"})

    def test_namuwiki_rejected(self):
        cfg = {**BASE, "fact_sources": [{"url": "https://namu.wiki/w/한동훈"}]}
        with pytest.raises(ValueError, match="나무위키"):
            validate_config(cfg)

    def test_report_style_title_blocked(self):
        """034 보도체 게이트는 포맷 공통."""
        with pytest.raises(ValueError):
            validate_config({**BASE, "yt_title": "한동훈이 영화를 비판했다"})


class TestWarnings:
    def test_base_has_no_v4_warnings(self):
        ws = config_warnings(BASE)
        assert not any("사진" in w for w in ws)
        assert not any("헤드라인" in w for w in ws)

    def test_few_photos_warn(self):
        cfg = {**BASE, "photos": BASE["photos"][:MIN_PHOTOS - 1]}
        assert any("사진" in w for w in config_warnings(cfg))

    def test_long_headline_line_warns(self):
        cfg = {**BASE, "headline": ["가" * 13, "짧은 줄"]}
        assert any("헤드라인" in w for w in config_warnings(cfg))

    def test_three_line_headline_warns(self):
        cfg = {**BASE, "headline": ["하나", "둘", "셋"]}
        assert any("헤드라인" in w for w in config_warnings(cfg))

    def test_no_question_requirement_on_line_two(self):
        """V3.0 의 '2열 질문형' 규칙은 인물 프로필 전용 — V4 는 '직격탄' 같은 명사형."""
        assert not any("질문형" in w for w in config_warnings(BASE))

    def test_missing_tag_warns(self):
        assert any("tag" in w for w in config_warnings(_without("tag")))

    def test_no_intro_warning(self):
        """육성 훅이 없어 첫 문장이 곧 인트로 — intro 규칙 면제."""
        assert not any("인트로" in w for w in config_warnings(BASE))


class TestLabels:
    def test_headline_two_lines(self):
        assert headline_text(BASE) == "영화 암살자들\n한동훈 직격탄"

    def test_credit_label_dedup_in_order(self):
        """벤치마크: '출처 : 연합뉴스 · 하이브미디어코프 · 한동훈 페이스북 · …'."""
        assert photo_credit_label(BASE) == "출처 : 연합뉴스 · 한동훈 페이스북 · 뉴스1"

    def test_credit_label_explicit_override(self):
        cfg = {**BASE, "source_channel": "연합뉴스 외"}
        assert photo_credit_label(cfg) == "출처 : 연합뉴스 외"

    def test_tag_badge(self):
        assert tag_badge(BASE) == "페이스북 직격 비판"
        assert tag_badge(_without("tag")) == ""


class TestCaptionText:
    def test_fills_text_from_voice_without_mutating(self):
        """업로드 패키지 3줄요약은 `text` 를 읽는다 — V4 자막 = 나레이션."""
        out = with_caption_text(BASE)
        assert out["scenes"][0]["text"] == BASE["scenes"][0]["voice"]
        assert "text" not in BASE["scenes"][0]
        assert out is not BASE

    def test_keeps_explicit_text(self):
        cfg = {**BASE, "scenes": [{"voice": "나레이션.", "text": "자막"}]}
        assert with_caption_text(cfg)["scenes"][0]["text"] == "자막"


# ── Phase D: 렌더 조립 순수 로직 ─────────────────────────────────────
from scripts.render_news_v4 import (  # noqa: E402
    build_news_card,
    build_script,
    estimated_timings,
    missing_photos,
)

TIMINGS = [
    {"scene_id": 0, "start_ms": 0, "end_ms": 6930},
    {"scene_id": 1, "start_ms": 6930, "end_ms": 12000},
    {"scene_id": -1, "start_ms": 12000, "end_ms": 14000},
]


class TestBuildScript:
    def test_one_scene_per_sentence(self):
        s = build_script(with_caption_text(BASE))
        assert [sc.voice_text for sc in s.scenes] == [sc["voice"] for sc in BASE["scenes"]]
        assert [sc.id for sc in s.scenes] == [0, 1]

    def test_headline_title_and_white_canvas(self):
        s = build_script(with_caption_text(BASE))
        assert s.metadata.title == "영화 암살자들\n한동훈 직격탄"
        assert s.background.colors == ("#F5F5F5", "#F5F5F5")
        assert s.metadata.source_type == "political_pro"

    def test_no_hook_scene(self):
        """육성 훅이 없다 — 씬 0 도 나레이션이 있는 일반 씬."""
        s = build_script(with_caption_text(BASE))
        assert all(sc.voice_text for sc in s.scenes)


class TestBuildNewsCard:
    def test_first_photo_spans_first_sentence(self):
        card = build_news_card(BASE, TIMINGS)
        assert card["photos"][0]["end_ms"] == 6930
        assert card["photos"][-1]["end_ms"] == 12000

    def test_outro_timing_ignored(self):
        card = build_news_card(BASE, TIMINGS)
        assert max(p["end_ms"] for p in card["photos"]) == 12000
        assert max(c["end_ms"] for c in card["captions"]) == 12000

    def test_captions_cover_each_sentence(self):
        card = build_news_card(BASE, TIMINGS)
        joined = " ".join(c["text"] for c in card["captions"])
        assert joined == " ".join(sc["voice"] for sc in BASE["scenes"])

    def test_credit_line_only_lists_photos_on_screen(self):
        """TTS 가 추정보다 짧으면 뒤쪽 사진은 안 나온다 — 안 나온 사진의 출처를
        화면에 적으면 출처 표기가 틀린다 (2026-09-30 DMZ 편 실측: 뉴스1)."""
        cfg = {**BASE, "photos": [*BASE["photos"], {"path": "e.jpg", "credit": "경향신문"}]}
        card = build_news_card(cfg, TIMINGS)
        assert "e.jpg" not in [p["path"] for p in card["photos"]]
        assert "경향신문" not in card["credit_line"]

    def test_credit_font_and_fit(self):
        card = build_news_card(BASE, TIMINGS)
        assert card["credit_line"] == "출처 : 연합뉴스 · 한동훈 페이스북 · 뉴스1"
        assert card["font_family"] == "BM Dohyeon"
        assert card["photos"][1]["fit"] == "contain"


class TestPhotoFiles:
    def test_missing_photos_listed(self, tmp_path):
        present = tmp_path / "a.jpg"
        present.write_bytes(b"x")
        cfg = {**BASE, "photos": [{"path": str(present), "credit": "c"},
                                  {"path": str(tmp_path / "nope.jpg"), "credit": "c"}]}
        assert missing_photos(cfg) == [str(tmp_path / "nope.jpg")]


class TestEstimatedTimings:
    def test_contiguous_estimate_for_preview(self):
        est = estimated_timings(BASE)
        assert [t["scene_id"] for t in est] == [0, 1]
        assert est[0]["start_ms"] == 0
        assert est[0]["end_ms"] == est[1]["start_ms"] > 0


# ── 완료 블록: 자극적 제목 A/B + 3줄요약 + 해시태그 (사용자 지시 2026-09-30) ──
from scripts.render_news_v4 import MIN_HASHTAGS, news_v4_chat_block  # noqa: E402

PKG = {**BASE, "yt_title": "김여정 '자작극'이라더니… 유엔사 판단은 위반",
       "yt_title_alt": "장병 3명 다쳤는데 '자작극'이라는 김여정",
       "hashtags": ["#김여정", "#DMZ지뢰", "#유엔사", "#합참"]}


class TestChatBlock:
    def test_has_both_titles_summary_and_hashtags(self):
        block = news_v4_chat_block(with_caption_text(PKG))
        assert "제목 A: 김여정 '자작극'이라더니… 유엔사 판단은 위반" in block
        assert "제목 B: 장병 3명 다쳤는데 '자작극'이라는 김여정" in block
        assert "3줄요약:" in block
        assert "해시태그: #김여정 #DMZ지뢰 #유엔사 #합참" in block

    def test_without_alt_title_shows_single(self):
        cfg = {k: v for k, v in PKG.items() if k != "yt_title_alt"}
        block = news_v4_chat_block(with_caption_text(cfg))
        assert "제목: " in block and "제목 B" not in block


class TestPackagingWarnings:
    def test_missing_alt_title_warns(self):
        cfg = {k: v for k, v in PKG.items() if k != "yt_title_alt"}
        assert any("yt_title_alt" in w for w in config_warnings(cfg))

    def test_few_hashtags_warn(self):
        cfg = {**PKG, "hashtags": ["#김여정"][:MIN_HASHTAGS - 1]}
        assert any("해시태그" in w for w in config_warnings(cfg))

    def test_persons_fallback_counts_as_few(self):
        """hashtags 미지정이면 persons 로 1~2개만 붙는다 — 검색 노출이 약하다."""
        cfg = {k: v for k, v in PKG.items() if k != "hashtags"}
        assert any("해시태그" in w for w in config_warnings(cfg))

    def test_complete_package_silent(self):
        ws = config_warnings(PKG)
        assert not any("yt_title_alt" in w or "해시태그" in w for w in ws)
