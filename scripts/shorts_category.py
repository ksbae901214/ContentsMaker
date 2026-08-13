"""쇼츠 카테고리 원장·추론 (036 Phase 0) — 정치 외 경제·사회·연예 확장 계측.

**왜 필요한가**: 단일 채널에 정치 외 카테고리를 섞기로 한 이상(사용자 확정
2026-08-13), "어느 카테고리가 먹히는가"와 "혼합이 기존 정치 성과를 희석하는가"를
숫자로 못 보면 확장이 도박이 된다. 035까지의 리포트는 제목 유형·길이·해시태그로만
쪼갤 수 있어 카테고리 축이 없다.

**두 갈래로 카테고리를 정한다**:

1. **원장(ledger, 권위 있음)** — `data/channel_analytics/category_ledger.json`.
   `upload_package.md` 생성 시 config 의 `category` 를 제목과 함께 자동 기록한다.
   업로드가 수동이라 유튜브 쪽에는 카테고리 정보가 남지 않으므로 로컬 원장이 유일한
   정답 소스다.
2. **제목 키워드 추론(폴백, best-effort)** — 원장이 없던 과거 편(88편) 백필용.
   정치 인물명처럼 시간이 지나면 낡는 신호가 섞여 있어 정확도를 보장하지 않는다.
   추론 결과가 틀리면 원장에 직접 항목을 추가해 덮어쓰면 된다.

제목 매칭은 해시태그·NFD 를 정규화한 뒤 비교하고, 업로드 시 제목 뒤에 해시태그나
꼬리말이 붙는 경우까지 **접두 일치**로 흡수한다 (config `yt_title` 과 실제 업로드
제목이 정확히 같을 거라 기대할 수 없다).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

CATEGORIES = ("political", "economic", "society", "entertainment")
DEFAULT_CATEGORY = "political"      # 미지정 config = 기존 정치쇼츠 (동작 무변경)
UNKNOWN = "unknown"                 # 원장에도 없고 키워드도 안 걸린 편

LEDGER_VERSION = 1
_HASHTAG_RE = re.compile(r"#\S+")

# 동점일 때의 우선순위 — 채널의 기본축(정치)부터.
_TIE_PRIORITY = CATEGORIES

# 제목 키워드 — **추론 폴백 전용**. 정확도보다 백필 커버리지가 목적이라
# 겹치는 단어(세금·검찰 등)가 있어도 점수 합산으로 흡수한다. 채널 소재가 바뀌면
# 이 목록을 직접 수정할 것.
#
# 영문 키워드는 채널의 영문 제목 편(실측 절반가량)을 위해 필요하다. 소문자로
# 적고 **어간**으로 둔다(prosecut → prosecution/prosecutor) — 해시태그가
# CamelCase 로 붙어 있어(#StockMarketCrash) 단어 경계 매칭이 안 먹기 때문에
# 부분 문자열로 비교한다. 짧고 흔한 단어(tax, won)는 오탐이 나므로 넣지 않는다.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "political": (
        "대통령", "국회", "여당", "야당", "민주당", "국민의힘", "의원", "장관",
        "특검", "개헌", "탄핵", "선관위", "대선", "총선", "지방선거", "당대표",
        "법사위", "국정감사", "청문회", "원내대표", "대변인", "공천", "표결",
        "본회의", "상임위", "내각", "청와대", "대통령실", "정부", "여야",
        # 고빈도 인물명 — 낡기 쉬운 신호라 원장이 생기면 자연히 덜 쓰이게 된다
        "이재명", "윤석열", "한동훈", "조국", "오세훈", "장동혁", "박근혜",
        "이준석", "추경호", "김부겸", "나경원", "정점식",
        "president", "lawmaker", "parliament", "assembly", "ruling party",
        "opposition", "minister", "impeach", "election", "constitutional",
        "insurrection", "candidate", "politic", "dictator", "petition",
        "prosecution's", "cabinet", "nationalelection", "localelection",
    ),
    "economic": (
        "금리", "물가", "환율", "코스피", "코스닥", "주가", "증시", "부동산",
        "전세", "집값", "분양", "대출", "종부세", "상속세", "연봉", "최저임금",
        "수출", "반도체", "실업", "인플레", "자영업", "파산", "상장", "배당",
        "연금", "경제", "세금", "재정", "추경", "국채", "코인", "환급", "지원금",
        "stock", "market crash", "real estate", "realestate", "housing",
        "mortgage", "inflation", "export", "semiconductor", "subsid",
        "budget", "economic", "economy", "net worth", "tax arrears",
        "housing price", "etf", "won mortgage",
    ),
    "society": (
        "판결", "무죄", "유죄", "구속", "검찰", "경찰", "재판", "선고", "기소",
        "학교", "교사", "학폭", "의사", "병원", "화재", "사고", "범죄",
        "음주운전", "층간소음", "출산율", "저출생", "고령화", "노조", "산재",
        "피해자", "유족", "실종", "폭행", "성범죄", "아동", "복지",
        "police", "murder", "verdict", "prison", "crime", "criminal",
        "drunk driving", "victim", "arrest", "school girl", "hospital",
    ),
    "entertainment": (
        "배우", "가수", "아이돌", "연예인", "드라마", "영화", "예능", "열애",
        "결별", "이혼", "은퇴", "컴백", "소속사", "콘서트", "앨범", "유튜버",
        "인플루언서", "데뷔", "하차", "스캔들", "팬미팅", "시상식", "출연",
        "actor", "actress", "singer", "idol", "celebrity", "drama series",
        "box office", "comeback", "agency", "concert", "album",
    ),
}


# ── 제목 정규화 ────────────────────────────────────────────────────
def ledger_key(title: str) -> str:
    """원장 조회용 정규화 키 — NFC + 해시태그 제거 + 공백 축약.

    yt-dlp 경유 제목은 NFD(자모 분해형)일 수 있고, 업로드 시 제목에 해시태그가
    덧붙는다. 양쪽을 같은 규칙으로 눌러 비교 가능하게 만든다.
    """
    t = unicodedata.normalize("NFC", title or "")
    t = _HASHTAG_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


# ── 키워드 추론 (폴백) ─────────────────────────────────────────────
def classify_haystack(title: str) -> str:
    """카테고리 추론용 비교 문자열 — NFC + 소문자 + 공백 축약.

    `ledger_key` 와 달리 **해시태그를 남긴다**: `#종부세`·`#StockMarketCrash`
    처럼 해시태그가 주제를 가장 직접적으로 말해주기 때문이다. (제목 *문체*
    분류인 `classify_title` 이 해시태그를 벗기는 것과는 목적이 다르다 — 그쪽은
    태그 속 단어가 어조 판정을 오염시키는 게 문제였다.)
    """
    t = unicodedata.normalize("NFC", title or "").lower()
    return re.sub(r"\s+", " ", t).strip()


def category_scores(title: str) -> dict[str, int]:
    """카테고리별 키워드 적중 수 — 추론 근거 확인·튜닝용."""
    hay = classify_haystack(title)
    return {
        cat: sum(1 for kw in words if kw in hay)
        for cat, words in CATEGORY_KEYWORDS.items()
    }


def classify_category(title: str) -> str:
    """제목 키워드로 카테고리 추론. 적중 없으면 `unknown`.

    동점은 `_TIE_PRIORITY`(정치 우선)로 깬다 — 채널의 기본축이 정치이므로
    애매한 편을 정치로 두는 쪽이 기존 통계와 연속성이 있다.
    """
    scores = category_scores(title)
    best = max(scores.values(), default=0)
    if best == 0:
        return UNKNOWN
    return next(c for c in _TIE_PRIORITY if scores[c] == best)


# ── 원장 I/O ───────────────────────────────────────────────────────
def _validate_category(category: str) -> str:
    if category not in CATEGORIES:
        raise ValueError(
            f"알 수 없는 category={category!r} — {', '.join(CATEGORIES)} 중 하나여야 합니다")
    return category


def resolve_config_category(cfg: dict) -> str:
    """config 의 `category` 검증 후 반환. 미지정이면 political (기존 동작)."""
    return _validate_category(cfg.get("category") or DEFAULT_CATEGORY)


def load_ledger(path: Path) -> dict[str, str]:
    """원장 파일 → {정규화 제목: category}. 없거나 깨졌으면 빈 dict.

    계측 보조 장치이므로 파일이 손상돼도 렌더·분석을 막지 않는다.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        key: entry["category"]
        for key, entry in entries.items()
        if isinstance(entry, dict) and entry.get("category") in CATEGORIES
    }


def record_category(path: Path, title: str, category: str,
                    slug: str = "") -> dict[str, str]:
    """원장에 한 편을 기록하고 갱신된 {제목: category} 매핑을 **새로** 반환.

    같은 제목을 다시 기록하면 최신 값으로 덮어쓴다 (제목 수정 후 재렌더 대응).
    제목이 비면 기록하지 않는다 — 키 없는 항목은 조회가 불가능해 쓸모가 없다.
    """
    _validate_category(category)
    key = ledger_key(title)
    if not key:
        return load_ledger(path)

    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {}
    entries = raw.get("entries") if isinstance(raw.get("entries"), dict) else {}

    updated = {
        **raw,
        "version": LEDGER_VERSION,
        "description": (
            "쇼츠 카테고리 원장 (036) — upload_package 생성 시 자동 기록. "
            "키는 해시태그를 뗀 정규화 제목. 추론이 틀린 과거 편은 여기에 직접 추가."
        ),
        "entries": {
            **entries,
            key: {
                "category": category,
                "slug": slug,
                "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return {k: v["category"] for k, v in updated["entries"].items()
            if v.get("category") in CATEGORIES}


def resolve_category(title: str, ledger: dict[str, str]) -> str:
    """원장 우선 → 접두 일치 → 키워드 추론 → `unknown`.

    접두 일치: 업로드 제목 뒤에 해시태그·꼬리말이 붙어도 원장 항목을 찾아낸다
    (config `yt_title` 과 실제 업로드 제목이 같다고 보장할 수 없다).
    """
    key = ledger_key(title)
    if key:
        if key in ledger:
            return ledger[key]
        for known, category in ledger.items():
            if known and key.startswith(known):
                return category
    # 원장 키가 비어도(해시태그만으로 된 제목) 키워드 추론은 계속한다
    return classify_category(title)


__all__ = [
    "CATEGORIES", "CATEGORY_KEYWORDS", "DEFAULT_CATEGORY", "LEDGER_VERSION",
    "UNKNOWN", "category_scores", "classify_category", "classify_haystack",
    "ledger_key",
    "load_ledger", "record_category", "resolve_category",
    "resolve_config_category",
]
