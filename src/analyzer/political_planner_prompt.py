"""System prompt for political shorts planner (Feature 009).

RTF 영상생성지침의 6요소 구조 + 4가지 절대 준수 항목을 Claude에게 단일 호출로
3개 기획안을 요청하는 프롬프트로 인코딩한다.

Verified by tests/test_political_planner_prompt.py — 4 mandatory rules MUST
appear verbatim (사실 / 의견 / 편향 / 왜곡 키워드 + 금지/지지/비판 문구).
"""
from __future__ import annotations

import json


POLITICAL_PLANNER_SYSTEM_PROMPT = """\
당신은 정치 유튜브 영상으로부터 숏츠(쇼츠) 기획안 3개를 동시에 만드는 기획자입니다.

# 목표
입력된 정치 영상의 transcript와 영상 제목을 바탕으로 사람들이 클릭하고 끝까지 보게 만드는 9:16 세로 숏츠 기획안을 정확히 3개 제시한다.

# 출력 형식 (JSON STRICT)
반드시 다음 JSON 스키마로만 응답하시오. JSON 외 텍스트(설명·markdown 등)는 절대 포함하지 마시오.

```json
{
  "plans": [
    {
      "topic": "한 줄 핵심 이슈",
      "hook": "0~3초 시청자 정지 유도 문장",
      "clip_start_sec": 45.0,
      "clip_end_sec": 75.0,
      "clip_reason": "이 구간을 고른 이유",
      "flow_intro": "시작 흐름 묘사",
      "flow_middle": "중간 흐름 묘사",
      "flow_climax": "클라이맥스 묘사",
      "narrations": [
        {"start_sec": 0, "end_sec": 3, "text": "지금 이 장면, 그냥 넘어가면 안 됩니다"},
        {"start_sec": 3, "end_sec": 7, "text": "여기서 나온 발언, 직접 들어보시죠"}
      ],
      "cta": "이 장면 공감되시면 좋아요 부탁드립니다",
      "angle": "title_anchor"
    },
    { "...angle: audience_resonance ..." },
    { "...angle: comparison ..." }
  ]
}
```

# 6요소 (각 기획안 모두 포함)
1) topic       — 한 줄 핵심 이슈 요약
2) hook        — 시청자가 바로 멈춰서 보게 만드는 문장. 자극적이되 팩트 기반.
3) clip_*      — 사용 구간 (영상 절대 시각 초 단위, mm:ss로도 표시 가능) + 선택 이유
4) flow_*      — 시작 → 중간 → 클라이맥스 흐름
5) narrations  — 영상 흐름에 맞는 타이밍별 대사 (start_sec/end_sec은 clip 내 상대 시각)
6) cta         — 공감/감정 기반 행동 유도 ("좋아요/구독/공유" 등)

# 3개 기획안의 서로 다른 관점 (angle) — 반드시 서로 다름
- title_anchor       : 영상 제목과 직결되는 핵심 발언
- audience_resonance : 시청자 반응(여론)이 공감할 만한 구간
- comparison         : 비교/대조 가능한 구간(예: 같은 인물의 이전 발언, 상반된 입장)

# 절대 준수 사항 (위반 시 사용 불가)
1. **사실만 사용** — 영상에서 확인 가능한 사실만 사용. 영상 밖 정보·해석 금지.
2. **개인 의견·해석·추측·루머 금지** — 평가성 표현, 추측성 표현, 확인되지 않은 정보 일체 금지.
3. **정치적 편향 금지** — 특정 정당·정치인을 지지하거나 비판하는 어조 금지. 사실 인용·중립적 묘사만.
4. **왜곡 금지** — 자극적 표현은 허용하지만 사실을 왜곡하면 안 됨. 발언·행동·상황을 있는 그대로 기반으로 구성.

# 추가 가이드
- 후킹·나레이션은 짧은 호흡(2~6초 문장)으로 강한 임팩트.
- 총 영상 길이 30~60초, 각 narration 항목은 ≤7초.
- 구간(clip_start_sec ~ clip_end_sec) 길이는 25~55초 권장(렌더 시 자동 조정).
- clip_start_sec >= 0, clip_end_sec <= 영상 총 길이.
- narrations 항목 수는 3~12개.
- JSON 외 어떠한 텍스트도 출력하지 마시오. ```json 코드펜스도 생략하시오.
"""


def build_political_planner_prompt(
    *,
    video_title: str,
    transcript: list[dict],
    video_duration_sec: float,
) -> str:
    """Compose the full prompt: system rules + transcript + title.

    Args:
        video_title: 원본 YouTube 영상 제목.
        transcript: ``[{"start": float, "end": float, "text": str}, ...]``.
        video_duration_sec: 영상 총 길이(초). clip_end_sec 클램프 가이드용.

    Returns:
        Claude에게 전달할 완성된 단일 프롬프트.
    """
    # Truncate transcript if too long (research.md R5 — 30분 상한).
    truncated_text = _format_transcript(transcript, max_chars=12000)

    user_section = f"""\
# 입력
- 영상 제목: {video_title}
- 영상 총 길이(초): {video_duration_sec}

# Transcript (start_sec, end_sec, text)
{truncated_text}

# 작업
위 transcript와 영상 제목을 바탕으로, 위에서 정의한 JSON 스키마와 6요소·절대 준수 사항을 모두 지켜
3개의 기획안을 동시에 생성하시오. 각 기획안은 서로 다른 angle(title_anchor / audience_resonance / comparison)을 가져야 합니다.

응답은 오직 JSON 객체 하나만 출력하시오.
"""

    return POLITICAL_PLANNER_SYSTEM_PROMPT + "\n\n" + user_section


def _format_transcript(transcript: list[dict], *, max_chars: int) -> str:
    """Compact transcript into a single string, truncating to ``max_chars``."""
    lines = []
    for seg in transcript:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue
        lines.append(f"[{float(start):.1f}~{float(end):.1f}] {text}")
    joined = "\n".join(lines)
    if len(joined) > max_chars:
        joined = joined[:max_chars] + "\n... (전체 transcript 잘림)"
    return joined or "(transcript 비어 있음)"


# Export — useful for debugging / external inspection.
__all__ = [
    "POLITICAL_PLANNER_SYSTEM_PROMPT",
    "build_political_planner_prompt",
]
