"""V5.0 화면 레이어 타임라인 — 순수 함수 (043 Phase B)."""
from __future__ import annotations

import pytest

from scripts.evidence_v5_timeline import (
    CAPTION_CHARS,
    DEFAULT_HEADLINE_COLORS,
    POP_MS,
    build_layer,
    caption_chunks,
    evidence_card,
    headline_lines,
    pop_event,
    validate_framing,
    validate_marks,
)


class TestFraming:
    @pytest.mark.parametrize("sc", [{"zoom": 0.5}, {"zoom": 3.5}, {"focus_x": -0.1},
                                    {"focus_x": 1.2}, {"zoom": "big"}])
    def test_bad_framing_rejected(self, sc):
        with pytest.raises(ValueError):
            validate_framing(sc)

    def test_good_framing(self):
        validate_framing({"zoom": 2.0, "focus_x": 0.0})
        validate_framing({})


class TestHeadline:
    def test_list(self):
        assert headline_lines({"headline": ["최저시급 차등?", "여기 대한민국이야?"]}) == [
            "최저시급 차등?", "여기 대한민국이야?"]

    def test_string_split(self):
        assert headline_lines({"headline": "a\nb"}) == ["a", "b"]

    def test_fallback_title(self):
        assert headline_lines({"title": "배너"}) == ["배너"]


class TestCaptions:
    def test_tts_scene_uses_voice_split_short(self):
        sc = {"mode": "tts", "voice": "지방 사니까 최저시급도 깎자는 기적의 논리입니다", "text": "x"}
        chunks = caption_chunks(sc, 0, 4000)
        assert all(len(c.text) <= CAPTION_CHARS for c in chunks)
        assert "".join(c.text.replace(" ", "") for c in chunks) == sc["voice"].replace(" ", "")
        assert chunks[0].start_ms == 0 and chunks[-1].end_ms == 4000

    def test_clip_scene_uses_text(self):
        sc = {"mode": "clip", "text": "재선거를 실시해야 합니다"}
        chunks = caption_chunks(sc, 1000, 3000)
        assert "".join(c.text for c in chunks).replace(" ", "") == "재선거를실시해야합니다"

    def test_cta_scene_one_block(self):
        sc = {"_cta": True, "text": "① 말 바꾸기\n② 현실 반영", "voice": "질문"}
        chunks = caption_chunks(sc, 0, 5000)
        assert len(chunks) == 1 and chunks[0].text == "① 말 바꾸기\n② 현실 반영"

    def test_highlight_kept_only_where_present(self):
        sc = {"voice": "세금 730억 그런데 돌값은 40억", "hl": ["730억", "40억"]}
        chunks = caption_chunks(sc, 0, 3000)
        for c in chunks:
            assert all(w in c.text for w in c.hl)

    def test_empty_scene(self):
        assert caption_chunks({"mode": "clip", "text": ""}, 0, 1000) == ()


class TestPop:
    def test_pop_at_scene_start(self):
        ev = pop_event({"pop": "지방 사니까"}, 2000, 9000)
        assert (ev.text, ev.start_ms, ev.end_ms) == ("지방 사니까", 2000, 2000 + POP_MS)

    def test_pop_clamped_to_scene(self):
        assert pop_event({"pop": "깍자!"}, 0, 900).end_ms == 900

    def test_no_pop(self):
        assert pop_event({}, 0, 1000) is None


class TestEvidence:
    def test_card_spans_scene(self):
        card = evidence_card({"evidence": {"image": "a.png", "marks": [
            {"kind": "circle", "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}]}}, 1000, 5000)
        assert card.path == "a.png" and (card.start_ms, card.end_ms) == (1000, 5000)
        assert card.marks[0]["kind"] == "circle"

    def test_none_without_evidence(self):
        assert evidence_card({}, 0, 1) is None

    @pytest.mark.parametrize("mark", [
        {"kind": "arrow", "x": 0, "y": 0, "w": 0.1, "h": 0.1},
        {"kind": "circle", "x": 1.2, "y": 0, "w": 0.1, "h": 0.1},
        {"kind": "underline", "x": 0.5, "y": 0.5, "w": 0.6, "h": 0.05},
        {"kind": "circle", "x": 0.1, "y": 0.1},
    ])
    def test_bad_marks_rejected(self, mark):
        with pytest.raises(ValueError):
            validate_marks([mark])

    def test_good_marks(self):
        validate_marks([{"kind": "underline", "x": 0.1, "y": 0.5, "w": 0.6, "h": 0.04}])


CFG = {
    "headline": ["한동훈 2달만에", "KTX-SRT 결합 증편 성과?"],
    "source_label": "영상출처: 입국열차, 강성범TV",
    "scenes": [
        {"mode": "tts", "voice": "한동훈이 두 달 만에 고속열차를 뚫었다고요?", "pop": "두 달 만에"},
        {"mode": "clip", "text": "오늘 날짜로 합병한 거죠"},
        {"mode": "tts", "voice": "그런데 승인 완료된 날은 8월 2일", "flash": True,
         "evidence": {"image": "e.png", "marks": [
             {"kind": "underline", "x": 0.1, "y": 0.6, "w": 0.5, "h": 0.04}]}},
    ],
}
TIMINGS = [
    {"scene_id": 0, "start_ms": 0, "end_ms": 4000},
    {"scene_id": 1, "start_ms": 4000, "end_ms": 7000},
    {"scene_id": 2, "start_ms": 7000, "end_ms": 10000},
    {"scene_id": -1, "start_ms": 10000, "end_ms": 12000},
]


class TestBuildLayer:
    def test_layer_shape(self):
        layer = build_layer(CFG, TIMINGS)
        assert layer["headline"] == CFG["headline"]
        assert layer["headline_colors"] == list(DEFAULT_HEADLINE_COLORS)
        assert layer["source_label"] == "영상출처: 입국열차, 강성범TV"
        assert layer["captions"][0]["start_ms"] == 0
        assert layer["captions"][-1]["end_ms"] == 10000
        assert [p["text"] for p in layer["pops"]] == ["두 달 만에"]
        assert layer["evidence"][0]["path"] == "e.png"
        assert layer["flashes"] == [7000]
        assert layer["font_family"] == "BM Dohyeon"

    def test_outro_ignored(self):
        layer = build_layer(CFG, TIMINGS)
        assert all(c["end_ms"] <= 10000 for c in layer["captions"])

    def test_headline_colors_override(self):
        layer = build_layer({**CFG, "headline_colors": ["#3FE0F0", "#FFE14D"]}, TIMINGS)
        assert layer["headline_colors"] == ["#3FE0F0", "#FFE14D"]

    def test_framing_defaults_fill_center(self):
        layer = build_layer(CFG, TIMINGS)
        assert layer["framing"][0] == {"scene_id": 0, "zoom": 1.0, "focus_x": 0.5}
        assert len(layer["framing"]) == 3

    def test_framing_override(self):
        scenes = [{**CFG["scenes"][0], "zoom": 1.4, "focus_x": 0.3}, *CFG["scenes"][1:]]
        layer = build_layer({**CFG, "scenes": scenes}, TIMINGS)
        assert layer["framing"][0] == {"scene_id": 0, "zoom": 1.4, "focus_x": 0.3}

    def test_missing_timing_raises(self):
        with pytest.raises(ValueError, match="scene 2"):
            build_layer(CFG, TIMINGS[:2])
