"""V3 하이브리드 정치쇼츠 planner — Gemini Stage A + Claude Stage B × 3.

Public entry point:
    generate_three_hybrid_plans() — Gemini로 원본 인용 후보 풀(4~6개) 추출 후,
    Claude를 angle별 3회 호출해 ThreeHybridPlansResult를 만든다.

V2 political_planner와 동일한 패턴이지만, 출력 객체는 HybridShortsPlan.
재시도/backoff/웹 폴백/JSON 파싱은 political_planner의 검증된 헬퍼를 재사용.
"""
from __future__ import annotations

import json as _json
import logging
import os
import time as _time
from datetime import datetime
from pathlib import Path

from src.analyzer.claude_analyzer import AnalyzerError, _call_claude
from src.analyzer.hybrid_plan_models import (
    HybridShortsPlan,
    PlanValidationError,
    ThreeHybridPlansResult,
)
from src.analyzer.hybrid_planner_stage_a_prompt import build_stage_a_hybrid_prompt
from src.analyzer.hybrid_planner_stage_b_prompt import build_stage_b_hybrid_prompt
from src.analyzer.political_planner import (
    PoliticalPlannerError,
    _extract_json_object,  # JSON 추출 헬퍼 재사용
)

logger = logging.getLogger(__name__)


class HybridPlannerError(Exception):
    """Raised when V3 hybrid 3-plan generation fails."""


_ANGLES = ("title_anchor", "audience_resonance", "comparison")
_BACKOFF = (1.0, 5.0, 15.0, 30.0)
_MAX_GEMINI_ATTEMPTS = 5
_MAX_CLAUDE_ATTEMPTS = 2


def _is_transient(err: Exception) -> bool:
    s = str(err)
    return any(t in s for t in (
        "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
        "DEADLINE", "INTERNAL", "TIMEOUT", "timeout",
    ))


def _backoff_sleep(attempt_idx: int, err: Exception) -> None:
    idx = min(attempt_idx, len(_BACKOFF) - 1)
    wait = _BACKOFF[idx] * (2 if _is_transient(err) else 1)
    logger.info("재시도 %.1fs 대기...", wait)
    _time.sleep(wait)


# ─────────────────────────── Stage A — Gemini ───────────────────────────


def _stage_a_hybrid_gemini(
    *,
    video_title: str,
    transcript: list[dict],
    video_duration_sec: float,
) -> list[dict]:
    """Gemini로 원본 인용 후보 4~6개 추출. 형식: list[OriginalCandidate dict]."""
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise HybridPlannerError(
            "GEMINI_API_KEY 환경변수가 필요합니다 (V3 Stage A)."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise HybridPlannerError(f"google-genai 패키지 미설치: {e}") from e

    prompt = build_stage_a_hybrid_prompt(
        video_title=video_title,
        transcript=transcript,
        video_duration_sec=video_duration_sec,
    )
    client = genai.Client(api_key=api_key)
    last_err: Exception | None = None

    for attempt in range(1, _MAX_GEMINI_ATTEMPTS + 1):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            last_err = e
            logger.warning(
                "V3 Stage A Gemini 실패 (%d/%d): %s",
                attempt, _MAX_GEMINI_ATTEMPTS, e,
            )
            if attempt < _MAX_GEMINI_ATTEMPTS:
                _backoff_sleep(attempt - 1, e)
            continue

        cand = resp.candidates[0] if resp.candidates else None
        if not cand or not cand.content or not cand.content.parts:
            last_err = HybridPlannerError("Gemini 빈 응답")
            if attempt < _MAX_GEMINI_ATTEMPTS:
                _backoff_sleep(attempt - 1, last_err)
            continue

        raw = cand.content.parts[0].text or ""
        try:
            data = _extract_json_object(raw)
        except PoliticalPlannerError as e:
            last_err = e
            if attempt < _MAX_GEMINI_ATTEMPTS:
                _backoff_sleep(attempt - 1, e)
            continue

        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(candidates, list) or not (4 <= len(candidates) <= 6):
            last_err = HybridPlannerError(
                f"V3 Stage A: candidates 4~6개 필요 — got "
                f"{len(candidates) if isinstance(candidates, list) else type(candidates).__name__}"
            )
            if attempt < _MAX_GEMINI_ATTEMPTS:
                _backoff_sleep(attempt - 1, last_err)
            continue

        # 최소 필드 검증
        valid = True
        for i, c in enumerate(candidates):
            for k in (
                "clip_start_sec", "clip_end_sec", "raw_text_summary",
                "quotability_score",
            ):
                if k not in c:
                    last_err = HybridPlannerError(
                        f"V3 Stage A: 후보 [{i}] 필드 {k!r} 누락"
                    )
                    valid = False
                    break
            # default fill
            c.setdefault("speaker_hint", "")
            c.setdefault("why_impactful", "")
            c.setdefault("topic_tag", "")
            c.setdefault("is_clean_audio", True)
            if not valid:
                break
        if not valid:
            if attempt < _MAX_GEMINI_ATTEMPTS:
                _backoff_sleep(attempt - 1, last_err)  # type: ignore[arg-type]
            continue

        # quotability_score 내림차순 정렬
        candidates.sort(key=lambda c: float(c.get("quotability_score", 0)), reverse=True)
        return candidates

    raise HybridPlannerError(
        f"V3 Stage A Gemini {_MAX_GEMINI_ATTEMPTS}회 실패: {last_err}"
    )


# ─────────────────────────── Stage B — Claude × 3 ───────────────────────────


def _stage_b_hybrid_claude(
    *,
    video_title: str,
    video_channel: str,
    angle: str,
    candidates_pool: list[dict],
    full_transcript: list[dict],
) -> dict:
    """Claude로 단일 angle에 대해 HybridShortsPlan dict 1개 생성."""
    prompt = build_stage_b_hybrid_prompt(
        video_title=video_title,
        video_channel=video_channel,
        angle=angle,
        candidates_pool=candidates_pool,
        full_transcript=full_transcript,
    )
    last_err: Exception | None = None

    for attempt in range(1, _MAX_CLAUDE_ATTEMPTS + 1):
        try:
            raw = _call_claude(prompt)
        except AnalyzerError as e:
            last_err = e
            logger.warning(
                "V3 Stage B Claude 실패 (%d/%d, angle=%s): %s",
                attempt, _MAX_CLAUDE_ATTEMPTS, angle, e,
            )
            continue
        try:
            data = _extract_json_object(raw)
        except PoliticalPlannerError as e:
            last_err = e
            continue
        if not isinstance(data, dict):
            last_err = HybridPlannerError("Stage B: 응답이 dict 아님")
            continue

        # 최소 필드 확인
        for k in ("topic", "hook", "beats", "cta", "angle"):
            if k not in data:
                last_err = HybridPlannerError(f"Stage B: 필드 {k!r} 누락")
                break
        else:
            return data

    raise HybridPlannerError(
        f"V3 Stage B Claude (angle={angle}) {_MAX_CLAUDE_ATTEMPTS}회 실패: {last_err}"
    )


# ─────────────────────────── public entry point ───────────────────────────


def generate_three_hybrid_plans(
    *,
    youtube_url: str,
    transcript: list[dict],
    video_title: str,
    video_duration_sec: float,
    video_path: str = "",
    transcript_path: str = "",
    output_dir: Path | None = None,
    video_channel: str = "",
) -> ThreeHybridPlansResult:
    """V3 하이브리드 3 angle 플랜 생성.

    호출 비용: Gemini 1회 + Claude 3회.
    출력 저장: output_dir/plans_hybrid.json (V2의 plans.json 옆에 공존).
    """
    logger.info("V3 Stage A: Gemini로 원본 인용 후보 추출 중...")
    pool = _stage_a_hybrid_gemini(
        video_title=video_title,
        transcript=transcript,
        video_duration_sec=video_duration_sec,
    )
    logger.info("V3 Stage A 완료: %d개 후보 (점수 평균 %.1f)",
                len(pool),
                sum(float(c.get("quotability_score", 0)) for c in pool) / max(len(pool), 1))

    # 영상 길이 클램프
    for c in pool:
        if float(c.get("clip_end_sec", 0)) > video_duration_sec:
            c["clip_end_sec"] = video_duration_sec

    plans: list[HybridShortsPlan] = []
    for i, angle in enumerate(_ANGLES, 1):
        logger.info("V3 Stage B[%d/3]: Claude로 angle=%s 조립 중...", i, angle)
        raw_dict = _stage_b_hybrid_claude(
            video_title=video_title,
            video_channel=video_channel,
            angle=angle,
            candidates_pool=pool,
            full_transcript=transcript,
        )
        # 메타데이터 보강 (LLM이 안 넣은 부분)
        raw_dict.setdefault("source_url", youtube_url)
        raw_dict.setdefault("source_channel", video_channel)
        raw_dict.setdefault("source_title", video_title)
        # angle은 LLM이 입력 angle 그대로 반환했는지 검증
        if raw_dict.get("angle") != angle:
            logger.warning(
                "Stage B angle mismatch (got=%s, expected=%s) — overriding",
                raw_dict.get("angle"), angle,
            )
            raw_dict["angle"] = angle

        # clip_end_sec 영상 길이 클램프 (원본 비트)
        for b in raw_dict.get("beats", []):
            if b.get("kind") == "original":
                end = float(b.get("clip_end_sec", 0))
                if end > video_duration_sec:
                    b["clip_end_sec"] = video_duration_sec

        try:
            plan = HybridShortsPlan.from_dict(raw_dict)
        except PlanValidationError as e:
            raise HybridPlannerError(
                f"V3 Stage B angle={angle} 검증 실패: {e}\n"
                f"raw: {_json.dumps(raw_dict, ensure_ascii=False)[:600]}"
            ) from e
        plans.append(plan)

    if len(plans) != 3:
        raise HybridPlannerError(f"3 plans 필요 (생성 {len(plans)})")

    result = ThreeHybridPlansResult(
        plans=(plans[0], plans[1], plans[2]),
        candidates_pool=tuple(pool),
        youtube_url=youtube_url,
        video_title=video_title,
        video_channel=video_channel,
        video_path=video_path,
        transcript_path=transcript_path,
        video_duration_sec=video_duration_sec,
        generated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_json = output_dir / "plans_hybrid.json"
        out_json.write_text(
            _json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("V3 기획안 저장: %s", out_json)

    return result


__all__ = [
    "HybridPlannerError",
    "generate_three_hybrid_plans",
]
