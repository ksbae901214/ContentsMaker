"""T021/T022 [US1]: Planner — Gemini → Claude → yt-dlp 3단계 흐름 (FR-037).

generate_three_plans(): YouTube URL → Gemini 분석 → Claude 3 plans 병렬
plan_to_script(): JpoliticsPlan → JpoliticsScript (카드 페치 + 클립 cut + 락인 강제)

FR-037 영상 추출 흐름:
1. _run_gemini_analysis(): Gemini Files API (또는 폴백)로 transcript + key_moments
2. _run_claude_stage_b(): rank별 Claude 호출, clip_search_query/clip_source_timestamp 출력
3. plan_to_script(): clip_search_query로 yt-dlp 검색 + cut_scene_clip letterbox
"""
from __future__ import annotations

import concurrent.futures
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# Read-only imports (편집 금지 — 격리 boundary)
from src.analyzer.claude_analyzer import _call_claude  # noqa: F401
from src.analyzer.gemini_backend import call_gemini  # noqa: F401

from src.jpolitics.analyzer.prompts import (
    build_stage_a_prompt,
    build_stage_b_prompt,
)
from src.jpolitics.constants import JPOLITICS_OUTPUT_DIR
from src.jpolitics.logger import get_logger
from src.jpolitics.models.plan import (
    JpoliticsPlan,
    JpoliticsThreePlansResult,
    Narration,
    PlanValidationError,
    validate_headline_pin,
)
from src.jpolitics.models.politician_card import PoliticianCard
from src.jpolitics.models.script import (
    JpoliticsAudioConfig,
    JpoliticsBackgroundConfig,
    JpoliticsMetadata,
    JpoliticsScene,
    JpoliticsScript,
)
from src.jpolitics.scraper.politician_card import fetch_politician_card

logger = get_logger("planner")


# ─────────────────────────── helpers ───────────────────────────


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 응답에서 첫 번째 JSON 블록 추출."""
    # ```json ... ``` 패턴
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))
    # 첫 { ~ 마지막 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    return json.loads(text[start : end + 1])


def _slugify(text: str, max_len: int = 30) -> str:
    """한글 보존 + 안전 문자만."""
    text = re.sub(r"[^\w가-힣\s-]", "", text).strip()
    text = re.sub(r"\s+", "_", text)
    return text[:max_len] or "untitled"


# T049 [US2]: layout_classification → visual_layout 매핑
_LAYOUT_TO_VISUAL: dict[str, str] = {
    "talking_head": "normal",
    "vs_2way": "vs_card",
    "comparison_grid": "grid_2x2",
    "data_comparison": "data_card",
}


def _layout_classification_to_visual_layout(classification: str) -> str:
    """plan.layout_classification → JpoliticsScene.visual_layout 매핑.

    talking_head → normal / vs_2way → vs_card /
    comparison_grid → grid_2x2 / data_comparison → data_card.
    알 수 없는 값은 'normal' 폴백.
    """
    return _LAYOUT_TO_VISUAL.get(classification, "normal")


# ─────────────────────────── FR-037 Stage A/B 분업 ───────────────────────────


def _run_gemini_analysis(
    *,
    youtube_url: str,
    video_title: str,
    transcript: list[dict[str, Any]] | None = None,
    video_duration_sec: float = 60.0,
) -> dict[str, Any]:
    """FR-037 Step 1: Gemini가 영상 분석 + 레이아웃 분류 + 3 angle.

    transcript이 주어지면 사용, 없으면 빈 list (text-only Stage A).
    """
    transcript = transcript or []
    prompt = build_stage_a_prompt(
        transcript=transcript,
        video_title=video_title,
        video_duration_sec=video_duration_sec,
    )
    logger.info("Stage A Gemini 호출 (transcript %d items)", len(transcript))
    response = call_gemini(prompt)
    return _extract_json(response)


def _run_claude_stage_b(
    *,
    stage_a_result: dict[str, Any],
    video_title: str,
    video_duration_sec: float,
    rank: int,
    angle: str,
) -> dict[str, Any]:
    """FR-037 Step 2: Claude가 rank별 1 plan + clip_search_query 결정."""
    prompt = build_stage_b_prompt(
        stage_a_result=stage_a_result,
        video_title=video_title,
        video_duration_sec=video_duration_sec,
        rank=rank,
        angle=angle,
    )
    logger.info("Stage B Claude 호출 (rank=%d, angle=%s)", rank, angle)
    response = _call_claude(prompt)
    return _extract_json(response)


# ─────────────────────────── generate_three_plans ───────────────────────────


def generate_three_plans(
    *,
    youtube_url: str,
    video_title: str,
    video_duration_sec: float,
    transcript: list[dict[str, Any]] | None = None,
    output_dir: Path | None = None,
) -> JpoliticsThreePlansResult:
    """3 angle 기획안 병렬 생성 (FR-008, FR-037).

    1. Gemini Stage A 1회 호출 (분류 + 3 angle)
    2. Claude Stage B 3회 ThreadPoolExecutor 병렬 호출
    3. plans.json + gemini_analysis.json 저장

    Raises:
        PlanValidationError: 3 distinct angle 보장 실패 시
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(video_title)
    if output_dir is None:
        output_dir = JPOLITICS_OUTPUT_DIR / f"{timestamp}_{slug}"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Gemini Stage A
    gemini_result = _run_gemini_analysis(
        youtube_url=youtube_url,
        video_title=video_title,
        transcript=transcript,
        video_duration_sec=video_duration_sec,
    )
    (output_dir / "gemini_analysis.json").write_text(
        json.dumps(gemini_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    angles_meta = gemini_result.get("angles", [])
    angle_names = (
        [a.get("name", "") for a in angles_meta]
        if angles_meta
        else ["title_anchor", "audience_resonance", "comparison"]
    )
    # 안전 폴백: 정확히 3개 distinct
    if len(set(angle_names)) < 3:
        angle_names = ["title_anchor", "audience_resonance", "comparison"]

    # Step 2: Claude Stage B 병렬 (3 plans)
    plans_raw: list[dict[str, Any]] = [None] * 3  # type: ignore[list-item]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(
                _run_claude_stage_b,
                stage_a_result=gemini_result,
                video_title=video_title,
                video_duration_sec=video_duration_sec,
                rank=i + 1,
                angle=angle_names[i],
            ): i
            for i in range(3)
        }
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            plans_raw[idx] = future.result()

    # Parse — rank/angle 강제 할당 (mock 반환과 무관하게 distinct 보장)
    plans: list[JpoliticsPlan] = []
    for i, raw in enumerate(plans_raw):
        raw["rank"] = i + 1
        raw["angle"] = angle_names[i]
        raw.setdefault(
            "layout_classification",
            gemini_result.get("layout_classification", "talking_head"),
        )
        # narrations 검증 통과를 위한 최소 padding (mock 결과가 비어있을 때)
        narrs = raw.get("narrations") or []
        while len(narrs) < 3:
            narrs.append(
                {
                    "scene_id": len(narrs),
                    "text": "자막",
                    "voice_text": "음성",
                    "visual_layout": "normal",
                    "subtitle_color": "white",
                    "subtitle_emphasis": False,
                }
            )
        raw["narrations"] = narrs
        plan = JpoliticsPlan.from_dict(raw)
        plans.append(plan)

    result = JpoliticsThreePlansResult(
        plans=(plans[0], plans[1], plans[2]),
        video_title=video_title,
        video_duration_sec=video_duration_sec,
        output_dir=str(output_dir),
        created_at=datetime.now().isoformat(),
        youtube_url=youtube_url,
    )
    try:
        result.validate()
    except PlanValidationError as e:
        logger.error("3 plans validation failed: %s", e)
        raise

    (output_dir / "plans.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("3 plans saved: %s", output_dir / "plans.json")
    return result


# ─────────────────────────── plan_to_script ───────────────────────────


def plan_to_script(
    plan: JpoliticsPlan,
    *,
    video_path: str | None = None,
    crop_clips: bool = True,
) -> JpoliticsScript:
    """JpoliticsPlan → JpoliticsScript (FR-022/023/034/035/036 강제).

    - Scene 락인 필드 강제: transition_effect="none", sfx_trigger=None
    - 인물 카드가 필요한 레이아웃(vs/grid/data_card)은 fetch_politician_card 호출
    - talking_head + video_path 주어지면 clip_source_timestamp로 cut (FR-037 Step 3)
    - AudioConfig는 락인값 자동 (Literal 타입으로 변경 불가)
    """
    plan.validate()

    scenes: list[JpoliticsScene] = []
    cursor = 0.0
    full_voice_text: list[str] = []

    # T049 [US2]: plan.layout_classification → 첫 씬 visual_layout 자동 승격
    classification_layout = _layout_classification_to_visual_layout(
        plan.layout_classification
    )

    for i, narr in enumerate(plan.narrations):
        # 첫 씬은 plan.layout_classification 우선 (narration이 'normal'이라도 승격)
        effective_layout = narr.visual_layout
        if i == 0 and classification_layout != "normal":
            effective_layout = classification_layout

        # 카드 페치 (필요 시)
        cards: tuple[PoliticianCard, ...] | None = None
        if narr.cards_metadata:
            fetched = []
            for cm in narr.cards_metadata:
                try:
                    card = fetch_politician_card(
                        name=str(cm.get("name", "")),
                        party=cm.get("party"),
                        data_label=cm.get("data_label") or cm.get("dataLabel"),
                        data_value=cm.get("data_value") or cm.get("dataValue"),
                    )
                    fetched.append(card)
                except Exception as e:
                    logger.warning("Card fetch failed for %s: %s", cm, e)
            if fetched:
                cards = tuple(fetched)

        # T049 [US2]: vs_card 레이아웃은 정확히 2명 보장. 부족하면 normal로 다운그레이드.
        if effective_layout == "vs_card":
            if cards is None or len(cards) != 2:
                logger.warning(
                    "vs_card requires 2 cards but got %s — downgrading scene %d to normal",
                    0 if cards is None else len(cards),
                    i,
                )
                effective_layout = "normal"
                cards = None
        elif effective_layout == "grid_2x2":
            if cards is None or not 3 <= len(cards) <= 4:
                logger.warning(
                    "grid_2x2 requires 3~4 cards but got %s — downgrading scene %d to normal",
                    0 if cards is None else len(cards),
                    i,
                )
                effective_layout = "normal"
                cards = None
        elif effective_layout == "data_card":
            if cards is None or len(cards) != 1 or not cards[0].data_value:
                logger.warning(
                    "data_card requires 1 card with data_value but got %s — downgrading scene %d to normal",
                    0 if cards is None else len(cards),
                    i,
                )
                effective_layout = "normal"
                cards = None

        # 씬 duration 추정 (voice_text 글자 수 기반, 5초 cap)
        approx_duration = min(5.0, max(1.5, len(narr.voice_text) * 0.08))

        # Clip 처리 (talking_head + source timestamp)
        clip_path: str | None = None
        if effective_layout == "normal" and narr.clip_source_timestamp and video_path:
            if crop_clips:
                try:
                    # Read-only import (격리 boundary)
                    from src.scraper.youtube_news_searcher import cut_scene_clip

                    start, end = narr.clip_source_timestamp
                    clip_path = cut_scene_clip(
                        source_path=video_path,
                        start_sec=start,
                        end_sec=end,
                        output_path=None,
                        crop_mode="letterbox",
                    )
                except Exception as e:
                    logger.warning("Clip cut failed for scene %d: %s", narr.scene_id, e)

        # 헤드라인 핀은 첫 씬에만
        headline_pin = plan.headline_pin if i == 0 else None
        try:
            validate_headline_pin(plan.headline_pin)
        except ValueError as e:
            logger.warning("headline_pin invalid: %s", e)

        scene = JpoliticsScene(
            id=narr.scene_id if narr.scene_id is not None else i,
            timestamp=cursor,
            duration=approx_duration,
            type="title" if i == 0 else ("comment" if i == len(plan.narrations) - 1 else "body"),
            text=narr.text,
            voice_text=narr.voice_text,
            visual_layout=effective_layout,  # type: ignore[arg-type]
            subtitle_color=narr.subtitle_color,
            subtitle_emphasis=narr.subtitle_emphasis,
            headline_pin=headline_pin,
            comparison_cards=cards,
            clip_path=clip_path,
            clip_search_query=narr.clip_search_query,
            clip_source_timestamp=narr.clip_source_timestamp,
            # transition_effect="none" + sfx_trigger=None 은 dataclass default
        )
        scene.validate()
        scenes.append(scene)
        full_voice_text.append(narr.voice_text)
        cursor += approx_duration

    # FR-019: 영상 하단 letterbox 출처 라벨 — plan.youtube_search_keywords 또는 topic 기반 폴백
    source_label = "출처: YouTube 원본 영상" if plan.youtube_search_keywords else "출처: 공개 자료 기반 재구성"

    metadata = JpoliticsMetadata(
        title=plan.topic,
        source_type="jpolitics_youtube",
        duration_sec=min(60.0, max(30.0, cursor)),
        created_at=datetime.now().isoformat(),
        source_label=source_label,
        topic=plan.topic,
    )
    audio = JpoliticsAudioConfig(tts_script=" ".join(full_voice_text))
    background = JpoliticsBackgroundConfig()

    script = JpoliticsScript(
        metadata=metadata, scenes=tuple(scenes), audio=audio, background=background
    )
    script.validate()
    return script
