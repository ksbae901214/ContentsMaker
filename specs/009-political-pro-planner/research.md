# Phase 0 — Research: Political Shorts Planner

**Branch**: `009-political-pro-planner`
**Date**: 2026-05-13
**Spec**: [spec.md](./spec.md)

> 본 단계는 spec의 모든 NEEDS CLARIFICATION 해소 + 기술 의사결정의 근거를 정리한다. spec 자체에는 [NEEDS CLARIFICATION] 마커가 없지만, plan 단계의 Technical Context에서 결정해야 할 항목이 6개 있어 각각 연구한 결과를 기록한다.

---

## R1. 3개 기획안 생성 방식 — Claude 단일 호출 vs N회 호출

**Decision**: **Claude 단일 호출 + 출력 JSON 스키마 strict** 방식.

**Rationale**
- `analyze_topic` / `analyze_political` 등 기존 호출은 Claude Code 서브프로세스이고 1회 호출당 30s~3min 소요. 3회 직렬 호출 시 1.5~9분 → spec SC-001(90초) 위반.
- 1회 호출에서 3개 plan을 동시 생성하면 toplevel JSON 배열 `{"plans": [p1, p2, p3]}` 형태로 받을 수 있어 결정적이고 빠름.
- 단일 호출이지만 시스템 프롬프트에 "3개는 서로 다른 angle을 가져야 한다" 명시로 다양성 확보.
- 기존 `claude_analyzer.py`의 응답 파서 패턴(`json.loads` + 재시도) 그대로 활용.

**Alternatives considered**
- ❌ Claude 3회 병렬 호출: 90초 한도는 만족하나 Claude CLI는 동시 호출 시 락 충돌 사례 있음(`86476e5` 커밋 참조). 또 angle 다양성을 명시적으로 강제 못함(각 호출이 독립적).
- ❌ Claude 3회 직렬 호출(angle별 1회): 시간 초과 위험.
- ❌ Streaming 부분 결과: 사용자 체감은 좋으나 UI 복잡도 증가, 본 단계는 비채택.

---

## R2. TTS 공급자 — Gemini TTS Charon vs edge-tts

**Decision**: **Gemini TTS (Charon voice)** 사용. Constitution 원칙 I 표면 충돌이지만, "변동 비용 $0"의 본질적 원칙을 만족하므로 plan.md의 Complexity Tracking에서 정당화함.

**Rationale**
- 사용자가 명시적으로 지정: Charon / Newscaster 스타일 / Rapid 페이스 / British(RP) / Temp 0.5. 영상생성지침의 "임팩트 있는 뉴스 톤" 요구사항에 일치.
- 기존 `src/tts/gemini_tts_generator.py` 이미 존재 — 호출 인프라 재사용 가능. 신규 작업은 `voice_name="Charon"` + `style_prompt` + `temperature` 파라미터 추가뿐.
- Gemini TTS 무료 한도(5 RPM, 일일 한도 내) 안에서 운영하면 변동비 $0. 원칙 I의 본질 만족.
- edge-tts의 한국어 음성에는 "뉴스 아나운서 + British RP" 스타일이 없음 → 사용자 명시 요구 미충족.

**Alternatives considered**
- ❌ edge-tts `ko-KR-InJoonNeural` (angry 톤): Constitution 원칙 I 글자 그대로는 만족하나 사용자 요구(British RP 뉴스 톤) 미충족.
- ❌ 사용자 토글: 매 호출 사용자 결정 추가 → UX 마찰 증가. 본 모드는 정치 콘텐츠 전용이므로 단일 음성으로 고정.

**Constitution mitigation**
- Gemini TTS는 **유료 API 아님**(무료 한도 안에서 운영). 원칙 I의 진정한 의도("운영비 0"")는 위배하지 않음.
- 무료 한도 초과 시 사용자에게 명시적 오류(FR-019) — 변동비 발생 방지 가드 내재.
- plan.md의 Complexity Tracking에 본 정당화를 기록.

---

## R3. Constitution 원칙 IV "정치/종교 자동 스킵" 충돌 해소

**Decision**: 본 기능은 원칙 IV의 "자동 스킵" 대상에서 **명시적 예외** 처리. 단, 안전 가드 4종을 시스템 프롬프트에 인코딩하여 위험 최소화.

**Rationale**
- 원칙 IV는 "블라인드 자동 파이프라인이 정치 글을 자동 게시하지 못하도록" 보호하기 위한 가드.
- 본 기능은 **명시적 정치 콘텐츠 워크플로우**로, 사용자가 의도적으로 정치 URL을 입력하고 2단계 검수(기획안 + 스크립트)를 거친 후에만 영상이 생성됨. "자동" 파이프라인이 아니므로 원칙 IV의 본래 의도를 위배하지 않음.
- 4가지 절대 준수 항목(사실만 / 의견금지 / 편향금지 / 왜곡금지)을 프롬프트에 명시(FR-007).
- 결과 화면에 "출력 전 사용자 검수 필수" 경고(FR-021).
- 자동 업로드는 명시적으로 차단(FR-020).

**Alternatives considered**
- ❌ 원칙 IV 정정 후 진행: 헌법 개정은 본 plan 범위 밖.
- ❌ 기능 자체 거절: 사용자 요구사항을 무시하므로 비채택.

**Constitution mitigation**
- plan.md Complexity Tracking에 본 예외 명시.
- 후속 단계에서 헌법 v1.3.0 개정 제안(원칙 IV에 "사용자가 명시적으로 시작한 정치 워크플로우는 예외" 단서 추가) — 본 plan에서는 다루지 않음.

---

## R4. 사용 구간 선택 알고리즘 — 자동 vs Claude가 결정

**Decision**: **Claude가 plan별 사용 구간을 결정**(기존 `select_best_clip` 미사용).

**Rationale**
- `select_best_clip`은 키워드 점수로 1개 최적 구간을 뽑는 알고리즘 — 3개 서로 다른 angle을 만들려면 1개 베스트로는 부족.
- Claude는 transcript 전체를 보고 "이 구간은 영상 제목과 직결" / "이 구간은 시청자 반응 공감" / "이 구간은 비교/대조" 등 의미적 판단 가능.
- 출력 스키마에 `clip_start_sec`, `clip_end_sec`을 Claude가 직접 채우도록 명시.
- 영상 길이를 시스템 프롬프트에 함께 전달하여 범위 검증.

**Alternatives considered**
- ❌ `select_best_clip` 3회 호출(다른 max_duration): 비슷한 구간만 반복 선택. angle 다양성 미확보.
- ❌ Claude + post-validation: 범위 클램프만 후처리(FR-013)로 적용.

---

## R5. transcript 길이가 너무 길 때 Claude 입력 truncation

**Decision**: transcript를 영상 길이 기준 **5분 단위 청크**로 자르되, 이 기능에서는 **상한 30분**까지만 처리. 30분 초과 영상은 명시적 경고와 함께 앞 30분만 사용.

**Rationale**
- Claude Sonnet 4.6 입력 토큰 한도는 충분하지만, 너무 긴 transcript는 (a) 토큰 비용 (b) 응답 품질 저하 (c) 시간 초과(90초) 위험.
- 정치 발언 영상은 대부분 30분 이내. 2시간 국정감사 영상 등 예외는 사용자에게 안내(spec Edge Case).
- 1시간 미만에선 truncation 불필요 — 짧은 영상은 그대로 전달.

**Alternatives considered**
- ❌ 무제한 처리: 토큰 비용 + 응답 시간 폭증.
- ❌ 사용자가 청크 선택: UX 마찰.

---

## R6. 검수 화면 재사용 — 기존 ScriptReviewer

**Decision**: 기존 `app/components/ScriptReviewer.tsx`를 그대로 재사용. 본 기능 전용 UI는 기획안 picker(`PoliticalPlanPicker.tsx`)만 신규.

**Rationale**
- `ScriptReviewer`는 이미 씬별 텍스트·길이·이미지 미리보기·재생성을 지원하며 다른 모드(blind, topic, celebrity 등)에서 검증됨.
- ShortsScript를 그대로 받기 때문에 `plan_to_script` 변환만 통과하면 추가 작업 없이 동작.

**Alternatives considered**
- ❌ 정치 모드 전용 검수 UI 신규 구현: 중복 코드 증가, Constitution 원칙 VI(모듈성) 위배.

---

## 의존성 / 통합 패턴 연구

### D1. Claude CLI 호출 패턴
- 기존 `analyze_political`, `analyze_topic` 모두 동일한 subprocess 패턴 사용 (timeout=1800s).
- 본 기능의 `generate_three_plans`도 동일 패턴 적용. 응답 파싱 실패 시 1회 재시도(`86476e5` 패턴).

### D2. Gemini TTS 확장 패턴
- 현재 `_call_gemini_tts`는 `text + voice_name + api_key` 받음.
- 신규 파라미터: `style_prompt: str | None`(텍스트 prefix), `temperature: float = 1.0`.
- `temperature`는 `GenerateContentConfig`에 추가; `style_prompt`는 호출 텍스트 앞에 prefix로 결합.
- 호출 예: `"Read this in a British RP newscaster voice at a rapid pace, with neutral political tone: {actual_text}"`

### D3. 영상 클립 cut 패턴
- 기존 `src/dem_shorts/editor/segment_cutter.cut_segment(input_path, output_path, start_sec, end_sec)` 그대로 활용 — 9:16 변환은 이 함수 내부에서 ffmpeg `scale + pad`로 처리.
- 씬별 비례 분할 로직은 기존 `natv_clip` 분기(`app/api/generate/route.ts:577-593`) 재사용.

### D4. SSE 진행 메시지
- 기존 `withStage(label, expected_seconds, fn)` 패턴 그대로 사용.
- 신규 단계: "정치 영상 다운로드"(90s) → "Transcript 확보"(60s) → "3 기획안 생성"(120s) → "기획안 표시 대기"(사용자) → "스크립트 변환"(5s) → "검수 대기"(사용자) → "씬 클립 분할"(30s) → "Gemini TTS"(20s) → "Remotion 렌더"(60s).

---

## 결론

모든 NEEDS CLARIFICATION 해소 완료. spec 수정 없이 Phase 1으로 진행 가능.

Constitution 충돌 2건(원칙 I, IV)은 plan.md의 Complexity Tracking에 정당화 기록.
