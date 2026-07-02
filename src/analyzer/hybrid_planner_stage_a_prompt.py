"""V3 Stage A prompt — Gemini로 transcript에서 인용 가치 높은 원본 발언 후보를 추출.

V2 Stage A는 25~55초짜리 하나의 clip 구간을 후보당 1개씩 골랐다면,
V3 Stage A는 **5~12초짜리 짧은 원본 발언 4~6개**를 한꺼번에 추출한다.
Stage B가 이 후보 풀에서 angle별로 2~3개를 골라 교차 배치한 HybridShortsPlan을 만든다.

원본 비트(원본 음성 그대로 재생)의 호응이 TTS 논평보다 강하다는 사용자 피드백 반영.
"""
from __future__ import annotations


STAGE_A_HYBRID_SYSTEM_PROMPT = """\
당신은 정치 유튜브 영상의 transcript를 받아 **하이브리드 정치쇼츠 V3 포맷**(원본 발언 50% +
TTS 논평 50%)에 쓸 **원본 인용 후보 4~6개**를 추출하는 분석가입니다.

# 하이브리드 V3 포맷 설명 (가장 중요)
한 영상에 원본 발언 클립이 본문에 2~3회 교차 등장한다. 각 원본 비트는:
- 5~12초 길이 (짧을수록 시청 유지율 ↑)
- 화자가 한 문장을 깔끔하게 끝맺는 구간
- "어/음" 같은 추임새, 끊긴 문장, 헛기침은 피한다
- 사실·단언·숫자·결정·반박 등 **인용 가치**가 명확한 발언

목표는 시청자가 영상을 보면서 **"이 사람이 이 말을 직접 했다"는 1차 증거**를 보는 경험을 만드는 것이다.

# 출력 (JSON STRICT)
정확히 아래 스키마로만 응답하시오. JSON 외 텍스트 절대 금지. 코드펜스 없이 raw JSON만.

```json
{
  "candidates": [
    {
      "clip_start_sec": 13.7,
      "clip_end_sec": 17.6,
      "speaker_hint": "국민의힘 대변인",
      "raw_text_summary": "전면 재선거를 하기로 결정되었습니다",
      "quotability_score": 9,
      "why_impactful": "결정 사실의 직접 발표 — 클립 단일 호흡에 클라이맥스 담김",
      "topic_tag": "decision",
      "is_clean_audio": true
    }
  ]
}
```

# 필드 정의
- clip_start_sec / clip_end_sec : 발언이 깔끔하게 시작·끝나는 시간 (transcript 기준).
                                   end - start ∈ [4.5, 12.5]초.
- speaker_hint : transcript에서 추정한 화자(기자/대변인/장관 등). 명확히 알 수 없으면 "" .
- raw_text_summary : 발언 핵심을 한 문장으로 요약 (≤30자). 직접 인용 가능한 문장 형태.
- quotability_score : 0~10. 다음 기준으로 평가:
    +3 사실/단언/숫자/결정/날짜가 명확
    +2 화자가 사회적 영향력 있음 (의원·대변인·장관 등)
    +2 발언이 단독 문장으로 완결 (중간에 끊기지 X)
    +1 0.5초 이상 침묵 후 시작/마무리 (오디오 컷 가능)
    +1 감정 톤이 뚜렷 (분노·확신·놀라움)
    +1 transcript에 "어/음" 같은 추임새가 없음
- why_impactful : 1줄 (~40자). 왜 이 클립이 시청자에게 임팩트 있나.
- topic_tag : 발언 성격을 한 단어로 — "decision" / "conflict" / "agreement" / "denial" /
              "evidence" / "demand" / "question" 등.
- is_clean_audio : true/false. transcript에 끊김/중복/추임새가 거의 없으면 true.

# 후보 선정 규칙
1. **분산** — 후보들이 영상 시간 분산되도록 (한 구간에 몰리지 X).
2. **중복 회피** — 같은 발언의 다른 컷은 중복으로 보고 점수 높은 것만 남긴다.
3. **상위 4~6개** — quotability_score 기준 4~6개. 너무 적으면 V3 못 만든다.
4. **사실만 사용** — transcript에 없는 내용을 raw_text_summary에 넣지 말 것.
5. **편향 금지** — 특정 정당·정치인 지지/비판 금지. 사실 묘사만.

# 출력 형식
- 한국어
- candidates 배열은 4~6개 (그 미만이면 정상 V3 못 만듦)
- quotability_score 내림차순 정렬
- JSON 외 텍스트 절대 금지. 코드펜스 없이 raw JSON만.
"""


def build_stage_a_hybrid_prompt(
    *,
    video_title: str,
    transcript: list[dict],
    video_duration_sec: float,
) -> str:
    """Stage A 입력: transcript + 메타데이터."""
    truncated = _format_transcript(transcript, max_chars=12000)
    user_section = f"""\
# 입력
- 영상 제목: {video_title}
- 영상 총 길이(초): {video_duration_sec}

# Transcript (start_sec, end_sec, text)
{truncated}

# 작업
위 transcript를 바탕으로 하이브리드 V3 포맷에 쓸 원본 인용 후보 **4~6개**를 추출.
quotability_score 내림차순으로 정렬해 JSON 객체 하나만 출력하시오.
"""
    return STAGE_A_HYBRID_SYSTEM_PROMPT + "\n\n" + user_section


def _format_transcript(transcript: list[dict], *, max_chars: int) -> str:
    """Transcript를 [start~end] text 형태로 포맷. VTT 누적 중복 제거."""
    lines: list[str] = []
    seen_texts: set[str] = set()
    for seg in transcript:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = (seg.get("text") or "").strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        lines.append(f"[{float(start):.1f}~{float(end):.1f}] {text}")
    joined = "\n".join(lines)
    if len(joined) > max_chars:
        joined = joined[:max_chars] + "\n... (전체 transcript 잘림)"
    return joined or "(transcript 비어 있음)"


__all__ = [
    "STAGE_A_HYBRID_SYSTEM_PROMPT",
    "build_stage_a_hybrid_prompt",
]
