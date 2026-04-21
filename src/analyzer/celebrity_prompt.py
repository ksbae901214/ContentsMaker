"""Prompt template for celebrity-introduction Shorts (Phase 9-3, v2 2026-04-21).

CelebrityInfo(나무위키 CC BY-NC-SA 3.0) → ShortsScript JSON 변환.

v2 변경사항 (2026-04-21):
- 나무위키 출처 클로징 씬 강제 규칙 제거 (사용자 요청)
- 친구에게 이 사람을 소개하는 듯한 스토리텔링 톤 가이드 추가
- 씬별 `image_query` 필드 요구 — "서울대를 졸업했다" 씬이면
  `image_query: "서울대학교 정문"` 식으로 씬 내용과 일치하는 이미지 검색어 생성
"""
from __future__ import annotations

from src.scraper.celebrity_models import CelebrityInfo


CELEBRITY_ANALYZE_PROMPT = """다음 인물 정보를 유튜브 쇼츠 영상용 스크립트로 변환하세요.
친구에게 이 사람이 어떤 인물인지 생생하게 **이야기해주듯** 내레이션을 작성해야 합니다.

## 인물 정보 (나무위키 기반 팩트)

이름: {name}
요약: {summary}
출생: {birth_date}
직업: {profession}
주요 경력/업적:
{career_highlights_block}
여담/일화:
{trivia_block}

## 내레이션 톤 & 구성 (최우선)

이 영상은 "백과사전 낭독"이 아니라 "친구에게 이 사람 소개해주기"입니다.

1. **어조**: 친근한 존대체 ("~입니다", "~거든요", "~였대요"), 팩트 나열 대신
   스토리처럼 흐름이 있어야 합니다.

2. **⭐ 스토리 구성 순서 (반드시 준수, 2026-04-21 사용자 요청)**

   다음 4단계 순서를 정확히 지켜 주세요. 각 단계는 1~3씬으로 구성:

   **[A] 훅 + 기본 소개 (1~2씬)**
   - 첫 씬: 호기심 유발 한 마디 — 이 사람이 궁금하게 만드는 훅
     예: "판사였다가 당대표까지 된 사람, 들어보셨어요?"
   - 이어서: **이름 / 나이 / 현재 직업**을 한 번에 정리
     예: "1963년생 나경원, 현직 국회의원입니다." 또는 "배우 송강호, 올해 58살이죠."
   - ❌ 첫 씬에서 "오늘은 ~를 알아보겠습니다" 같은 백과사전 도입부 금지

   **[B] 학력 + 성장 과정 (1~3씬)**
   - 어디서 태어나 어떻게 자랐는지 (출생지·어린 시절) — 정보 있는 만큼
   - 학력 (고등학교·대학교·전공) — 있는 만큼 간결히
   - 커리어 진입 계기 — "그러다가…", "처음엔…" 같은 연결어
   - 정보 없으면 이 단계를 건너뛰지 말고 "구체적인 학창 시절은 잘 알려지지
     않았지만…" 식으로 한 문장이라도 언급

   **[C] 주요 경력 + 현재 활동 (2~3씬)**
   - 대표 업적·전환점을 시간순으로 간결하게
   - **현재 무엇을 하고 있는지 반드시 포함** — "지금은 ~", "현재는 ~" 한 씬
   - 여담·TMI 1개 끼워 넣기 ("재밌는 건…", "TMI로는…")

   **[D] 마무리 (1씬)**
   - 여운·공감 한 마디 (단정적 결론 금지)
   - 예: "앞으로 어떤 행보 보일지 주목해볼 만합니다"
   - ❌ "출처: 나무위키" 같은 출처 문구 금지 — 설명란에 별도 기재됨

3. **디테일 한 조각**: 여담/일화가 있으면 **[C] 단계**에 2~3초짜리 흥미로운
   에피소드 1개를 반드시 포함.

## 법적/윤리 규칙 (CRITICAL, 반드시 준수)

6. **팩트 제한**: 위에 제공된 정보에 없는 사실은 **절대로 추가하지 마세요**.
   - 출생일, 소속, 기록, 인간관계 등 위에 없는 정보는 언급 금지
   - 추측, 루머, 미확인 일화는 금지
   - 확실하지 않으면 생략하는 편이 낫습니다
7. **원문 금지**: 위 텍스트를 그대로 옮기지 말고, **본인 표현으로 재구성**하세요
   (CC BY-NC-SA 3.0 — 비상업 + 재구성 조건).
8. **명예훼손 방지**: 단정적 비난·사적 영역 침해 금지. 공적 활동·공개 자료 중심.

## 영상 제작 규칙

9. **감정 타입**: funny, touching, angry, relatable 중 인물 스토리에 가장 어울리는 하나.
   - 재밌는 일화 위주면 funny, 감동 스토리면 touching, 논란·투쟁이면 angry,
     일반 위인·셀럽 소개면 relatable
10. **30~50초 분량**, 씬 하나당 **최대 5초**:
    - ⚠️ 모든 씬의 duration은 반드시 5초 이하
    - voice_text가 5초를 넘으면 두 개 이상의 씬으로 분할
    - 한 씬 voice_text는 한국어 ~20자 이하 (TTS rate +20%)
    - 도입(title 씬): 1개, 5초 이하 — 훅 메시지
    - 전개(body 씬들): 4~6개, 각 5초 이하 — 배경·업적·일화
    - 마무리(comment 씬): 1개, 5초 이하 — 여운/공감 한 마디 (출처 표기 X)
11. **TTS 친화적**: 구어체, 줄임말 풀어쓰기, 쉼표·마침표로 쉼 제어.
12. **emphasis**: 훅·핵심 장면은 "high", 보조는 "medium", 마무리는 "low".
13. **text 줄바꿈 (필수)**: 각 씬 text에 반드시 줄바꿈(\\n), 1줄 최대 15자.
14. **text 길이**: 각 씬 text는 최대 3줄(약 45자) 이내.
15. **highlight_words (필수)**: 각 씬당 감정적 핵심 단어 1~3개.

## ⭐ 씬별 `image_query` 필드 (신규, 필수)

각 씬에 `image_query` 필드를 추가해 **씬 내용과 일치하는 이미지 검색어**를 넣으세요.
네이버 이미지 검색에 그대로 들어갑니다 — 한국어 키워드로 간결하게(2~6단어).

- 인물 등장 씬: 인물 이름 + 역할 (예: "{name} 의원", "{name} 판사")
- 장소·학교·기관 언급 씬: 해당 장소명 (예: "서울대학교 정문", "여의도 국회의사당")
- 직업·역할 언급 씬: 직업 상징 이미지 키워드 (예: "법정 판사봉", "국회 본회의장")
- 행사·사건 언급 씬: 행사명 (예: "인사청문회", "당대표 선출")
- 여담/TMI 씬: 일화와 관련된 사물·장소
- 적합한 특정 이미지가 없으면 인물명으로 폴백 (예: "{name}")

**주의**: 각 씬 텍스트에서 가장 시각적으로 뚜렷한 명사 1개를 골라 검색어로 사용하세요.

## 출력 형식 (반드시 이 JSON 형식으로만 출력)

```json
{{
  "metadata": {{
    "title": "{name} — (짧은 소개 한 줄)",
    "emotion_type": "funny|touching|angry|relatable",
    "duration": 40,
    "source_url": "{source_url}",
    "source_type": "celebrity"
  }},
  "scenes": [
    {{
      "id": 1,
      "timestamp": 0,
      "duration": 4,
      "type": "title",
      "text": "화면에 표시할 텍스트\\n줄바꿈 포함",
      "voice_text": "TTS가 읽을 텍스트… (예: [A] 훅)",
      "emphasis": "high",
      "highlight_words": ["핵심단어"],
      "image_query": "{name}"
    }},
    {{
      "id": 2,
      "timestamp": 4,
      "duration": 4,
      "type": "body",
      "text": "…",
      "voice_text": "예: [A] 이름·나이·현재 직업 한 번에 (1963년생 ~씨, 현직 ~)",
      "emphasis": "medium",
      "highlight_words": ["이름", "직업"],
      "image_query": "{name}"
    }},
    {{
      "id": 3,
      "timestamp": 8,
      "duration": 5,
      "type": "body",
      "text": "…",
      "voice_text": "예: [B] 출생지·학력·성장 과정",
      "emphasis": "medium",
      "highlight_words": ["학력 키워드"],
      "image_query": "학력 관련 이미지 (예: 서울대학교 정문)"
    }},
    {{
      "id": 4,
      "timestamp": 13,
      "duration": 5,
      "type": "body",
      "text": "…",
      "voice_text": "예: [C] 주요 경력 + 현재 활동 ('지금은 ~ 하고 있습니다')",
      "emphasis": "high",
      "highlight_words": ["경력"],
      "image_query": "직업·경력 관련 이미지"
    }},
    {{
      "id": 5,
      "timestamp": 18,
      "duration": 4,
      "type": "comment",
      "text": "…",
      "voice_text": "예: [D] 여운/공감 한 마디 (출처 표기 금지)",
      "emphasis": "low",
      "highlight_words": ["마무리 키워드"],
      "image_query": "{name}"
    }}
  ],
  "audio": {{
    "tts_script": "전체 TTS 대본 (모든 scene voice_text 이어붙임)",
    "voice": "",
    "rate": "",
    "pitch": ""
  }},
  "background": {{
    "type": "gradient",
    "colors": []
  }}
}}
```

audio.voice/rate/pitch, background.colors는 빈 값으로 두세요 (시스템 자동 설정).

## ⚠️ 출력 형식 강제 (절대 준수)

- **JSON만 출력**하세요. 다른 설명·질문·선택지·마크다운 부가 텍스트 전면 금지.
- 제공된 정보가 부족해 보여도 **질문하지 말고** 위 정보만으로 최선의 스크립트를
  작성하세요. 예: "대한민국의 판사 출신 정치인." 한 줄만 주어져도
  - 훅 씬: "판사 출신 정치인, 누군지 아시나요?"
  - 본론: 요약 문장을 2~3개 씬으로 재구성
  - 마무리: "앞으로 주목해볼 만한 인물입니다"
  처럼 짧게라도 8~10 씬·30~45초 스크립트를 반드시 완성.
- "정보가 부족해서 만들 수 없습니다" 같은 응답은 **절대 허용 안 됨**.
- 출력은 반드시 여는 중괄호로 시작해서 닫는 중괄호로 끝나야 합니다."""


def build_celebrity_prompt(info: CelebrityInfo) -> str:
    """Fill the celebrity template with facts from `info`."""
    highlights_block = _format_bullet_list(info.career_highlights)
    trivia_block = _format_bullet_list(info.trivia)

    return CELEBRITY_ANALYZE_PROMPT.format(
        name=info.name,
        summary=info.summary or "(제공된 요약 없음)",
        birth_date=info.birth_date or "(제공된 정보 없음)",
        profession=info.profession or "(제공된 정보 없음)",
        career_highlights_block=highlights_block,
        trivia_block=trivia_block,
        source_url=info.source_url,
    )


def _format_bullet_list(items: tuple[str, ...]) -> str:
    if not items:
        return "  (제공된 정보 없음)"
    return "\n".join(f"  - {item}" for item in items)
