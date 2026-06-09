"""T019/T020 [US1]: Stage A (Gemini) + Stage B (Claude) 프롬프트.

Stage A: 영상 transcript + 레이아웃 4종 분류 + 3 angle 생성.
Stage B: rank별 1개 plan 생성 (6요소 + headline_pin + clip_search_query).
"""
from __future__ import annotations

import json
from typing import Any

STAGE_A_LAYOUT_EXAMPLES = """
[레이아웃 4종 예시]
- talking_head: 정치인 1인의 인터뷰/연설/논평 (예: 조국 사퇴 기자회견)
- vs_2way: 두 정치인의 대결/대립 (예: 양향자 vs 추미애 경기도지사 대결)
- comparison_grid: 3~4인 후보 비교 (예: 평택을 후보 4명 재산 비교)
- data_comparison: 1인 + 수치 데이터 강조 (예: "조국 재산 56억 5년간 0원")
""".strip()


def build_stage_a_prompt(
    *,
    transcript: list[dict[str, Any]],
    video_title: str,
    video_duration_sec: float,
) -> str:
    """Stage A: Gemini가 영상 분석 + 레이아웃 분류 + 3 angle 생성."""
    transcript_text = "\n".join(
        f"[{t.get('start', 0):.1f}~{t.get('end', 0):.1f}] {t.get('text', '')}"
        for t in transcript[:60]  # 너무 길면 자르기
    )
    return f"""당신은 정치 쇼츠 제작 분석가입니다.

## 입력 영상
제목: {video_title}
길이: {video_duration_sec:.1f}초

## Transcript
{transcript_text}

## 작업
1. 영상 분석 후 핵심 시각 구조를 4종 중 하나로 분류:
{STAGE_A_LAYOUT_EXAMPLES}

2. 3개 서로 다른 angle 도출:
- title_anchor: 영상 제목을 후크로 (가장 안전)
- audience_resonance: 시청자 공감 포인트 강조
- comparison: 다른 인물/사건과 비교

3. 핵심 발언 timestamp 추출 (key_moments)

## 출력 형식 (JSON only, no markdown)
{{
  "layout_classification": "talking_head" | "vs_2way" | "comparison_grid" | "data_comparison",
  "transcript": [{{"start": float, "end": float, "text": str}}, ...],
  "key_moments": [{{"start": float, "end": float, "summary": str}}, ...],
  "angles": [
    {{"name": "title_anchor", "topic": str, "hook": str, "reason": str}},
    {{"name": "audience_resonance", "topic": str, "hook": str, "reason": str}},
    {{"name": "comparison", "topic": str, "hook": str, "reason": str}}
  ]
}}
"""


def build_stage_b_prompt(
    *,
    stage_a_result: dict[str, Any],
    video_title: str,
    video_duration_sec: float,
    rank: int,
    angle: str,
) -> str:
    """Stage B: rank별 1개 plan 생성 — 6요소 + clip_search_query + headline_pin."""
    layout = stage_a_result.get("layout_classification", "talking_head")
    transcript = stage_a_result.get("transcript", [])[:30]
    transcript_text = "\n".join(
        f"[{t.get('start', 0):.1f}~{t.get('end', 0):.1f}] {t.get('text', '')}"
        for t in transcript
    )
    return f"""당신은 정치 쇼츠 기획자입니다. (Rank {rank} / Angle: {angle})

## 입력
영상 제목: {video_title}
영상 길이: {video_duration_sec:.1f}초
레이아웃 분류: {layout}

## Transcript (Stage A 결과)
{transcript_text}

## 작업
선택된 angle "{angle}" 관점으로 60초 이내 쇼츠 기획안 1개 작성.

각 씬에 대해 다음을 출력:
- text: 화면 자막 (1~80자)
- voice_text: TTS 원문 (자막보다 자연스러운 문장, 1~200자)
- visual_layout: "normal" / "vs_card" / "grid_2x2" / "data_card"
- subtitle_color: "white" / "yellow" / "red" / "blue"
- subtitle_emphasis: true (강조 폰트) / false
- clip_search_query: yt-dlp ytsearch1 검색어 (FR-037, 예: "{video_title} 핵심발언")
- clip_source_timestamp: 원본 영상에서 사용할 시간 구간 [start_sec, end_sec]
- cards_metadata: vs_card/grid_2x2/data_card 시 인물 정보 [{{"name": str, "party": str, "data_label"?: str, "data_value"?: str}}] (없으면 null)

## 카드 분류 규칙 (T048 [US2])
- layout_classification == "vs_2way"이면 narrations[0].visual_layout = "vs_card" + cards_metadata에 정확히 2명 포함 (각자의 party 명시 필수).
  예: [{{"name": "양향자", "party": "국민의힘"}}, {{"name": "추미애", "party": "더불어민주당"}}]
- layout_classification == "comparison_grid"이면 narrations[0].visual_layout = "grid_2x2" + cards_metadata에 3~4명 포함.
- layout_classification == "data_comparison"이면 narrations[0].visual_layout = "data_card" + cards_metadata에 정확히 1명 + data_label/data_value 필수.
- layout_classification == "talking_head"이면 cards_metadata = null.

## 출력 형식 (JSON only, no markdown)
{{
  "rank": {rank},
  "angle": "{angle}",
  "format_type": "A" | "B" | "C",
  "layout_classification": "{layout}",
  "topic": str,
  "hook": str,
  "clip_section": str (예: "01:23~01:45"),
  "reason": str,
  "flow_intro": str,
  "flow_middle": str,
  "flow_climax": str,
  "narrations": [
    {{
      "scene_id": int,
      "text": str,
      "voice_text": str,
      "visual_layout": "normal",
      "subtitle_color": "white",
      "subtitle_emphasis": false,
      "clip_search_query": str | null,
      "clip_source_timestamp": [float, float] | null,
      "cards_metadata": null
    }}
  ],
  "cta": str,
  "headline_pin": str (정확히 8~14자 한글)
}}
"""
