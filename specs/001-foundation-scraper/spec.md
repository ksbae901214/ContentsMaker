# Feature Specification: Foundation - Project Init + Blind Scraper

**Feature Branch**: `001-foundation-scraper`
**Created**: 2026-03-23
**Status**: Draft
**Input**: User description: "Phase 1: Foundation - 프로젝트 초기화 + 수동/자동 2가지 방식의 Scraper 모듈. 처음에는 수동 입력으로 시작하고, 이후 자동 크롤링을 추가한다."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 수동 입력으로 블라인드 글 등록 (Priority: P1)

사용자가 블라인드 앱에서 캡처하거나 복사한 게시글 내용(제목, 본문, 댓글)을 직접 입력하면, 시스템이 BlindPost 스키마에 맞게 검증하고 구조화된 JSON 파일로 저장한다.

비유하면, 요리 레시피 카드를 작성하는 것과 같다. 인터넷에서 본 레시피를 직접 카드에 정리해서 보관함에 넣는 것처럼, 블라인드에서 본 글을 정해진 양식의 JSON으로 옮기는 과정이다.

**Why this priority**: 자동 크롤링은 블라인드 정책/DOM 변경에 취약하다. 수동 입력은 항상 동작하는 확실한 입력 경로이며, 이후 파이프라인(분석→TTS→영상) 개발을 즉시 시작할 수 있게 해준다.

**Independent Test**: 샘플 JSON을 작성하여 스키마 검증 통과 + `data/raw/` 저장을 확인하면 독립 검증 가능.

**Acceptance Scenarios**:

1. **Given** 사용자가 BlindPost 스키마에 맞는 JSON 파일을 작성했을 때, **When** 시스템에 입력하면, **Then** 스키마 검증 통과 후 `data/raw/{id}.json`으로 저장된다
2. **Given** 필수 필드(title, body)가 누락된 JSON, **When** 검증하면, **Then** 누락된 필드를 명시하는 에러 메시지가 출력된다
3. **Given** 댓글이 없는 게시글, **When** comments를 빈 배열(`[]`)로 입력하면, **Then** 정상적으로 저장된다
4. **Given** 특수문자, 이모지가 포함된 텍스트, **When** 저장하면, **Then** UTF-8 인코딩으로 그대로 보존된다
5. **Given** CLI에서 `--interactive` 모드를 실행하면, **When** 프롬프트가 나타나고, **Then** 제목/본문/댓글을 순차적으로 입력받아 JSON을 생성한다

---

### User Story 2 - 수동 입력 검증 및 에러 처리 (Priority: P1)

잘못된 형식의 입력, 스키마 불일치, 파일 저장 실패 등 다양한 에러 상황에서 명확한 에러 메시지를 출력하고 안전하게 처리한다.

**Why this priority**: 파이프라인의 첫 관문. 잘못된 데이터가 이후 단계로 흘러가면 TTS/영상 생성이 모두 실패한다. (Constitution 원칙 II)

**Independent Test**: 의도적으로 잘못된 JSON을 입력하여 에러 메시지 출력을 확인.

**Acceptance Scenarios**:

1. **Given** JSON 파싱이 불가능한 텍스트, **When** 입력하면, **Then** "유효하지 않은 JSON 형식입니다" 에러 출력
2. **Given** title이 빈 문자열인 경우, **When** 검증하면, **Then** "title은 비어있을 수 없습니다" 에러 출력
3. **Given** body가 10자 미만인 경우, **When** 검증하면, **Then** "본문이 너무 짧습니다 (최소 10자)" 경고 출력
4. **Given** comments 배열 내 항목에 text 필드가 없는 경우, **When** 검증하면, **Then** 해당 댓글의 구조 오류를 명시

---

### User Story 3 - 자동 크롤링으로 블라인드 글 수집 (Priority: P2)

사용자가 블라인드 게시글 URL을 입력하면, 시스템이 Playwright로 해당 페이지를 열어 제목, 본문, 댓글을 자동 추출하여 JSON 파일로 저장한다.

비유하면, 수동 스크랩이 직접 기사를 오리는 것이라면, 자동 크롤링은 스크랩 로봇이 대신 해주는 것이다.

**Why this priority**: 수동 입력(P1)이 먼저 동작해야 파이프라인 개발이 가능. 자동 크롤링은 편의성 향상 기능으로, 수동 입력이 안정화된 후 추가한다.

**Independent Test**: 블라인드 URL 1개로 크롤링 실행 → 생성된 JSON이 수동 입력과 동일한 스키마인지 확인.

**Acceptance Scenarios**:

1. **Given** 유효한 블라인드 게시글 URL, **When** 크롤링을 실행하면, **Then** `data/raw/{id}.json` 파일이 생성되고, 수동 입력과 동일한 BlindPost 스키마를 따른다
2. **Given** 게시글에 댓글이 20개 이상 있을 때, **When** 크롤링하면, **Then** 좋아요 수 기준 상위 10개 댓글만 추출된다
3. **Given** 존재하지 않는 블라인드 URL, **When** 크롤링하면, **Then** 명확한 에러 메시지 출력 + 비정상 종료 코드 반환
4. **Given** 블라인드가 아닌 URL, **When** 크롤링하면, **Then** "블라인드 URL만 지원합니다" 에러 출력

---

### User Story 4 - 크롤링 윤리 준수 (Priority: P2)

자동 크롤링 시 블라인드 서버에 과도한 부하를 주지 않도록, 요청 간 대기 시간을 두고 윤리적으로 크롤링한다.

**Why this priority**: Constitution 원칙 IV (법적 준수). 자동 크롤링(US3)과 함께 구현.

**Independent Test**: 연속 크롤링 시 요청 간격 측정.

**Acceptance Scenarios**:

1. **Given** 여러 URL을 순차 크롤링할 때, **When** 각 요청 간격을 측정하면, **Then** 최소 5초 이상의 간격이 보장된다
2. **Given** 크롤링 실행 시, **When** 브라우저가 열리면, **Then** 일반 사용자와 유사한 User-Agent가 설정된다

---

### Edge Cases

- 본문이 매우 긴 경우 (3000자 이상) → 전체 텍스트를 그대로 저장 (요약은 Analyzer 담당)
- 댓글에 대댓글이 있는 경우 → 대댓글도 추출 (depth 필드로 구분)
- 특수문자, 이모지 포함 → UTF-8 인코딩으로 그대로 보존
- 블라인드 로그인 필요 게시글 → 에러 메시지 ("로그인 필요 게시글은 지원하지 않습니다")
- 삭제/비공개 게시글 → 에러 메시지 + 스킵
- `data/raw/` 디렉토리 미존재 시 → 자동 생성

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템 MUST 수동 입력 모드를 제공한다 (JSON 파일 직접 작성 또는 대화형 입력)
- **FR-002**: 시스템 MUST 자동 크롤링 모드를 제공한다 (Playwright 기반 URL 크롤링)
- **FR-003**: 시스템 MUST 두 모드 모두 동일한 BlindPost 스키마의 JSON을 출력한다
- **FR-004**: 시스템 MUST 입력 데이터를 BlindPost 스키마에 대해 검증한다 (필수 필드, 타입, 최소 길이)
- **FR-005**: 시스템 MUST 댓글을 좋아요 수 기준 내림차순으로 정렬하여 상위 10개만 저장한다
- **FR-006**: 시스템 MUST 결과를 `data/raw/` 디렉토리에 JSON 파일로 저장한다
- **FR-007**: 시스템 MUST 잘못된 입력에 대해 구체적인 에러 메시지를 출력한다
- **FR-008**: 시스템 MUST 자동 크롤링 시 요청 간 최소 5초의 대기 시간을 둔다
- **FR-009**: 시스템 MUST 블라인드 도메인(teamblind.com)이 아닌 URL을 거부한다
- **FR-010**: 시스템 MUST 특수문자와 이모지를 UTF-8 인코딩으로 보존한다
- **FR-011**: 시스템 MUST CLI 대화형 모드(`--interactive`)를 제공하여 제목/본문/댓글을 순차 입력받는다

### Key Entities

- **BlindPost**: 블라인드 게시글 데이터. 핵심 속성: 제목(title), 작성자(author: 직장명 + 닉네임), 본문(body), 댓글 목록(comments), 원본 URL(url, optional), 크롤링/입력 시각(created_at)
- **Comment**: 댓글 데이터. 핵심 속성: 텍스트(text), 좋아요 수(likes), 작성자 정보(author: 직장명 + 닉네임)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 수동 작성 JSON이 스키마 검증을 통과하고 `data/raw/`에 저장된다
- **SC-002**: CLI 대화형 모드에서 제목/본문/댓글을 입력하면 30초 이내에 JSON 파일이 생성된다
- **SC-003**: 생성된 JSON 파일은 BlindPost 스키마와 100% 일치한다 (필수 필드 누락 없음)
- **SC-004**: 잘못된 JSON 3종(파싱 불가, 필수 필드 누락, 타입 불일치)에서 적절한 에러 메시지가 출력된다
- **SC-005**: 자동 크롤링으로 서로 다른 유형의 게시글 3개 이상에서 성공한다
- **SC-006**: 수동 입력과 자동 크롤링의 출력 JSON이 동일한 스키마를 따른다

## Assumptions

- 초기 MVP는 수동 입력만으로 시작하며, 자동 크롤링은 이후 추가한다
- 블라인드 웹사이트(teamblind.com/kr)의 DOM 구조는 자동 크롤링 구현 시점에서 확인 필요
- 크롤링 대상은 공개 게시글만 해당 (로그인 필요 게시글 제외)
- 한국어 블라인드(teamblind.com/kr) 게시글만 지원
