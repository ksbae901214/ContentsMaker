"""T065: Claude CLI에 전달할 해설 자막 프롬프트 템플릿.

톤앤매너 주입 + 팩트 기반 + 15자 이내 강제. 선거 모드 분기 포함(FR-032).
"""
from __future__ import annotations

COMMENTARY_SYSTEM_PROMPT = """당신은 정치 쇼츠 해설 자막 작성 어시스턴트입니다.

원칙:
1. 팩트 기반으로만 작성 (추측·단정 금지)
2. 1줄당 15자 이내 (한글 1자=1카운트)
3. 중립적·객관적 어조 (선동·비방 금지)
4. 원본 발언 맥락을 왜곡하지 말 것
5. 편향적 형용사 사용 금지 ("역대급", "처참한" 등)
"""

COMMENTARY_USER_PROMPT = """다음 발언에 대한 쇼츠 해설 자막 후보 3개를 JSON으로 작성하세요.

## 발언자
이름: {politician_name}
톤앤매너 가이드: {tone_guide}

## 회의 타입
{session_type}

## 원본 발언
{stt_text}

## 요구 톤 힌트
{tone_hint}

## 출력 형식 (반드시 JSON만 출력, 코드 블록 없이)
{{
  "candidates": [
    {{"text": "후보1 텍스트 (15자 이내)", "confidence": 0.0~1.0}},
    {{"text": "후보2", "confidence": 0.0~1.0}},
    {{"text": "후보3", "confidence": 0.0~1.0}}
  ]
}}

## 제약
- 각 후보는 반드시 15자 이내
- confidence는 해당 후보가 원본 맥락을 잘 요약한 정도 (0.0~1.0)
- 중립 톤 유지
"""

COMMENTARY_NEUTRAL_PROMPT = """당신은 선거기간 정치 쇼츠 해설 자막 작성 어시스턴트입니다.
⚠️ 선거기간: 후보 우호 표현 절대 금지, 정책 설명 중심으로만 작성 (FR-032).

원칙:
1. 후보자 개인 특성/성품 언급 금지
2. 정책·발언 내용만 설명
3. "훌륭한", "뛰어난", "역량있는" 등 우호적 형용사 금지
4. 팩트 기반·중립적 어조 엄수
5. 1줄당 15자 이내
"""


def build_commentary_prompt(
    *,
    politician_name: str,
    stt_text: str,
    tone_guide: str,
    tone_hint: str,
    session_type: str,
    is_election_period: bool = False,
) -> str:
    """Claude CLI에 전달할 프롬프트 문자열 생성."""
    system = COMMENTARY_NEUTRAL_PROMPT if is_election_period else COMMENTARY_SYSTEM_PROMPT
    user = COMMENTARY_USER_PROMPT.format(
        politician_name=politician_name,
        tone_guide=tone_guide or "(가이드 없음)",
        session_type=session_type or "(미지정)",
        stt_text=stt_text,
        tone_hint=tone_hint or "팩트 기반 객관적",
    )
    return f"{system}\n\n---\n\n{user}"
