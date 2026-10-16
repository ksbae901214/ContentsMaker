"""정보쇼츠 V1.0 타임라인 — 챕터별 일러스트 컷 + 줌 시점 + 자막 큐 분할 (045).

벤치마크(@hamster.743606, 공개 12편 실측):
  - **일러스트 1장 = 챕터 1개.** 컷은 챕터 사이 무음의 한가운데서 하드컷한다.
  - 챕터 0 은 커버(피사체 컷아웃)라 정지, 이후 장마다 **3.5초 줌이 딱 한 번** —
    그 장면을 묘사하는 문장이 시작될 때 들어간다(80번 중 78번이 0.3초 안).
  - 자막 큐 1개 = 문장 또는 쉼표 절 1개, 줄당 약 17자, 최대 3줄, 폭 기준 줄바꿈.
  - 말 속도 약 8.2음절/초, 상위 편 길이 99~135초.
    Gemini Kore 는 1.0배에 5.6음절/초라 기본 1.3배속으로 당긴다(파일럿 실측).

V4.0(`news_v4_timeline`)과 코드를 공유하지 않는다 — 사진이 고정 타이머로 넘어가는
V4.0 과 달리 이 포맷은 컷이 챕터(=TTS 덩어리) 경계에 묶여 있어 시계가 하나다.

전부 순수 함수 — 렌더 없이 단위 테스트한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

CAPTION_LINE_CHARS = 17      # 실측 줄당 16~17자 (1080 폭, 57px)
CAPTION_MAX_LINES = 3
CUE_MAX_CHARS = 34           # 공백 포함 — 실측 큐당 24~31자(공백 제외)
ZOOM_MS = 3500               # 실측 모션 버스트 길이
BENCH_SYLLABLES_PER_SEC = 8.2   # 벤치마크 실측 11/12편 8.0~8.4 — 목표 속도
KORE_SYLLABLES_PER_SEC = 5.63   # Gemini Kore 1.0배 실측 (파일럿 673자 / 119.6초, 2026-10-14)
DEFAULT_TTS_SPEED = 1.3         # Kore ×1.3 ≈ 7.3음절/초 — 벤치마크 쪽으로 당긴다
MAX_FINAL_SEC = 180.0        # 차단 — 인스타·쇼츠 3분 상한
RECOMMENDED_MIN_SEC = 95.0
RECOMMENDED_MAX_SEC = 135.0  # 150초 이상은 하위 편에만 있었다

_CLAUSE_RE = re.compile(r"(?<=,)\s+")


@dataclass(frozen=True)
class SentenceRef:
    chapter: int
    index: int
    text: str


@dataclass(frozen=True)
class CaptionCue:
    lines: tuple[str, ...]
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class ImageSlot:
    chapter: int
    start_ms: int
    end_ms: int
    zoom_start_ms: int | None


# ── 문장 ────────────────────────────────────────────────────────
def flatten_sentences(chapters: list[dict]) -> tuple[SentenceRef, ...]:
    """챕터 → 문장 순서대로 평탄화. 빈 문장은 TTS 에 들어가지 않으므로 뺀다."""
    return tuple(
        SentenceRef(ci, si, text.strip())
        for ci, ch in enumerate(chapters)
        for si, text in enumerate(ch.get("sentences") or [])
        if text and text.strip()
    )


# ── 자막 ────────────────────────────────────────────────────────
def _hard_split(word: str, width: int) -> list[str]:
    return [word[i:i + width] for i in range(0, len(word), width)]


def wrap_lines(text: str, width: int = CAPTION_LINE_CHARS) -> tuple[str, ...]:
    """어절 경계 기준 탐욕적 줄바꿈. 폭보다 긴 어절은 글자 단위로 자른다."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        for piece in _hard_split(word, width) if len(word) > width else [word]:
            candidate = f"{current} {piece}" if current else piece
            if len(candidate) <= width:
                current = candidate
            else:
                lines.append(current)
                current = piece
    if current:
        lines.append(current)
    return tuple(lines)


def _split_by_words(text: str, max_chars: int) -> list[str]:
    out: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            out.append(current)
            current = word
    if current:
        out.append(current)
    return out


def split_cues(sentence: str, max_chars: int = CUE_MAX_CHARS) -> tuple[str, ...]:
    """문장 → 자막 큐. 짧으면 그대로, 길면 쉼표 절 우선, 그래도 길면 어절 단위.

    쉼표 절끼리는 합칠 수 있지만, 쪼개진 긴 절의 조각과는 합치지 않는다 —
    쉼표에서 큐가 바뀌어야 나레이션 호흡과 맞는다.
    """
    sentence = " ".join(sentence.split())
    if len(sentence) <= max_chars:
        return (sentence,)
    cues: list[str] = []
    pending = ""
    for clause in _CLAUSE_RE.split(sentence):
        if len(clause) > max_chars:
            if pending:
                cues.append(pending)
                pending = ""
            cues.extend(_split_by_words(clause, max_chars))
            continue
        candidate = f"{pending} {clause}" if pending else clause
        if len(candidate) <= max_chars:
            pending = candidate
        else:
            cues.append(pending)
            pending = clause
    if pending:
        cues.append(pending)
    return tuple(cues)


def caption_cues(sentence: str, start_ms: int, end_ms: int) -> tuple[CaptionCue, ...]:
    """문장 구간을 큐 글자 수(공백 제외) 비례로 나눈다. 빈틈 없이 이어진다."""
    texts = split_cues(sentence)
    weights = [max(1, len(t.replace(" ", ""))) for t in texts]
    total = sum(weights)
    span = end_ms - start_ms
    cues: list[CaptionCue] = []
    t = start_ms
    acc = 0
    for i, (text, w) in enumerate(zip(texts, weights)):
        acc += w
        end = end_ms if i == len(texts) - 1 else start_ms + round(span * acc / total)
        cues.append(CaptionCue(wrap_lines(text), t, end))
        t = end
    return tuple(cues)


# ── 일러스트 슬롯 ────────────────────────────────────────────────
def _chapter_ranges(refs: tuple[SentenceRef, ...], n_chapters: int) -> list[tuple[int, int]]:
    ranges = []
    for c in range(n_chapters):
        idx = [i for i, r in enumerate(refs) if r.chapter == c]
        if not idx:
            raise ValueError(f"챕터 {c} 에 문장이 없습니다")
        ranges.append((idx[0], idx[-1]))
    return ranges


def _zoom_start(chapter: dict, ci: int, first: int, last: int,
                timings: list[tuple[int, int]], slot: tuple[int, int]) -> int | None:
    if ci == 0 or chapter.get("motion") is False:
        return None
    n = last - first + 1
    at = int(chapter.get("zoom_at", 1 if n >= 2 else 0))
    at = max(0, min(at, n - 1))
    start = timings[first + at][0]
    return max(slot[0], min(start, slot[1] - ZOOM_MS))


def image_slots(chapters: list[dict],
                timings: list[tuple[int, int]]) -> tuple[ImageSlot, ...]:
    """챕터별 일러스트 노출 구간 + 줌 시작 시점.

    timings: `flatten_sentences` 순서의 문장별 (start_ms, end_ms).
    """
    refs = flatten_sentences(chapters)
    if len(refs) != len(timings):
        raise ValueError(f"문장 {len(refs)}개 ≠ 타이밍 {len(timings)}개")
    ranges = _chapter_ranges(refs, len(chapters))
    total_ms = timings[-1][1]
    bounds = [0] + [
        (timings[ranges[c - 1][1]][1] + timings[ranges[c][0]][0]) // 2
        for c in range(1, len(chapters))
    ] + [total_ms]
    slots = []
    for ci, (first, last) in enumerate(ranges):
        span = (bounds[ci], bounds[ci + 1])
        zoom = _zoom_start(chapters[ci], ci, first, last, timings, span)
        slots.append(ImageSlot(ci, span[0], span[1], zoom))
    return tuple(slots)


# ── 길이 ────────────────────────────────────────────────────────
def estimate_sec(chapters: list[dict], speed: float = DEFAULT_TTS_SPEED) -> float:
    """글자 수(공백 제외) 기반 나레이션 길이 추정 — validate 단계용 (Kore 실측 속도 기준)."""
    chars = sum(len(r.text.replace(" ", "")) for r in flatten_sentences(chapters))
    return chars / KORE_SYLLABLES_PER_SEC / speed


def scale_timings(timings: list[dict], speed: float) -> list[dict]:
    """오디오를 speed 배속했을 때의 타이밍 — 새 리스트를 만든다."""
    return [{**t, "start_ms": round(t["start_ms"] / speed),
             "end_ms": round(t["end_ms"] / speed)} for t in timings]


def length_problems(sec: float) -> tuple[bool, tuple[str, ...]]:
    """(차단 여부, 경고들). 180초 초과는 차단, 권장 범위 밖은 경고."""
    if sec > MAX_FINAL_SEC:
        return True, (f"길이 {sec:.1f}초 > 상한 {MAX_FINAL_SEC:.0f}초 — 챕터를 줄이세요",)
    if sec > RECOMMENDED_MAX_SEC:
        return False, (f"길이 {sec:.1f}초 — 벤치마크 하위 편 구간(>{RECOMMENDED_MAX_SEC:.0f}초)",)
    if sec < RECOMMENDED_MIN_SEC:
        return False, (f"길이 {sec:.1f}초 — 권장 {RECOMMENDED_MIN_SEC:.0f}~{RECOMMENDED_MAX_SEC:.0f}초보다 짧음",)
    return False, ()
