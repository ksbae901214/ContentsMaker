"""V4.0 사진 슬라이드 타임라인 — 사진 트랙 배치 + 호흡 단위 자막 분할 (042 Phase B).

**사진과 자막은 서로 다른 시계로 돈다.** 벤치마크(@gokorea012, 29.3초) 실측 컷은
0 / 6.93 / 11.47 / 14.87 / 18.27 / 21.67 / 25.07 / 28.43 — 첫 사진은 첫 문장
(사건 요약) 끝까지, 그 뒤는 문장 경계와 무관한 **3.4초 고정 타이머**다. 문장 중간에
사진이 바뀌어도 자막이 이어 주므로 어색하지 않고, 편집 비용이 0에 가깝다.

**자막은 문장이 아니라 호흡 단위(최대 16자)** 로 바뀐다. TTS 는 문장 단위 그대로
합성하고(Gemini 일일 한도 무영향) 화면 자막만 글자 수 비례로 쪼갠다.

전부 순수 함수 — 렌더 없이 단위 테스트한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import cycle

DEFAULT_INTERVAL_MS = 3400      # 벤치마크 실측 컷 간격
MIN_TAIL_MS = 1000              # 이보다 짧은 마지막 컷은 깜빡임 — 앞 컷에 흡수
DEFAULT_CAPTION_CHARS = 16      # 벤치마크 최장 자막 '세월호 참사가 민주당 소행이라는'
FITS = ("cover", "contain")     # contain = SNS·기사 캡처(잘리면 안 읽힌다)
DEFAULT_FIT = "cover"


@dataclass(frozen=True)
class PhotoSlot:
    path: str
    fit: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class CaptionChunk:
    text: str
    start_ms: int
    end_ms: int
    hl: tuple[str, ...]
    color: str


# ── 사진 트랙 ─────────────────────────────────────────────────────
def _dur_ms(photo: dict, default_ms: int) -> int:
    dur = photo.get("dur")
    return int(round(float(dur) * 1000)) if dur else default_ms


def _slot(photo: dict, start_ms: int, end_ms: int) -> PhotoSlot:
    return PhotoSlot(photo["path"], photo.get("fit") or DEFAULT_FIT, start_ms, end_ms)


def photo_schedule(photos: list[dict], first_scene_end_ms: int, total_ms: int,
                   interval_ms: int = DEFAULT_INTERVAL_MS) -> tuple[PhotoSlot, ...]:
    """사진 컷 배치 — 첫 사진은 첫 문장 끝까지, 이후 고정 간격, 빈틈 없이 끝까지.

    사진이 모자라면 `photos[1:]` 을 순환한다. 첫 사진은 보통 사건 요약용 합성
    컷이라 중간에 다시 나오면 영상이 처음으로 돌아간 것처럼 보인다.
    """
    if not photos or total_ms <= 0:
        return ()
    first_end = min(_dur_ms(photos[0], first_scene_end_ms) or interval_ms, total_ms)
    slots = [_slot(photos[0], 0, first_end)]
    rest = cycle(photos[1:] or photos[:1])
    t = first_end
    while t < total_ms:
        photo = next(rest)
        end = min(t + _dur_ms(photo, interval_ms), total_ms)
        slots.append(_slot(photo, t, end))
        t = end
    return _merge_short_tail(slots)


def _merge_short_tail(slots: list[PhotoSlot]) -> tuple[PhotoSlot, ...]:
    if len(slots) < 2:
        return tuple(slots)
    last = slots[-1]
    if last.end_ms - last.start_ms >= MIN_TAIL_MS:
        return tuple(slots)
    prev = slots[-2]
    merged = PhotoSlot(prev.path, prev.fit, prev.start_ms, last.end_ms)
    return (*slots[:-2], merged)


def schedule_warnings(photos: list[dict], slots: tuple[PhotoSlot, ...]) -> list[str]:
    if len(slots) <= len(photos):
        return []
    need = len(slots) - len(photos)
    return [
        f"사진 {len(photos)}장으로 컷 {len(slots)}개를 채워 {need}번 반복됩니다 — "
        f"같은 사진이 다시 나오면 슬라이드가 짧아 보입니다. 사진을 {need}장 더 "
        "넣거나 photos[*].dur 로 컷을 늘리세요"
    ]


# ── 자막 분할 ─────────────────────────────────────────────────────
def _pack_line(words: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}" if cur else w
        if cur and len(cand) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = cand
    return [*chunks, cur] if cur else chunks


def split_caption(text: str, max_chars: int = DEFAULT_CAPTION_CHARS) -> tuple[str, ...]:
    """어절 경계로 max_chars 이하 조각에 채워 넣는다. 줄바꿈은 강제 경계."""
    out: list[str] = []
    for line in text.split("\n"):
        out.extend(_pack_line(line.split(), max_chars))
    return tuple(out)


def chunk_timings(chunks: tuple[str, ...], start_ms: int,
                  end_ms: int) -> tuple[tuple[int, int], ...]:
    """구간을 글자 수(공백 제외) 비례로 나눈다. 끝은 정확히 end_ms."""
    if not chunks:
        return ()
    weights = [max(len(c.replace(" ", "")), 1) for c in chunks]
    total = sum(weights)
    span = end_ms - start_ms
    bounds = [start_ms]
    acc = 0
    for w in weights[:-1]:
        acc += w
        bounds.append(start_ms + round(span * acc / total))
    bounds.append(end_ms)
    return tuple(zip(bounds, bounds[1:]))


def caption_chunks_for_scene(scene: dict, start_ms: int, end_ms: int,
                             max_chars: int = DEFAULT_CAPTION_CHARS
                             ) -> tuple[CaptionChunk, ...]:
    """한 문장 씬 → 화면 자막 조각들.

    일반 씬은 **나레이션 그대로**(벤치마크 번인 자막 = 낭독 원문). CTA 씬만
    `text`(2줄 'A / VS B')를 한 덩어리로 보여 준다.
    """
    color = scene.get("color", "white")
    hl = tuple(scene.get("hl", ()))
    if scene.get("_cta"):
        text = scene.get("text") or scene.get("voice", "")
        return (CaptionChunk(text, start_ms, end_ms, (), color),)
    pieces = split_caption(scene.get("voice", ""), max_chars)
    spans = chunk_timings(pieces, start_ms, end_ms)
    return tuple(
        CaptionChunk(p, s, e, tuple(w for w in hl if w in p), color)
        for p, (s, e) in zip(pieces, spans)
    )


__all__ = [
    "DEFAULT_CAPTION_CHARS", "DEFAULT_FIT", "DEFAULT_INTERVAL_MS", "FITS",
    "MIN_TAIL_MS", "CaptionChunk", "PhotoSlot", "caption_chunks_for_scene",
    "chunk_timings", "photo_schedule", "schedule_warnings", "split_caption",
]
