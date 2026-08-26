"""039 Phase 2 — 자동자막 단어 타임스탬프로 '말 끝맺음' 컷 산출 (037-2).

`political_v2_configs/README.md` 437행의 bash 절차를 모듈화한 것이다. 무인 운영은
사람이 파형을 보고 끊을 수 없으니, 그 판단을 재현 가능한 규칙으로 바꾼다.

**규칙**
  - 컷은 **문장 끝 단어가 다 발화된 뒤** 끊는다. 어미가 잘리면("…맞고 있") 시청자가
    말이 끊긴 것으로 인지해 이탈한다.
  - `duration` = 마지막 단어 시작 + 발화 길이(= **다음 단어 시작 시각**).
  - 다음 문장 첫 단어가 물려 들어가면 안 된다 — 0.2초라도 엉뚱한 음절이 붙어
    들리면 잘린 것만큼 어색하다.
  - **블록(큐) 타임스탬프를 쓰지 않는다.** 롤링 자막은 문장 경계와 안 맞는다.

한국어 자동자막에는 문장부호가 없다. 그래서 문장 끝은 **종결어미 + 휴지**를 함께
본다 — 어미만 보면 '중요'(요로 끝남) 같은 어절에서 잘못 끊긴다.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

FPS = 30                    # Remotion 컴포지션 프레임레이트 — 씬 경계 격자
DEFAULT_TAIL_SEC = 0.6      # 마지막 단어의 발화 길이 추정치 (다음 단어가 없을 때)
MIN_PAUSE_SEC = 0.30        # 문장 경계로 인정할 최소 휴지
#: 한국어 낭독 속도 실측 중앙값. 035 길이 게이트와 같은 값을 쓴다 — 두 곳이
#: 갈라지면 컷 길이와 길이 캡 추정이 서로 안 맞는다.
CHARS_PER_SEC = 7.4
SENTENCE_MARKS = (".", "?", "!", "…")

#: 한국어 종결어미. 휴지와 **함께** 성립해야 문장 끝으로 본다.
SENTENCE_ENDINGS = (
    "습니다", "합니다", "입니다", "됩니다", "십니다", "ㅂ니다", "니다",
    "세요", "네요", "군요", "거든요", "잖아요", "인데요", "고요", "죠", "요",
    "겠다", "한다", "된다", "이다", "았다", "었다", "간다", "온다", "니까",
    "습니까", "입니까", "까요", "다", "까",
)

_CUE_RE = re.compile(
    r"^(\d\d):(\d\d):(\d\d)\.(\d{1,3})\s*-->\s*\d\d:\d\d:\d\d\.\d{1,3}",
    re.MULTILINE,
)
_INLINE_RE = re.compile(r"<(\d\d):(\d\d):(\d\d)\.(\d{1,3})><c>([^<]*)</c>")
_TAG_RE = re.compile(r"<[^>]*>")


@dataclass(frozen=True)
class Word:
    """자막 어절 하나와 그 시작 시각(초)."""

    start: float
    text: str


@dataclass(frozen=True)
class Cut:
    """클립 씬 후보. `duration` 은 이미 프레임 격자에 맞춰져 있다."""

    start_sec: float
    duration: float
    text: str

    @property
    def end_sec(self) -> float:
        return self.start_sec + self.duration

    def to_dict(self) -> dict:
        return {"start_sec": round(self.start_sec, 3),
                "duration": round(self.duration, 3), "text": self.text}


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def quantize(duration: float) -> float:
    """30fps 격자로 반올림. 반프레임(±17ms) 밀리면 립싱크가 어긋난다."""
    return round(duration * FPS) / FPS


def parse_word_timestamps(vtt_text: str) -> list[Word]:
    """VTT → 단어 단위 Word 목록 (시간순, 롤링 중복 제거).

    큐의 **첫 어절에는 인라인 태그가 없다** — 큐 시작 시각을 준다. 이걸 빠뜨리면
    컷 시작이 한 어절씩 밀린다.
    """
    seen: set[tuple[float, str]] = set()
    words: list[Word] = []

    for block in _split_cues(vtt_text):
        cue_start, body = block
        head, _, _ = body.partition("<")
        for token in head.split():
            _append(words, seen, Word(cue_start, _TAG_RE.sub("", token).strip()))
        for m in _INLINE_RE.finditer(body):
            start = _to_seconds(*m.group(1, 2, 3, 4))
            for token in m.group(5).split():
                _append(words, seen, Word(start, token.strip()))

    return sorted(words, key=lambda w: w.start)


def _split_cues(vtt_text: str) -> list[tuple[float, str]]:
    """(큐 시작 초, 큐 본문) 목록. 인라인 태그가 없는 롤링 큐는 버린다."""
    cues, matches = [], list(_CUE_RE.finditer(vtt_text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(vtt_text)
        body = vtt_text[m.end():end].strip()
        if "<c>" not in body:
            continue                    # 타임스탬프 없는 롤링 반복 — 정보 없음
        # 마지막 줄만 새 내용이다. 앞줄은 직전 큐의 잔상.
        cues.append((_to_seconds(*m.group(1, 2, 3, 4)),
                     body.splitlines()[-1].strip()))
    return cues


def _append(words: list[Word], seen: set, word: Word) -> None:
    key = (round(word.start, 3), word.text)
    if word.text and key not in seen:
        seen.add(key)
        words.append(word)


def word_end(words: list[Word], index: int) -> float:
    """단어 i 의 발화 끝 = **다음 단어의 시작**. 같은 시각은 건너뛴다."""
    current = words[index].start
    for nxt in words[index + 1:]:
        if nxt.start > current:
            return nxt.start
    return current + DEFAULT_TAIL_SEC


def pause_after(words: list[Word], index: int) -> float:
    """단어 뒤 휴지(초) 추정.

    자동자막은 단어의 **시작**만 준다. 그래서 '다음 단어 시작 - 이 단어 시작'
    이라는 슬롯 길이에서 글자 수로 추정한 발화 시간을 빼 휴지를 얻는다.
    (`word_end` 를 그대로 빼면 정의상 항상 0이다.)
    """
    slot = word_end(words, index) - words[index].start
    return slot - len(words[index].text) / CHARS_PER_SEC


def _is_sentence_end(words: list[Word], index: int) -> bool:
    text = words[index].text
    if text.endswith(SENTENCE_MARKS):
        return True
    if not text.endswith(SENTENCE_ENDINGS):
        return False
    if index + 1 >= len(words):
        return True
    # 어미만으로는 부족하다 — 휴지가 있어야 진짜 문장 끝이다.
    # ('중요'처럼 요로 끝나는 일반 어절에서 잘못 끊기는 것을 막는다.)
    return pause_after(words, index) >= MIN_PAUSE_SEC


def split_sentences(words: list[Word]) -> list[list[Word]]:
    """종결어미 + 휴지(또는 문장부호)로 문장 단위 분리."""
    sentences: list[list[Word]] = []
    current: list[Word] = []
    for i, word in enumerate(words):
        current.append(word)
        if _is_sentence_end(words, i):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences


def _cut_from(words: list[Word], sentence: list[Word]) -> Cut:
    """문장 하나(또는 연속 문장 묶음) → Cut. 끝은 마지막 단어의 발화 끝."""
    last_index = words.index(sentence[-1])
    start = sentence[0].start
    duration = quantize(word_end(words, last_index) - start)
    return Cut(start_sec=start, duration=duration,
               text=" ".join(w.text for w in sentence))


def build_cuts(words: list[Word], *, min_sec: float = 1.0,
               max_sec: float = 12.0) -> list[Cut]:
    """문장 경계 컷 후보 목록.

    - 상한을 넘는 문장은 **버린다** — 어미를 살리려면 중간에서 못 자른다.
    - 하한보다 짧으면 다음 문장을 붙여 늘린다.
    """
    if not words:
        return []

    cuts, buffer = [], []
    for sentence in split_sentences(words):
        buffer.extend(sentence)
        cut = _cut_from(words, buffer)
        if cut.duration > max_sec:
            buffer = []                 # 통째로 못 쓴다 — 다음 문장부터 다시
            continue
        if cut.duration >= min_sec:
            cuts.append(cut)
            buffer = []
    return cuts


def fetch_auto_subs(url: str, out_dir: Path, key: str,
                    *, runner=subprocess.run) -> Path | None:
    """yt-dlp 로 한국어 자동자막만 받는다. 실패는 None.

    403/포맷없음은 버전이나 player_client 문제가 아니라 챌린지 솔버 부재다 —
    `--remote-components ejs:github` 로 푼다 (`[[ytdlp-youtube-403-ejs]]`).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp", url, "--skip-download", "--write-auto-subs",
        "--sub-langs", "ko", "--convert-subs", "vtt",
        "--remote-components", "ejs:github",
        "-o", str(out_dir / key),
    ]
    result = runner(cmd, capture_output=True, text=True)
    if getattr(result, "returncode", 1) != 0:
        return None
    return next(iter(sorted(out_dir.glob(f"{key}*.vtt"))), None)
