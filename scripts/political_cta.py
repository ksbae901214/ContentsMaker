"""정치쇼츠 CTA — 편 가르기 질문으로 댓글 유도 (035, 038).

**근거 (채널 실측 2026-08-05, 당시 최근 18편)**: 조회 19,835회에 좋아요 507
(2.56%), 댓글 47(0.24%). 쇼츠 건강 기준(좋아요 4~5%, 댓글 0.5~1%)의 절반 이하다.
당시 "CTA가 마지막 씬에 있어 도달 자체가 안 된다"고 보고 **40% 지점**으로
옮겼었다. **038(2026-08-25, 사용자 지시)로 다시 마지막 씬으로 되돌렸다** —
영상 중간에 CTA가 끼어드는 게 시청 흐름을 끊는다는 판단. 되돌린 뒤 댓글율을
다시 확인해볼 것(강제 아님). "여러분 생각은 어떠신가요?" 같은 열린 질문은
위치와 무관하게 편이 갈리지 않아 답글이 붙지 않으므로 ②는 그대로 유지한다.

처방: ① CTA를 별도 짧은 tts 씬으로 떼어 **마지막 씬 뒤**에 삽입(038),
② 질문을 **선택지형(①/②·누구 잘못·어느 쪽)** 으로 강제(미달 시 경고),
③ 마지막 씬(CTA 삽입 전 기준)에 남은 "댓글로…" 잔존 문구를 경고로 잡아 중복 제거,
④ 나레이션을 **"댓글로 알려주세요"** 로 닫기(미달 시 경고, 사용자 지시 2026-08-18).

④는 말투 규칙이다. CTA는 영상에서 유일하게 시청자에게 직접 말을 거는 문장인데
"번호로 답글." 같은 명사형·반말 종결은 지시처럼 들린다. 채널 톤은 존댓말이므로
CTA도 존댓말로 닫는다.

config 예시:
```json
"cta": {
  "text": "이거 누구 잘못?\\n① 조국  ② 이준석",
  "voice": "누구 잘못일까요? 1번 조국, 2번 이준석. 댓글로 알려주세요.",
  "hl": ["누구 잘못"]
}
```
"""
from __future__ import annotations

from scripts.political_length import estimate_tts_sec

DEFAULT_CTA_AT_FRAC = 0.4       # 038: apply_cta는 더 이상 이 값을 쓰지 않음(항상 마지막
                                 # 씬 뒤 삽입) — cta_insert_index()의 기본 인자로만 남음
CTA_MAX_SEC = 4.0               # CTA 씬 권장 상한 — 2지선다 낭독 1회분 (길이 캡 잠식 방지)

# 댓글 유도 문구 — 일반 씬에 남아 있으면 중복 CTA
CTA_PHRASES = ("댓글", "덧글")
# 편이 갈리는 질문 신호 — 하나라도 있으면 선택지형으로 인정
SIDE_PICK_MARKERS = (
    "①", "②", "③", "1번", "2번", "3번", "몇 번",
    "누구 잘못", "누가 잘못", "누구 편", "누가 더", "누가 맞",
    "어느 쪽", "어느 편", "어느 쪽이", "찬성", "반대", "vs", "VS",
)


# CTA 나레이션 종결 문구 (사용자 지시 2026-08-18) — 존댓말로 닫는다.
CTA_CLOSING = "댓글로 알려주세요"
# 씬으로 직접 쓴 CTA를 자막에서 알아보는 신호 (선택지 기호만 — 오탐 방지)
CTA_SCENE_MARKERS = ("①", "②", "③", "1번", "2번", "3번")


def is_side_picking(text: str) -> bool:
    """편이 갈리는(선택지형) 질문인지 — 일반 열린 질문과 구분."""
    return any(m in (text or "") for m in SIDE_PICK_MARKERS)


def lint_cta_closing(voice: str) -> list[str]:
    """CTA 나레이션이 존댓말 종결로 닫히는지.

    CTA는 영상에서 유일하게 시청자에게 직접 말을 거는 문장이라, "번호로 답글."
    같은 명사형·반말 종결은 지시처럼 들린다. 채널 톤에 맞춰 존댓말로 닫는다.
    """
    if not voice or CTA_CLOSING in voice:
        return []
    return [f'CTA 나레이션을 "{CTA_CLOSING}"로 닫으세요 — 반말·명사형 종결'
            f'("번호로 답글." 등)은 지시처럼 들립니다 (사용자 지시 2026-08-18). '
            f'현재: "{voice[-20:]}"']


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
    warnings.extend(lint_cta_closing(voice))
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

    038: `apply_cta()`는 이제 이 함수를 쓰지 않는다(항상 마지막 씬 뒤에 삽입).
    frac 기반 중반 삽입이 다시 필요해지는 경우를 위해 로직만 보존한다.
    scene[0](훅) 앞과 마지막 씬 뒤는 제외 — 훅 보호 + 중반 삽입 시 말미 회귀 방지.
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
    """cfg["cta"] 를 **마지막 씬 뒤**의 tts 씬으로 삽입한 **새 cfg** 반환 (불변, 038).

    035에서 쓰던 40% 지점 삽입(`cta_insert_index`)은 더 이상 쓰지 않는다 —
    사용자 지시(2026-08-25)로 CTA는 항상 영상 맨 끝에 온다.
    """
    cta = cfg.get("cta")
    scenes = cfg.get("scenes")
    if not cta or not isinstance(scenes, list) or not scenes:
        return cfg
    scene = build_cta_scene(cta, scenes[-1])
    return {**cfg, "scenes": [*scenes, scene]}


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
                "cta 블록으로 옮기세요 (CTA는 마지막 씬 1회만, 035/038)")
    return warnings


def scene_cta_closing_warnings(cfg: dict) -> list[str]:
    """씬으로 **직접 쓴** CTA의 종결 검사.

    2026-08-14 지시 이후 CTA를 top-level `cta` 블록이 아니라 마지막 씬에 직접
    쓰는 config 가 표준이 됐다. `lint_cta` 는 블록만 보므로 그 경로가 검사에서
    통째로 빠진다 — 이 함수가 그 구멍을 메운다.

    오탐을 줄이려고 자막에 선택지 기호(①/1번…)가 박힌 씬만 CTA로 본다.
    나레이션에 '찬성/반대' 같은 단어가 스쳐 지나가는 일반 씬은 걸리지 않는다.
    """
    warnings = []
    for i, sc in enumerate(cfg.get("scenes") or []):
        if sc.get("_cta"):      # 블록에서 삽입된 씬은 lint_cta 가 이미 본다
            continue
        if not any(m in (sc.get("text") or "") for m in CTA_SCENE_MARKERS):
            continue
        warnings.extend(f"scene[{i}] {w}" for w in lint_cta_closing(sc.get("voice", "")))
    return warnings


__all__ = [
    "CTA_CLOSING", "CTA_MAX_SEC", "CTA_PHRASES", "CTA_SCENE_MARKERS",
    "DEFAULT_CTA_AT_FRAC", "SIDE_PICK_MARKERS",
    "apply_cta", "build_cta_scene", "cta_insert_index", "is_side_picking",
    "lint_cta", "lint_cta_closing", "scene_cta_closing_warnings",
    "trailing_cta_warnings",
]
