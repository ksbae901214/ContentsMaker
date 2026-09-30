"""돌파 조건 게이트 (039) — 조회수 밴드를 뚫는 소재의 3조건.

**측정 배경**: 2026-09-03 스냅샷 130편. 조회수 중앙 1,300 / 75%분위 2,200 /
90%분위 3,149. 즉 이 채널의 조회수는 1,000~2,200 밴드에 갇혀 있고, 3,000회
이상은 16편(12%)뿐이다. 소재·인물·언어·제목 유형을 87편(정치) 바꿔가며 시도해도
분포가 안 흔들렸다 — **편차를 만드는 건 제작 품질이 아니라 소재 조건**이다.

돌파 여부를 가른 조건 (3,000회+ = '돌파'):

| 조건 조합 | 편수 | 중앙 | 돌파율 |
|---|---|---|---|
| 민간인 × 대가 치름 | 6 | 6,071 | **83%** |
| 민간인 (대가 무관) | 8 | 5,873 | 75% |
| 정치인 × 진영 무관 반칙 | 8 | 1,800 | 25% |
| 어디에도 안 걸림 | 107 | 1,300 | 7% |
| **정치인 × 당내 정치** | 7 | 959 | **0%** |
| 정치인 × 대가 × 당내 정치 | 6 | 921 | **0%** |

세 조건으로 정리된다:

1. **당사자가 진영 밖 인물인가** — 민간인·연예인 돌파율 75%, 직업 정치인 9%.
   시청자가 *진영을 확인하지 않고* 화낼 수 있어야 한다. 정치인은 지지자와
   반대자가 정반대로 반응해서 어느 쪽도 끝까지 볼 이유가 없다. 정치인이라도
   정책이 아니라 **반칙**(겸직·귀빈실·내로남불)이면 부분 통과(25%).
2. **당사자가 이미 대가를 치렀는가** — 사과·취소·폐쇄·사퇴·박탈·진실 폭로.
   해당 22편 돌파율 36% vs 나머지 7%. 주의: **중앙값은 1,521 vs 1,300으로
   거의 같은데 돌파율만 5배**다. 이 조건은 평균을 올리는 게 아니라 상한을
   넘을 티켓을 준다.
3. **사건이 끝났는가** — 당내 정치(제명·재신임·공천·청원·낙선·징계)는
   **13편 연속 0%**. ②를 갖춰도 ③을 어기면 죽는다. 반례가 명확하다:
   장동혁 제명 위기 1,500 / 조국 징역 2년 1,471 / 오세훈 시장직 상실형 1,100 /
   한동훈 제명 1,100 / 이진숙 복귀 반전 581 / 장동혁 재신임 조건 **16회**.
   전부 '대가' 어휘를 달고 있는데 전멸이다. 당내 처벌은 시청자에게 결말이
   아니라 **진행 중인 편싸움**으로 읽힌다.

**증폭기(조건 아님)**: 뚫린 소재는 후속도 뚫린다. 박위 55,523 → 7,002 → 6,208,
용혜인 4,226 → 3,300 → 3,149. 반대로 밴드 안 소재의 후속은 그대로 밴드 안
(조국 1,471 → 1,248). 한 편이 뚫리면 새 소재를 찾기 전에 후속을 먼저 붙인다.

**035 결과 프레임과의 관계**: 035 `_OUTCOME_WORDS` 는 *사건이* 결말났는지를 본다
(철회·부결·타결). 039 `COST_WORDS` 는 *당사자가* 무엇을 잃었는지를 본다
(사과·취소·박탈). 겹치지만 다른 축이라 따로 둔다 — 035는 '결과가 났나',
039는 '누가 값을 치렀나'.

**정책**: 전부 경고, 차단 없음. 035 길이 캡·036 도메인 게이트와 같은 방침으로
과거 config 는 그대로 두고 신규만 이 기준을 적용한다. 우회: `"breakout_gate": "off"`.

**신뢰도**: ③(당내 정치 0%)은 13편 전멸이라 강하다. ①②는 민간인 표본이 8~11편,
그중 박위 3편이 들어 있어 83%는 "6편 중 5편"이다. 방향은 분명하나 배수는
아직 확정이 아니다 — 이 기준으로 5~6편 더 찍으면 판정된다.
"""
from __future__ import annotations

from dataclasses import dataclass

GATE_KEY = "breakout_gate"
GATE_OFF = "off"
SUBJECT_KEY = "subject_type"

CIVILIAN = "civilian"
POLITICIAN = "politician"
INSTITUTION = "institution"
SUBJECT_TYPES = (CIVILIAN, POLITICIAN, INSTITUTION)

# 돌파 기준 — 2026-09-03 스냅샷의 3,000회(90%분위 3,149 근처)
BREAKOUT_VIEWS = 3000

# ① 당사자가 직업 정치인인지 — 제목·인물명에 붙는 직함
POLITICIAN_MARKERS = (
    "의원", "장관", "대표", "시장", "지사", "총리", "대통령", "후보", "위원장",
    "청장", "원내", "당선", "여당", "야당", "국회", "민주당", "국민의힘",
    "조국혁신당", "기본소득당", "정의당",
)

# ② 당사자가 치른 대가 — 잃은 것이 제목에 드러나는가
COST_WORDS = (
    "사과", "취소", "철회", "폐쇄", "중단", "떠난", "떠났", "물러", "사퇴",
    "해임", "경질", "파면", "박탈", "제외", "하차", "손절", "폐지",
    "유죄", "실형", "징역", "구속", "벌금", "배상",
    "들통", "발각", "탄로", "진실", "실체", "뒤집", "반전", "역전", "컴백",
)

# ③ 당내 정치 = 돌파율 0% (13편 전멸). 가장 강한 하방 신호.
INNER_PARTY_WORDS = (
    "제명", "재신임", "징계", "공천", "경선", "원구성", "상임위", "당명",
    "전당원", "전당대회", "당대표", "최고위", "지도부", "당권", "계파",
    "청원", "낙선", "보이콧", "당론", "탈당", "복당", "출마 선언",
)

# ③ 아직 진행 중 = 결말 없음. 035 공방 프레임과 같은 방향의 하방 신호.
UNSETTLED_WORDS = (
    "논의", "공방", "촉구", "요구", "주장", "추진", "발의", "제안", "검토",
    "예정", "전망", "계획", "방침", "예고", "협상", "설명",
)

# ①의 예외 — 정치인이라도 진영 무관 '반칙'이면 부분 통과 (돌파율 25%)
PARTISAN_FREE_FOUL_WORDS = (
    "내로남불", "위선", "이중잣대", "특권", "귀빈실", "겸직", "갑질",
    "다주택", "근저당", "탈영", "병역", "위장전입", "새치기", "무전취식",
    "말바꾸", "말 바꾸", "거짓 해명", "사생활",
)

# 등급 — 실측 돌파율을 그대로 라벨에 박아 기획 단계에서 비교되게 한다
TIER_A = "A"
TIER_B = "B"
TIER_C = "C"
TIER_DEAD = "DEAD"

_TIER_NOTE = {
    TIER_A: "민간인 당사자 — 실측 돌파율 75~83%",
    TIER_B: "정치인 + 진영 무관 반칙 — 실측 돌파율 25%",
    TIER_C: "조건 미충족 — 실측 돌파율 7% (밴드 1,000~2,200에 갇힘)",
    TIER_DEAD: "당내 정치 — 실측 돌파율 0% (13편 전멸)",
}


@dataclass(frozen=True)
class BreakoutVerdict:
    """한 config 의 돌파 조건 판정. 전부 불변 — 조회만 한다."""

    tier: str
    subject_type: str
    partisan_free: bool     # ① 진영 밖 인물인가
    cost_paid: bool         # ② 대가를 치렀는가
    settled: bool           # ③ 사건이 끝났는가
    hits: tuple[str, ...]   # 판정 근거가 된 어휘

    @property
    def note(self) -> str:
        return _TIER_NOTE[self.tier]

    @property
    def conditions_met(self) -> int:
        return sum((self.partisan_free, self.cost_paid, self.settled))


def _has(text: str, words: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(w for w in words if w in text)


def gate_disabled(cfg: dict) -> bool:
    return cfg.get(GATE_KEY) == GATE_OFF


def subject_text(cfg: dict) -> str:
    """당사자 판정용 텍스트 — 제목과 인물명만 본다.

    씬 자막까지 넣으면 정치 소재를 인용한 연예 편이 정치인으로 오분류된다.
    """
    parts = [cfg.get("yt_title", ""), cfg.get("yt_title_alt", ""),
             cfg.get("title", ""), *(cfg.get("persons") or [])]
    return " ".join(p for p in parts if p)


def title_text(cfg: dict) -> str:
    """소재 판정용 텍스트 — 제목만.

    ③(당내 정치·진행 중)은 **제목으로만** 판정한다. 씬 자막까지 넣었더니
    배경 서술 한 단어로 오판이 났다 — '조국은 왜 방배동을 안 팔까'(개인 위선
    소재)가 자막의 "어제 전당대회 영상 축사" 때문에 당내 정치로 분류됐다.
    소재의 정체는 제목이 정한다.
    """
    parts = [cfg.get("yt_title", ""), cfg.get("yt_title_alt", ""),
             cfg.get("title", "")]
    return " ".join(p for p in parts if p)


def frame_text(cfg: dict) -> str:
    """②(대가) 판정용 텍스트 — 제목 + 씬 자막.

    나레이션(voice)은 제외한다. 대가·결말은 화면에 보여야 클릭에 반영된다.
    """
    parts = [cfg.get("yt_title", ""), cfg.get("yt_title_alt", ""),
             cfg.get("title", "")]
    parts += [sc.get("text", "") for sc in (cfg.get("scenes") or [])]
    return " ".join(p for p in parts if p)


# 036 카테고리 → 당사자 기본값. 직함이 안 붙은 정치인 이름("용혜인 내로남불")을
# 민간인으로 오판하면 게이트가 조용히 통과시켜 버린다 — 가장 위험한 실패라
# 카테고리를 1차 신호로 쓰고, 예외는 config 에 `subject_type` 으로 명시한다.
_CATEGORY_SUBJECT = {
    "political": POLITICIAN,
    "economic": INSTITUTION,
    "society": CIVILIAN,
    "entertainment": CIVILIAN,
}


def infer_subject_type(cfg: dict) -> str:
    """당사자 유형 — 명시값 > 직함 > 카테고리 기본값 순.

    추정은 보조 수단이다. 정치 카테고리인데 당사자가 민간인인 편(공무원 갑질
    피해자 등)은 config 에 `"subject_type": "civilian"` 을 직접 박아야 한다.
    """
    declared = cfg.get(SUBJECT_KEY)
    if declared in SUBJECT_TYPES:
        return declared
    if _has(subject_text(cfg), POLITICIAN_MARKERS):
        return POLITICIAN
    from scripts.shorts_category import resolve_config_category
    default = _CATEGORY_SUBJECT.get(resolve_config_category(cfg), POLITICIAN)
    if default == CIVILIAN and not cfg.get("persons"):
        return INSTITUTION
    return default


def evaluate(cfg: dict) -> BreakoutVerdict:
    """3조건을 판정해 등급을 매긴다. 순수 함수 — config 를 바꾸지 않는다."""
    subject = infer_subject_type(cfg)
    title = title_text(cfg)

    inner = _has(title, INNER_PARTY_WORDS)
    unsettled = _has(title, UNSETTLED_WORDS)
    cost = _has(frame_text(cfg), COST_WORDS)
    foul = _has(subject_text(cfg) + " " + frame_text(cfg),
                PARTISAN_FREE_FOUL_WORDS)

    partisan_free = subject == CIVILIAN or bool(foul)
    settled = not inner and not unsettled
    hits = tuple(dict.fromkeys(inner + unsettled + cost + foul))

    if inner:
        tier = TIER_DEAD
    elif subject == CIVILIAN:
        tier = TIER_A
    elif foul and settled:
        tier = TIER_B
    else:
        tier = TIER_C

    return BreakoutVerdict(
        tier=tier, subject_type=subject, partisan_free=partisan_free,
        cost_paid=bool(cost), settled=settled, hits=hits,
    )


def breakout_warnings(cfg: dict) -> list[str]:
    """039 돌파 조건 경고 (하드 오류 아님). 우회: `"breakout_gate": "off"`."""
    if gate_disabled(cfg):
        return []
    v = evaluate(cfg)
    warnings: list[str] = []

    if v.tier == TIER_DEAD:
        inner = ", ".join(_has(title_text(cfg), INNER_PARTY_WORDS))
        warnings.append(
            f"[039] 제목이 당내 정치 소재({inner}) — 실측 돌파율 0% (13편 전멸). "
            "제명·재신임·공천 같은 당내 처벌은 시청자에게 결말이 아니라 "
            "진행 중인 편싸움으로 읽힙니다. 소재를 바꾸는 걸 권합니다.")
        return warnings

    # 제목은 멀쩡한데 자막이 당내 정치로 끌고 가는 경우 — 판정은 안 바꾸고 알린다
    scene_inner = [w for w in _has(frame_text(cfg), INNER_PARTY_WORDS)
                   if w not in title_text(cfg)]
    if scene_inner:
        warnings.append(
            f"[039] 자막에 당내 정치 어휘({', '.join(scene_inner)}) — 제목은 "
            "통과했지만 본문이 당내 편싸움으로 흐르면 완주율이 떨어집니다.")

    # 041: V3.0 인물 프로필은 정치인 소재가 기본값이라 아래 세 경고가 매 편 전부
    # 붙는다. 사용자가 실측을 알고 택한 포맷이므로(2026-09-14) 개별 지적 대신
    # 1회 고지로 낮춘다 — 경고를 남발하면 게이트 전체가 무시당한다(040 방침).
    # 당내 절차(DEAD)만은 위에서 그대로 차단 수준의 경고를 낸다.
    from scripts.shorts_format import rules_for_config
    if rules_for_config(cfg).breakout_notice_only:
        warnings.append(
            f"[039] 인물 프로필(V3.0) — 등급 {v.tier}. 정치인 인물편은 실측 "
            "돌파율 9%입니다 (political 90편 중앙 1,255회 / 민간인 소재 75~83%). "
            "사용자 확정 포맷이라 개별 경고는 생략합니다 — 파일럿 8~10편 뒤 "
            "포맷별 중앙값으로 판정하세요 (041 §7).")
        return warnings

    if not v.partisan_free:
        warnings.append(
            "[039] 당사자가 직업 정치인이고 '진영 무관 반칙' 프레임도 아닙니다 "
            "— 실측 돌파율 9%. 겸직·특권·내로남불처럼 지지 성향과 무관하게 "
            "화낼 수 있는 반칙으로 좁히면 25%까지 올라갑니다.")
    if not v.cost_paid:
        warnings.append(
            "[039] 당사자가 치른 대가가 제목·자막에 없습니다 (사과·취소·사퇴·"
            "박탈·진실 폭로) — 실측 돌파율 7% vs 36%. 대가가 아직 안 나왔으면 "
            "나올 때까지 미루는 편이 낫습니다.")
    if not v.settled and v.tier != TIER_DEAD:
        unsettled = ", ".join(_has(title_text(cfg), UNSETTLED_WORDS))
        warnings.append(
            f"[039] 아직 진행 중인 사건({unsettled}) — 결말이 없으면 밴드에 "
            "갇힙니다 (035 공방 프레임과 같은 하방).")
    return warnings


def verdict_line(cfg: dict) -> str:
    """업로드 패키지·콘솔에 한 줄로 남길 판정 요약."""
    v = evaluate(cfg)
    marks = "".join("O" if c else "X"
                    for c in (v.partisan_free, v.cost_paid, v.settled))
    return (f"돌파 등급 {v.tier} ({v.note}) — 진영밖/대가/종결 = {marks}, "
            f"당사자 {v.subject_type}")


__all__ = [
    "BREAKOUT_VIEWS", "CIVILIAN", "COST_WORDS", "GATE_KEY", "GATE_OFF",
    "INNER_PARTY_WORDS", "INSTITUTION", "PARTISAN_FREE_FOUL_WORDS",
    "POLITICIAN", "SUBJECT_KEY", "SUBJECT_TYPES", "TIER_A", "TIER_B",
    "TIER_C", "TIER_DEAD", "UNSETTLED_WORDS", "BreakoutVerdict",
    "breakout_warnings", "evaluate", "frame_text", "gate_disabled",
    "title_text",
    "infer_subject_type", "subject_text", "verdict_line",
]
