"""Prompt template for celebrity-introduction Shorts (Phase 9-3).

Converts a CelebrityInfo (sourced from Namuwiki, CC BY-NC-SA 3.0) into the
ShortsScript JSON. The prompt explicitly forbids quoting Namuwiki text
verbatim and forbids adding facts that are not in the provided context —
Claude hallucinations in a biographical video are a real defamation risk.

The prompt also forces the last scene to end with an attribution line
("출처: 나무위키") so the final render preserves source credit.
"""
from __future__ import annotations

from src.scraper.celebrity_models import CelebrityInfo


CELEBRITY_ANALYZE_PROMPT = """다음 인물 정보를 유튜브 쇼츠 영상용 스크립트로 변환하세요.

## 인물 정보 (나무위키 출처)

이름: {name}
요약: {summary}
출생: {birth_date}
직업: {profession}
주요 경력/업적:
{career_highlights_block}
여담/일화:
{trivia_block}

## 법적/윤리 규칙 (CRITICAL, 반드시 준수)

1. **팩트 제한**: 위에 제공된 정보에 없는 사실은 **절대로 추가하지 마세요**.
   - 출생일, 소속, 기록, 인간관계 등 위에 없는 정보는 언급 금지
   - 추측, 루머, 미확인 일화는 금지
   - 확실하지 않으면 생략하는 편이 낫습니다
2. **원문 금지**: 위 텍스트를 그대로 옮기지 말고, **본인 표현으로 재구성**하세요
   (나무위키 라이선스 CC BY-NC-SA 3.0 준수).
3. **마지막 씬 필수**: 마지막 씬의 text는 반드시 다음 중 하나로 끝내세요:
   - "출처: 나무위키"
   - "정보 출처\\n나무위키"
   이 줄은 영상 엔딩 출처 표기 역할을 합니다.

## 영상 제작 규칙

4. **감정 타입**: funny, touching, angry, relatable 중 인물 스토리에 가장 어울리는 하나 선택.
   - 재밌는 일화 위주면 funny, 감동 스토리면 touching, 논란/투쟁이면 angry, 보통 위인/셀럽 소개면 relatable
5. **30-50초 분량**으로 구성, 씬 하나당 **최대 5초**:
   - ⚠️ CRITICAL: 모든 씬의 duration은 반드시 5초 이하
   - voice_text가 5초를 넘으면 두 개 이상의 씬으로 분할
   - 한 씬의 voice_text는 한국어 ~20자 이하 (TTS rate +20%)
   - 도입(title 씬): 1개, 5초 이하 — 인물명 + 한 줄 소개
   - 전개(body 씬들): 4-6개, 각 5초 이하 — 핵심 업적/일화
   - 마무리(comment 씬): 1개, 5초 이하 — "출처: 나무위키" 포함
6. **TTS 친화적**: voice_text는 구어체, 줄임말 풀어쓰기, 쉼표/마침표로 쉼 제어
7. **emphasis**: 핵심 문장은 "high", 보조는 "medium", 마무리는 "low"
8. **text 줄바꿈 (필수)**: 각 씬의 text에 반드시 줄바꿈(\\n) 삽입, 1줄당 최대 15자 이내
9. **text 길이**: 각 씬 text는 최대 3줄(약 45자) 이내
10. **highlight_words (필수)**: 각 씬당 감정적 핵심 단어 1-3개
11. **자연스러운 발화 리듬**: 쉼표/마침표/말줄임표로 호흡 조절, SSML 금지
12. **존칭 처리**: 역사 인물은 "~입니다/~였습니다" 체, 현존 인물은 중립 존칭
13. **추측 표현 금지**: "~라고 합니다", "~로 알려져 있습니다" 정도로 마무리하는 게 안전

## 출력 형식 (반드시 이 JSON 형식으로만 출력)

```json
{{
  "metadata": {{
    "title": "{name} (짧은 소개)",
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
      "voice_text": "TTS가 읽을 텍스트...",
      "emphasis": "high",
      "highlight_words": ["핵심단어"]
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

audio.voice/rate/pitch, background.colors는 빈 값으로 두세요 (시스템이 자동 설정).

JSON만 출력하세요. 다른 설명은 포함하지 마세요."""


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
