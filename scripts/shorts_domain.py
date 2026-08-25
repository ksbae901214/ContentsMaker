"""카테고리별 도메인 규칙 팩 (036 Phase 1/2) — 정치 외 경제·사회·연예 확장.

**설계 판단**: 파이프라인은 도메인과 무관하다. 렌더러·38~42초 길이 캡·육성 릴레이
구조·40% CTA 삽입 로직은 경제든 연예든 그대로다. 실제로 달라지는 건 **검사 기준표**
뿐이라, 새 모듈/스크립트를 늘리지 않고 이 규칙 팩 하나를 카테고리로 조회한다.

035의 '결과가 난 사건' 프레임은 도메인이 바뀌어도 그대로 산다 — 어휘만 갈아끼운다:

| | 결과어 | 예시 |
|---|---|---|
| 정치 | 사퇴·부결·철회·경질 | '13시간 만에 뒤집힌 표결' |
| 경제 | 동결·급락·파산·리콜 | '결국 동결된 금리' |
| 사회 | 무죄·구속·폐지 | '3년 재판 끝 무죄' |
| 연예 | 인정·하차·복귀 | '9년 만에 복귀' |

**가드레일 2단**:
- `banned_words` → `gate_domain_words()` 가 **ValueError 로 차단**. 법적 리스크가
  분명한 것만 (경제 투자권유 = 유사투자자문 소지).
- `caution_words` → `domain_warnings()` 가 **경고**. 사람 판단이 필요한 것
  (사회 피의사실·연예 미확인 사생활).

둘 다 config 에 `"domain_gate": "off"` 로 우회한다.

**호환**: `category` 미지정 = `political` = 035까지의 동작과 동일. 정치 규칙의
어휘·고정댓글은 `political_upload_package` 의 기존 상수를 그대로 참조해 두 곳이
갈라지지 않게 했다.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.shorts_category import CATEGORIES, resolve_config_category

GATE_OFF = "off"                 # config `"domain_gate": "off"` 로 전체 우회
GATE_KEY = "domain_gate"


@dataclass(frozen=True)
class DomainRules:
    """한 카테고리의 검사 기준표. 전부 불변 — 조회만 한다."""

    category: str
    label: str
    # 035 소재 프레임 — 공방어만 있고 결과어가 없으면 경고
    clash_words: tuple[str, ...]
    outcome_words: tuple[str, ...]
    outcome_example: str
    # 035 중반 CTA — 편 가르는 선택지형
    default_pinned_comment: str
    cta_example: str
    # 030 제목 앵커 — 정치는 실명, 경제는 숫자·기관명
    anchor_label: str
    # 렌더 기본값 (config 명시값이 우선)
    emotion_type: str
    bg_colors: tuple[str, ...]
    # 036 Phase 2 가드레일
    banned_words: tuple[str, ...]
    banned_reason: str
    caution_words: tuple[str, ...]
    caution_reason: str
    require_source_channel: bool
    checklist: tuple[str, ...]


# 정치 어휘는 기존 상수를 그대로 재사용 — 두 곳이 갈라지면 035 게이트가 조용히
# 약해진다. (import 는 함수 밖 모듈 최상단에 두면 순환 import 가 된다.)
def _political_constants() -> tuple[tuple[str, ...], tuple[str, ...], str]:
    from scripts.political_upload_package import (
        _CLASH_WORDS, _OUTCOME_WORDS, DEFAULT_PINNED_COMMENT,
    )
    return _CLASH_WORDS, _OUTCOME_WORDS, DEFAULT_PINNED_COMMENT


_CLASH_COMMON = (
    "직격", "저격", "공방", "정면충돌", "충돌", "맞불", "발끈", "일침", "일갈",
    "돌직구", "질타", "성토", "반박", "역공", "설전",
)

_CHECKLIST_COMMON = (
    "제목에 해시태그 없음 · 해시태그는 설명란 3~4개만",
    "길이 38~42초인가 (캡 42초 — 완주율이 조회수 천장을 만든다, 035)",
    "댓글 CTA가 40% 지점에 있는가 · 편 가르는 선택지형인가 (035)",
    "CTA 나레이션이 \"댓글로 알려주세요\"로 끝나는가 (반말·명사형 종결 금지)",
    "클립 컷이 **말 끝맺음까지** 들어갔는가 — 문장 끝 단어가 다 발화된 뒤 끊는다 "
    "(자동자막 단어 타임스탬프로 확인, 눈대중 금지)",
)


def _build_domain_rules() -> dict[str, DomainRules]:
    clash_pol, outcome_pol, pinned_pol = _political_constants()
    return {
        "political": DomainRules(
            category="political", label="정치",
            clash_words=clash_pol,
            outcome_words=outcome_pol,
            outcome_example="'13시간 만에 뒤집힌 표결', '9년 침묵 끝 컴백'",
            default_pinned_comment=pinned_pol,
            cta_example="이거 누구 잘못? ① 여당 ② 야당",
            anchor_label="실명(persons)",
            emotion_type="angry",
            bg_colors=("#7f1d1d", "#450a0a", "#000000"),
            banned_words=(),
            banned_reason="",
            caution_words=(),
            caution_reason="",
            require_source_channel=False,
            checklist=(
                "썸네일 = 인물 표정 절정 컷인가 (웃음/한숨/야유/침묵 — 후보 중 선택)",
                "같은 주제 V2.1/V2.2 중복 업로드 금지 — 플랫폼 분리 "
                "(V2.2→유튜브, V2.1→틱톡)",
                *_CHECKLIST_COMMON,
                "소재가 '누가 누구를 저격'이 아니라 '결과가 난 사건'인가 (035)",
            ),
        ),
        "economic": DomainRules(
            category="economic", label="경제",
            clash_words=_CLASH_COMMON,
            outcome_words=(
                "동결", "인상", "인하", "급락", "급등", "폭락", "반토막", "최저",
                "최고", "파산", "부도", "철수", "리콜", "상장폐지", "적자", "흑자",
                "무산", "철회", "확정", "타결", "합의", "결국", "끝내", "만에",
                "뒤집", "역전", "회복", "붕괴",
            ),
            outcome_example="'결국 동결된 금리', '한 달 만에 반토막 난 OO'",
            default_pinned_comment=(
                "지금 집값, 앞으로 어떻게 될까요? ① 더 오른다  ② 떨어진다 "
                "— 번호로 답글 👇"),
            cta_example="이 정책, 내 지갑엔? ① 이득 ② 손해",
            anchor_label="숫자 또는 기업·기관명(persons)",
            emotion_type="relatable",
            bg_colors=("#0f766e", "#134e4a", "#000000"),
            banned_words=(
                "매수", "매도", "추천주", "추천 종목", "급등각", "존버", "물타기",
                "풀매수", "몰빵", "수익 보장", "수익률 보장", "익절각", "손절각",
            ),
            banned_reason=(
                "투자 권유·종목 추천으로 읽힐 수 있습니다 (유사투자자문 소지). "
                "사실·수치 전달로 바꾸세요"),
            caution_words=("전망", "예상", "될 것", "할 것"),
            caution_reason=(
                "전망·예측 표현 — 출처와 기준시점을 함께 밝히세요 "
                "(누구의 전망인지 없으면 투자 조언처럼 들립니다)"),
            require_source_channel=False,
            checklist=(
                "scenes[0](훅)이 **가진 클립 중 가장 센 컷**인가 — 사연 전개 순서대로 "
                "배열하면 상황 설명이 앞에 오고 절정이 뒤로 간다 (1호 실패 사례)",
                "수치에 출처·기준시점이 붙어 있는가 (‘OO 기준 O월 O일’)",
                "특정 종목·상품 매수/매도 권유로 읽힐 문장이 없는가",
                *_CHECKLIST_COMMON,
                "소재가 '전망'이 아니라 '결과가 난 사건'인가 (035)",
            ),
        ),
        "society": DomainRules(
            category="society", label="사회",
            clash_words=_CLASH_COMMON,
            outcome_words=(
                "무죄", "유죄", "구속", "석방", "선고", "판결", "확정", "기각",
                "인용", "실형", "집행유예", "폐지", "제정", "개정", "사과",
                "해임", "파면", "징계", "결국", "끝내", "만에", "뒤집", "재심",
            ),
            outcome_example="'3년 재판 끝 무죄', '결국 폐지된 OO 제도'",
            default_pinned_comment=(
                "이 처벌, 어떻게 보세요? ① 너무 약하다  ② 적당하다 "
                "— 번호로 답글 👇"),
            cta_example="이 판결 ① 너무 약하다 ② 적당하다",
            anchor_label="사건명 또는 실명(persons)",
            emotion_type="touching",
            bg_colors=("#1e3a8a", "#172554", "#000000"),
            banned_words=(),
            banned_reason="",
            caution_words=(
                "피의자", "용의자", "구속영장", "입건", "내사", "범인", "살인마",
            ),
            caution_reason=(
                "판결 확정 전 단정·신원 노출 위험 — 피의사실공표·명예훼손 소지. "
                "확정 판결 사건을 우선하고, 단정 표현은 '혐의'로 바꾸세요"),
            require_source_channel=False,
            checklist=(
                "판결이 확정된 사건인가 (수사 중 사건은 단정 표현 금지)",
                "피해자·유족 신원이 드러나지 않는가 (2차 가해 방지)",
                *_CHECKLIST_COMMON,
                "소재가 '사건 발생'이 아니라 '결과가 난 사건'인가 (035)",
            ),
        ),
        "entertainment": DomainRules(
            category="entertainment", label="연예",
            clash_words=_CLASH_COMMON,
            outcome_words=(
                "인정", "부인", "결별", "열애", "이혼", "재혼", "은퇴", "복귀",
                "컴백", "하차", "퇴출", "해지", "계약종료", "사과", "폭로",
                "결국", "끝내", "만에", "뒤집", "확정", "무산",
            ),
            outcome_example="'9년 만에 복귀', '3시간 만에 번복된 열애 부인'",
            default_pinned_comment=(
                "이번 복귀, 어떻게 보세요? ① 응원한다  ② 이르다 "
                "— 번호로 답글 👇"),
            cta_example="이 복귀 ① 응원한다 ② 이르다",
            anchor_label="실명(persons)",
            emotion_type="funny",
            bg_colors=("#7e22ce", "#4c1d95", "#000000"),
            banned_words=(),
            banned_reason="",
            caution_words=(
                "불륜", "양다리", "임신설", "마약설", "이혼설", "사생활", "루머",
            ),
            caution_reason=(
                "미확인 사생활 단정 — 명예훼손 위험이 정치보다 큽니다. "
                "공식 입장·보도로 확인된 사실만 쓰세요"),
            require_source_channel=True,
            checklist=(
                "⚠️ 방송 클립 저작권 — 인용 구간을 최소화하고 출처를 화면·설명란에 "
                "명시했는가 (연예는 이 채널에서 저작권 위험이 가장 큰 카테고리)",
                "미확인 사생활·루머가 아니라 공식 입장/보도로 확인된 사실인가",
                *_CHECKLIST_COMMON,
                "소재가 '설(說)'이 아니라 '결과가 난 사건'인가 (035)",
            ),
        ),
    }


DOMAIN_RULES: dict[str, DomainRules] = _build_domain_rules()


# ── 조회 ───────────────────────────────────────────────────────────
def rules_for(category: str) -> DomainRules:
    if category not in DOMAIN_RULES:
        raise ValueError(
            f"알 수 없는 category={category!r} — {', '.join(CATEGORIES)} 중 하나여야 합니다")
    return DOMAIN_RULES[category]


def rules_for_config(cfg: dict) -> DomainRules:
    """config 의 category 로 규칙 조회. 미지정이면 정치 (기존 동작)."""
    return rules_for(resolve_config_category(cfg))


def resolve_emotion_type(cfg: dict) -> str:
    """config 명시값 > 카테고리 기본값."""
    return cfg.get("emotion_type") or rules_for_config(cfg).emotion_type


def resolve_bg_colors(cfg: dict) -> tuple[str, ...]:
    """config 명시값 > 카테고리 기본 그라데이션."""
    return tuple(cfg.get("bg_colors") or rules_for_config(cfg).bg_colors)


# ── 가드레일 ───────────────────────────────────────────────────────
def collect_config_text(cfg: dict) -> str:
    """검사 대상 텍스트 전부 — 제목·씬 자막/나레이션·CTA."""
    parts = [cfg.get("yt_title", ""), cfg.get("yt_title_alt", ""),
             cfg.get("title", ""), cfg.get("description", "")]
    for sc in cfg.get("scenes") or []:
        parts += [sc.get("text", ""), sc.get("voice", "")]
    cta = cfg.get("cta") or {}
    parts += [cta.get("text", ""), cta.get("voice", "")]
    return " ".join(p for p in parts if p)


def _gate_disabled(cfg: dict) -> bool:
    return cfg.get(GATE_KEY) == GATE_OFF


def gate_domain_words(cfg: dict) -> None:
    """법적 리스크가 분명한 금지어는 렌더 전에 차단 (ValueError).

    현재는 경제의 투자 권유 표현만 해당한다. 우회: `"domain_gate": "off"`.
    """
    if _gate_disabled(cfg):
        return
    rules = rules_for_config(cfg)
    if not rules.banned_words:
        return
    text = collect_config_text(cfg)
    hits = [w for w in rules.banned_words if w in text]
    if hits:
        raise ValueError(
            f"[{rules.label}] 금지 표현 {', '.join(hits)} — {rules.banned_reason} "
            f"(우회: \"{GATE_KEY}\": \"{GATE_OFF}\")")


def domain_warnings(cfg: dict) -> list[str]:
    """사람 판단이 필요한 주의어·필수 항목 경고 (하드 오류 아님)."""
    if _gate_disabled(cfg):
        return []
    rules = rules_for_config(cfg)
    warnings = []
    text = collect_config_text(cfg)
    hits = [w for w in rules.caution_words if w in text]
    if hits:
        warnings.append(
            f"[{rules.label}] 주의 표현 {', '.join(hits)} — {rules.caution_reason}")
    if rules.require_source_channel and not cfg.get("source_channel"):
        warnings.append(
            f"[{rules.label}] source_channel 미지정 — 출처 표기가 필요한 "
            "카테고리입니다 (저작권·명예훼손 방어선)")
    return warnings


__all__ = [
    "DOMAIN_RULES", "GATE_KEY", "GATE_OFF", "DomainRules",
    "collect_config_text", "domain_warnings", "gate_domain_words",
    "resolve_bg_colors", "resolve_emotion_type", "rules_for", "rules_for_config",
]
