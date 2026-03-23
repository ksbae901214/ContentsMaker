"""Prompt template for Claude Code analysis.

Generates the prompt that converts a BlindPost into a ShortsScript JSON.
"""
from __future__ import annotations

ANALYZE_PROMPT = """다음 블라인드 게시글을 유튜브 쇼츠 영상용 스크립트로 변환하세요.

## 규칙

1. **감정 타입 자동 감지**: funny(재밌음), touching(감동), angry(분노), relatable(공감) 중 하나
2. **30-60초 분량**으로 편집:
   - 도입(title 씬): 5초 — 제목을 임팩트 있게
   - 전개(body 씬들): 25-45초 — 핵심 내용만 추출
   - 결말(comment 씬): 5-10초 — 베스트 댓글 1-2개
3. **TTS 친화적**으로 텍스트 변환:
   - voice_text는 읽기 쉽게 구어체로
   - 줄임말, 신조어는 풀어서 작성
   - ㅋㅋㅋ → "크크크" 또는 의미 설명으로 변환
4. **개인정보 제거**: 실명, 직급, 부서명, 연락처 → 제거 또는 "OO"으로 마스킹
5. **욕설/비속어 순화**: 영상에 적합한 표현으로 순화
6. **emphasis 설정**: 핵심 문장은 "high", 보조 문장은 "medium", 댓글은 "low"

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
      "duration": 5,
      "type": "title",
      "text": "화면에 표시할 텍스트",
      "voice_text": "TTS가 읽을 텍스트",
      "emphasis": "high"
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
