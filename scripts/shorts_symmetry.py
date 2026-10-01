"""진영 대칭·기록 대조 검사 (040) — 중도를 포지션이 아니라 상품으로.

**측정 배경**: 2026-09-04 스냅샷 133편의 제목 진영 감사.

| 구분 | 편수 | 조회수 중앙 |
|---|---|---|
| 여권만 등장 | 21 | 1,400 |
| 야권만 등장 | 22 | 1,300 |
| 양쪽 등장 | 32 | 1,297 |

인물별로도 국민의힘 39편 / 이재명 27편 / 민주당 21편 / 장동혁 13편으로 **채널
전체로 보면 이미 균형**이다. 그런데 셋 다 1,300이다. 즉 이 채널의 중도는 성과를
만들지 못하고 있다.

원인 진단: **균형이 133편 단위로만 존재하고 한 편 단위로는 없다.** 시청자는 133편을
보지 않고 한 편을 본다. 한 편에 한쪽 진영만 나오면 그 편은 진영 콘텐츠로 읽히고,
반대 진영 시청자는 이탈하고 같은 진영 시청자는 이 채널을 구독할 이유가 없다
(더 세게 말해주는 진영 채널이 있다).

**벤치마크 근거**: 진영 채널 9곳의 구독자 대비 쇼츠 중앙값은 0.1~3.8%인데,
중도·설명형인 김지윤의 지식Play 4.8% / 슈카월드 10.4%가 그 전부를 이긴다.
진영 채널은 감정을 팔고 중도 채널은 이해를 판다 — 중도가 이기려면 '누구 편도
안 든다'가 아니라 **'양쪽을 같은 잣대로 잰다'**가 화면에 보여야 한다.

두 가지를 본다:

1. **진영 대칭** — 한 편의 제목·자막에 양쪽 진영이 다 등장하는가.
   V2.2 릴레이 포맷(육성 클립 2~3개)이 이 구조를 이미 담을 수 있으므로
   파이프라인 변경이 아니라 **클립 선정 규칙**의 문제다.
2. **기록 대조 프레임** — '과거 발언 vs 현재 행동'인가. 채널 정치편 상위가 전부
   이 프레임이다 (용혜인 내로남불 5,118 / 유시민 왕정 비유 2,492 /
   '다주택은 손 떼라'더니 4채 2,200 / 이재명 근저당 내로남불 1,800).
   이 소재는 양쪽 모두에게 성립하므로 중도 포지션이 자동으로 유지된다.

**판정 범위**: 제목 + 씬 자막(`text`)만 본다. 나레이션(`voice`)은 제외 — 039
`frame_text` 와 같은 이유로, 대칭은 **화면에 보여야** 시청자의 판단에 반영된다.

**정책**: 전부 경고, 차단 없음 (035/036/039와 같은 방침). 사전에 없는 인물이면
경고하지 않는다 — 오탐으로 경고를 남발하면 게이트 전체가 무시당한다.
우회: `"symmetry_gate": "off"`.

**한계**: 진영 사전은 수동 목록이라 신인·비주류 인물은 못 잡는다. 그리고 이
모듈이 검사하는 건 '양쪽이 등장하는가'이지 '같은 잣대로 다뤘는가'가 아니다.
후자는 사람이 판단해야 한다 — 체크리스트에 남겨 두었다.
"""
from __future__ import annotations

from dataclasses import dataclass

GATE_KEY = "symmetry_gate"
GATE_OFF = "off"

LEFT = "left"      # 여권·진보 진영
RIGHT = "right"    # 야권·보수 진영

# 진영 사전 — 소문자로 비교한다(영문 제목이 실측 절반가량). 한글은 대소문자가
# 없으므로 그대로 매칭된다. 인물명은 낡는 신호라 정기 갱신이 필요하다.
LEFT_MARKERS: tuple[str, ...] = (
    "이재명", "조국", "용혜인", "정청래", "추미애", "김어준", "유시민",
    "박찬대", "정원오", "김민석", "한성숙", "안규백",
    "민주당", "더불어민주당", "기본소득당", "조국혁신당", "진보당",
    "여당", "여권", "친명", "친문",
    "lee jae-myung", "leejaemyung", "cho kuk", "chokuk", "cho guk",
    "yong hye-in", "yonghyein", "rhyu si-min", "democratic party",
    "ruling party", "chung chung-rae",
)

RIGHT_MARKERS: tuple[str, ...] = (
    "장동혁", "한동훈", "오세훈", "박근혜", "윤석열", "나경원", "정점식",
    "추경호", "이준석", "김문수", "안철수", "홍준표", "박형준", "조경태",
    "이명박", "박성훈", "이진숙",
    "국민의힘", "개혁신당", "자유한국당", "야당", "야권", "친윤", "친한",
    "han dong-hoon", "handonghoon", "oh se-hoon", "people power",
    "park geun-hye", "yoon suk-yeol", "choo kyung-ho", "lee jun-seok",
    "opposition party",
)

# 한 단어로 양쪽을 가리키는 표현 — 개별 진영 매칭으로는 안 잡힌다
BOTH_MARKERS: tuple[str, ...] = (
    "여야", "양당", "여야정", "both parties", "across the aisle",
)

# 축 3 — '과거 발언 vs 현재 행동' 프레임 신호.
# 경고를 *띄우지 않기 위한* 검사라 오탐은 무해하다(경고가 안 뜰 뿐).
RECORD_CONTRAST_WORDS: tuple[str, ...] = (
    "내로남불", "이중잣대", "위선", "말바꾸", "말 바꾸", "번복", "뒤집",
    "돌변", "정반대", "달라진", "달라졌", "그때는", "당시엔", "당시는",
    "라더니", "더니", "했었", "약속", "과거 발언", "년 전", "개월 전",
    "지난해엔", "작년엔", "기록", "발언 대조",
    "flip-flop", "back then", "years ago", "once said", "double standard",
    "hypocrisy", "u-turn", "reversal",
)


@dataclass(frozen=True)
class SymmetryVerdict:
    """한 config 의 대칭·프레임 판정. 전부 불변 — 조회만 한다."""

    sides: frozenset[str]
    left_hits: tuple[str, ...]
    right_hits: tuple[str, ...]
    contrast_hits: tuple[str, ...]

    @property
    def symmetric(self) -> bool:
        """양쪽 진영이 다 화면에 등장하는가."""
        return self.sides == frozenset({LEFT, RIGHT})

    @property
    def one_sided(self) -> bool:
        """한쪽만 등장 — 진영 콘텐츠로 읽힌다."""
        return len(self.sides) == 1

    @property
    def record_contrast(self) -> bool:
        return bool(self.contrast_hits)


def _normalize(text: str) -> str:
    return text.lower()


def _hits(text: str, words: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(w for w in words if w in text)


def sides_in(text: str) -> frozenset[str]:
    """텍스트에 등장하는 진영 집합. 사전에 없으면 빈 집합."""
    low = _normalize(text)
    if _hits(low, BOTH_MARKERS):
        return frozenset({LEFT, RIGHT})
    found = set()
    if _hits(low, LEFT_MARKERS):
        found.add(LEFT)
    if _hits(low, RIGHT_MARKERS):
        found.add(RIGHT)
    return frozenset(found)


def has_record_contrast(text: str) -> bool:
    """'과거 발언 vs 현재 행동' 프레임 신호가 있는가."""
    return bool(_hits(_normalize(text), RECORD_CONTRAST_WORDS))


def symmetry_text(cfg: dict) -> str:
    """판정 대상 텍스트 — 제목 + 씬 자막.

    나레이션(`voice`)은 제외한다. 대칭은 화면에 보여야 시청자 판단에 반영된다
    (039 `frame_text` 와 같은 판단).
    """
    parts = [cfg.get("yt_title", ""), cfg.get("yt_title_alt", ""),
             cfg.get("title", "")]
    parts += [sc.get("text", "") for sc in (cfg.get("scenes") or [])]
    return " ".join(p for p in parts if p)


def gate_disabled(cfg: dict) -> bool:
    return cfg.get(GATE_KEY) == GATE_OFF


def evaluate_symmetry(cfg: dict) -> SymmetryVerdict:
    """대칭·프레임을 판정한다. 순수 함수 — config 를 바꾸지 않는다."""
    text = _normalize(symmetry_text(cfg))
    both = _hits(text, BOTH_MARKERS)
    left = _hits(text, LEFT_MARKERS) or (both if both else ())
    right = _hits(text, RIGHT_MARKERS) or (both if both else ())
    return SymmetryVerdict(
        sides=sides_in(symmetry_text(cfg)),
        left_hits=left,
        right_hits=right,
        contrast_hits=_hits(text, RECORD_CONTRAST_WORDS),
    )


def symmetry_warnings(cfg: dict) -> list[str]:
    """040 중도 상품화 경고 (하드 오류 아님). 우회: `"symmetry_gate": "off"`.

    정치 카테고리에만 적용한다 — 사회·경제·연예 편은 진영 대칭이 개념상 성립하지
    않는다. 041: 같은 이유로 **인물 1명을 다루는 V3.0 프로필 포맷**도 제외한다
    (`FormatRules.symmetry_applies`).
    """
    if gate_disabled(cfg):
        return []
    from scripts.shorts_category import resolve_config_category
    if resolve_config_category(cfg) != "political":
        return []
    from scripts.shorts_format import rules_for_config
    if not rules_for_config(cfg).symmetry_applies:
        return []

    v = evaluate_symmetry(cfg)
    warnings: list[str] = []

    if v.one_sided:
        side_label = "여권" if LEFT in v.sides else "야권"
        hits = ", ".join(v.left_hits or v.right_hits)
        warnings.append(
            f"[040] 한쪽 진영({side_label})만 등장합니다 ({hits}) — 채널 전체는 "
            "여권 21편/야권 22편으로 균형이지만 시청자는 한 편만 봅니다. "
            "반대 진영의 같은 사안 육성 클립을 한 컷 넣어 대칭으로 만드세요.")

    if not v.record_contrast:
        warnings.append(
            "[040] 기록 대조 프레임이 없습니다 ('과거 발언 vs 현재 행동') — "
            "정치편 상위가 전부 이 프레임입니다 (용혜인 내로남불 5,118 / "
            "'다주택은 손 떼라'더니 4채 2,200). 양쪽 모두에게 성립하는 소재라 "
            "중도 포지션이 자동으로 유지됩니다.")

    return warnings


def symmetry_line(cfg: dict) -> str:
    """업로드 패키지·콘솔에 한 줄로 남길 판정 요약."""
    v = evaluate_symmetry(cfg)
    if not v.sides:
        sides = "진영 미검출"
    elif v.symmetric:
        sides = "양쪽"
    else:
        sides = "여권만" if LEFT in v.sides else "야권만"
    contrast = "O" if v.record_contrast else "X"
    return f"중도 판정 — 진영 {sides}, 기록 대조 {contrast}"


__all__ = [
    "BOTH_MARKERS", "GATE_KEY", "GATE_OFF", "LEFT", "LEFT_MARKERS",
    "RECORD_CONTRAST_WORDS", "RIGHT", "RIGHT_MARKERS", "SymmetryVerdict",
    "evaluate_symmetry", "gate_disabled", "has_record_contrast", "sides_in",
    "symmetry_line", "symmetry_text", "symmetry_warnings",
]
