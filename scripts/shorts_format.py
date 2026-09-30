"""쇼츠 포맷 축 — 계측 원장 + 포맷별 규칙 팩 (041 Phase A1).

**왜 필요한가**: V3.0(인물 프로필)은 사용자가 확정한 두 결정이 채널 실측과
반대 방향이다 — ①정치인 인물편(039 실측 political 90편 중앙 1,255회, 정치인
돌파율 9%) ②구독 유도형 CTA(035 실측 열린 CTA 댓글율 0.24%). 차단하지 않기로
한 이상, **포맷별 성과를 숫자로 못 쪼개면 파일럿이 판정 불가능한 도박이 된다.**
036이 카테고리 축을 계측부터 붙인 것과 같은 이유이고, 원장도 같은 파일을 쓴다.

**카테고리와 포맷은 직교한다**: 인물 프로필은 정치·경제·사회·연예 어디서든
성립한다. 그래서 `category` 를 대체하지 않고 별도 축으로 둔다.

**추론하지 않는다**: 카테고리는 제목 키워드로 과거 편을 백필할 수 있었지만
(036), 제목만 보고 그 편이 V2.1인지 V2.2인지 알 방법은 없다. 원장에 없으면
`unknown` 으로 두고 리포트에서 "포맷 기록 이전(legacy)"으로 읽는다 — 틀린 추론을
넣으면 파일럿 판정 근거가 오염된다.

**호환**: `format` 미지정 = `v2_1` = 040까지의 동작과 완전히 동일. 기존 config
107개는 무변경으로 통과한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.shorts_category import (
    ledger_key,
    load_entry_field,
    record_entry_fields,
)

V2_1 = "v2_1"
V2_2 = "v2_2"
PROFILE_V3 = "profile_v3"
NEWS_V4 = "news_v4"

FORMATS = (V2_1, V2_2, PROFILE_V3, NEWS_V4)
DEFAULT_FORMAT = V2_1          # 미지정 config = 기존 정치쇼츠 (동작 무변경)
UNKNOWN_FORMAT = "unknown"     # 원장에 기록이 없는 과거 편
FORMAT_KEY = "format"

# CTA 스타일 값 — 실체는 political_cta 가 해석한다. 여기서는 문자열만 들고 있어
# 순환 import 를 피한다 (political_cta 가 이 모듈을 함수 안에서 import 한다).
CTA_STYLE_PICK = "pick"
CTA_STYLE_SUBSCRIBE = "subscribe"


@dataclass(frozen=True)
class FormatRules:
    """한 포맷의 게이트 적용 방침 + 렌더 기본값. 전부 불변 — 조회만 한다."""

    format: str
    label: str
    audio_policy: str
    # 040 진영 대칭 검사 대상인가 (인물 1명 포맷은 개념상 성립하지 않는다)
    symmetry_applies: bool
    # 039 경고를 개별 항목 대신 1회 고지로 낮출 것인가 (DEAD 는 그대로 유지)
    breakout_notice_only: bool
    default_cta_style: str
    # 헤드라인 서체 — "" 면 렌더러 기본값(037 Noto Sans KR 100px)
    headline_font: str
    # 훅 앞 한 줄 상황 설명(intro) 이 기본인가 (사용자 확정 2026-09-15)
    intro_required: bool
    checklist: tuple[str, ...]


_V2_CHECKLIST = (
    "클립 컷이 말 끝맺음까지 들어갔는가 (037)",
    "scenes[0](훅)이 가진 클립 중 가장 센 컷인가 (036)",
    "훅 앞에 한 줄짜리 인트로(상황 설명 TTS)가 있는가 — 등장인물이 여럿인 "
    "소재는 맥락 없이 육성부터 틀면 누가 누구에게 하는 말인지 몰라 이탈한다",
)

FORMAT_RULES: dict[str, FormatRules] = {
    V2_1: FormatRules(
        format=V2_1, label="V2.1 훅 육성 + TTS 논평",
        audio_policy="scene 0 육성 훅 + 이후 TTS (클립 비중 약 35%)",
        symmetry_applies=True, breakout_notice_only=False,
        default_cta_style=CTA_STYLE_PICK, headline_font="",
        intro_required=True,
        checklist=_V2_CHECKLIST,
    ),
    V2_2: FormatRules(
        format=V2_2, label="V2.2 원본 육성 릴레이",
        audio_policy="육성 클립 3~5개 + TTS 정리 1개 (클립 비중 ≥65%)",
        symmetry_applies=True, breakout_notice_only=False,
        default_cta_style=CTA_STYLE_PICK, headline_font="",
        intro_required=True,
        checklist=_V2_CHECKLIST,
    ),
    PROFILE_V3: FormatRules(
        format=PROFILE_V3, label="V3.0 인물 프로필 다큐멘터리",
        audio_policy="scene 0 육성 훅 + 이후 원본 음소거 B-roll + 전체 TTS",
        # 인물 1명을 다루는 포맷이라 '양쪽 진영 등장'이 성립하지 않는다.
        # 오탐으로 경고를 남발하면 게이트 전체가 무시당한다 (040 방침).
        symmetry_applies=False,
        # 정치인 인물편은 039 기준 C 등급이 기본이다. 사용자가 알고 택한
        # 포맷이므로 개별 경고 3줄 대신 1회 고지로 낮춘다 (DEAD 는 유지).
        breakout_notice_only=True,
        default_cta_style=CTA_STYLE_SUBSCRIBE,
        headline_font="GungSeo",
        # 훅 육성 뒤 나레이션이 전체를 끌고 가는 구조라 별도 상황 설명이 중복된다.
        intro_required=False,
        checklist=(
            "나레이션의 모든 이력·수치가 fact_sources 의 실제 기사에 있는가 "
            "— 소스에 없는 경력·직책·수상·생년을 지어내지 않았는가 (명예훼손 "
            "방어선: V2.2와 달리 육성 인용이라는 방패가 없다)",
            "나무위키를 팩트 소스로 쓰지 않았는가 — CC BY-NC-SA 라 업로드가 "
            "막혀 있다 (celebrity 모드 경로 재사용 금지)",
            "사용한 클립의 채널명을 전부 화면·설명란에 표기했는가 — 인물 B-roll은 "
            "비평 대상이 그 영상이 아니라서 인용 목적성이 V2.2보다 약하다",
            "각 클립에 **그 인물 본인**이 화면에 나오는가 (기자회견·위원회 영상은 "
            "사회자·다른 발언자가 잡힌다 — 확신 없으면 인물 사진으로 대체)",
            "헤드라인 2열이 이력·배경에 대한 **질문형 훅**인가 "
            "(예: '구글 엔지니어 출신?') — 스캔들형 '의혹?' 과는 다르다",
            "인물 배지(실명+직책)가 사실과 일치하는가",
            "CTA가 구독·댓글 유도형이고 존댓말로 닫히는가",
        ),
    ),
    NEWS_V4: FormatRules(
        format=NEWS_V4, label="V4.0 사진 슬라이드 뉴스 카드",
        audio_policy="전 구간 TTS, 원본 육성 0, BGM 없음 — 사진 3.4초 고정 교체",
        # 벤치마크(042)의 인용문 자체가 양 진영 가정으로 대칭이다 — 정치 1편
        # 단위 대칭(040)이 이 포맷의 뼈대라 그대로 적용한다.
        symmetry_applies=True,
        breakout_notice_only=False,
        default_cta_style=CTA_STYLE_PICK,
        # 벤치마크의 두꺼운 고딕에 가장 가까운 로컬 설치 서체 (사용자 확정 2026-09-30)
        headline_font="BM Dohyeon",
        # 육성 훅이 없어 첫 문장(사건 요약)이 곧 상황 설명이다.
        intro_required=False,
        checklist=(
            "나레이션의 모든 사실·수치가 fact_sources 의 실제 기사에 있는가 "
            "— 육성 인용이라는 방패가 없다 (나레이션 100% 가 채널 자신의 서술)",
            "인물 발언은 간접화법('~라며', '~고 밝혔습니다')으로 옮겼는가 — "
            "원문에 없는 표현을 따옴표로 넣지 않았는가",
            "모든 사진의 출처가 하단 출처 줄에 있는가 — 가능하면 당사자 SNS·"
            "공식 브리핑 사진을 먼저 쓴다 (통신사 사진은 표기해도 이용 허락이 아니다)",
            "각 사진에 **그 인물 본인**이 나오는가 (검색 결과에는 동명이인·"
            "동석자 사진이 섞인다)",
            "원문 캡처(SNS·기사)는 fit=contain 으로 잘리지 않고 읽히는가",
            "완료 블록에 자극적 제목 A/B(yt_title·yt_title_alt) + 3줄요약 + 해시태그 "
            "3~4개가 다 있는가 — 공포·충격·호기심 톤, 명사로 닫기 (사용자 지시 2026-09-30)",
        ),
    ),
}


# ── 조회 ───────────────────────────────────────────────────────────
def _validate_format(fmt: str) -> str:
    if fmt not in FORMATS:
        raise ValueError(
            f"알 수 없는 format={fmt!r} — {', '.join(FORMATS)} 중 하나여야 합니다")
    return fmt


def resolve_config_format(cfg: dict) -> str:
    """config 의 `format` 검증 후 반환. 미지정이면 v2_1 (기존 동작)."""
    return _validate_format(cfg.get(FORMAT_KEY) or DEFAULT_FORMAT)


def rules_for_format(fmt: str) -> FormatRules:
    return FORMAT_RULES[_validate_format(fmt)]


def rules_for_config(cfg: dict) -> FormatRules:
    return rules_for_format(resolve_config_format(cfg))


# ── 원장 I/O (036 카테고리 원장과 같은 파일을 공유한다) ────────────
def load_formats(path: Path) -> dict[str, str]:
    """원장 파일 → {정규화 제목: format}. 없거나 깨졌으면 빈 dict."""
    return load_entry_field(path, FORMAT_KEY, FORMATS)


def record_format(path: Path, title: str, fmt: str,
                  slug: str = "") -> dict[str, str]:
    """원장에 한 편의 포맷을 기록하고 갱신된 {제목: format} 을 새로 반환."""
    _validate_format(fmt)
    entries = record_entry_fields(path, title, {FORMAT_KEY: fmt}, slug=slug)
    return {k: v[FORMAT_KEY] for k, v in entries.items()
            if isinstance(v, dict) and v.get(FORMAT_KEY) in FORMATS}


def resolve_format(title: str, ledger: dict[str, str]) -> str:
    """원장 우선 → 접두 일치 → `unknown`.

    접두 일치는 036과 같은 이유다 — 업로드 제목 뒤에 해시태그·꼬리말이 붙어도
    원장 항목을 찾아낸다. **키워드 추론은 하지 않는다** (모듈 docstring 참고).
    """
    key = ledger_key(title)
    if not key:
        return UNKNOWN_FORMAT
    if key in ledger:
        return ledger[key]
    for known, fmt in ledger.items():
        if known and key.startswith(known):
            return fmt
    return UNKNOWN_FORMAT


__all__ = [
    "CTA_STYLE_PICK", "CTA_STYLE_SUBSCRIBE", "DEFAULT_FORMAT", "FORMATS",
    "FORMAT_KEY", "FORMAT_RULES", "NEWS_V4", "PROFILE_V3", "UNKNOWN_FORMAT", "V2_1",
    "V2_2", "FormatRules", "load_formats", "record_format",
    "resolve_config_format", "resolve_format", "rules_for_config",
    "rules_for_format",
]
