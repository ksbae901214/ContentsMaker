"""자막 분할 + 명시적 줄바꿈 공용 모듈.

2026-05-20 Phase 6+: political_planner.py 전용이던 알고리즘을 모든 영상 생성 경로
(blind, topic, manual, url, celebrity, political, political_pro)가 공유하도록 추출.

핵심:
    - _split_subtitle_segments(text): 28자 초과 텍스트를 한국어 조사·종결어미·구두점 점수화로 자연스럽게 분할.
    - _insert_linebreak(text): 15자 초과면 14자 부근에 명시적 '\\n' 삽입.
    - apply_subtitle_split(script): ShortsScript의 모든 씬에 위 알고리즘 적용. 분할 자식들에 동일 subtitle_group_id 부여.

엣지-TTS는 같은 group_id의 연속 자식들을 1번에 합성(`edge_tts_generator._group_scenes_by_subtitle_group`) → 무음 누적 제거.
SceneText.tsx는 group_first=False면 fade-in 생략 → 분할 자식 끊김 없음.
"""
from __future__ import annotations

from src.analyzer.script_models import Scene, ShortsScript

_MAX_SUBTITLE_CHARS = 28  # 한 자막 2줄 한계 (폰트 56px 기준 14자/줄 × 2)

_PUNCTUATION = set(".,!?·…")
# 한국 종결어미 단음절 — "...했다", "...지요", "...까", "...네" 같은 자연스러운 문장 끝
_ENDINGS_FINAL = set("다요까네지죠군라")
# 한국 조사 단음절 — "정책을", "후보가" 의 끝 글자. 어절 경계 표시.
_PARTICLES_SHORT = set("을를이가은는의에와과도만로서며고데니죠")


def _score_split_position(text: str, i: int, max_chars: int) -> float:
    """위치 i에서 분할(left=text[:i], right=text[i:])했을 때 자연스러운 정도.

    높을수록 좋은 경계. 0 = 단어 중간(수용 불가).
    점수 체계:
        10 — 구두점 + 공백 ("문장1. " 직후)
         9 — 구두점만 ("문장1," 직후)
         8 — 종결어미 + 공백 ("했어요 " 직후)
         6 — 조사 + 공백 ("정책을 " 직후)
         4 — 일반 공백
         0 — 어절 중간
    + 균형 보너스 (최대 2): max_chars/2 부근일수록 가산.
    """
    if i <= 0 or i >= len(text):
        return 0.0

    prev = text[i - 1]
    prev2 = text[i - 2] if i >= 2 else ""

    if prev == " ":
        if prev2 in _PUNCTUATION:
            base = 10.0
        elif prev2 in _ENDINGS_FINAL:
            base = 8.0
        elif prev2 in _PARTICLES_SHORT:
            base = 6.0
        else:
            base = 4.0
    elif prev in _PUNCTUATION:
        base = 9.0
    else:
        return 0.0

    center = max_chars / 2
    deviation = abs(i - center) / max(center, 1.0)
    balance = 2.0 * max(0.0, 1.0 - deviation)

    return base + balance


def _insert_linebreak(text: str, target_line_chars: int = 14) -> str:
    """한 자막을 명시적 '\\n'으로 2줄 분할. CSS word-break:keep-all에 의존하지 않고
    코드로 줄바꿈 위치를 통제해 orphan 줄(짧은 단어 외톨이) 방지.

    target_line_chars(=14) 부근에서 _score_split_position 동일 점수화 적용.
    좋은 경계 못 찾으면 원문 그대로 반환 (CSS 폴백).
    """
    if len(text) <= target_line_chars or "\n" in text:
        return text

    lo = max(1, int(target_line_chars * 0.5))
    hi = min(len(text), target_line_chars * 2 - 1)

    best_score = 0.0
    best_pos = -1
    for i in range(lo, hi + 1):
        s = _score_split_position(text, i, target_line_chars * 2)
        deviation = abs(i - target_line_chars) / target_line_chars
        focus_bonus = 1.5 * max(0.0, 1.0 - deviation)
        s = s + focus_bonus
        if s > best_score:
            best_score = s
            best_pos = i

    if best_pos < 0:
        return text

    left = text[:best_pos].rstrip()
    right = text[best_pos:].lstrip()
    if not left or not right:
        return text
    return f"{left}\n{right}"


def _split_subtitle_segments(text: str, max_chars: int = _MAX_SUBTITLE_CHARS) -> list[str]:
    """긴 텍스트를 max_chars 이내 세그먼트로 분할 (말줄임표 사용 안 함).

    분할 방식:
        - max_chars*0.25 ~ max_chars 범위의 모든 후보 위치 점수화
        - 최고점 위치 선택 (구두점 > 종결어미 > 조사 > 일반공백)
        - 좋은 경계 없으면 max_chars 직후 ~ +3자 까지 확장 탐색
        - 모두 실패 시 max_chars에서 강제 분할 (한국어 음절 단위 — 손상 없음)
    + 단일 세그먼트도 15자+면 명시적 '\\n' 삽입.
    """
    text = (text or "").strip()
    if not text:
        return []
    # AI가 의도적으로 넣은 '\n' 보존 — 줄별로 max_chars 이내면 원본 그대로.
    if "\n" in text:
        lines = [line.strip() for line in text.split("\n")]
        if all(len(line) <= max_chars for line in lines):
            return [text]
        # 한 줄이라도 max_chars 초과면 전체 재분할 (줄바꿈 무시하고 재계산)
        flat = " ".join(lines)
        return _split_subtitle_segments(flat, max_chars)
    if len(text) <= max_chars:
        return [_insert_linebreak(text)]

    segments: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            segments.append(remaining)
            break

        # 25%부터 탐색 — 균형 보너스가 너무 짧은 first segment를 자연 억제하면서도
        # 강한 구두점 경계(예: "안녕하세요. ")는 7자 위치에서도 포착 가능.
        lo = max(1, int(max_chars * 0.25))
        hi = min(len(remaining), max_chars)

        best_score = 0.0
        best_pos = -1
        for i in range(lo, hi + 1):
            s = _score_split_position(remaining, i, max_chars)
            if s > best_score:
                best_score = s
                best_pos = i

        # 1차 범위에서 좋은 경계 못 찾으면 max_chars 직후 ~ +3자 확장.
        if best_score == 0.0:
            overflow_hi = min(len(remaining), max_chars + 3)
            for i in range(hi + 1, overflow_hi + 1):
                s = _score_split_position(remaining, i, max_chars)
                if s > 0:
                    best_score = s
                    best_pos = i
                    break

        if best_pos < 0:
            best_pos = hi

        left = remaining[:best_pos].rstrip(" ,.·")
        if left:
            segments.append(left)
        remaining = remaining[best_pos:].lstrip()

    return [_insert_linebreak(s) for s in segments if s]


def apply_subtitle_split(
    script: ShortsScript,
    max_chars: int = _MAX_SUBTITLE_CHARS,
) -> ShortsScript:
    """ShortsScript의 모든 씬에 자막 분할 + 명시적 줄바꿈 적용.

    - 28자 초과 씬 → 자식 씬들로 분할, 동일 subtitle_group_id 부여 (첫 자식만 group_first=True)
    - 15자 초과 단일 씬 → 명시적 '\\n' 삽입 (그룹 ID 부여 안 함)
    - 모든 V2 필드 (subtitle_color, subtitle_emphasis, hook, highlight_category, image_query 등) 보존
    - 자식 씬들의 duration은 글자수 비율로 분배 (최소 0.6s)
    - timestamp는 마지막에 재계산

    이 함수는 idempotent — 이미 분할된 씬에 다시 호출해도 안전 (각 씬이 max_chars 이내).
    """
    if not script.scenes:
        return script

    new_scenes: list[Scene] = []
    next_id = 0
    cursor = 0.0
    # 새 group_id를 부여할 때 기존 그룹과 충돌 안 하게 max+1부터 시작
    existing_gids = [s.subtitle_group_id for s in script.scenes if s.subtitle_group_id is not None]
    next_group_id = (max(existing_gids) + 1) if existing_gids else 1

    for scene in script.scenes:
        segs = _split_subtitle_segments(scene.text, max_chars)
        if not segs:
            # 빈 텍스트 — 원본 그대로 유지
            new_scenes.append(_replace_scene(scene, id=next_id, timestamp=cursor))
            next_id += 1
            cursor += scene.duration
            continue

        if len(segs) == 1:
            # 분할 없음 — \n만 적용된 단일 씬. 그룹 ID 부여 안 함 (단독 씬은 group_id 유지).
            new_scenes.append(_replace_scene(
                scene,
                id=next_id,
                timestamp=cursor,
                text=segs[0],
            ))
            next_id += 1
            cursor += scene.duration
            continue

        # 분할됨 — 자식 씬들로 교체 + 그룹 ID 부여 (기존 group_id 있으면 유지)
        gid = scene.subtitle_group_id if scene.subtitle_group_id is not None else next_group_id
        if scene.subtitle_group_id is None:
            next_group_id += 1
        # 글자수 비율로 duration 분배 (최소 0.6s/자식)
        total_chars = sum(len(s.replace("\n", "")) for s in segs) or 1
        for ci, seg in enumerate(segs):
            char_count = len(seg.replace("\n", ""))
            child_dur = max(0.6, scene.duration * char_count / total_chars)
            # 각 자식이 자기 voice_text — TTS 그룹 단위 합성으로 무음 누적 제거됨.
            voice_text = seg.replace("\n", " ").strip()
            new_scenes.append(_replace_scene(
                scene,
                id=next_id,
                timestamp=cursor,
                duration=round(child_dur, 2),
                text=seg,
                voice_text=voice_text,
                subtitle_group_id=gid,
                subtitle_group_first=(ci == 0),
                # hook은 첫 자식에만 (펀치줌 1회만 발동)
                hook=scene.hook if ci == 0 else False,
            ))
            next_id += 1
            cursor += child_dur

    return ShortsScript(
        metadata=script.metadata,
        scenes=tuple(new_scenes),
        audio=script.audio,
        background=script.background,
    )


def _replace_scene(scene: Scene, **changes) -> Scene:
    """frozen Scene 변경 — 모든 필드 보존 + 변경 사항 덮어쓰기.

    `dataclasses.replace` 대안 (Scene이 frozen). subtitle_group_id 등 V2 필드까지 안전하게 보존.
    """
    from dataclasses import replace
    return replace(scene, **changes)


__all__ = [
    "apply_subtitle_split",
    "_split_subtitle_segments",
    "_insert_linebreak",
    "_score_split_position",
    "_MAX_SUBTITLE_CHARS",
]
