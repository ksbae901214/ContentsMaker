"""039 Phase 3 — V2.2 config 초안 자동 작성 + 게이트 재시도 루프.

지금까지 config 는 사람이 썼다. 무인 운영에서는 LLM 이 쓰되, **기존 게이트를
전부 통과할 때까지 자기 실패 사유를 되먹여 다시 쓴다.** 게이트는 새로 만들지
않는다 — `validate_config`(034 보도체·036 도메인 금지어) + `config_warnings`
(035 길이·CTA 형식·종결 말투)를 그대로 호출한다. 두 벌이 되면 조용히 갈라진다.

**게이트가 막지 못하는 것**: 밋밋한 훅, 어색한 자막 카피. 그래서 초기 2주는
review_gate 가 전부 보류하고 사람이 채택률을 잰다. 무수정 통과율이 50% 미만이면
"후보 3개 제시 → 사람이 번호 선택"으로 축소한다 (039 계획).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from scripts.auto_daily.cut_planner import Cut
from scripts.auto_daily.source_finder import SourceCandidate
from scripts.auto_daily.topic_ranker import TopicCluster
from scripts.shorts_domain import rules_for

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
#: 원본은 항상 하나다 — 컷이 그 영상 하나에서 나왔기 때문에.
SOURCE_KEY = "main"
_JSON_START = re.compile(r"[{]")


@dataclass(frozen=True)
class DraftResult:
    """초안 작성 결과. `ok` 가 False 면 다음 소재 후보로 넘어간다."""

    config: dict | None
    attempts: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    ok: bool


def extract_json(text: str) -> dict:
    """LLM 응답에서 첫 JSON 객체를 뽑는다. 코드펜스·앞뒤 설명을 견딘다."""
    for match in _JSON_START.finditer(text or ""):
        depth, in_string, escaped = 0, False, False
        for i in range(match.start(), len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[match.start():i + 1])
                    except ValueError:
                        break               # 다음 '{' 부터 다시 시도
                    if isinstance(parsed, dict):
                        return parsed
                    break
    raise ValueError("응답에서 JSON 객체를 찾지 못했습니다")


def check_config(cfg: dict) -> tuple[list[str], list[str]]:
    """(하드 오류, 경고). 예외를 문자열로 바꿔 LLM 에 되먹일 수 있게 한다."""
    from scripts.render_political_v2_1 import config_warnings
    from scripts.render_political_v2_2 import validate_config

    errors: list[str] = []
    warnings: list[str] = []
    try:
        warnings.extend(validate_config(cfg))
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    try:
        warnings.extend(config_warnings(cfg))
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors, warnings


# ── 프롬프트 ────────────────────────────────────────────────────────
_RULES = """\
[제작 규칙 — 어기면 렌더가 차단되거나 조회수가 무너진다]

1. 훅(scenes[0])은 **가진 클립 중 가장 센 컷**이다. 시간순으로 배열하지 마라 —
   그러면 상황 설명이 앞에 오고 절정이 뒤로 간다. 컷 후보를 세기 순으로 다시
   정렬해 1등을 scenes[0]에 놓는다. 순서를 바꿔 문맥이 깨지면 자막이 메운다.
2. 클립 씬(mode: "clip")의 start_sec/duration 은 **아래 컷 후보에서 그대로**
   가져온다. 임의로 바꾸면 말 끝맺음이 잘려 이탈이 는다.
   **scenes[0](훅)은 10.0초 이하 컷만 쓸 수 있다** — 넘으면 렌더가 차단된다.
   본문 클립은 12.0초까지 허용된다.
3. 제목(yt_title)은 15~30자. 공포·충격·호기심 톤이 기본값이되 **과거형 어미로
   끝내지 마라**('~했다/~밝혔다/~됐다'). 명사로 닫는다. 해시태그 금지.
   결과어가 드러나야 한다 — {outcome_example}
4. 마지막 씬은 CTA다. 편 가르는 선택지형(① / ②)으로 쓰고 나레이션은 반드시
   **"댓글로 알려주세요"로 닫는다**. 명사형·반말 종결('번호로 답글.') 금지 —
   부탁이 아니라 지시로 들린다. 나레이션 4초(약 32자) 이내.
5. 총 길이 38~42초. 넘으면 정보량이 가장 낮은 씬을 뺀다.
6. emotion_type 은 BGM 스위치다. 카테고리 기본값을 무심코 물려받지 말고 소재
   톤으로 직접 고른다 — 사실전달 relatable / 대립·규탄 angry / 비극 touching /
   축하·가벼움 funny(논란 소재 금지).
7. 자막(text)은 줄바꿈(\\n) 포함 2줄 이내, 한 줄 12자 안팎. hl 에 강조어를 넣는다.
8. 클립 씬은 원본 육성이라 voice 를 쓰지 않는다. tts 씬에만 voice 를 쓴다.
"""

_CATEGORY_NOTES = {
    "economic": (
        "[경제 주의] 투자 권유로 읽히는 표현은 렌더가 차단한다 — 매수·매도·추천주·"
        "존버·물타기·수익률 보장 등(유사투자자문 소지). 수치에는 출처와 기준시점을 "
        "붙인다. 경제의 절정은 표정이 아니라 '내 돈이 걸린 한 문장'이다 — 당사자 "
        "1인칭 항의·반문 > 화면에 숫자가 박힌 컷 > 당국자의 말 바꾸기 > 기자 나레이션."
    ),
    "society": (
        "[사회 주의] 확정되지 않은 피의사실을 단정하지 않는다. 판결·처분 등 "
        "'결과가 난 사건'만 다룬다."
    ),
    "entertainment": (
        "[연예 주의] 확인되지 않은 사생활을 단정하지 않는다. source_channel 을 "
        "반드시 채운다. 논평이 단죄로 읽히지 않도록 tts 씬은 사실 정리에 그친다."
    ),
    "political": (
        "[정치 주의] 결과 없는 공방형('A가 B를 직격')은 조회수 1,100대에서 멈춘다. "
        "결과가 난 사건으로 프레임을 잡는다."
    ),
}

_SCHEMA_HINT = """\
[출력] 아래 스키마의 **JSON 객체 하나만** 출력한다. 설명·코드펜스 없이.
{
  "category": "<카테고리>",
  "title": "<영상 상단 배너 제목, 20자 내외>",
  "yt_title": "<유튜브 제목>",
  "yt_title_alt": "<대안 제목>",
  "persons": ["<인물 또는 기관명>"],
  "emotion_type": "angry|relatable|touching|funny",
  "hashtags": ["#태그1", "#태그2", "#태그3"],
  "tts_speed": 1.1,
  "sources": {"main": {"url": "<자동 주입 — 그대로 두라>"}},
  "scenes": [
    {"mode": "clip", "source": "main", "start_sec": 0.0, "duration": 4.0,
     "speaker": "<발화자>", "text": "\\"자막\\n두 줄\\"", "hl": ["강조어"]},
    {"mode": "tts", "source": "main", "frac": 0.5, "color": "yellow",
     "text": "정리\\n자막", "voice": "나레이션 문장.", "hl": ["강조어"]}
  ]
}
"""


def build_prompt(topic: TopicCluster, candidate: SourceCandidate,
                 cuts: list[Cut], *, category: str, slug: str,
                 feedback: list[str] | None = None) -> str:
    """초안 작성 프롬프트. `feedback` 은 직전 시도의 게이트 실패 사유."""
    rules = rules_for(category)
    cut_lines = "\n".join(
        f"  [{i}] start_sec={c.start_sec:.1f} duration={c.duration:.1f} "
        f'전사="{c.text}"'
        for i, c in enumerate(cuts)
    ) or "  (없음 — 클립을 쓸 수 없다)"

    headlines = "\n".join(f"  - {a.title}" for a in topic.articles[:6])
    parts = [
        f"너는 {rules.label} 유튜브 쇼츠(9:16, 38~42초)의 제작 설정 JSON을 쓴다.",
        "",
        f"[소재] {topic.headline}",
        f"[반응] 관련 기사 {topic.article_count}건 / 총 {topic.total_metric:,}",
        f"[관련 헤드라인]\n{headlines}",
        "",
        f"[원본 영상] {candidate.title} — 채널 {candidate.channel} "
        f"({candidate.duration}초)",
        f"[말 끝맺음이 보장된 컷 후보]\n{cut_lines}",
        "",
        _RULES.format(outcome_example=rules.outcome_example),
        _CATEGORY_NOTES.get(category, ""),
        "",
        _SCHEMA_HINT,
    ]
    if feedback:
        parts += [
            "",
            "[이전 시도가 게이트에 걸렸다 — 아래를 전부 고쳐서 다시 써라]",
            *(f"  - {f}" for f in feedback),
        ]
    return "\n".join(parts)


# ── 재시도 루프 ─────────────────────────────────────────────────────
def _force_provenance(cfg: dict, *, slug: str, category: str,
                      candidate: SourceCandidate) -> dict:
    """LLM 이 지어낼 수 없어야 하는 값을 덮어쓴다.

    채널명·URL 을 지어내면 저작권 추적이 끊기고, slug 가 어긋나면 산출물이
    엉뚱한 디렉터리로 간다. 불변 원칙대로 새 dict 를 만든다.

    **sources 를 단일 URL 로 고정하는 것이 핵심이다.** 컷 타임스탬프는 특정
    영상에서 뽑은 값인데, config 가 검색어(`query`)를 쓰면 렌더러의 download
    단계가 같은 검색으로 **다른 영상**을 받아올 수 있다. 그러면 모든 클립이
    엉뚱한 구간을 가리킨다 — 렌더는 성공하고 내용만 틀리는 최악의 실패다.
    """
    dur_max = max(int(candidate.duration) + 60, 900)
    return {
        **cfg,
        "slug": slug,
        "category": category,
        "source_channel": candidate.channel,
        "source_title": candidate.title,
        "youtube_url": candidate.url,
        "sources": {SOURCE_KEY: {"url": candidate.url, "dur_max": dur_max,
                                 "verify_frac": 0.3}},
        "scenes": [{**scene, "source": SOURCE_KEY}
                   for scene in cfg.get("scenes", [])],
    }


def _call_claude_cli(prompt: str) -> str:
    from src.analyzer.claude_analyzer import _call_claude
    return _call_claude(prompt)


def draft_with_gates(topic: TopicCluster, candidate: SourceCandidate,
                     cuts: list[Cut], *, category: str, slug: str,
                     llm=None, max_attempts: int = MAX_ATTEMPTS) -> DraftResult:
    """게이트를 통과하는 config 가 나올 때까지 최대 `max_attempts` 회 재작성."""
    llm = llm or _call_claude_cli
    feedback: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    for attempt in range(1, max_attempts + 1):
        prompt = build_prompt(topic, candidate, cuts, category=category,
                              slug=slug, feedback=feedback)
        try:
            cfg = _force_provenance(extract_json(llm(prompt)), slug=slug,
                                    category=category, candidate=candidate)
        except Exception as exc:  # noqa: BLE001 — 어떤 실패든 재시도 사유로 쓴다
            logger.warning("[%s] 초안 %d회차 실패: %s", slug, attempt, exc)
            errors, feedback = [str(exc)], [str(exc)]
            continue

        errors, warnings = check_config(cfg)
        if not errors:
            return DraftResult(config=cfg, attempts=attempt, errors=(),
                               warnings=tuple(warnings), ok=True)
        logger.warning("[%s] 초안 %d회차 게이트 실패: %s", slug, attempt, errors)
        feedback = list(errors)

    return DraftResult(config=None, attempts=max_attempts, errors=tuple(errors),
                       warnings=tuple(warnings), ok=False)
