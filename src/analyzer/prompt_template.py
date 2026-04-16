"""Prompt template for Claude Code analysis.

Generates the prompt that converts a BlindPost into a ShortsScript JSON.
"""
from __future__ import annotations

ANALYZE_PROMPT = """다음 블라인드 게시글을 유튜브 쇼츠 영상용 스크립트로 변환하세요.

## 규칙

1. **감정 타입 자동 감지**: funny(재밌음), touching(감동), angry(분노), relatable(공감) 중 하나
2. **30-60초 분량**으로 편집, 씬 하나당 **최대 5초**:
   - ⚠️ CRITICAL: 모든 씬의 duration은 **반드시 5초 이하**여야 합니다.
     (Kling 2.5 등 AI 영상 생성 모델이 5초 클립만 만들기 때문에,
     5초를 넘는 씬은 영상이 중간에 멈춰서 freeze됩니다.)
   - voice_text가 5초를 넘으면 **두 개 이상의 씬으로 분할**하세요.
   - 한 씬의 voice_text는 한국어 기준 약 12~15음절 또는 ~20자 이하로 유지하세요 (TTS rate +20%).
   - 도입(title 씬): 5초 — 제목을 임팩트 있게 (한 문장)
   - 전개(body 씬들): 25-45초 — 여러 개의 5초 이하 씬으로 나누어 구성
   - 결말(comment 씬): 5-10초 — 베스트 댓글 1-2개를 각각 5초 이하 씬으로
3. **TTS 친화적**으로 텍스트 변환:
   - voice_text는 읽기 쉽게 구어체로
   - 줄임말, 신조어는 풀어서 작성
   - ㅋㅋㅋ → "크크크" 또는 의미 설명으로 변환
4. **개인정보 제거**: 실명, 직급, 부서명, 연락처 → 제거 또는 "OO"으로 마스킹
5. **욕설/비속어 순화**: 영상에 적합한 표현으로 순화
6. **emphasis 설정**: 핵심 문장은 "high", 보조 문장은 "medium", 댓글은 "low"
7. **text 줄바꿈 (필수)**: 각 씬의 text에 반드시 줄바꿈(\\n)을 삽입하세요.
   - 1줄당 최대 15자 이내
   - 문맥 단위로 끊기: 조사 뒤(은/는/이/가/을/를/에서/도), 쉼표 뒤, 의미 단위 경계
   - 예: "회사에서 3년 일했는데\\n월급이 200도 안 돼요"
   - 예: "이직하고 싶은데\\n용기가 안 나네요"
   - 화면 가로 80% 이내에 들어와야 하므로 1줄을 짧게 유지
8. **text 길이 제한**: 각 씬 text는 최대 3줄(약 45자) 이내로 요약
9. **highlight_words (필수)**: 각 씬에서 감정적으로 핵심이 되는 단어 1-3개를 highlight_words 배열에 넣으세요. 이 단어들은 영상에서 색상으로 강조됩니다.
   - 예: text가 "월급이 200도 안 돼요"면 highlight_words: ["200", "안 돼요"]
   - 숫자, 금액, 감정 표현, 핵심 명사를 우선 선택
10. **마무리 씬 필수**: 마지막 씬은 반드시 영상을 깔끔하게 마무리하는 한 줄 멘트로 끝내세요. 원본 글이 마무리가 부족해도 AI가 자연스러운 결론을 만들어주세요.
11. **자연스러운 발화 리듬 (필수)**: voice_text에 구두점을 활용하여 사람처럼 말하게 만드세요:
   - 짧은 쉼: 쉼표(,)를 사용 — TTS가 자연스럽게 짧은 pause를 넣음
   - 중간 쉼: 마침표(.)를 사용 — TTS가 문장 끝에서 중간 pause
   - 긴 쉼 (씬 전환/강조): 말줄임표(...)를 사용 — TTS가 더 긴 pause
   - 예: "나는 선넘네라는 말, 친한 친구한테도 안 쓰거든요..."
   - 예: "아무리 서운해도, 어른한테 선넘네는, 좀 아니지..."
   - 예: "월급이 200도 안 돼요. 이직하고 싶은데, 용기가 안 나네요..."
   - 누군가에게 이야기를 설명하듯 자연스러운 템포로 만드세요
   - 랩처럼 빠르게 이어지지 않도록 적절한 쉼을 반드시 넣으세요
   - SSML 태그(예: <break/>)는 절대 사용하지 마세요. TTS가 태그를 텍스트로 읽습니다

## 원본 데이터

제목: {title}
작성자: {author}
본문:
{body}

댓글:
{comments_text}

## 출력 형식 (반드시 이 JSON 형식으로만 출력)

```json
{{
  "metadata": {{
    "title": "영상 제목",
    "emotion_type": "funny|touching|angry|relatable",
    "duration": 45,
    "source_url": ""
  }},
  "scenes": [
    {{
      "id": 1,
      "timestamp": 0,
      "duration": 4,
      "type": "title",
      "text": "화면에 표시할 텍스트\\n줄바꿈 포함",
      "voice_text": "TTS가 읽을 텍스트, 쉼표 뒤 짧은 pause. 마침표 뒤 중간 pause...",
      "emphasis": "high",
      "highlight_words": ["핵심단어1", "핵심단어2"]
    }}
  ],
  "audio": {{
    "tts_script": "전체 TTS 대본 (모든 scene의 voice_text를 이어붙인 것)",
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

audio.voice, audio.rate, audio.pitch, background.colors는 빈 값으로 두세요 (시스템이 감정 타입에 따라 자동 설정합니다).

JSON만 출력하세요. 다른 설명은 포함하지 마세요."""


TOPIC_ANALYZE_PROMPT = """다음 주제를 유튜브 쇼츠 영상용 스크립트로 변환하세요.

## 주제 정보

주제: {topic}
스타일: {style_desc}
톤: {tone}
추가 설명: {details}

## 규칙

1. **감정 타입 자동 감지**: funny(재밌음), touching(감동), angry(분노), relatable(공감) 중 하나
2. **30-60초 분량**으로 구성, 씬 하나당 **최대 5초**:
   - ⚠️ CRITICAL: 모든 씬의 duration은 **반드시 5초 이하**여야 합니다.
     (Kling 2.5 등 AI 영상 생성 모델이 5초 클립만 만들기 때문에,
     5초를 넘는 씬은 영상이 중간에 멈춰서 freeze됩니다.)
   - voice_text가 5초를 넘으면 **두 개 이상의 씬으로 분할**하세요.
   - 한 씬의 voice_text는 약 12~15음절 (~20자) 이하로 유지하세요.
   - 도입(title 씬): 5초 — 주제를 임팩트 있게 소개
   - 전개(body 씬들): 25-45초 — 여러 개의 5초 이하 씬으로 스토리텔링
   - 마무리(body 씬): 5초 이하 — 깔끔한 결론
3. **TTS 친화적**으로 텍스트 변환:
   - voice_text는 읽기 쉽게 구어체로
   - 줄임말, 신조어는 풀어서 작성
4. **emphasis 설정**: 핵심 문장은 "high", 보조 문장은 "medium", 마무리는 "low"
5. **text 줄바꿈 (필수)**: 각 씬의 text에 반드시 줄바꿈(\\n)을 삽입하세요.
   - 1줄당 최대 15자 이내
   - 문맥 단위로 끊기: 조사 뒤(은/는/이/가/을/를/에서/도), 쉼표 뒤, 의미 단위 경계
   - 화면 가로 80% 이내에 들어와야 하므로 1줄을 짧게 유지
6. **text 길이 제한**: 각 씬 text는 최대 3줄(약 45자) 이내로 요약
7. **highlight_words (필수)**: 각 씬에서 감정적으로 핵심이 되는 단어 1-3개를 highlight_words 배열에 넣으세요.
   - 숫자, 금액, 감정 표현, 핵심 명사를 우선 선택
8. **마무리 씬 필수**: 마지막 씬은 반드시 영상을 깔끔하게 마무리하는 한 줄 멘트로 끝내세요.
9. **자연스러운 발화 리듬 (필수)**: voice_text에 구두점을 활용하여 사람처럼 말하게 만드세요:
   - 짧은 쉼: 쉼표(,)를 사용
   - 중간 쉼: 마침표(.)를 사용
   - 긴 쉼 (씬 전환/강조): 말줄임표(...)를 사용
   - 누군가에게 이야기를 설명하듯 자연스러운 템포로 만드세요
   - SSML 태그(예: <break/>)는 절대 사용하지 마세요
10. **스토리텔링**: 주제에 대해 시청자가 흥미를 느끼도록 이야기를 풀어주세요. 단순 나열이 아닌, 기승전결 구조로 구성하세요.

## 출력 형식 (반드시 이 JSON 형식으로만 출력)

```json
{{{{
  "metadata": {{{{
    "title": "영상 제목",
    "emotion_type": "funny|touching|angry|relatable",
    "duration": 45,
    "source_url": "",
    "source_type": "topic"
  }}}},
  "scenes": [
    {{{{
      "id": 1,
      "timestamp": 0,
      "duration": 4,
      "type": "title",
      "text": "화면에 표시할 텍스트\\n줄바꿈 포함",
      "voice_text": "TTS가 읽을 텍스트, 쉼표 뒤 짧은 pause. 마침표 뒤 중간 pause...",
      "emphasis": "high",
      "highlight_words": ["핵심단어1", "핵심단어2"]
    }}}}
  ],
  "audio": {{{{
    "tts_script": "전체 TTS 대본",
    "voice": "",
    "rate": "",
    "pitch": ""
  }}}},
  "background": {{{{
    "type": "gradient",
    "colors": []
  }}}}
}}}}
```

audio.voice, audio.rate, audio.pitch, background.colors는 빈 값으로 두세요 (시스템이 감정 타입에 따라 자동 설정합니다).

JSON만 출력하세요. 다른 설명은 포함하지 마세요."""

_STYLE_DESCRIPTIONS = {
    "narration": "나레이션 스타일 — 화자가 시청자에게 이야기를 들려주듯 설명",
    "skit": "스킷/콩트 스타일 — 등장인물들의 대화와 상황극으로 구성",
    "review": "리뷰 스타일 — 주제에 대한 분석과 평가를 중심으로 구성",
}


def build_prompt(title: str, author: str, body: str, comments: list[dict]) -> str:
    """Build the analysis prompt from BlindPost data."""
    comments_text = "\n".join(
        f"- [{c.get('author', '익명')}] {c['text']} (좋아요 {c.get('likes', 0)})"
        for c in comments
    ) if comments else "(댓글 없음)"

    return ANALYZE_PROMPT.format(
        title=title,
        author=author,
        body=body,
        comments_text=comments_text,
    )


def build_topic_prompt(
    topic: str,
    style: str = "narration",
    tone: str = "",
    details: str = "",
) -> str:
    """Build the analysis prompt from TopicInput data."""
    style_desc = _STYLE_DESCRIPTIONS.get(style, _STYLE_DESCRIPTIONS["narration"])
    return TOPIC_ANALYZE_PROMPT.format(
        topic=topic,
        style_desc=style_desc,
        tone=tone or "(자동 감지)",
        details=details or "(없음)",
    )


# ── Political commentary prompt ─────────────────────────────────────────

POLITICAL_ANALYZE_PROMPT = """다음 국회 발언 영상의 자막을 분석하여 유튜브 쇼츠 정치 해설 영상 스크립트를 생성하세요.

## 원본 정보
영상 URL: {youtube_url}
클립 구간: {clip_start}초 ~ {clip_end}초
톤: {tone}
추가 지시: {details}

## 자막 (시간별)
{transcript_text}

## 교차 편집 규칙 (필수)

1. **구조**: title → clip → commentary → clip → commentary → ... → commentary
2. **"clip" 씬**: 원본 영상의 특정 구간 재생
   - clip_start / clip_end 필드 필수 (원본 클립 내 상대 시간, 0초부터)
   - text: 원본 자막 내용 (화면에 자막으로 표시)
   - voice_text: 빈 문자열 "" (TTS 안 함, 원본 오디오 재생)
3. **"commentary" 씬**: AI 해설 (그라디언트 배경 + 텍스트)
   - voice_text: 해설 내용 (TTS로 읽힘)
   - clip_start / clip_end 불필요
4. **"title" 씬**: 첫 번째 씬, 임팩트 있는 제목 (3초)

## 구성 규칙

- clip 씬 3-4개: 원본 발언의 핵심 구간 (각 3-5초)
- commentary 씬 3-4개: 각 clip 직후 해설 (각 3-5초)
- 마무리 commentary 1개: 결론/전망
- **총 30-60초**, 씬 하나당 **최대 5초**
- emotion_type: "angry" (비판적 톤) 또는 "relatable" (분석/공감 톤)

## 해설 규칙

- 정치적 편향 최소화, 핵심을 짚는 분석
- 시청자가 이해하기 쉬운 구어체
- highlight_words로 핵심 단어 1-3개 강조

## 텍스트 규칙

- text 줄바꿈: 15자 이내
- voice_text: 자연스러운 구어체, 문장 끝에 마침표
- audio.tts_script: commentary + title 씬의 voice_text만 이어붙이기 (clip 씬 제외)

## 출력 JSON

```json
{{{{
  "metadata": {{{{
    "title": "임팩트 있는 제목",
    "emotion_type": "relatable",
    "duration": 45,
    "source_url": "{youtube_url}",
    "source_type": "political"
  }}}},
  "scenes": [
    {{{{ "id": 1, "timestamp": 0, "duration": 3, "type": "title",
       "text": "제목\\n두 줄", "voice_text": "제목 음성",
       "emphasis": "high", "highlight_words": ["핵심"] }}}},
    {{{{ "id": 2, "timestamp": 3, "duration": 5, "type": "clip",
       "text": "의원의 발언\\n자막", "voice_text": "",
       "emphasis": "high", "highlight_words": ["핵심단어"],
       "clip_start": 0.0, "clip_end": 5.0 }}}},
    {{{{ "id": 3, "timestamp": 8, "duration": 4, "type": "commentary",
       "text": "해설 텍스트\\n두 줄", "voice_text": "이 발언의 핵심은 이것입니다.",
       "emphasis": "medium", "highlight_words": ["핵심"] }}}}
  ],
  "audio": {{{{
    "tts_script": "제목 음성 이 발언의 핵심은 이것입니다. ...",
    "voice": "",
    "rate": "",
    "pitch": ""
  }}}},
  "background": {{{{
    "type": "gradient",
    "colors": []
  }}}}
}}}}
```

audio.voice, audio.rate, audio.pitch, background.colors는 빈 값으로 두세요 (시스템이 자동 설정).
JSON만 출력하세요. 다른 설명은 포함하지 마세요."""


def build_political_prompt(
    youtube_url: str,
    transcript: list[dict],
    clip_start: float,
    clip_end: float,
    tone: str = "",
    details: str = "",
) -> str:
    """Build the analysis prompt for political commentary."""
    transcript_text = "\n".join(
        f"[{seg['start']:.1f}s-{seg['end']:.1f}s] {seg['text']}"
        for seg in transcript
    ) if transcript else "(자막 없음 — 영상 내용을 기반으로 일반적인 정치 해설 구성)"

    return POLITICAL_ANALYZE_PROMPT.format(
        youtube_url=youtube_url,
        clip_start=clip_start,
        clip_end=clip_end,
        tone=tone or "객관적 분석",
        details=details or "(없음)",
        transcript_text=transcript_text,
    )
