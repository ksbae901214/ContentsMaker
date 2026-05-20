"""Political shorts planner — generates 3 plans from a YouTube video transcript
and converts a selected plan into a ShortsScript.

Two public entry points:
    - generate_three_plans(): Claude single-call → ThreePlansResult
    - plan_to_script(): ShortsPlan → ShortsScript (FR-011, FR-012, FR-013)

Constitutional principle VI: all output data is immutable (frozen dataclass).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from src.analyzer.claude_analyzer import (
    AnalyzerError,
    _call_claude,  # reuse existing transient-error retry logic
)
from src.analyzer.political_plan_models import (
    Narration,
    PlanValidationError,
    ShortsPlan,
    ThreePlansResult,
)
from src.analyzer.political_planner_prompt import build_political_planner_prompt
from src.analyzer.political_planner_stage_a_prompt import build_stage_a_prompt
from src.analyzer.political_planner_stage_b_prompt import build_stage_b_prompt
from src.analyzer.script_models import (
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.config.settings import DATA_DIR, MAX_SCENE_DURATION_SECONDS
from src.editor.scene_ops import split_scenes_to_max_duration
from src.tts.voice_config import get_voice_config, get_gradient

logger = logging.getLogger(__name__)


class PoliticalPlannerError(Exception):
    """Raised when 3-plan generation or conversion fails."""


# ─────────────────────────────── generate_three_plans ───────────────────────────────


def generate_three_plans(
    *,
    youtube_url: str,
    transcript: list[dict],
    video_title: str,
    video_duration_sec: float,
    video_path: str | None = None,
    transcript_path: str | None = None,
    output_dir: Path | None = None,
    use_hybrid: bool = True,
    video_channel: str = "",
) -> ThreePlansResult:
    """Generate exactly 3 ShortsPlan candidates (Hybrid: Gemini + Claude).

    Hybrid pipeline (use_hybrid=True, default):
      Stage A — Gemini: items 1,2,3 (topic / hook / clip section + reason) for 3
                        candidates in a single JSON call.
      Stage B — Claude: items 4,5,6 (flow_intro/middle/climax + narrations + cta)
                        for each candidate, called 3 times sequentially.

    Legacy mode (use_hybrid=False): single Claude call producing all 6 items.
    Used for unit tests that mock _call_claude.

    Args:
        youtube_url: YouTube source URL.
        transcript: [{"start": float, "end": float, "text": str}, ...].
        video_title: Source video title.
        video_duration_sec: Total video duration (seconds).
        video_path / transcript_path: optional artifact paths.
        output_dir: Where to save plans.json. Defaults to
            ``data/political_pro/{timestamp}_{slug}/``.
        use_hybrid: True → Gemini(1,2,3) + Claude(4,5,6). False → Claude all-in-one.

    Returns:
        ThreePlansResult containing 3 distinct-angle plans + paths.

    Raises:
        PoliticalPlannerError: on stage failure or schema violation.
    """
    logger.info("정치 기획안 3개 생성 시작 (hybrid=%s) — %s", use_hybrid, youtube_url)

    if use_hybrid:
        plans = _generate_three_plans_hybrid(
            youtube_url=youtube_url,
            transcript=transcript,
            video_title=video_title,
            video_duration_sec=video_duration_sec,
        )
    else:
        plans = _generate_three_plans_legacy(
            transcript=transcript,
            video_title=video_title,
            video_duration_sec=video_duration_sec,
        )

    try:
        result = ThreePlansResult(
            plans=plans,
            youtube_url=youtube_url,
            video_path=video_path or "",
            video_duration_sec=video_duration_sec,
            transcript_path=transcript_path or "",
            video_title=video_title,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            video_channel=video_channel or "",
        )
    except PlanValidationError as e:
        raise PoliticalPlannerError(f"3 기획안 검증 실패: {e}") from e

    # Persist plans.json for traceability.
    target_dir = output_dir
    if target_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _safe_slug(video_title) or "politicalpro"
        target_dir = DATA_DIR / "political_pro" / f"{timestamp}_{slug}"
    target_dir.mkdir(parents=True, exist_ok=True)
    plans_path = target_dir / "plans.json"
    plans_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("기획안 저장: %s", plans_path)

    return result


def _generate_three_plans_legacy(
    *,
    transcript: list[dict],
    video_title: str,
    video_duration_sec: float,
) -> tuple[ShortsPlan, ShortsPlan, ShortsPlan]:
    """기존 단일 Claude 호출 방식 (테스트 호환)."""
    prompt = build_political_planner_prompt(
        video_title=video_title,
        transcript=transcript,
        video_duration_sec=video_duration_sec,
    )
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            raw = _call_claude(prompt)
        except AnalyzerError as e:
            last_error = e
            logger.warning("Claude 호출 실패 (시도 %d/2): %s", attempt, e)
            continue
        try:
            return _parse_three_plans(raw, video_duration_sec=video_duration_sec)
        except (PoliticalPlannerError, PlanValidationError, ValueError) as e:
            last_error = e
            logger.warning("Claude 응답 파싱 실패 (시도 %d/2): %s", attempt, e)
            continue
    raise PoliticalPlannerError(f"3 기획안 생성 실패 (legacy 2회 시도 모두): {last_error}")


def _generate_three_plans_hybrid(
    *,
    youtube_url: str,
    transcript: list[dict],
    video_title: str,
    video_duration_sec: float,
) -> tuple[ShortsPlan, ShortsPlan, ShortsPlan]:
    """Stage A (Gemini, 1+2+3) → Stage B (Claude, 4+5+6) × 3."""
    # ── Stage A — Gemini로 후보 3개의 골격 추출 ──
    logger.info("Stage A: Gemini로 후보 3개 추출 중...")
    candidates = _stage_a_gemini(
        video_title=video_title,
        transcript=transcript,
        video_duration_sec=video_duration_sec,
    )
    logger.info("Stage A 완료: %d개 후보", len(candidates))

    # Clamp clip ranges to video duration (FR-013)
    for c in candidates:
        if c.get("clip_end_sec", 0) > video_duration_sec:
            c["clip_end_sec"] = video_duration_sec

    # ── Stage B — 각 후보에 대해 Claude로 4,5,6 생성 ──
    plans: list[ShortsPlan] = []
    for i, candidate in enumerate(candidates, 1):
        logger.info("Stage B[%d/3]: Claude로 4,5,6 생성 (angle=%s)", i, candidate.get("angle"))
        clip_segs = _filter_transcript_to_clip(
            transcript,
            start=float(candidate["clip_start_sec"]),
            end=float(candidate["clip_end_sec"]),
        )
        details = _stage_b_claude(
            video_title=video_title,
            candidate=candidate,
            full_transcript=transcript,
            clip_transcript=clip_segs,
        )
        # Merge stage A (1,2,3 + 포맷) + stage B (4,5,6 + 자막색·시각연출) into a
        # single ShortsPlan dict. V2 (Feature 011): format_type/visual_directives.
        merged = {
            "topic": candidate.get("topic", ""),
            "hook": candidate.get("hook", ""),
            "clip_start_sec": float(candidate.get("clip_start_sec", 0.0)),
            "clip_end_sec": float(candidate.get("clip_end_sec", 0.0)),
            "clip_reason": candidate.get("clip_reason", ""),
            "flow_intro": details.get("flow_intro", ""),
            "flow_middle": details.get("flow_middle", ""),
            "flow_climax": details.get("flow_climax", ""),
            "narrations": details.get("narrations", []),
            "cta": details.get("cta", ""),
            "angle": candidate.get("angle", ""),
            # V2 — Stage A에서 포맷 분류
            "format_type": candidate.get("format_type", "A"),
            "format_reason": candidate.get("format_reason", ""),
            # V2 — Stage B에서 시각 연출 지시
            "visual_directives": details.get("visual_directives", []),
        }
        try:
            plans.append(ShortsPlan.from_dict(merged))
        except PlanValidationError as e:
            raise PoliticalPlannerError(
                f"Stage B 후보 {i} 병합 결과 검증 실패: {e}"
            ) from e

    if len(plans) != 3:
        raise PoliticalPlannerError(f"3개 plan 필요, {len(plans)}개 생성됨")

    return plans[0], plans[1], plans[2]


_SPLIT_KEYWORDS = ("분할", "split", "좌(", "좌:", "Left:", "left:")
_SPLIT_TIME_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*~\s*(\d+(?:\.\d+)?)\s*초")


def _apply_visual_directives_to_scenes(
    scenes: list[Scene],
    directives: tuple[str, ...],
) -> list[Scene]:
    """V2 Phase B: visual_directives에 '분할'/'split' 키워드 → 매칭 씬에 layout=split.

    디렉티브에 "0~3초", "12~15초" 같은 시각 범위가 있으면 그 범위와 겹치는 씬에만,
    범위가 없으면 첫 body 씬에 적용.
    """
    if not directives:
        return scenes

    # 분할 디렉티브 추출
    split_dirs = [d for d in directives if any(kw in d for kw in _SPLIT_KEYWORDS)]
    if not split_dirs:
        return scenes

    targets: set[int] = set()  # scene id 집합
    for d in split_dirs:
        m = _SPLIT_TIME_RANGE_RE.search(d)
        if m:
            r_start, r_end = float(m.group(1)), float(m.group(2))
            for s in scenes:
                s_start = s.timestamp
                s_end = s.timestamp + s.duration
                # 시간 범위와 겹치는 씬
                if s_start < r_end and s_end > r_start:
                    targets.add(s.id)
        else:
            # 범위 없음 → 첫 body 씬
            body_scenes = [s for s in scenes if s.type == "body"]
            if body_scenes:
                targets.add(body_scenes[0].id)

    if not targets:
        return scenes

    # 매칭 씬에 visual_layout="split" 적용 (불변성 — replace로 새 인스턴스)
    return [
        replace(s, visual_layout="split") if s.id in targets else s
        for s in scenes
    ]


def _filter_transcript_to_clip(
    transcript: list[dict], *, start: float, end: float, padding: float = 2.0,
) -> list[dict]:
    """Clip 구간에 해당하는 transcript 세그먼트만 필터 (Stage B 입력용)."""
    return [
        s for s in transcript
        if s.get("start", 0) >= start - padding
        and s.get("end", 0) <= end + padding
    ]


def _stage_a_gemini(
    *,
    video_title: str,
    transcript: list[dict],
    video_duration_sec: float,
) -> list[dict]:
    """Stage A: Gemini API로 후보 3개의 골격(topic/hook/clip) 추출.

    Returns: list of dicts with keys topic, hook, clip_start_sec, clip_end_sec,
             clip_reason, angle. Raises PoliticalPlannerError on failure.
    """
    import os
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise PoliticalPlannerError(
            "GEMINI_API_KEY 환경변수가 설정되지 않았습니다 "
            "(political_pro hybrid 모드는 Stage A에 Gemini 필요)."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise PoliticalPlannerError(f"google-genai 패키지 미설치: {e}") from e

    prompt = build_stage_a_prompt(
        video_title=video_title,
        transcript=transcript,
        video_duration_sec=video_duration_sec,
    )

    client = genai.Client(api_key=api_key)
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            last_error = e
            logger.warning("Stage A Gemini 호출 실패 (시도 %d/2): %s", attempt, e)
            continue

        cand = response.candidates[0] if response.candidates else None
        if not cand or not cand.content or not cand.content.parts:
            last_error = PoliticalPlannerError(
                f"Gemini 빈 응답 (finish_reason={getattr(cand, 'finish_reason', 'N/A')})"
            )
            logger.warning("Stage A 빈 응답 (시도 %d/2)", attempt)
            continue

        raw = cand.content.parts[0].text or ""
        try:
            data = _extract_json_object(raw)
        except PoliticalPlannerError as e:
            last_error = e
            logger.warning("Stage A JSON 파싱 실패 (시도 %d/2): %s", attempt, e)
            continue

        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(candidates, list) or len(candidates) != 3:
            last_error = PoliticalPlannerError(
                f"Stage A: candidates 배열(3개) 누락 — got {type(candidates).__name__}"
            )
            logger.warning("Stage A schema 위반 (시도 %d/2): %s", attempt, last_error)
            continue

        # 각 항목에 angle/topic/hook/clip_*가 있는지 최소 검증
        # V2: format_type도 검증하되 누락 시 default("A")로 보강 (V1 호환).
        for c in candidates:
            if "format_type" not in c:
                c["format_type"] = "A"  # default fallback
            if "format_reason" not in c:
                c["format_reason"] = ""
            for k in ("topic", "hook", "clip_start_sec", "clip_end_sec", "angle"):
                if k not in c:
                    last_error = PoliticalPlannerError(f"Stage A: 필드 {k!r} 누락")
                    break
            else:
                continue
            break
        else:
            return candidates

    raise PoliticalPlannerError(
        f"Stage A (Gemini) 실패 (2회 시도 모두): {last_error}"
    )


def _stage_b_claude(
    *,
    video_title: str,
    candidate: dict,
    full_transcript: list[dict],
    clip_transcript: list[dict],
) -> dict:
    """Stage B: Claude로 단일 candidate의 4,5,6 (flow/narrations/cta) 생성."""
    prompt = build_stage_b_prompt(
        video_title=video_title,
        candidate=candidate,
        full_transcript=full_transcript,
        clip_transcript=clip_transcript,
    )
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            raw = _call_claude(prompt)
        except AnalyzerError as e:
            last_error = e
            logger.warning("Stage B Claude 호출 실패 (시도 %d/2): %s", attempt, e)
            continue
        try:
            data = _extract_json_object(raw)
        except PoliticalPlannerError as e:
            last_error = e
            logger.warning("Stage B JSON 파싱 실패 (시도 %d/2): %s", attempt, e)
            continue
        if not isinstance(data, dict):
            last_error = PoliticalPlannerError("Stage B: 응답이 dict 아님")
            continue
        # 최소 필드 확인
        for k in ("flow_intro", "flow_middle", "flow_climax", "narrations", "cta"):
            if k not in data:
                last_error = PoliticalPlannerError(f"Stage B: 필드 {k!r} 누락")
                break
        else:
            return data
        logger.warning("Stage B schema 위반 (시도 %d/2)", attempt)

    raise PoliticalPlannerError(
        f"Stage B (Claude) 실패 (2회 시도 모두): {last_error}"
    )


def _parse_three_plans(
    raw: str, *, video_duration_sec: float,
) -> tuple[ShortsPlan, ShortsPlan, ShortsPlan]:
    """Parse Claude's response and clamp clip ranges to video duration."""
    data = _extract_json_object(raw)
    plans_raw = data.get("plans") if isinstance(data, dict) else None
    if not isinstance(plans_raw, list) or len(plans_raw) != 3:
        raise PoliticalPlannerError(
            f"응답에 plans 배열(3개)이 없습니다: {str(data)[:200]}"
        )

    clamped: list[ShortsPlan] = []
    for raw_plan in plans_raw:
        if not isinstance(raw_plan, dict):
            raise PoliticalPlannerError(f"plan 항목이 객체가 아님: {raw_plan!r}")
        # Clamp clip_end_sec ≤ video_duration_sec (FR-013).
        end = float(raw_plan.get("clip_end_sec", raw_plan.get("clipEndSec", 0.0)))
        if end > video_duration_sec:
            raw_plan["clip_end_sec"] = video_duration_sec
            raw_plan.pop("clipEndSec", None)
        plan = ShortsPlan.from_dict(raw_plan)
        clamped.append(plan)

    return clamped[0], clamped[1], clamped[2]


def _extract_json_object(raw: str) -> dict:
    """Extract a JSON object from a possibly markdown-wrapped Claude response."""
    text = (raw or "").strip()
    # Direct JSON.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "result" in obj and isinstance(obj["result"], str):
            return _extract_json_object(obj["result"])
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # ```json ... ``` fence.
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # First {...} block.
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    raise PoliticalPlannerError(f"JSON 객체 추출 실패: {text[:200]}")


def _safe_slug(s: str) -> str:
    cleaned = "".join(c for c in (s or "")[:30] if c.isalnum() or c in " _-")
    return cleaned.strip().replace(" ", "_")


# ─────────────────────────────── plan_to_script ───────────────────────────────


# 자막 분할 + 줄바꿈 알고리즘은 src/editor/subtitle_split.py로 추출 (2026-05-20 Phase 6+).
# 모든 영상 생성 경로(blind/topic/celebrity/political/political_pro)가 공유.
from src.editor.subtitle_split import (
    _MAX_SUBTITLE_CHARS,
    _insert_linebreak,
    _score_split_position,
    _split_subtitle_segments,
)


def plan_to_script(
    plan: ShortsPlan,
    *,
    video_title: str,
    video_duration_sec: float,
    youtube_url: str,
    source_channel: str = "",
    source_title: str = "",
    output_dir: Path | None = None,
    save: bool = True,
) -> ShortsScript:
    """Convert a selected ShortsPlan into a ShortsScript (FR-011).

    - Hook → 첫 씬 텍스트
    - 각 Narration → Scene (≤ MAX_SCENE_DURATION_SECONDS, 자동 분할)
    - CTA → 마지막 추가 씬
    - source_type = "political_pro"
    - clip_end_sec ≤ video_duration_sec 클램프 (FR-013)
    """
    clip_start = max(0.0, plan.clip_start_sec)
    clip_end = min(plan.clip_end_sec, video_duration_sec)
    if clip_end <= clip_start:
        raise PoliticalPlannerError(
            f"클램프 후 clip 범위가 유효하지 않음 (start={clip_start}, end={clip_end})"
        )

    emotion = "angry"  # 정치 모드 기본 — 강한 톤
    vc = get_voice_config(emotion)
    gradient = get_gradient(emotion)

    scenes: list[Scene] = []

    def _add_split_scenes(
        *,
        text: str,
        total_duration: float,
        scene_type: str,
        color: str,
        emphasis: bool,
    ) -> None:
        """텍스트가 길면 28자 세그먼트로 분할해 여러 씬 추가.
        2026-05-16 사용자 요청: "..." 생략 금지, 분할 표시.
        Phase 3 (2026-05-20): 같은 원본 문장의 분할 자식들에 동일 group_id 부여.
        SceneText.tsx가 group_first=False면 fade-in 생략 → 같은 문장 안에서 끊김 제거.
        """
        segs = _split_subtitle_segments(text)
        if not segs:
            return
        per_seg = max(0.6, total_duration / len(segs))
        nonlocal_cursor = scenes[-1].timestamp + scenes[-1].duration if scenes else 0.0
        # 분할이 일어나는 경우(2+개 segs)에만 group_id 부여. 단일 세그먼트는 group_id=None.
        group_id = len(scenes) if len(segs) >= 2 else None
        for j, seg in enumerate(segs):
            scenes.append(Scene(
                id=len(scenes),
                timestamp=nonlocal_cursor,
                duration=per_seg,
                type=scene_type,
                text=seg,
                # 각 분할 자식도 자기 자막 텍스트로 TTS 합성 → 음성도 자연스럽게 분할.
                # char ratio로 timing 자동 분배되어 자막·음성·영상 동기화 보장.
                voice_text=seg,
                emphasis=emphasis,
                highlight_words=(),
                subtitle_color=color,
                subtitle_emphasis=emphasis,
                subtitle_group_id=group_id,
                subtitle_group_first=(j == 0),
            ))
            nonlocal_cursor += per_seg

    # Scene 0 — Hook
    _add_split_scenes(
        text=plan.hook,
        total_duration=min(3.0, MAX_SCENE_DURATION_SECONDS),
        scene_type="title",
        color="yellow",
        emphasis=True,
    )

    for narr in plan.narrations:
        narr_dur = max(0.5, narr.end_sec - narr.start_sec)
        _add_split_scenes(
            text=narr.text,
            total_duration=narr_dur,
            scene_type="body",
            color=narr.subtitle_color,
            emphasis=narr.subtitle_emphasis,
        )

    # CTA
    _add_split_scenes(
        text=plan.cta,
        total_duration=3.0,
        scene_type="comment",
        color="yellow",
        emphasis=True,
    )
    cursor = scenes[-1].timestamp + scenes[-1].duration if scenes else 0.0

    # 2026-05-16: split-screen 자동 적용 비활성화 (사용자 피드백).
    # 정치_pro 모드는 원본 영상 1개만 있어서 좌·우/상·하 분할이 동일 영상의
    # 다른 구간만 보여줘 어색함. 진짜 비교 클립이 있을 때만 의미 있음 → Phase D
    # (수동 secondary_clip_path 지정)로 미룸. 자동 매핑 OFF.
    # scenes = _apply_visual_directives_to_scenes(scenes, plan.visual_directives)

    total_duration = min(cursor, 60.0)

    script = ShortsScript(
        metadata=Metadata(
            title=plan.topic,
            emotion_type=emotion,
            duration=total_duration,
            source_url=youtube_url,
            source_type="political_pro",
            source_channel=source_channel or "",
            source_title=source_title or video_title or "",
            # V2 — 추적·디버깅용 (Phase A에서는 렌더 비활용, Phase B에서 분기 키로 사용)
            format_type=getattr(plan, "format_type", "") or "",
            format_reason=getattr(plan, "format_reason", "") or "",
            visual_directives=tuple(getattr(plan, "visual_directives", ()) or ()),
        ),
        scenes=tuple(scenes),
        audio=AudioConfig(
            tts_script=" ".join(s.voice_text for s in scenes if s.voice_text),
            voice=vc["voice"],
            rate=vc["rate"],
            pitch=vc["pitch"],
        ),
        background=BackgroundConfig(type="gradient", colors=tuple(gradient)),
    )

    # FR-012 — split any scene > MAX_SCENE_DURATION_SECONDS
    script = split_scenes_to_max_duration(script)

    if save:
        from src.config.settings import DATA_SCRIPTS_DIR
        target_dir = output_dir or DATA_SCRIPTS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _safe_slug(plan.topic) or "politicalpro"
        path = target_dir / f"{timestamp}_{slug}_political_pro.json"
        script.save(path)
        logger.info("political_pro 스크립트 저장: %s", path)

    return script


__all__ = [
    "PoliticalPlannerError",
    "generate_three_plans",
    "plan_to_script",
]
