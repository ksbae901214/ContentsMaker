"""039 Phase 2 — 단어 단위 컷 산출 테스트.

037-2 규칙: `mode: "clip"` 씬은 **문장 끝 단어가 다 발화된 뒤** 끊는다.
어미가 잘리면 시청자가 말이 끊긴 것으로 인지해 이탈한다.
`duration` = 마지막 단어 시작 + 발화 길이(= 다음 단어 시작).
**눈대중·auto-caption 블록 타임스탬프 금지** — 롤링 자막은 문장 경계와 안 맞는다.
"""
import pytest

from scripts.auto_daily.cut_planner import (
    FPS, Cut, Word, build_cuts, parse_word_timestamps, split_sentences, word_end,
)

# 유튜브 자동자막 실제 구조 — 롤링(같은 문장이 다음 큐에 다시 나옴) 포함.
ROLLING_VTT = """WEBVTT
Kind: captions
Language: ko

00:00:00.030 --> 00:00:03.470 align:start position:0%
장동혁<00:00:00.630><c> 대표는</c><00:00:01.230><c> 오늘</c><00:00:02.100><c> 사퇴하겠다고</c>

00:00:03.470 --> 00:00:03.480 align:start position:0%
장동혁 대표는 오늘 사퇴하겠다고

00:00:03.480 --> 00:00:06.500 align:start position:0%
장동혁 대표는 오늘 사퇴하겠다고
밝혔습니다<00:00:04.500><c> 당내</c><00:00:05.100><c> 반발이</c><00:00:05.800><c> 거셉니다</c>
"""


# ── VTT 파싱 ────────────────────────────────────────────────────────
def test_인라인_단어_타임스탬프를_뽑는다():
    words = parse_word_timestamps(ROLLING_VTT)
    assert [w.text for w in words] == [
        "장동혁", "대표는", "오늘", "사퇴하겠다고",
        "밝혔습니다", "당내", "반발이", "거셉니다",
    ]


def test_각_큐의_첫단어는_큐_시작시각을_받는다():
    """첫 단어에는 인라인 태그가 없다 — 빠뜨리면 컷 시작이 밀린다."""
    words = parse_word_timestamps(ROLLING_VTT)
    by_text = {w.text: w.start for w in words}
    assert by_text["장동혁"] == pytest.approx(0.030)
    assert by_text["밝혔습니다"] == pytest.approx(3.480)
    assert by_text["대표는"] == pytest.approx(0.630)


def test_롤링_중복은_한_번만_센다():
    words = parse_word_timestamps(ROLLING_VTT)
    assert [w.text for w in words].count("장동혁") == 1
    assert [w.text for w in words].count("사퇴하겠다고") == 1


def test_시간순으로_정렬된다():
    starts = [w.start for w in parse_word_timestamps(ROLLING_VTT)]
    assert starts == sorted(starts)


def test_자막이_없으면_빈리스트():
    assert parse_word_timestamps("WEBVTT\n\n") == []


def test_시분초_밀리초를_초로_바꾼다():
    vtt = ("WEBVTT\n\n01:02:03.500 --> 01:02:05.000\n"
           "가<01:02:04.250><c> 나</c>\n")
    words = parse_word_timestamps(vtt)
    assert words[0].start == pytest.approx(3723.5)
    assert words[1].start == pytest.approx(3724.25)


# ── 단어 끝 시각 ────────────────────────────────────────────────────
def test_단어의_끝은_다음_단어_시작이다():
    words = [Word(1.0, "가"), Word(1.6, "나")]
    assert word_end(words, 0) == pytest.approx(1.6)


def test_같은_시각_단어는_건너뛰고_다음_시각을_본다():
    """한 큐의 첫 어절이 여러 개면 시작 시각이 같다."""
    words = [Word(1.0, "가"), Word(1.0, "나"), Word(2.0, "다")]
    assert word_end(words, 0) == pytest.approx(2.0)


def test_마지막_단어는_기본_꼬리길이를_붙인다():
    words = [Word(1.0, "끝입니다")]
    assert word_end(words, 0) > 1.0


# ── 문장 분리 ───────────────────────────────────────────────────────
def test_종결어미와_휴지가_함께_있어야_문장이_끝난다():
    words = [Word(0.0, "오늘"), Word(0.5, "사퇴합니다"),   # 0.5→1.5 = 1.0초 휴지
             Word(1.5, "당내"), Word(2.0, "반발이"), Word(2.5, "거셉니다")]
    assert [w.text for w in split_sentences(words)[0]] == ["오늘", "사퇴합니다"]


def test_종결어미여도_휴지가_없으면_이어진다():
    """'중요'처럼 요로 끝나는 일반 어절에서 잘못 끊기는 것을 막는다."""
    words = [Word(0.0, "가장"), Word(0.3, "중요"), Word(0.5, "한"),
             Word(0.8, "것은"), Word(1.1, "신뢰입니다"), Word(2.5, "다음")]
    assert len(split_sentences(words)) == 2


def test_마침표는_휴지_없이도_문장을_끝낸다():
    words = [Word(0.0, "끝났다."), Word(0.2, "다음"), Word(0.5, "문장입니다")]
    assert [w.text for w in split_sentences(words)[0]] == ["끝났다."]


def test_물음표_느낌표도_문장경계다():
    for mark in ("?", "!"):
        words = [Word(0.0, f"맞습니까{mark}"), Word(0.2, "예")]
        assert len(split_sentences(words)) == 2


def test_종결어미가_없으면_통째로_한_문장():
    words = [Word(0.0, "가"), Word(0.3, "나"), Word(0.6, "다람쥐")]
    assert len(split_sentences(words)) == 1


def test_빈_입력은_빈_문장목록():
    assert split_sentences([]) == []


# ── 컷 후보 ─────────────────────────────────────────────────────────
def _sentence_words():
    # 문장1: 0.0~2.5 (2.5초) / 문장2: 2.5~6.0 (3.5초)
    return [
        Word(0.0, "저는"), Word(0.6, "사퇴하지"), Word(1.4, "않습니다"),
        Word(2.5, "당의"), Word(3.2, "결정을"), Word(4.1, "따르겠습니다"),
        Word(6.0, "이상"),
    ]


def test_컷은_문장_끝까지_포함한다():
    cuts = build_cuts(_sentence_words(), min_sec=1.0, max_sec=12.0)
    first = cuts[0]
    assert first.start_sec == pytest.approx(0.0)
    # 마지막 단어('않습니다') 시작 1.4 + 발화 길이(다음 단어 시작 2.5까지)
    assert first.duration == pytest.approx(2.5, abs=1 / FPS)
    assert first.text == "저는 사퇴하지 않습니다"


def test_다음_문장_첫단어가_물려들어가지_않는다():
    cuts = build_cuts(_sentence_words(), min_sec=1.0, max_sec=12.0)
    assert "당의" not in cuts[0].text


def test_duration은_30fps_프레임격자로_반올림된다():
    """씬 경계가 정수 프레임에 안 떨어지면 클립 오디오가 반프레임 밀린다."""
    for cut in build_cuts(_sentence_words(), min_sec=1.0, max_sec=12.0):
        assert cut.duration * FPS == pytest.approx(round(cut.duration * FPS))


def test_상한을_넘는_문장은_후보에서_제외된다():
    """어미를 살리려고 자르면 안 되므로, 못 쓰는 문장은 버린다."""
    long_words = [Word(0.0, "아주"), Word(7.0, "긴문장입니다"), Word(20.0, "끝")]
    assert build_cuts(long_words, min_sec=1.0, max_sec=12.0) == []


def test_하한보다_짧은_문장은_다음_문장과_합친다():
    words = [Word(0.0, "네"), Word(0.4, "맞습니다"),          # 0.9초 — 너무 짧음
             Word(0.9, "그건"), Word(1.6, "사실입니다"), Word(3.0, "끝")]
    cuts = build_cuts(words, min_sec=1.0, max_sec=12.0)
    assert cuts[0].text.startswith("네 맞습니다 그건")
    assert cuts[0].duration >= 1.0


def test_훅용_상한은_더_짧게_줄_수_있다():
    cuts = build_cuts(_sentence_words(), min_sec=1.0, max_sec=3.0)
    assert all(c.duration <= 3.0 for c in cuts)
    assert cuts, "3초 안에 끝나는 문장이 하나는 있어야 한다"


def test_Cut은_불변이다():
    c = Cut(start_sec=0.0, duration=1.0, text="x")
    with pytest.raises(Exception):
        c.duration = 2.0  # type: ignore[misc]


def test_컷_후보에_원문_전사가_남는다():
    """config_drafter 가 자막 문구를 쓸 때 원문이 필요하다."""
    assert build_cuts(_sentence_words(), min_sec=1.0, max_sec=12.0)[0].text
