# Tasks: Foundation - Project Init + Blind Scraper

**Input**: Design documents from `/specs/001-foundation-scraper/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: 포함 (Constitution 원칙 VII 증거 기반 완료)

**Organization**: 수동 입력(P1)을 먼저 완성하여 MVP로 동작시킨 뒤, 자동 크롤링(P2)을 추가한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 초기화, 디렉토리 구조 생성, 의존성 설정

- [x] T001 프로젝트 디렉토리 구조 생성 (src/scraper/, src/config/, data/raw/, tests/samples/)
- [x] T002 Python 환경 설정: requirements.txt 작성 (pytest, playwright는 P2 전용)
- [x] T003 [P] .gitignore 작성 (data/raw/*.json, .env, __pycache__, .pytest_cache)
- [x] T004 [P] src/config/settings.py 작성: 경로 상수 (DATA_RAW_DIR, MAX_COMMENTS 등)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story가 공유하는 데이터 모델과 검증 로직

**⚠️ CRITICAL**: US1, US2, US3, US4 모두 이 Phase에 의존

- [x] T005 BlindPost, Comment 데이터 클래스 정의 in `src/scraper/models.py`
- [x] T006 BlindPost → dict, dict → BlindPost 직렬화/역직렬화 함수 in `src/scraper/models.py`
- [x] T007 JSON 스키마 검증기 구현 in `src/scraper/validator.py` (필수 필드, 타입, 최소 길이 체크)
- [x] T008 [P] 테스트용 샘플 JSON 작성 in `tests/samples/` (valid_post.json, valid_no_comments.json, invalid_missing_title.json, invalid_bad_json.txt)
- [x] T009 [P] 데이터 모델 테스트 in `tests/test_models.py` (직렬화, 역직렬화, frozen 불변성)
- [x] T010 검증기 테스트 in `tests/test_validator.py` (유효/무효 JSON, 에러 메시지)

**Checkpoint**: `python -m pytest tests/test_models.py tests/test_validator.py` — 모든 테스트 통과

---

## Phase 3: User Story 1 + 2 — 수동 입력 + 검증 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 JSON 파일을 직접 작성하거나 대화형으로 입력하면, 검증 후 `data/raw/`에 저장

**Independent Test**: `python src/main.py manual --file tests/samples/valid_post.json` → `data/raw/` 에 저장 확인

### Implementation

- [x] T011 [US1] 수동 입력 모듈 구현 in `src/scraper/manual_input.py` — JSON 파일 읽기 + validator 호출 + 저장
- [x] T012 [US1] 대화형 입력 모드 구현 in `src/scraper/manual_input.py` — stdin으로 제목/본문/댓글 순차 입력 → BlindPost 생성
- [x] T013 [US1][US2] CLI 진입점 구현 in `src/main.py` — argparse로 `manual --file` / `manual --interactive` 서브커맨드
- [x] T014 [US2] 에러 처리 강화 in `src/scraper/manual_input.py` — JSON 파싱 실패, 필수 필드 누락, 타입 불일치 시 구체적 에러 메시지
- [x] T015 [US1] 수동 입력 테스트 in `tests/test_manual_input.py` — 유효 JSON → 저장 성공, 무효 JSON → 에러 메시지
- [x] T016 [US2] 에러 처리 테스트 in `tests/test_manual_input.py` — 파싱 불가, 빈 title, 짧은 body, 잘못된 comments 구조

**Checkpoint**: 아래 명령어 모두 성공
```bash
# 유효 JSON → 저장 성공
python src/main.py manual --file tests/samples/valid_post.json

# 무효 JSON → 에러 메시지 출력
python src/main.py manual --file tests/samples/invalid_missing_title.json

# 대화형 모드 → JSON 생성
python src/main.py manual --interactive

# 전체 테스트
python -m pytest tests/ -v
```

---

## Phase 4: User Story 3 + 4 — 자동 크롤링 + 윤리 준수 (Priority: P2)

**Goal**: 블라인드 URL을 입력하면 Playwright로 자동 크롤링하여 동일한 BlindPost JSON으로 저장

**Independent Test**: `python src/main.py crawl --url <BLIND_URL>` → `data/raw/` 에 JSON 저장 확인

### Implementation

- [ ] T017 [US3] Playwright 의존성 추가: requirements.txt에 `playwright` 추가 + `playwright install chromium`
- [ ] T018 [US3] 자동 크롤러 구현 in `src/scraper/auto_crawler.py` — URL 검증 → Playwright 실행 → DOM 파싱 → BlindPost 생성 → validator → 저장
- [ ] T019 [US3] URL 검증 함수 in `src/scraper/auto_crawler.py` — teamblind.com 도메인 체크, 형식 검증
- [ ] T020 [US3] 댓글 추출 + 좋아요순 정렬 in `src/scraper/auto_crawler.py` — 상위 10개만
- [ ] T021 [US4] Rate limiting 구현 in `src/scraper/auto_crawler.py` — 연속 크롤링 시 5초 대기, User-Agent 설정
- [ ] T022 [US3] CLI에 crawl 서브커맨드 추가 in `src/main.py` — `crawl --url` / `crawl --urls-file`
- [ ] T023 [US3] 크롤링 에러 처리 — 페이지 미발견, 네트워크 오류, 타임아웃, 비공개 글
- [ ] T024 [US3] 크롤러 테스트 in `tests/test_auto_crawler.py` — URL 검증, 에러 처리 (실제 크롤링은 수동 검증)

**Checkpoint**: 아래 명령어 모두 성공
```bash
# 실제 블라인드 URL로 크롤링
python src/main.py crawl --url "https://www.teamblind.com/kr/post/..."

# 잘못된 URL → 에러
python src/main.py crawl --url "https://google.com"

# 수동 입력과 자동 크롤링 출력 스키마 비교
python -m pytest tests/ -v
```

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: 전체 품질 향상

- [ ] T025 [P] 로깅 추가 in `src/scraper/` — 각 모듈에 logging 적용 (print 대신)
- [ ] T026 [P] `data/raw/` 자동 생성 in `src/config/settings.py` — 디렉토리 미존재 시 자동 생성
- [ ] T027 전체 테스트 실행 + 커버리지 확인: `python -m pytest tests/ -v --tb=short`
- [ ] T028 샘플 데이터 5개 생성: 다양한 유형의 블라인드 글 (긴 본문, 이모지, 대댓글, 댓글 없음, 일반)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1+2, P1 MVP)
                                          → Phase 4 (US3+4, P2 크롤링)
                                          → Phase 5 (Polish)
```

### User Story Dependencies

- **US1 (수동 입력)**: Phase 2 완료 후 즉시 시작 가능 — **MVP 핵심**
- **US2 (에러 처리)**: US1과 동시 구현 (같은 모듈)
- **US3 (자동 크롤링)**: Phase 2 완료 후 시작 가능 — US1과 독립
- **US4 (크롤링 윤리)**: US3와 동시 구현 (같은 모듈)

### Parallel Opportunities

```bash
# Phase 1: 병렬 실행 가능
T003 (.gitignore) || T004 (settings.py)

# Phase 2: 병렬 실행 가능
T008 (샘플 JSON) || T009 (모델 테스트)

# Phase 3-4: US1+2와 US3+4는 독립적이므로 병렬 가능 (별도 파일)
Phase 3 (manual_input.py) || Phase 4 (auto_crawler.py)
```

---

## Implementation Strategy

### MVP First (Phase 1 → 2 → 3)

1. Phase 1: 프로젝트 구조 + 설정
2. Phase 2: 데이터 모델 + 검증기 + 테스트
3. Phase 3: 수동 입력 + CLI
4. **STOP and VALIDATE**: `python src/main.py manual --file` 성공 확인
5. **이후 파이프라인 개발 시작 가능** (Analyzer, TTS, Video)

### P2 추가 (Phase 4)

6. Phase 4: 자동 크롤링 추가
7. **VALIDATE**: 수동 입력과 자동 크롤링 출력 스키마 동일 확인

---

## Summary

| Phase | 태스크 수 | 핵심 산출물 |
|-------|----------|------------|
| Phase 1 Setup | 4개 | 디렉토리, 설정 |
| Phase 2 Foundation | 6개 | models.py, validator.py, 테스트 |
| Phase 3 US1+2 (P1) | 6개 | manual_input.py, main.py, CLI |
| Phase 4 US3+4 (P2) | 8개 | auto_crawler.py, Playwright |
| Phase 5 Polish | 4개 | 로깅, 커버리지 |
| **Total** | **28개** | |

**Suggested MVP scope**: Phase 1 + 2 + 3 = **16개 태스크** → 수동 입력으로 JSON 생성 가능
