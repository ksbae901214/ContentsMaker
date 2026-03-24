# Tasks: BGM 자동 삽입 + 자막 줄바꿈 최적화 + URL 콘텐츠 소스 확장

**Input**: Design documents from `/specs/004-bgm-subtitle-url/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: 테스트는 각 Phase 완료 후 수동 검증 (quickstart.md 기반). 별도 테스트 코드 생성 안 함.

**Organization**: 3개 User Story를 독립적으로 구현 가능하도록 Phase별 구성.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: BGM 파일 준비 + Playwright 설치

- [x] T001 `data/bgm/` 디렉토리 생성 및 감정별 BGM 4개 파일 배치 (funny.mp3, touching.mp3, angry.mp3, relatable.mp3)
- [x] T002 [P] Playwright 의존성 설치 (`pip install playwright && playwright install chromium`)
- [x] T003 [P] `.gitignore`에 `data/bgm/` 추가 (로열티프리 MP3는 git 추적 제외)

---

## Phase 2: Foundational

**Purpose**: 기존 데이터 모델 확장 (모든 User Story에서 사용)

- [x] T004 Scene 모델에 `highlight_words: tuple[str, ...]` 필드 추가 in `src/analyzer/script_models.py`
- [x] T005 [P] Remotion SceneData 타입에 `highlightWords?: string[]` 추가 in `src/video/remotion/src/types.ts`
- [x] T006 [P] `voice_config.py`에 BGM 파일 매핑 딕셔너리 추가 (`BGM_FILES` — emotion → filename)
- [x] T007 [P] `voice_config.py`에 감정별 하이라이트 색상 딕셔너리 추가 (`HIGHLIGHT_COLORS` — emotion → hex color)

**Checkpoint**: 데이터 모델 확장 완료 — User Story 구현 가능

---

## Phase 3: User Story 1 — BGM 자동 삽입 (Priority: P1) 🎯 MVP

**Goal**: 체크박스로 BGM ON/OFF 선택, 감정별 BGM이 영상에 자동 삽입

**Independent Test**: 웹 UI에서 BGM ON 영상 생성 → MP4에서 TTS+BGM 동시 재생 확인

### Implementation for User Story 1

- [x] T008 [US1] 웹 UI `app/page.tsx`에 "배경음악 넣기" 체크박스 추가 (기본 ON), FormData에 `bgm` 필드 전달
- [x] T009 [US1] `app/api/generate/route.ts`에서 `bgm` 옵션 파싱 → 렌더링 단계에 `use_bgm` 전달
- [x] T010 [US1] `src/video/renderer.py`에서 BGM 파일을 `public/`에 복사 + props에 `bgmFile` 추가
- [x] T011 [US1] `ShortsComposition.tsx`에 bgmFile prop 추가, `<Audio src={staticFile(bgmFile)} volume={0.15} loop />` 렌더링
- [x] T012 [US1] `src/main.py` CLI에 `--no-bgm` 옵션 추가 (image, pipeline 서브커맨드)
- [x] T013 [US1] BGM 파일 누락 시 경고 로그 출력 후 BGM 없이 진행하는 폴백 로직 in `renderer.py`

**Checkpoint**: BGM ON/OFF 영상 모두 생성 가능. TTS가 묻히지 않는 볼륨 확인.

---

## Phase 4: User Story 2 — 자막 줄바꿈 최적화 (Priority: P1)

**Goal**: 씬 텍스트가 문맥 단위 줄바꿈 + 감정별 키워드 하이라이트

**Independent Test**: 생성된 script.json의 text에 `\n` 포함 확인, 영상에서 키워드 색상 구분 확인

### Implementation for User Story 2

- [x] T014 [US2] `src/analyzer/prompt_template.py` 수정 — 줄바꿈 규칙 추가 (1줄 15자, 문맥 단위, `\n` 삽입) + `highlight_words` 배열 생성 지시
- [x] T015 [US2] `src/analyzer/prompt_template.py` JSON 출력 형식에 `highlight_words` 필드 추가
- [x] T016 [US2] `src/analyzer/claude_analyzer.py`에서 `highlight_words` 파싱 + Scene 객체에 전달
- [x] T017 [US2] `src/video/renderer.py`의 `_convert_to_camel_case`가 `highlight_words` → `highlightWords` 변환 확인
- [x] T018 [US2] `SceneText.tsx` 수정 — text에서 `highlightWords` 매칭 단어를 감정별 색상 `<span>`으로 렌더링
- [x] T019 [US2] 줄바꿈 폴백: AI가 줄바꿈 누락 시 Python 후처리로 15자 단위 강제 줄바꿈 in `src/analyzer/claude_analyzer.py`

**Checkpoint**: 모든 씬 텍스트 1줄 15자 내외 줄바꿈, 키워드 색상 구분 확인.

---

## Phase 5: User Story 3 — URL 입력으로 콘텐츠 생성 (Priority: P2)

**Goal**: 디시인사이드/네이트판/네이버카페 URL → 자동 추출 → 영상 생성

**Independent Test**: 디시인사이드 URL 입력 → 제목/본문/댓글 추출 → 영상 생성 성공

### Implementation for User Story 3

- [ ] T020 [P] [US3] `src/scraper/parsers/__init__.py` 생성 + 사이트 감지 라우터 함수 (`detect_site(url) → parser`)
- [ ] T021 [P] [US3] `src/scraper/parsers/dcinside.py` — Playwright로 디시인사이드 게시글 파싱 (제목/본문/댓글)
- [ ] T022 [P] [US3] `src/scraper/parsers/natepann.py` — Playwright로 네이트판 게시글 파싱
- [ ] T023 [P] [US3] `src/scraper/parsers/naver_cafe.py` — Playwright로 네이버카페 게시글 파싱 (iframe 접근)
- [ ] T024 [US3] `src/scraper/url_scraper.py` — URL 입력 → 사이트 감지 → 파서 호출 → BlindPost 반환 허브 모듈
- [ ] T025 [US3] `src/main.py`에 `url` 서브커맨드 추가 (`python3 -m src.main url <URL>`)
- [ ] T026 [US3] `app/page.tsx`에 "URL 입력" 탭 추가 (URL 입력 필드 + 생성 버튼)
- [ ] T027 [US3] `app/api/generate/route.ts`에 URL 모드 추가 (url → url_scraper.py → 기존 파이프라인)
- [ ] T028 [US3] 에러 처리: 미지원 사이트, 접근 불가, 로그인 필요, 텍스트 부족 시 명확한 에러 메시지

**Checkpoint**: 3개 사이트 URL로 각 1개 영상 생성 성공.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 통합 테스트 + 문서 업데이트

- [ ] T029 quickstart.md 검증 실행 — BGM ON/OFF, 줄바꿈, 3개 사이트 URL 테스트
- [ ] T030 [P] README.md 업데이트 — BGM, 줄바꿈, URL 기능 문서 추가
- [ ] T031 [P] prompt_plan.md 업데이트 — Phase 4-6 완료 상태 반영
- [ ] T032 커밋 & 푸시 & PR 업데이트

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 후 시작. 모든 User Story를 블록.
- **US1 BGM (Phase 3)**: Foundational 완료 후. 독립 구현 가능.
- **US2 자막 (Phase 4)**: Foundational 완료 후. 독립 구현 가능.
- **US3 URL (Phase 5)**: Foundational 완료 후. 독립 구현 가능.
- **Polish (Phase 6)**: 원하는 User Story 완료 후.

### User Story Dependencies

- **US1 (BGM)**: Foundational만 의존. US2/US3와 독립.
- **US2 (자막)**: Foundational만 의존. US1/US3와 독립.
- **US3 (URL)**: Foundational만 의존. US1/US2와 독립.

### Parallel Opportunities

- T002, T003: Setup 내 병렬 가능
- T005, T006, T007: Foundational 내 병렬 가능
- T020, T021, T022, T023: US3 파서 3개 + 라우터 병렬 가능
- **US1, US2, US3 전체가 Foundational 후 병렬 가능**

---

## Parallel Example: User Story 3 (URL 파서)

```bash
# 3개 사이트 파서를 동시에 개발 (서로 독립 파일):
Task: "src/scraper/parsers/dcinside.py"
Task: "src/scraper/parsers/natepann.py"
Task: "src/scraper/parsers/naver_cafe.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 — BGM)

1. Phase 1: Setup (BGM 파일 배치)
2. Phase 2: Foundational (모델 확장)
3. Phase 3: US1 BGM 구현
4. **STOP**: BGM ON/OFF 영상 테스트
5. 바로 사용 가능!

### Incremental Delivery

1. Setup + Foundational → 기반 준비
2. US1 BGM → 영상 품질 즉시 향상 (MVP)
3. US2 자막 줄바꿈 → 가독성 향상
4. US3 URL → 콘텐츠 소싱 효율화
5. Polish → 문서 + 통합 테스트

---

## Notes

- [P] 태스크 = 다른 파일, 의존성 없음 → 병렬 가능
- BGM 파일은 수동 다운로드 (Pixabay Music)
- 네이버 카페는 공개 게시글만 지원
- 줄바꿈은 AI 우선, 실패 시 Python 후처리 폴백
