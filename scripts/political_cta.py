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
④ 나레이션을 **"댓글로 알려주세요"** 로 닫기(미달 시 경고, 사용자 지시 2026-08-18),
⑤ 나레이션이 **질문까지 읽기**(미달 시 경고, 사용자 지시 2026-09-17).

④는 말투 규칙이다. CTA는 영상에서 유일하게 시청자에게 직접 말을 거는 문장인데
"번호로 답글." 같은 명사형·반말 종결은 지시처럼 들린다. 채널 톤은 존댓말이므로
CTA도 존댓말로 닫는다.

⑤는 035를 뒤집은 것이다. 035는 "질문은 화면 자막이 이미 보여주니 나레이션에선
빼고 선택지만 읽는다"였는데(4초 상한을 아끼려는 판단), 그러면 소리만 듣는
시청자에게는 "1번 노인, 2번 여성"만 들려 **무엇을 고르라는 건지 알 수 없다.**
질문 낭독을 고정 지침으로 올리면서 상한도 4.0 → 5.0초로 함께 올렸다.

config 예시:
```json
"cta": {
  "text": "이거 누구 잘못?\\n① 조국  ② 이준석",
  "voice": "이건 누가 잘못한 걸까요? 1번 조국, 2번 이준석. 댓글로 알려주세요.",
  "hl": ["누구 잘못"]
}
```
"""
from __future__ import annotations

from scripts.political_length import estimate_tts_sec
from scripts.shorts_format import (
    CTA_STYLE_PICK,
    CTA_STYLE_SUBSCRIBE,
    rules_for_config,
)

DEFAULT_CTA_AT_FRAC = 0.4       # 038: apply_cta는 더 이상 이 값을 쓰지 않음(항상 마지막
                                 # 씬 뒤 삽입) — cta_insert_index()의 기본 인자로만 남음
# CTA 씬 권장 상한. 035에서는 4.0초(선택지만 낭독)였는데, 질문 낭독을 고정
# 지침으로 올리면서(2026-09-17 사용자 지시) 질문 한 문장(약 13자 ≈ 1.6초)이
# 더 들어간다. "이건 누가 잘못한 걸까요? 1번 노인, 2번 여성. 댓글로 알려주세요."
# = 39자 ≈ 4.8초라 5.0초로 올렸다. 더 늘리면 본편 38~42초 캡을 잠식한다.
CTA_MAX_SEC = 5.0

# 041: 포맷별 CTA 스타일. `pick`(기본) = 035/040 선택지형, `subscribe` = V3.0
# 인물 프로필의 구독·댓글 유도형(사용자 확정 2026-09-14).
CTA_STYLE_KEY = "cta_style"
CTA_STYLES = (CTA_STYLE_PICK, CTA_STYLE_SUBSCRIBE)

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
# 구독형 CTA는 문구가 고정될 수 없으므로(질문이 아니라 부탁) 존댓말 종결형으로 본다.
# 말투 규칙의 취지는 특정 문장이 아니라 "명사형·반말로 끊지 말 것"이다.
POLITE_CLOSINGS = ("주세요", "주시고", "주시면", "부탁드립니다", "부탁드려요",
                   "바랍니다", "주시길")
# CTA 나레이션이 질문을 읽는지 보는 신호 (사용자 지시 2026-09-17).
# 035는 "질문은 화면 자막이 이미 보여주니 나레이션에선 빼고 선택지만 읽는다"였다.
# 사용자가 뒤집었다 — 쇼츠는 소리만 듣는 시청자가 많고, 선택지 번호만 들리면
# 무엇을 고르라는 건지 알 수 없다. 질문을 읽어야 CTA가 성립한다.
SPOKEN_QUESTION_MARKERS = (
    "?", "까요", "가요", "나요", "볼까", "어떠세요", "어떻게 보",
)
# 씬으로 직접 쓴 CTA를 자막에서 알아보는 신호 (선택지 기호만 — 오탐 방지)
CTA_SCENE_MARKERS = ("①", "②", "③", "1번", "2번", "3번")
# 구독형 CTA 씬에는 ①/1번이 없어 위 탐지기가 통째로 놓친다 — 별도 신호를 쓴다.
CTA_SUBSCRIBE_SCENE_MARKERS = ("구독", "댓글", "덧글")


def is_side_picking(text: str) -> bool:
    """편이 갈리는(선택지형) 질문인지 — 일반 열린 질문과 구분."""
    return any(m in (text or "") for m in SIDE_PICK_MARKERS)


def resolve_cta_style(cfg: dict) -> str:
    """config 의 `cta_style` 검증 후 반환. 미지정이면 포맷 기본값 (041).

    v2_1/v2_2 → `pick`(035/040 선택지형), profile_v3 → `subscribe`.
    """
    declared = cfg.get(CTA_STYLE_KEY)
    if not declared:
        return rules_for_config(cfg).default_cta_style
    if declared not in CTA_STYLES:
        raise ValueError(
            f"알 수 없는 {CTA_STYLE_KEY}={declared!r} — "
            f"{', '.join(CTA_STYLES)} 중 하나여야 합니다")
    return declared


def lint_cta_closing(voice: str, style: str = CTA_STYLE_PICK) -> list[str]:
    """CTA 나레이션이 존댓말 종결로 닫히는지.

    CTA는 영상에서 유일하게 시청자에게 직접 말을 거는 문장이라, "번호로 답글."
    같은 명사형·반말 종결은 지시처럼 들린다. 채널 톤에 맞춰 존댓말로 닫는다.

    041: 구독형(`subscribe`)은 고정 문구가 성립하지 않으므로 존댓말 종결형이면
    통과시킨다. **말투 규칙 자체는 포맷과 무관하게 계속 적용된다.**
    """
    if not voice:
        return []
    if style == CTA_STYLE_SUBSCRIBE:
        if any(c in voice for c in POLITE_CLOSINGS):
            return []
        return ['CTA 나레이션을 존댓말로 닫으세요 (예: "댓글로 남겨주세요", '
                '"구독 부탁드립니다") — 반말·명사형 종결은 지시처럼 들립니다 '
                f'(사용자 지시 2026-08-18). 현재: "{voice[-20:]}"']
    if CTA_CLOSING in voice:
        return []
    return [f'CTA 나레이션을 "{CTA_CLOSING}"로 닫으세요 — 반말·명사형 종결'
            f'("번호로 답글." 등)은 지시처럼 들립니다 (사용자 지시 2026-08-18). '
            f'현재: "{voice[-20:]}"']


def has_spoken_question(voice: str) -> bool:
    """CTA 나레이션이 질문을 소리로 읽는지."""
    return any(m in (voice or "") for m in SPOKEN_QUESTION_MARKERS)


def lint_cta_question(voice: str, style: str = CTA_STYLE_PICK) -> list[str]:
    """CTA 나레이션이 질문까지 읽는지 (V2.1·V2.2 고정 지침, 사용자 지시 2026-09-17).

    선택지형 CTA는 "1번 노인, 2번 여성"만 읽으면 **무엇을 고르라는 건지 소리로는
    알 수 없다.** 화면 자막이 질문을 보여주긴 하지만 쇼츠는 화면을 안 보는
    시청자가 많고, 질문을 못 들으면 답글이 붙지 않는다. 035의 "질문은 자막이
    보여주니 나레이션에선 뺀다"를 뒤집는 결정이다.

    구독형(`subscribe`, 041 V3.0)은 질문이 아니라 부탁이라 면제한다.
    """
    if not voice or style == CTA_STYLE_SUBSCRIBE:
        return []
    if has_spoken_question(voice):
        return []
    return ['CTA 나레이션이 질문을 안 읽습니다 — 선택지 번호만 들리면 무엇을 '
            '고르라는 건지 소리로 알 수 없습니다. 질문을 앞에 붙이세요 '
            '(예: "이건 누가 잘못한 걸까요? 1번 …, 2번 …. 댓글로 알려주세요.") '
            f'(V2.1·V2.2 고정 지침, 사용자 지시 2026-09-17). 현재: "{voice[:24]}"']


def lint_cta(cta: dict, category: str = "political",
             style: str = CTA_STYLE_PICK) -> list[str]:
    """CTA 블록 권장 위반 경고 (하드 오류 아님).

    036: 안내 예시는 카테고리별 (경제 '① 이득 ② 손해', 사회 '① 약하다 ② 적당하다').
    041: `style="subscribe"`(V3.0 인물 프로필)는 선택지형·질문 낭독 요구가
    면제되고, 존댓말 종결·5초 상한은 그대로 적용된다.
    """
    from scripts.shorts_domain import rules_for
    warnings = []
    text, voice = (cta or {}).get("text", ""), (cta or {}).get("voice", "")
    if not text:
        warnings.append("cta.text(화면 자막) 누락")
    if not voice:
        warnings.append("cta.voice(나레이션) 누락")
    combined = f"{text} {voice}"
    if style == CTA_STYLE_SUBSCRIBE:
        if (text or voice) and not any(m in combined
                                       for m in CTA_SUBSCRIBE_SCENE_MARKERS):
            warnings.append(
                "구독형 CTA인데 구독·댓글 요청이 없습니다 — "
                "'더 궁금하다면? 댓글 + 구독' 처럼 행동을 하나는 요청하세요 (041)")
    elif (text or voice) and not is_side_picking(combined):
        warnings.append(
            "CTA가 열린 질문 — 편 가르는 선택지형으로 바꾸세요 "
            f"(예: '{rules_for(category).cta_example}'). "
            "열린 질문은 실측상 댓글율 0.24%로 답글이 안 붙습니다 (035)")
    warnings.extend(lint_cta_question(voice, style))
    warnings.extend(lint_cta_closing(voice, style))
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
    """CTA를 tts 씬 dict 로 변환. 소스·frac·자막 위치는 이웃 씬에서 상속.

    `subtitle_position` 을 상속하는 이유: 038 이후 CTA는 **항상 마지막 씬**이라
    b-roll 이 방송 클립이고, 그 클립엔 하단에 번인 자막 카드가 박혀 있다.
    이웃 씬이 그 카드를 피해 `"bottom"` 으로 내려가 있는데 CTA만 기본값
    (position_y 0.652 = 16:9 레터박스 안쪽)에 남으면 CTA 자막만 카드 위에 겹친다.
    미지정이면 `""` — 기존 config 동작 그대로다.
    """
    return {
        "mode": "tts",
        "type": "body",
        "source": cta.get("source") or neighbor.get("source"),
        "frac": cta.get("frac", neighbor.get("frac", 0.4)),
        "subtitle_position": cta.get(
            "subtitle_position", neighbor.get("subtitle_position", "")),
        # 강조어 색도 같은 이유로 상속한다 — 이웃 씬이 emotion 색을 끊고
        # 카테고리 색으로 고정해 뒀는데 CTA 만 emotion 색으로 튀면 눈에 걸린다.
        "highlight_category": cta.get(
            "highlight_category", neighbor.get("highlight_category", "neutral")),
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
    """씬으로 **직접 쓴** CTA의 질문·종결 검사.

    2026-08-14 지시 이후 CTA를 top-level `cta` 블록이 아니라 마지막 씬에 직접
    쓰는 config 가 표준이 됐다. `lint_cta` 는 블록만 보므로 그 경로가 검사에서
    통째로 빠진다 — 이 함수가 그 구멍을 메운다.

    오탐을 줄이려고 자막에 선택지 기호(①/1번…)가 박힌 씬만 CTA로 본다.
    나레이션에 '찬성/반대' 같은 단어가 스쳐 지나가는 일반 씬은 걸리지 않는다.

    041: 구독형 CTA 씬에는 선택지 기호가 없으므로 스타일에 맞는 신호로 찾는다.
    """
    style = resolve_cta_style(cfg)
    markers = (CTA_SUBSCRIBE_SCENE_MARKERS if style == CTA_STYLE_SUBSCRIBE
               else CTA_SCENE_MARKERS)
    warnings = []
    for i, sc in enumerate(cfg.get("scenes") or []):
        if sc.get("_cta"):      # 블록에서 삽입된 씬은 lint_cta 가 이미 본다
            continue
        if not any(m in (sc.get("text") or "") for m in markers):
            continue
        voice = sc.get("voice", "")
        warnings.extend(f"scene[{i}] {w}"
                        for w in lint_cta_question(voice, style))
        warnings.extend(f"scene[{i}] {w}"
                        for w in lint_cta_closing(voice, style))
    return warnings


__all__ = [
    "CTA_CLOSING", "CTA_MAX_SEC", "CTA_PHRASES", "CTA_SCENE_MARKERS",
    "CTA_STYLES", "CTA_STYLE_KEY", "CTA_STYLE_PICK", "CTA_STYLE_SUBSCRIBE",
    "CTA_SUBSCRIBE_SCENE_MARKERS", "DEFAULT_CTA_AT_FRAC", "POLITE_CLOSINGS",
    "SIDE_PICK_MARKERS", "SPOKEN_QUESTION_MARKERS",
    "apply_cta", "build_cta_scene", "cta_insert_index", "has_spoken_question",
    "is_side_picking",
    "lint_cta", "lint_cta_closing", "lint_cta_question", "resolve_cta_style",
    "scene_cta_closing_warnings", "trailing_cta_warnings",
]
