"""정보쇼츠 V1.0 타임라인 순수 함수 테스트 (045)."""
from __future__ import annotations

import pytest

from scripts.info_v1_timeline import (
    CAPTION_LINE_CHARS,
    KORE_SYLLABLES_PER_SEC,
    CAPTION_MAX_LINES,
    ZOOM_MS,
    caption_cues,
    estimate_sec,
    flatten_sentences,
    image_slots,
    length_problems,
    scale_timings,
    split_cues,
    wrap_lines,
)

CHAPTERS = [
    {"sentences": ["1968년, 미국 핵잠수함 한 척이 사라집니다."]},
    {"sentences": ["해군은 바다 전체를 뒤집니다.", "그런데 아무것도 나오지 않습니다."]},
    {"sentences": ["그때 한 수학자가 나섭니다.", "베이즈 정리입니다.", "확률로 바다를 칠합니다."]},
]


def _timings(durs_ms: list[int], gap_ms: int = 400) -> list[tuple[int, int]]:
    out, t = [], 0
    for d in durs_ms:
        out.append((t, t + d))
        t += d + gap_ms
    return out


# ── 문장 평탄화 ──────────────────────────────────────────────────
def test_flatten_sentences_keeps_chapter_index_in_order():
    refs = flatten_sentences(CHAPTERS)
    assert [r.chapter for r in refs] == [0, 1, 1, 2, 2, 2]
    assert [r.index for r in refs] == [0, 0, 1, 0, 1, 2]
    assert refs[3].text == "그때 한 수학자가 나섭니다."


def test_flatten_sentences_skips_blank():
    refs = flatten_sentences([{"sentences": ["가나다.", "  "]}])
    assert len(refs) == 1


# ── 줄바꿈 ──────────────────────────────────────────────────────
def test_wrap_lines_short_text_single_line():
    assert wrap_lines("베이즈 정리입니다.") == ("베이즈 정리입니다.",)


def test_wrap_lines_breaks_at_word_boundary_within_width():
    text = "해군은 대서양 바다 전체를 샅샅이 뒤지기 시작합니다"
    lines = wrap_lines(text)
    assert len(lines) >= 2
    assert all(len(line) <= CAPTION_LINE_CHARS for line in lines)
    assert " ".join(lines) == text


def test_wrap_lines_hard_splits_overlong_word():
    lines = wrap_lines("가" * 40)
    assert all(len(line) <= CAPTION_LINE_CHARS for line in lines)
    assert "".join(lines) == "가" * 40


# ── 큐 분할 ──────────────────────────────────────────────────────
def test_split_cues_short_sentence_is_one_cue():
    assert split_cues("베이즈 정리입니다.") == ("베이즈 정리입니다.",)


def test_split_cues_long_sentence_splits_at_comma_first():
    s = "1968년 5월, 미국 해군의 핵잠수함 스콜피온호가 대서양 한가운데에서 갑자기 연락이 끊깁니다."
    cues = split_cues(s)
    assert len(cues) >= 2
    assert cues[0].endswith(",")
    assert " ".join(cues) == s


def test_split_cues_every_cue_fits_three_lines():
    s = "그리고 이 수학자는 바다를 작은 칸으로 나눈 다음 각 칸마다 잠수함이 있을 확률을 하나하나 적어 넣고 수색할 때마다 그 숫자를 고쳐 나갑니다."
    for cue in split_cues(s):
        assert len(wrap_lines(cue)) <= CAPTION_MAX_LINES


# ── 자막 큐 타이밍 ────────────────────────────────────────────────
def test_caption_cues_cover_sentence_span_contiguously():
    s = "1968년 5월, 미국 해군의 핵잠수함 스콜피온호가 대서양 한가운데에서 갑자기 연락이 끊깁니다."
    cues = caption_cues(s, 1000, 7000)
    assert cues[0].start_ms == 1000
    assert cues[-1].end_ms == 7000
    for a, b in zip(cues, cues[1:]):
        assert a.end_ms == b.start_ms
    assert all(1 <= len(c.lines) <= CAPTION_MAX_LINES for c in cues)


# ── 일러스트 슬롯 ────────────────────────────────────────────────
def test_image_slots_one_per_chapter_cut_in_gap_middle():
    t = _timings([3000, 2000, 2000, 2000, 1500, 2500])
    slots = image_slots(CHAPTERS, t)
    assert len(slots) == 3
    assert slots[0].start_ms == 0
    # 챕터 0 끝(3000) ~ 챕터 1 시작(3400) 사이 무음의 가운데
    assert slots[0].end_ms == slots[1].start_ms == 3200
    assert slots[-1].end_ms == t[-1][1]


def test_image_slots_cover_has_no_zoom():
    slots = image_slots(CHAPTERS, _timings([3000, 2000, 2000, 2000, 1500, 2500]))
    assert slots[0].zoom_start_ms is None


def test_image_slots_zoom_defaults_to_second_sentence_start():
    t = _timings([3000, 2000, 6000, 6000, 6000, 6000])
    slots = image_slots(CHAPTERS, t)
    assert slots[2].zoom_start_ms == t[4][0]


def test_image_slots_zoom_at_override_and_clamped_to_slot_end():
    chapters = [CHAPTERS[0], {"sentences": ["가.", "나."], "zoom_at": 1}]
    t = _timings([3000, 4000, 1000])
    slots = image_slots(chapters, t)
    last = slots[-1]
    assert last.zoom_start_ms == last.end_ms - ZOOM_MS


def test_image_slots_motion_false_disables_zoom():
    chapters = [CHAPTERS[0], {"sentences": ["가.", "나."], "motion": False}]
    slots = image_slots(chapters, _timings([3000, 4000, 4000]))
    assert slots[1].zoom_start_ms is None


def test_image_slots_requires_matching_timing_count():
    with pytest.raises(ValueError):
        image_slots(CHAPTERS, _timings([1000, 1000]))


# ── 길이 ────────────────────────────────────────────────────────
def test_estimate_sec_uses_measured_kore_rate_and_speed():
    chars = round(KORE_SYLLABLES_PER_SEC * 10)
    chapters = [{"sentences": ["가" * chars]}]
    assert estimate_sec(chapters, speed=1.0) == pytest.approx(10.0, rel=0.02)
    assert estimate_sec(chapters, speed=2.0) == pytest.approx(5.0, rel=0.02)
    assert estimate_sec(chapters) < estimate_sec(chapters, speed=1.0)  # 기본 1.3배속


def test_scale_timings_divides_by_speed_without_mutating():
    timings = [{"scene_id": 0, "start_ms": 0, "end_ms": 1300},
               {"scene_id": 1, "start_ms": 1300, "end_ms": 2600}]
    scaled = scale_timings(timings, 1.3)
    assert scaled == [{"scene_id": 0, "start_ms": 0, "end_ms": 1000},
                      {"scene_id": 1, "start_ms": 1000, "end_ms": 2000}]
    assert timings[0]["end_ms"] == 1300


def test_length_problems_blocks_over_cap_and_warns_outside_range():
    blocked, warns = length_problems(181.0)
    assert blocked
    blocked, warns = length_problems(150.0)
    assert not blocked and warns
    blocked, warns = length_problems(120.0)
    assert not blocked and not warns
