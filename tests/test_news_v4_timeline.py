"""V4.0 사진 슬라이드 타임라인 순수 로직 (042 Phase B).

벤치마크 실측: 컷 0 / 6.93 / 11.47 / 14.87 / 18.27 / 21.67 / 25.07 / 28.43 —
첫 사진은 첫 문장 끝까지, 이후는 문장 경계와 무관한 3.4초 고정 타이머.
"""
from __future__ import annotations

import pytest

from scripts.news_v4_timeline import (
    DEFAULT_INTERVAL_MS,
    MIN_TAIL_MS,
    CaptionChunk,
    PhotoSlot,
    caption_chunks_for_scene,
    chunk_timings,
    photo_schedule,
    schedule_warnings,
    split_caption,
)

PHOTOS = [
    {"path": "a.jpg", "credit": "연합뉴스", "fit": "cover"},
    {"path": "fb.png", "credit": "한동훈 페이스북", "fit": "contain"},
    {"path": "c.jpg", "credit": "뉴스1"},
    {"path": "d.jpg", "credit": "이데일리"},
]


class TestPhotoSchedule:
    def test_first_photo_spans_first_sentence(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=6930, total_ms=20000)
        assert slots[0] == PhotoSlot("a.jpg", "cover", 0, 6930)

    def test_fixed_interval_after_first(self):
        """벤치마크: 컷3 이후 정확히 3.4초 — 문장 경계와 무관."""
        slots = photo_schedule(PHOTOS, first_scene_end_ms=6930, total_ms=16000)
        assert [(s.start_ms, s.end_ms) for s in slots[1:3]] == [
            (6930, 6930 + DEFAULT_INTERVAL_MS),
            (6930 + DEFAULT_INTERVAL_MS, 6930 + 2 * DEFAULT_INTERVAL_MS),
        ]

    def test_default_interval_is_benchmark(self):
        assert DEFAULT_INTERVAL_MS == 3400

    def test_fit_defaults_to_cover(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=3000, total_ms=12000)
        assert slots[1].fit == "contain"
        assert slots[2].fit == "cover"

    def test_covers_whole_timeline_without_gap(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=6930, total_ms=29000)
        assert slots[0].start_ms == 0
        assert slots[-1].end_ms == 29000
        for prev, nxt in zip(slots, slots[1:]):
            assert prev.end_ms == nxt.start_ms

    def test_cycles_skipping_first_photo(self):
        """사진이 모자라면 photos[1:] 을 돈다 — 첫 컷(사건 요약 합성)은 한 번만."""
        slots = photo_schedule(PHOTOS, first_scene_end_ms=3000, total_ms=30000)
        paths = [s.path for s in slots]
        assert paths[0] == "a.jpg"
        assert "a.jpg" not in paths[1:]
        assert paths[1:5] == ["fb.png", "c.jpg", "d.jpg", "fb.png"]

    def test_single_photo_reused(self):
        slots = photo_schedule(PHOTOS[:1], first_scene_end_ms=3000, total_ms=10000)
        assert {s.path for s in slots} == {"a.jpg"}
        assert slots[-1].end_ms == 10000

    def test_short_tail_merged_into_previous(self):
        """벤치마크 끝의 0.9초 컷 같은 자투리는 깜빡임으로 보인다 — 앞 컷에 흡수."""
        total = 3000 + DEFAULT_INTERVAL_MS + (MIN_TAIL_MS - 100)
        slots = photo_schedule(PHOTOS, first_scene_end_ms=3000, total_ms=total)
        assert len(slots) == 2
        assert slots[-1].end_ms == total

    def test_explicit_dur_wins(self):
        photos = [PHOTOS[0], {**PHOTOS[1], "dur": 4.5}, PHOTOS[2]]
        slots = photo_schedule(photos, first_scene_end_ms=6930, total_ms=20000)
        assert slots[1].end_ms - slots[1].start_ms == 4500

    def test_explicit_dur_on_first_photo(self):
        photos = [{**PHOTOS[0], "dur": 2.0}, *PHOTOS[1:]]
        slots = photo_schedule(photos, first_scene_end_ms=6930, total_ms=20000)
        assert slots[0].end_ms == 2000

    def test_first_scene_longer_than_total(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=9000, total_ms=5000)
        assert slots == (PhotoSlot("a.jpg", "cover", 0, 5000),)

    def test_empty_inputs(self):
        assert photo_schedule([], first_scene_end_ms=3000, total_ms=9000) == ()
        assert photo_schedule(PHOTOS, first_scene_end_ms=3000, total_ms=0) == ()

    def test_returns_immutable_tuple(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=3000, total_ms=9000)
        assert isinstance(slots, tuple)
        with pytest.raises(Exception):
            slots[0].start_ms = 5  # type: ignore[misc]


class TestScheduleWarnings:
    def test_reuse_warns(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=3000, total_ms=30000)
        assert any("반복" in w for w in schedule_warnings(PHOTOS, slots))

    def test_enough_photos_silent(self):
        slots = photo_schedule(PHOTOS, first_scene_end_ms=6930, total_ms=16000)
        assert schedule_warnings(PHOTOS, slots) == []


class TestSplitCaption:
    def test_packs_words_up_to_limit(self):
        """벤치마크 자막은 호흡 단위 — '관객 130만 명을 돌파하며' 한 덩어리."""
        chunks = split_caption("관객 130만 명을 돌파하며 역사 왜곡 논란에 휩싸였습니다.",
                               max_chars=16)
        assert chunks == ("관객 130만 명을 돌파하며", "역사 왜곡 논란에", "휩싸였습니다.")

    def test_every_chunk_within_limit(self):
        text = "만약 5.18이 북한 소행이라는 영화가 개봉되었다면 정말 많이 비판받았을 것이라며"
        assert all(len(c) <= 16 for c in split_caption(text, max_chars=16))

    def test_single_long_word_kept_whole(self):
        assert split_caption("가" * 20, max_chars=16) == ("가" * 20,)

    def test_newline_is_hard_break(self):
        assert split_caption("짧은 줄\n다음 줄", max_chars=16) == ("짧은 줄", "다음 줄")

    def test_empty(self):
        assert split_caption("   ", max_chars=16) == ()

    def test_words_preserved_in_order(self):
        text = "사전검열에는 반대한다는 한동훈 무소속 의원이 페이스북을 통해 쓴소리를 날렸습니다."
        assert " ".join(split_caption(text, max_chars=16)) == text


class TestChunkTimings:
    def test_proportional_to_chars_and_contiguous(self):
        spans = chunk_timings(("가나다라", "마바"), 1000, 1600)
        assert spans == ((1000, 1400), (1400, 1600))

    def test_last_ends_exactly_at_end(self):
        spans = chunk_timings(("가", "나다", "라마바"), 0, 1001)
        assert spans[-1][1] == 1001
        assert spans[0][0] == 0

    def test_spaces_not_counted(self):
        spans = chunk_timings(("가 나", "다라"), 0, 400)
        assert spans == ((0, 200), (200, 400))

    def test_empty(self):
        assert chunk_timings((), 0, 1000) == ()


class TestCaptionChunksForScene:
    SCENE = {"voice": "사전검열에는 반대한다는 한동훈 무소속 의원이 페이스북을 통해",
             "hl": ["한동훈"], "color": "white"}

    def test_chunks_follow_voice(self):
        chunks = caption_chunks_for_scene(self.SCENE, 0, 3000, max_chars=16)
        assert " ".join(c.text for c in chunks) == self.SCENE["voice"]

    def test_highlight_only_on_chunk_containing_word(self):
        chunks = caption_chunks_for_scene(self.SCENE, 0, 3000, max_chars=16)
        for c in chunks:
            assert c.hl == (("한동훈",) if "한동훈" in c.text else ())

    def test_cta_scene_shown_whole_from_text(self):
        """CTA 는 나레이션이 아니라 2줄 'A / VS B' 자막 한 덩어리 (벤치마크)."""
        cta = {"_cta": True, "voice": "어느 쪽일까요? 댓글로 알려주세요.",
               "text": "①역사 왜곡 비판 타당\nVS ②표현의 자유", "color": "red"}
        chunks = caption_chunks_for_scene(cta, 5000, 9000, max_chars=16)
        assert chunks == (CaptionChunk(cta["text"], 5000, 9000, (), "red"),)

    def test_color_carried(self):
        chunks = caption_chunks_for_scene({**self.SCENE, "color": "yellow"}, 0, 3000)
        assert {c.color for c in chunks} == {"yellow"}

    def test_spans_contiguous(self):
        chunks = caption_chunks_for_scene(self.SCENE, 1000, 4000, max_chars=16)
        assert chunks[0].start_ms == 1000 and chunks[-1].end_ms == 4000
        for a, b in zip(chunks, chunks[1:]):
            assert a.end_ms == b.start_ms
