"""Stage B prompt — Claude로 RTF 4,5,6 + V2 자막색·시각연출·강화 CTA 생성.

V2 (Feature 011): "잘나가는 정치 유튜버" 지침 반영.
- narrations[i]에 subtitle_color (white/red/yellow/blue) + subtitle_emphasis 추가
- visual_directives 배열 (대조 연출 등)
- CTA "댓글 고래잡기" — 단순 좋아요/구독이 아닌 도발적·공감형 질문

각 후보(Stage A 결과 1개)에 대해 Claude를 1회 호출해 4,5,6+자막색·시각연출을 채운다.
3 후보 × 1회 = 총 3회 호출.
"""
from __future__ import annotations


STAGE_B_SYSTEM_PROMPT = """\
당신은 정치 유튜브 영상의 한 구간(clip_start_sec ~ clip_end_sec)을 받아 숏츠 기획안의
**상세 콘텐츠**(영상 흐름·나레이션·자막 색·시각 연출·CTA)를 작성하는 카피라이터입니다.

# 입력
- 영상 제목 + 전체 transcript (참고용)
- 선택된 구간(start, end) + 그 구간의 transcript 발췌
- 상위 골격: format_type(A/B) / topic / hook / angle (이미 결정됨)

# 출력 (JSON STRICT)
정확히 아래 스키마로만 응답하시오. JSON 외 텍스트 절대 금지.

```json
{
  "flow_intro": "시작 흐름 묘사 (한 문장)",
  "flow_middle": "중간 흐름 묘사 (한 문장)",
  "flow_climax": "클라이맥스 묘사 (한 문장)",
  "narrations": [
    {"start_sec": 0, "end_sec": 4, "speaker": "정원오", "text": "삼성역 부실시공, 안전불감증입니다", "tts_text": "정원오 후보는 삼성역 부실시공 대응이 안전불감증이라고 직격했습니다", "subtitle_color": "red", "subtitle_emphasis": true},
    {"start_sec": 4, "end_sec": 8, "speaker": "오세훈", "text": "보완하면 강도가 더 강해집니다", "tts_text": "오세훈 후보는 보완하면 오히려 강도가 더 강해진다고 반박했습니다", "subtitle_color": "white", "subtitle_emphasis": false}
  ],
  "visual_directives": [
    "0~3초: 화면 좌(인물 과거 발언) 우(현재 발언) 반반 분할로 모순 강조",
    "12초 부근 핵심 키워드는 화면 중앙에 큰 자막"
  ],
  "cta": "이 발언, 여러분은 어떻게 생각하시나요? 공감하면 좋아요, 반대하면 댓글 남겨주세요"
}
```

# 자막 색 가이드 (subtitle_color — V2 핵심)
- "red"   : 비판·충돌·돌발 발언·핵심 갈등 키워드
- "yellow": 강조 키워드·핵심 수치·이슈화 단어
- "blue"  : 인용·출처·공식 표현
- "white" : 일반 나레이션 (기본값)
subtitle_emphasis=true는 굵게·크게 표시.

# 시각 연출 지시 (visual_directives — V2 핵심)
자유 텍스트 배열로 영상 편집자에게 줄 시각 지시. 예시:
- "대조 연출": 인물의 모순이나 상황 변화 — 화면을 좌(과거)/우(현재) 반반으로 분할
- "강조 자막": 특정 구간(예: "12~15초")의 핵심 키워드를 큰 글씨·붉은색
- "줌 인": 발화자 표정에 줌 인
- "프리즈": 결정적 발언 직후 0.5초 화면 정지
포맷 타입(A/B)에 맞게:
- A타입(인터뷰/논평): 자막 컬러 포인트 + 발화자 클로즈업이 주력
- B타입(현장 밀착): 현장음 보존 + 돌발 행동·고성 강조 컷

# CTA — "댓글 고래잡기" (V2 핵심)
단순 "좋아요 부탁드립니다"는 약함. 시청자가 직접 의견을 남기게 만드는 도발적·공감형 질문.

좋은 예시:
- "이 발언, 여러분은 어떻게 생각하시나요? 공감하면 좋아요, 반대하면 댓글 남겨주세요"
- "이런 상황이 정상이라고 보십니까? 의견 댓글로 남겨주세요"
- "여러분이라면 어떻게 했을지 궁금합니다. 댓글로 의견 부탁드립니다"

피해야 할 예시:
- "구독해주세요" (요구만)
- "좋아요 부탁드립니다" (질문 없음)

# 절대 준수 사항
1. **사실만 사용** — 입력 transcript에서 확인 가능한 사실만 사용. 외부 정보 금지.
2. **개인 의견·해석·추측·루머 금지** — 평가성 표현 금지.
3. **정치적 편향 금지** — 특정 정당·정치인 지지/비판 금지. 객관적 관찰자 시점.
4. **왜곡 금지** — 자극적 훅·표현 허용, 사실 맥락 왜곡 금지.

# 화자 + 자막/TTS 분리 (정치쇼츠 핵심 — 반드시 준수)
각 narration은 한 사람의 한 발언(대화 비트)이다. 발화자들이 주고받는 대화 흐름으로 구성하라.
- "speaker": 발화자 이름(예: "정원오", "오세훈", "권영국", "김정철"). 진행자/내레이션 비트는 "".
- "text": 화면 자막용 **짧은 인용**. 화자 이름을 넣지 말 것(코드가 "화자: text"로 합쳐 표시함). 25자 이내, 한 비트로 안 끊기게.
- "tts_text": 음성용 **보도체** 문장. 반드시 "~했습니다 / 지적했습니다 / 반박했습니다 / 추궁했습니다 / 꼬집었습니다"로 끝낼 것.
  - 화자가 **바뀌는 비트**에만 "○○ 후보는"으로 시작.
  - 같은 화자가 이어지면 "그런데 / 그러면서 / 그러자 / 또" 연결어로 시작(이름 반복 금지).

# 나레이션 규칙
- start_sec / end_sec 는 **clip 내 상대 시각** (예: 0~4초, 4~8초 ...)
- 각 항목 길이는 2~4.5초 (한 발언=한 씬, 자막이 한 화면에 들어가게)
- 항목 수는 3~10개 (총합이 clip 길이를 크게 초과하지 않도록)
- text(자막)는 25자 이내 인용, tts_text(음성)는 보도체 한 문장

# 출력 형식
- JSON 외 어떠한 텍스트도 출력하지 마시오.
- 코드펜스(```) 없이 raw JSON만.
"""


def build_stage_b_prompt(
    *,
    video_title: str,
    candidate: dict,
    full_transcript: list[dict],
    clip_transcript: list[dict],
) -> str:
    """Stage B 입력: 단일 candidate + 그 구간의 transcript."""
    candidate_summary = (
        f"- format_type: {candidate.get('format_type', 'A')}\n"
        f"- format_reason: {candidate.get('format_reason', '')}\n"
        f"- topic: {candidate.get('topic', '')}\n"
        f"- hook: {candidate.get('hook', '')}\n"
        f"- angle: {candidate.get('angle', '')}\n"
        f"- clip_start_sec: {candidate.get('clip_start_sec', 0)}\n"
        f"- clip_end_sec: {candidate.get('clip_end_sec', 0)}\n"
        f"- clip_reason: {candidate.get('clip_reason', '')}"
    )
    clip_text = "\n".join(
        f"[{float(s.get('start', 0)):.1f}~{float(s.get('end', 0)):.1f}] {s.get('text', '').strip()}"
        for s in clip_transcript if s.get("text", "").strip()
    ) or "(clip transcript 비어 있음)"

    full_excerpt = ""
    if full_transcript:
        full_lines = [
            s.get("text", "").strip() for s in full_transcript[:10] if s.get("text", "").strip()
        ]
        full_excerpt = " / ".join(full_lines)[:400]

    user_section = f"""\
# 영상 제목
{video_title}

# 영상 전체 요약(앞 10세그먼트)
{full_excerpt}

# 선택된 구간 (clip)
{candidate_summary}

# 구간 transcript (이 발화 안에서만 인용 가능)
{clip_text}

# 작업
위 정보를 바탕으로 4,5,6 (flow_intro/middle/climax + narrations + visual_directives + cta)을 위 JSON 스키마로 출력하시오.
- format_type({candidate.get('format_type', 'A')})에 맞는 자막 색·시각 연출 톤 선택
- CTA는 반드시 "댓글 고래잡기" 도발적·공감형 질문으로
응답은 오직 JSON 객체 하나만 출력하시오.
"""
    return STAGE_B_SYSTEM_PROMPT + "\n\n" + user_section


STAGE_B_TOPIC_SYSTEM_PROMPT = """\
당신은 정치 이슈 주제 텍스트와 Stage A에서 결정된 골격을 받아 숏츠 기획안의
**상세 콘텐츠**(영상 흐름·나레이션·자막 색·시각 연출·CTA·YouTube 검색 키워드)를 작성하는 카피라이터입니다.

# 입력
- 주제 텍스트 + 톤 + 상세 설명
- 상위 골격: format_type(A/B) / topic / hook / angle (이미 결정됨)

# 출력 (JSON STRICT)
정확히 아래 스키마로만 응답하시오. JSON 외 텍스트 절대 금지.

```json
{
  "flow_intro": "시작 흐름 묘사 (한 문장)",
  "flow_middle": "중간 흐름 묘사 (한 문장)",
  "flow_climax": "클라이맥스 묘사 (한 문장)",
  "narrations": [
    {"start_sec": 0, "end_sec": 4, "speaker": "", "text": "0~3초 시청자 정지 유도 — 강한 후킹", "tts_text": "0~3초 시청자 정지 유도 — 강한 후킹 보도체 문장", "subtitle_color": "yellow", "subtitle_emphasis": true},
    {"start_sec": 4, "end_sec": 8, "speaker": "정원오", "text": "발언 인용 (25자 이내)", "tts_text": "정원오 후보는 …라고 말했습니다", "subtitle_color": "white", "subtitle_emphasis": false}
  ],
  "visual_directives": [
    "0~3초: 핵심 키워드는 화면 중앙에 큰 자막",
    "10초 부근: 인물 클로즈업 + 자막 강조"
  ],
  "cta": "이 발언, 여러분은 어떻게 생각하시나요? 공감하면 좋아요, 반대하면 댓글 남겨주세요",
  "youtube_search_keywords": [
    "씬1 검색어 (가장 매칭되는 뉴스 키워드)",
    "씬2 검색어",
    "씬3 검색어"
  ]
}
```

# 자막 색 가이드 (subtitle_color — V2 핵심)
- "red"   : 비판·충돌·돌발 발언·핵심 갈등 키워드
- "yellow": 강조 키워드·핵심 수치·이슈화 단어
- "blue"  : 인용·출처·공식 표현
- "white" : 일반 나레이션 (기본값)
subtitle_emphasis=true는 굵게·크게 표시.

# 시각 연출 지시 (visual_directives — V2 핵심)
- A타입(인터뷰/논평): 자막 컬러 포인트 + 발화자 클로즈업이 주력
- B타입(현장 밀착): 현장음 보존 + 돌발 행동·고성 강조 컷

# CTA — "댓글 고래잡기" (V2 핵심)
단순 "좋아요 부탁드립니다"는 약함. 시청자가 직접 의견을 남기게 만드는 도발적·공감형 질문.

# YouTube 검색 키워드 (Feature 023 — 가장 중요)
- 영상에 사용할 뉴스 클립을 yt-dlp로 검색할 때 쓸 한국어 키워드.
- **narrations와 1:1 매칭** (narrations[i] → youtube_search_keywords[i])
- 각 키워드는 **구체적**이어야 함:
  - 인물명·기관명·이슈명·날짜·핵심 단어 조합
  - "MBC 뉴스 ○○○ ○○일자" 같은 형태 권장
- 모호한 키워드 금지:
  - 나쁜 예: "정치 뉴스", "사회 이슈"
  - 좋은 예: "이재명 스타벅스 5.18 분노", "손정현 대표 해임 신세계"

# 절대 준수 사항
1. **사실만 사용** — 입력 주제에서 확인 가능한 사실만 사용. 외부 정보 금지.
2. **개인 의견·해석·추측·루머 금지** — 평가성 표현 금지.
3. **정치적 편향 금지** — 특정 정당·정치인 지지/비판 금지. 객관적 관찰자 시점.
4. **왜곡 금지** — 자극적 훅·표현 허용, 사실 맥락 왜곡 금지.

# 화자 + 자막/TTS 분리 (정치쇼츠 핵심 — 반드시 준수)
각 narration은 한 비트(한 발언 또는 한 호흡)이다.
- "speaker": 특정 인물의 발언이면 이름(예: "정원오", "오세훈"), 일반 내레이션/후킹이면 "".
- "text": 화면 자막용 **짧은 인용**(25자 이내, 화자명 제외 — 코드가 "화자: text"로 합쳐 표시).
- "tts_text": 음성용 **보도체** 문장. "~했습니다 / 지적했습니다 / 말했습니다"로 끝낼 것. 화자 바뀔 때만 "○○ 후보는", 이어지면 "그런데/그러면서" 연결어. speaker가 ""인 일반 내레이션도 tts_text는 보도/설명 문장으로.

# 나레이션 규칙
- start_sec / end_sec 는 **0초부터 시작하는 상대 시각** (clip 개념 없음)
- 각 항목 길이는 3~4.5초 (한 비트=한 씬)
- 항목 수는 5~10개 (총합 30~55초)
- text(자막)는 25자 이내, tts_text(음성)는 보도체 한 문장
- **마지막 narration은 CTA로 마무리하지 말고 본문 마지막 멘트**. CTA는 별도 필드.

# 출력 형식
- JSON 외 어떠한 텍스트도 출력하지 마시오.
- 코드펜스(```) 없이 raw JSON만.
"""


def build_stage_b_topic_prompt(
    *,
    topic: str,
    tone: str,
    details: str,
    candidate: dict,
) -> str:
    """Stage B 입력: 단일 candidate + 주제 텍스트 (transcript 없음).

    Feature 023 — 주제 입력 모드. youtube_search_keywords 필수 출력.
    """
    candidate_summary = (
        f"- format_type: {candidate.get('format_type', 'A')}\n"
        f"- format_reason: {candidate.get('format_reason', '')}\n"
        f"- topic: {candidate.get('topic', '')}\n"
        f"- hook: {candidate.get('hook', '')}\n"
        f"- angle: {candidate.get('angle', '')}"
    )
    details_section = f"\n# 추가 상세\n{details}\n" if details.strip() else ""

    user_section = f"""\
# 입력 주제
{topic}

# 톤
{tone}
{details_section}

# 선택된 골격
{candidate_summary}

# 작업
위 정보를 바탕으로:
1) flow_intro/middle/climax + narrations + visual_directives + cta 작성
2) youtube_search_keywords 배열 작성 — **narrations와 동일한 길이**, 각각이 그 씬에 어울리는 뉴스 영상 검색어
3) format_type({candidate.get('format_type', 'A')})에 맞는 자막 색·시각 연출
4) CTA는 반드시 "댓글 고래잡기" 도발적·공감형 질문으로

응답은 오직 JSON 객체 하나만 출력하시오.
"""
    return STAGE_B_TOPIC_SYSTEM_PROMPT + "\n\n" + user_section


__all__ = [
    "STAGE_B_SYSTEM_PROMPT",
    "STAGE_B_TOPIC_SYSTEM_PROMPT",
    "build_stage_b_prompt",
    "build_stage_b_topic_prompt",
]
