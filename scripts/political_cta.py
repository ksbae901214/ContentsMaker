"""정치쇼츠 중반 CTA (035) — 댓글 유도를 40% 지점으로, 편 가르기 질문으로.

**근거 (채널 실측 2026-08-05, 최근 18편)**: 조회 19,835회에 좋아요 507(2.56%),
댓글 47(0.24%). 쇼츠 건강 기준(좋아요 4~5%, 댓글 0.5~1%)의 절반 이하다.
CTA가 마지막 씬에 있어 도달 자체가 안 되고, "여러분 생각은 어떠신가요?" 같은
열린 질문은 편이 갈리지 않아 답글이 붙지 않는다.

처방: ① CTA를 별도 짧은 tts 씬으로 떼어 **40% 지점**에 삽입,
② 질문을 **선택지형(①/②·누구 잘못·어느 쪽)** 으로 강제(미달 시 경고),
③ 마지막 씬에 남은 "댓글로…" 잔존 문구를 경고로 잡아 중복 제거.

config 예시:
```json
"cta": {
  "text": "이거 누구 잘못?\\n① 조국  ② 이준석",
  "voice": "이건 누구 잘못일까요? 1번, 2번 댓글로 남겨주세요.",
  "hl": ["누구 잘못"]
}
```
"""
from __future__ import annotations

from scripts.political_length import (
    estimate_tts_sec, hook_offset_sec, scene_duration_estimates,
)

DEFAULT_CTA_AT_FRAC = 0.4       # 040 지점 — 스와이프 이탈 전, 초반 훅 직후
CTA_MAX_SEC = 4.0               # CTA 씬 권장 상한 — 2지선다 낭독 1회분 (길이 캡 잠식 방지)

# 댓글 유도 문구 — 일반 씬에 남아 있으면 중복 CTA
CTA_PHRASES = ("댓글", "덧글")
# 편이 갈리는 질문 신호 — 하나라도 있으면 선택지형으로 인정
SIDE_PICK_MARKERS = (
    "①", "②", "③", "1번", "2번", "3번", "몇 번",
    "누구 잘못", "누가 잘못", "누구 편", "누가 더", "누가 맞",
    "어느 쪽", "어느 편", "어느 쪽이", "찬성", "반대", "vs", "VS",
)


def is_side_picking(text: str) -> bool:
    """편이 갈리는(선택지형) 질문인지 — 일반 열린 질문과 구분."""
    return any(m in (text or "") for m in SIDE_PICK_MARKERS)


def lint_cta(cta: dict, category: str = "political") -> list[str]:
    """CTA 블록 권장 위반 경고 (하드 오류 아님).

    036: 안내 예시는 카테고리별 (경제 '① 이득 ② 손해', 사회 '① 약하다 ② 적당하다').
    """
    from scripts.shorts_domain import rules_for
    warnings = []
    text, voice = (cta or {}).get("text", ""), (cta or {}).get("voice", "")
    if not text:
        warnings.append("cta.text(화면 자막) 누락")
    if not voice:
        warnings.append("cta.voice(나레이션) 누락")
    if (text or voice) and not is_side_picking(f"{text} {voice}"):
        warnings.append(
            "CTA가 열린 질문 — 편 가르는 선택지형으로 바꾸세요 "
            f"(예: '{rules_for(category).cta_example}'). "
            "열린 질문은 실측상 댓글율 0.24%로 답글이 안 붙습니다 (035)")
    est = estimate_tts_sec(len(voice))
    if est > CTA_MAX_SEC:
        warnings.append(
            f"CTA 나레이션 {est:.1f}초 — {CTA_MAX_SEC:.0f}초 이내로 짧게 "
            "(본편 길이 캡을 잠식합니다)")
    return warnings


def cta_insert_index(
    durations: list[float],
    at_frac: float = DEFAULT_CTA_AT_FRAC,
    prefix_sec: float = 0.0,
) -> int:
    """CTA를 끼워 넣을 씬 인덱스 — 누적 시간이 at_frac 지점에 가장 가까운 경계.

    scene[0](훅) 앞과 마지막 씬 뒤는 제외 — 훅 보호 + 말미 CTA 회귀 방지.
    """
    n = len(durations)
    if n < 2:
        return n
    total = prefix_sec + sum(durations)
    target = at_frac * total
    best, best_gap = 1, None
    cumulative = prefix_sec
    for j in range(1, n):
        cumulative += durations[j - 1]
        gap = abs(cumulative - target)
        if best_gap is None or gap < best_gap:
            best, best_gap = j, gap
    return best


def build_cta_scene(cta: dict, neighbor: dict) -> dict:
    """CTA를 tts 씬 dict 로 변환. 소스·frac 은 이웃 씬에서 상속."""
    return {
        "mode": "tts",
        "type": "body",
        "source": cta.get("source") or neighbor.get("source"),
        "frac": cta.get("frac", neighbor.get("frac", 0.4)),
        "color": cta.get("color", "yellow"),
        "emph": True,
        "text": cta.get("text", ""),
        "voice": cta.get("voice", ""),
        "hl": list(cta.get("hl", ())),
        "_cta": True,
    }


def apply_cta(cfg: dict) -> dict:
    """cfg["cta"] 를 40% 지점의 tts 씬으로 삽입한 **새 cfg** 반환 (불변)."""
    cta = cfg.get("cta")
    scenes = cfg.get("scenes")
    if not cta or not isinstance(scenes, list) or not scenes:
        return cfg
    idx = cta_insert_index(
        scene_duration_estimates(cfg),
        at_frac=float(cta.get("at_frac", DEFAULT_CTA_AT_FRAC)),
        prefix_sec=hook_offset_sec(cfg),
    )
    idx = max(1, min(idx, len(scenes)))
    scene = build_cta_scene(cta, scenes[idx - 1])
    return {**cfg, "scenes": [*scenes[:idx], scene, *scenes[idx:]]}


def trailing_cta_warnings(cfg: dict) -> list[str]:
    """일반 씬에 남은 댓글 유도 문구 감지 — 중반 CTA와 중복되면 힘이 분산된다."""
    warnings = []
    for i, sc in enumerate(cfg.get("scenes") or []):
        if sc.get("_cta"):
            continue
        voice = sc.get("voice", "")
        if any(p in voice for p in CTA_PHRASES):
            warnings.append(
                f"scene[{i}] 나레이션에 댓글 유도 문구 잔존 — "
                "cta 블록으로 옮기세요 (CTA는 40% 지점 1회만, 035)")
    return warnings


__all__ = [
    "CTA_MAX_SEC", "CTA_PHRASES", "DEFAULT_CTA_AT_FRAC", "SIDE_PICK_MARKERS",
    "apply_cta", "build_cta_scene", "cta_insert_index", "is_side_picking",
    "lint_cta", "trailing_cta_warnings",
]
