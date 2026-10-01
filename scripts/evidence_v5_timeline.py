"""V5.0 증거 삽입형 TTS 논평 — 화면 레이어 타임라인 (043 Phase B).

벤치마크(@lkbhop 폴리버스, 현 포맷기 상위 10편) 화면을 이루는 네 겹을 씬 타이밍
위에 배치한다. 시각 계산은 전부 여기서 끝내고 Remotion(EvidenceLayer.tsx)은
받은 ms 구간을 그대로 그린다 — 042 news_v4_timeline 과 같은 분업이다.

  1. **메인 자막** — 주황, 어절 2~4개(≤12자) 단위로 약 1초마다 바뀐다.
     TTS 씬은 나레이션 원문, 육성(clip) 씬은 발언 요지 `text`, CTA 씬은 `text` 한 덩어리.
  2. **강조어 팝업** — 씬의 `pop` 문구를 씬 시작에 초대형으로 잠깐 띄운다 (top8·top9).
  3. **증거 카드** — 씬의 `evidence` 캡처를 씬 구간 내내 카드로 띄우고 밑줄·원으로 짚는다.
  4. **반전 플래시** — `flash: true` 씬의 시작에 0.15초 흰 번쩍임 (시각만, 효과음 없음).

전부 순수 함수 — 렌더 없이 단위 테스트한다.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.news_v4_timeline import chunk_timings, split_caption

# 벤치마크 자막은 '시의원들이 찬양한 날'·'유치한 반말로' 처럼 2~4어절이다.
CAPTION_CHARS = 12
# 강조어는 씬 첫머리에 잠깐 — top8 '지방 사니까' 1.3초, '지역별 차등화!' 2초 실측
POP_MS = 1800
# 헤드라인 2줄 투톤 — 벤치마크는 노랑/시안을 편마다 순서만 바꿔 쓴다.
DEFAULT_HEADLINE_COLORS = ("#FFE14D", "#3FE0F0")
HEADLINE_FONT = "BM Dohyeon"
MARK_KINDS = ("circle", "underline")
# 미디어 프레이밍 — cut_segment 는 16:9 소스를 9:16 에 검정 패딩으로 넣는다. 그대로 두면
# 1080×1280 박스에 영상이 가는 띠로 뜬다. zoom 1.0 = 16:9 화면 높이를 박스 높이에 맞춤
# (벤치마크처럼 얼굴로 꽉 채움), focus_x = 가로로 어디를 보여 줄지(0 왼쪽 ~ 1 오른쪽).
ZOOM_RANGE = (1.0, 3.0)


@dataclass(frozen=True)
class Caption:
    text: str
    start_ms: int
    end_ms: int
    hl: tuple[str, ...]


@dataclass(frozen=True)
class Pop:
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class EvidenceCard:
    path: str
    start_ms: int
    end_ms: int
    marks: tuple[dict, ...]


# ── 헤드라인 ─────────────────────────────────────────────────────────
def headline_lines(cfg: dict) -> list[str]:
    """2줄 헤드라인. 미지정이면 제목 1줄로 폴백 (profile_v3 와 같은 규칙)."""
    head = cfg.get("headline")
    if isinstance(head, str):
        return [ln for ln in head.split("\n") if ln.strip()]
    if isinstance(head, list) and head:
        return [str(ln) for ln in head if str(ln).strip()]
    return [cfg.get("yt_title") or cfg.get("title") or ""]


# ── 자막 ─────────────────────────────────────────────────────────────
def _caption_source(scene: dict) -> str:
    if scene.get("_cta"):
        return scene.get("text") or scene.get("voice", "")
    if scene.get("mode", "tts") == "clip":
        return scene.get("text", "")
    return scene.get("voice", "")


def caption_chunks(scene: dict, start_ms: int, end_ms: int,
                   max_chars: int = CAPTION_CHARS) -> tuple[Caption, ...]:
    """한 씬 → 화면 자막 조각. CTA 는 선택지 2줄을 한 덩어리로 보여 준다."""
    text = _caption_source(scene)
    if not text.strip():
        return ()
    hl = tuple(scene.get("hl", ()))
    if scene.get("_cta"):
        return (Caption(text, start_ms, end_ms, ()),)
    pieces = split_caption(text, max_chars)
    return tuple(
        Caption(p, s, e, tuple(w for w in hl if w in p))
        for p, (s, e) in zip(pieces, chunk_timings(pieces, start_ms, end_ms))
    )


# ── 강조어 / 증거 ─────────────────────────────────────────────────────
def pop_event(scene: dict, start_ms: int, end_ms: int) -> Pop | None:
    text = (scene.get("pop") or "").strip()
    if not text:
        return None
    return Pop(text, start_ms, min(start_ms + POP_MS, end_ms))


def _in_unit(v) -> bool:
    return isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0


def validate_marks(marks: list[dict]) -> None:
    """마커 좌표는 증거 이미지 기준 0~1 정규화 박스여야 한다 (밖으로 나가면 하드 오류)."""
    for i, m in enumerate(marks):
        if m.get("kind") not in MARK_KINDS:
            raise ValueError(f"evidence.marks[{i}] kind={m.get('kind')!r} — 허용: {MARK_KINDS}")
        box = [m.get(k) for k in ("x", "y", "w", "h")]
        if not all(_in_unit(v) for v in box):
            raise ValueError(f"evidence.marks[{i}] x/y/w/h 는 0~1 정규화 값이어야 합니다: {m}")
        x, y, w, h = (float(v) for v in box)
        if x + w > 1.0 or y + h > 1.0:
            raise ValueError(f"evidence.marks[{i}] 박스가 이미지 밖으로 나갑니다: {m}")


def validate_framing(scene: dict) -> None:
    zoom = scene.get("zoom", 1.0)
    focus = scene.get("focus_x", 0.5)
    if not isinstance(zoom, (int, float)) or not ZOOM_RANGE[0] <= zoom <= ZOOM_RANGE[1]:
        raise ValueError(f"zoom={zoom!r} — {ZOOM_RANGE[0]}~{ZOOM_RANGE[1]} 사이 숫자여야 합니다")
    if not _in_unit(focus):
        raise ValueError(f"focus_x={focus!r} — 0~1 사이 숫자여야 합니다 (0 왼쪽 · 1 오른쪽)")


def framing(scene: dict, sid: int) -> dict:
    validate_framing(scene)
    return {"scene_id": sid, "zoom": float(scene.get("zoom", 1.0)),
            "focus_x": float(scene.get("focus_x", 0.5))}


def evidence_card(scene: dict, start_ms: int, end_ms: int) -> EvidenceCard | None:
    ev = scene.get("evidence")
    if not ev or not ev.get("image"):
        return None
    marks = list(ev.get("marks") or [])
    validate_marks(marks)
    return EvidenceCard(str(ev["image"]), start_ms, end_ms, tuple(dict(m) for m in marks))


# ── 조립 ─────────────────────────────────────────────────────────────
def _span(timings: dict[int, dict], sid: int) -> tuple[int, int]:
    t = timings.get(sid)
    if t is None:
        raise ValueError(f"scene {sid} 의 타이밍이 없습니다")
    return int(t["start_ms"]), int(t["end_ms"])


def build_layer(cfg: dict, global_timings: list[dict]) -> dict:
    """씬 타이밍 → renderer.render_video(evidence_layer=...) 에 넘길 snake_case dict."""
    timings = {t["scene_id"]: t for t in global_timings if t["scene_id"] != -1}
    captions, pops, cards, flashes, frames = [], [], [], [], []
    for sid, sc in enumerate(cfg.get("scenes") or []):
        start, end = _span(timings, sid)
        frames.append(framing(sc, sid))
        captions.extend(caption_chunks(sc, start, end))
        pop = pop_event(sc, start, end)
        if pop:
            pops.append(pop)
        card = evidence_card(sc, start, end)
        if card:
            cards.append(card)
        if sc.get("flash"):
            flashes.append(start)
    return {
        "headline": headline_lines(cfg),
        "headline_colors": list(cfg.get("headline_colors") or DEFAULT_HEADLINE_COLORS),
        "captions": [{"text": c.text, "start_ms": c.start_ms, "end_ms": c.end_ms,
                      "hl": list(c.hl)} for c in captions],
        "pops": [{"text": p.text, "start_ms": p.start_ms, "end_ms": p.end_ms} for p in pops],
        "evidence": [{"path": c.path, "start_ms": c.start_ms, "end_ms": c.end_ms,
                      "marks": [dict(m) for m in c.marks]} for c in cards],
        "flashes": flashes,
        "framing": frames,
        "channel_label": cfg.get("channel_label", ""),
        "source_label": cfg.get("source_label", ""),
        "font_family": HEADLINE_FONT,
    }


__all__ = [
    "CAPTION_CHARS", "DEFAULT_HEADLINE_COLORS", "HEADLINE_FONT", "MARK_KINDS", "POP_MS",
    "Caption", "EvidenceCard", "Pop", "build_layer", "caption_chunks", "evidence_card",
    "ZOOM_RANGE", "framing", "headline_lines", "pop_event", "validate_framing",
    "validate_marks",
]
