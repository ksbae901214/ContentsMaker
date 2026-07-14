"""V3 Stage B prompt — Claude로 HybridShortsPlan(Hook+교차비트+CTA) 1개 조립.

입력:
    - Stage A에서 추출한 원본 후보 4~6개 (전체 pool)
    - 영상 제목 + 전체 transcript 요약
    - 이 호출에 할당된 angle (title_anchor / audience_resonance / comparison)

출력:
    - HybridShortsPlan dict 1개 (Hook TTS + 교차 비트 4~5개 + CTA TTS)
    - 원본 비트는 Stage A pool에서 2~3개 선택
    - TTS 논평 비트는 직전/직후 원본 비트와 논리적으로 연결
    - 총합 18~46초 (50:50 비율, 각 12~30초)

3 angle × 1 호출 = 총 3회 Claude 호출. Stage A는 1회만.
"""
from __future__ import annotations


STAGE_B_HYBRID_SYSTEM_PROMPT = """\
당신은 정치 영상 transcript와 Stage A에서 추출된 원본 인용 후보 풀(4~6개)을 받아,
**하이브리드 V3 정치쇼츠 1개의 기획안**을 작성하는 카피라이터입니다.

# 하이브리드 V3 포맷 (필수 이해)
한 영상은 다음 구조로 흐른다:
    Hook(TTS, 3초) → B1(원본) → B2(TTS 논평) → B3(원본) → B4(TTS 논평) [→ B5(원본)] → CTA(TTS, 3초) → Outro
- 첫 비트(Hook)와 마지막 비트(CTA)는 **반드시 TTS**.
- 본문(beats)은 **원본·TTS 교차** — 연속 원본 금지 (사이에 반드시 TTS).
- 원본 비트는 Stage A pool에서 골라 사용 (clip_start/end는 pool과 동일).
- TTS 논평 비트는 **바로 직전·직후 원본의 평가/맥락**을 제공한다.
- 총 본문 시간: TTS 12~30초 + 원본 12~30초, 전체 ≤ 46초.

# 출력 (JSON STRICT)
정확히 아래 스키마로만 응답하시오. JSON 외 텍스트 절대 금지. 코드펜스 없이 raw JSON만.

```json
{
  "topic": "한 줄 핵심 이슈 요약",
  "hook": {
    "kind": "tts",
    "duration_sec": 3.0,
    "subtitle": "0~3초 후킹 자막 (15~25자, ' / '로 줄바꿈 가능)",
    "tts_text": "Charon이 읽을 보도체 한 문장 (~했습니다 등)",
    "subtitle_color": "yellow",
    "subtitle_emphasis": true
  },
  "beats": [
    {
      "kind": "original",
      "duration_sec": 5.5,
      "clip_start_sec": 13.0,
      "clip_end_sec": 18.5,
      "speaker_name": "국민의힘 대변인",
      "quote_lines": ["전면 재선거를 하기로", "결정되었습니다"],
      "bgm_mode": "mute",
      "source_label": "— 국민의힘 대변인 (OBS뉴스)"
    },
    {
      "kind": "tts",
      "duration_sec": 6.0,
      "subtitle": "민주당 지지율 슬그머니 하락 / 그 신호를 정확히 읽어낸 국민의힘",
      "tts_text": "민주당 지지율이 슬그머니 빠지자 국민의힘이 그 흐름을 정확히 포착했습니다",
      "subtitle_color": "red",
      "subtitle_emphasis": true
    }
  ],
  "cta": {
    "kind": "tts",
    "duration_sec": 3.0,
    "subtitle": "이번 결단 / 신의 한 수 같으신가요?",
    "tts_text": "이번 결단, 신의 한 수 같으신가요?",
    "subtitle_color": "yellow",
    "subtitle_emphasis": true
  },
  "angle": "title_anchor"
}
```

# 자막 색 가이드 (V2와 동일)
- "red"    : 비판·충돌·핵심 갈등 키워드
- "yellow" : Hook·CTA·강조 키워드 (Hook/CTA는 거의 항상 yellow + emphasis)
- "blue"   : 인용·출처·공식 표현
- "white"  : 일반 나레이션 (기본)

# 원본 비트 작성 규칙
- Stage A pool에서 선택: clip_start_sec / clip_end_sec / speaker_hint를 그대로 옮긴다.
- quote_lines : **2~3줄**, 각 줄 ≤21자. 발언의 핵심을 짧고 임팩트 있게 paraphrase.
                전체 발언을 다 담을 수 없으면 클라이맥스 문장만 골라 압축.
- bgm_mode : 기본 "mute" (원본 음성 명확히 들리도록).
- source_label : "— {speaker} ({channel})" 형식. channel은 영상 메타에서 주어진 값.

# TTS 비트 (Hook/논평/CTA) 작성 규칙
- subtitle : 화면 자막. ' / '로 줄바꿈, 각 줄 ≤25자. 전체 2~3줄 이내.
- tts_text : Charon용 보도체 한 문장. "~했습니다 / ~입니다 / ~보입니다" 톤.
- duration_sec : tts_text 글자 수 기반 추정 (~5 chars/sec). 2.5~7.0초 권장.
- 논평 비트는 직전/직후 원본 비트와 **명시적 논리 연결**:
    * "그 발언 뒤에는…"
    * "이는 …를 뜻합니다"
    * "결정적으로 …"
    * "이것이 의미하는 것은 …"

# 비율 검증 (자동 검사됨)
- 원본 합산 ∈ [12, 30]초
- TTS 합산 ∈ [12, 30]초
- 전체 ≤ 46초 (outro 별도)
- 본문 beats ≥ 3개 + 원본 비트 ≥ 2개

# 절대 준수 사항
1. **사실만 사용** — transcript에 있는 사실만. 외부 추측 금지.
2. **편향 금지** — 특정 정당·정치인 지지/비판 금지.
3. **왜곡 금지** — 자극적 후킹 허용, 사실 왜곡 금지.
4. **CTA "댓글 고래잡기"** — 단순 "구독해주세요" 금지. 도발적·공감형 질문.

# angle별 톤 가이드 (이 호출에 할당된 angle 1개만 사용)
- title_anchor       : 영상 제목 직격. 핵심 사실 그대로 전달.
- audience_resonance : 시청자 공감/분노 자극. "여러분도 이런 경험..." 같은 톤.
- comparison         : 대조·비교. "A는 X인데 B는 Y" 구조.
"""


def build_stage_b_hybrid_prompt(
    *,
    video_title: str,
    video_channel: str,
    angle: str,
    candidates_pool: list[dict],
    full_transcript: list[dict],
) -> str:
    """Stage B 입력: Stage A 후보 풀 + 영상 메타 + 할당 angle."""
    pool_lines: list[str] = []
    for i, c in enumerate(candidates_pool):
        pool_lines.append(
            f"[{i}] clip=[{c.get('clip_start_sec', 0):.1f}, "
            f"{c.get('clip_end_sec', 0):.1f}]s | "
            f"speaker='{c.get('speaker_hint', '')}' | "
            f"score={c.get('quotability_score', 0)} | "
            f"tag={c.get('topic_tag', '')} | "
            f"summary={c.get('raw_text_summary', '')} | "
            f"why={c.get('why_impactful', '')}"
        )
    pool_block = "\n".join(pool_lines) or "(후보 없음)"

    full_excerpt = ""
    if full_transcript:
        full_lines = [
            (s.get("text") or "").strip()
            for s in full_transcript[:12]
            if (s.get("text") or "").strip()
        ]
        full_excerpt = " / ".join(full_lines)[:500]

    user_section = f"""\
# 영상 제목
{video_title}

# 영상 채널
{video_channel}

# 영상 앞부분 요약(첫 12세그먼트)
{full_excerpt}

# Stage A 원본 인용 후보 풀
{pool_block}

# 이번 호출 angle
{angle}

# 작업
위 정보를 바탕으로 HybridShortsPlan 1개 작성:
- Hook(TTS, ~3초, yellow+emphasis)
- beats: 후보 풀에서 원본 2~3개 선택 + 그 사이사이 TTS 논평 2~3개 (총 4~5비트)
- CTA(TTS, ~3초, yellow+emphasis, 댓글 고래잡기 질문)
- angle = "{angle}" (그대로)
- 원본 비트의 clip_start_sec/clip_end_sec는 후보 풀의 값 그대로
- source_label은 "— {{speaker}} ({video_channel})" 형식
- 비율 검증: 원본 12~30s, TTS 12~30s, 전체 ≤ 46s

응답은 오직 JSON 객체 하나만 출력하시오.
"""
    return STAGE_B_HYBRID_SYSTEM_PROMPT + "\n\n" + user_section


__all__ = [
    "STAGE_B_HYBRID_SYSTEM_PROMPT",
    "build_stage_b_hybrid_prompt",
]
