# Feature Specification: Analyzer + TTS Module

**Feature Branch**: `002-analyzer-tts`
**Created**: 2026-03-23
**Status**: Draft
**Input**: User description: "Phase 2: raw_content.json을 Claude Code로 분석하여 쇼츠 스크립트(script.json)를 생성하고, edge-tts로 한국어 음성(voice.mp3)을 생성한다."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 블라인드 글을 쇼츠 스크립트로 변환 (Priority: P1)

사용자가 raw_content.json(블라인드 글)을 시스템에 전달하면, Claude Code(Sonnet 4.6)가 감정 분석, 60초 분량 요약, 씬 타임라인을 자동 생성하여 script.json으로 저장한다.

비유하면, 영화 감독이 원작 소설을 읽고 장면별 촬영 대본(콘티)을 만드는 것과 같다. 긴 원문을 60초짜리 영상에 맞게 핵심만 추리고, 어떤 순서로 보여줄지 타임라인을 짜는 과정이다.

**Why this priority**: TTS와 영상 렌더링의 입력이 되는 핵심 데이터. 이 스크립트 없이는 이후 모든 단계가 불가.

**Independent Test**: 샘플 raw_content.json → Claude Code 실행 → script.json 생성 확인 + ShortsScript 스키마 검증.

**Acceptance Scenarios**:

1. **Given** 유효한 raw_content.json, **When** Analyzer를 실행하면, **Then** script.json이 생성되고 ShortsScript 스키마와 일치한다
2. **Given** 유머러스한 블라인드 글, **When** 감정 분석하면, **Then** emotionType이 "funny"로 설정된다
3. **Given** 감동적인 이야기, **When** 감정 분석하면, **Then** emotionType이 "touching"으로 설정된다
4. **Given** 긴 본문(3000자 이상), **When** 요약하면, **Then** TTS 기준 30-60초 분량(약 150-300자)으로 축약된다
5. **Given** 베스트 댓글이 포함된 글, **When** 분석하면, **Then** 핵심 댓글 1-3개가 script.json의 comment 씬으로 포함된다

---

### User Story 2 - 스크립트를 한국어 음성으로 변환 (Priority: P1)

script.json의 TTS 스크립트를 edge-tts로 변환하여 자연스러운 한국어 음성 파일(voice.mp3)을 생성한다. 감정 타입에 따라 음성, 속도, 피치가 자동으로 최적화된다.

비유하면, 라디오 DJ가 대본을 받아서 감정에 맞는 목소리 톤으로 녹음하는 것과 같다.

**Why this priority**: 영상 렌더링의 오디오 소스. 스크립트와 함께 P1 핵심.

**Independent Test**: script.json → edge-tts 실행 → voice.mp3 재생 확인.

**Acceptance Scenarios**:

1. **Given** 유효한 script.json, **When** TTS를 실행하면, **Then** voice.mp3가 생성되고 재생 가능하다
2. **Given** emotionType이 "funny"인 스크립트, **When** TTS 실행하면, **Then** 밝고 빠른 목소리(ko-KR-BongJinNeural, +15% 속도)로 생성된다
3. **Given** emotionType이 "touching"인 스크립트, **When** TTS 실행하면, **Then** 부드럽고 느린 목소리(ko-KR-SunHiNeural, -10% 속도)로 생성된다
4. **Given** TTS 스크립트가 300자인 경우, **When** 음성 생성하면, **Then** 30-60초 분량의 MP3가 생성된다

---

### User Story 3 - 통합 파이프라인: raw → script → voice (Priority: P2)

사용자가 raw_content.json 경로를 입력하면, Analyzer와 TTS를 연속 실행하여 script.json과 voice.mp3를 한번에 생성한다.

**Why this priority**: 편의성 향상. US1+US2가 독립 동작한 후 통합.

**Independent Test**: `python3 -m src.main analyze --file raw.json` → script.json + voice.mp3 동시 생성 확인.

**Acceptance Scenarios**:

1. **Given** raw_content.json 경로, **When** 통합 명령어 실행, **Then** `data/scripts/`에 script.json, `data/audio/`에 voice.mp3가 모두 생성된다
2. **Given** Analyzer 성공 + TTS 실패, **When** 실행하면, **Then** script.json은 보존되고 TTS 에러만 보고된다

---

### Edge Cases

- Claude Code 실행 실패 (프로세스 에러, 타임아웃) → 에러 메시지 + 종료 코드
- edge-tts 네트워크 오류 → 재시도 1회 후 에러 보고
- 빈 본문 또는 매우 짧은 본문 → "분석에 충분한 내용이 없습니다" 에러
- 개인정보 포함 텍스트 → Analyzer 프롬프트에서 마스킹 지시 (Constitution 원칙 IV)
- script.json의 TTS 스크립트가 빈 문자열 → TTS 스킵 + 경고

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템 MUST raw_content.json을 입력받아 Claude Code(Sonnet 4.6)로 분석하여 script.json을 생성한다
- **FR-002**: 시스템 MUST 감정 타입(funny/touching/angry/relatable) 4종을 자동 분류한다
- **FR-003**: 시스템 MUST 원문을 30-60초 분량(TTS 기준)으로 요약한다
- **FR-004**: 시스템 MUST 씬 타임라인(도입-전개-클라이맥스-결말)을 자동 생성한다
- **FR-005**: 시스템 MUST 핵심 댓글 1-3개를 자동 선별하여 comment 씬으로 포함한다
- **FR-006**: 시스템 MUST 개인정보(실명, 직급, 부서명)를 마스킹한다
- **FR-007**: 시스템 MUST script.json의 TTS 스크립트를 edge-tts로 변환하여 voice.mp3를 생성한다
- **FR-008**: 시스템 MUST 감정 타입에 따라 음성(voice), 속도(rate), 피치(pitch)를 자동 설정한다
- **FR-009**: 시스템 MUST script.json을 `data/scripts/`에, voice.mp3를 `data/audio/`에 저장한다
- **FR-010**: 시스템 MUST Claude Code 또는 edge-tts 실패 시 명확한 에러 메시지를 출력한다

### Key Entities

- **ShortsScript**: 쇼츠 영상 제작용 스크립트. 핵심 속성: 메타데이터(title, emotionType, duration), 씬 목록(scenes: [{timestamp, duration, type, text, voiceText, emphasis}]), 오디오 설정(audio: {ttsScript, voice, rate, pitch}), 배경 설정(background)
- **Scene**: 개별 영상 씬. 핵심 속성: 시작 시각(timestamp), 지속 시간(duration), 유형(title/body/comment), 표시 텍스트(text), TTS 텍스트(voiceText), 강조 수준(emphasis)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: raw_content.json 입력 후 2분 이내에 script.json이 생성된다
- **SC-002**: 생성된 script.json은 ShortsScript 스키마와 100% 일치한다
- **SC-003**: 4종 감정 타입 각 1개씩 총 4개 샘플에서 감정 분류가 합리적이다
- **SC-004**: TTS 스크립트의 음성 길이가 30-60초 범위 내이다
- **SC-005**: voice.mp3가 정상 재생되며 한국어가 자연스럽다
- **SC-006**: 감정별 음성 톤이 구별 가능하다 (funny ≠ touching ≠ angry ≠ relatable)

## Assumptions

- Claude Code가 로컬에 설치되어 있고 `claude` 명령어로 실행 가능하다
- edge-tts는 `pip install edge-tts`로 설치하며 인터넷 연결이 필요하다
- Claude Code의 JSON 출력은 항상 유효한 JSON이다 (파싱 실패 시 재시도)
- TTS 스크립트는 한국어만 포함한다 (영어 혼용 시 발음 품질 저하 가능)
