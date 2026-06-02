---
description: "Task list for 007-dem-shorts-studio implementation"
---

# Tasks: 민주당 친화형 정치 쇼츠 반자동 제작 시스템

**Input**: Design documents from `/specs/007-dem-shorts-studio/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/*

**Tests**: **포함됨** — 프로젝트 Constitution 원칙 VII(Evidence-Based)·VIII(Full Test Gate)로 필수.

**Organization**: 5개 사용자 스토리(P1×3 / P2 / P3)별로 그룹화하여 독립 구현·테스트·배포 가능.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 서로 다른 파일·독립 의존 → 병렬 실행 가능
- **[Story]**: US1/US2/US3/US4/US5 (해당 없으면 SETUP/FOUND/POLISH)
- 파일 경로 모두 절대 루트 기준 (`src/dem_shorts/...`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 디렉토리·의존성·환경 설정 (원칙 I: $0 스택).

- [X] **T001** `src/dem_shorts/` 디렉토리 생성 + `__init__.py` 추가 (plan.md 프로젝트 구조대로)
- [X] **T002** `src/dem_shorts/editor/` 및 `src/dem_shorts/compliance/` 하위 패키지 + `__init__.py`
- [X] **T003** `app/dem-shorts/` 및 `app/api/dem-shorts/` Next.js 라우트 디렉토리 생성
- [X] **T004** `tests/dem_shorts/` 테스트 디렉토리 + `__init__.py` 생성
- [X] **T005** [P] `requirements-dem-shorts.txt` 생성: `openai-whisper`, `pyannote.audio>=3.1`, `google-api-python-client`, `pytrends`, `tesseract` (한국어), `opencv-python`
- [X] **T006** [P] `.env.example`에 `YOUTUBE_API_KEY`, `YOUTUBE_OAUTH_CLIENT`, `HUGGINGFACE_TOKEN`, `NATV_CHANNEL_HANDLE`, `DEM_SHORTS_ARCHIVE_DIR` 추가
- [X] **T007** [P] `data/dem_shorts/` 디렉토리 구조 생성: `{raw,transcripts,segments,drafts,outputs,bgm,archive,logs/batch}`
- [X] **T008** [P] `CLAUDE.md`에 007 기능 섹션 추가 (이미 업데이트됨 — 검증만)

**Checkpoint**: 구조 준비 완료, 다음 단계 이동 가능.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 스토리가 의존하는 모델·DB·공용 유틸. **이 단계 완료 전에는 어떤 US도 시작 불가**.

### Data Models (병렬 가능, 각 파일 독립)

- [X] **T009** [P] [FOUND] `src/dem_shorts/models/source_video.py` — `SourceVideo` frozen dataclass + `to_dict()`/`from_dict()` (data-model.md §1)
- [X] **T010** [P] [FOUND] `src/dem_shorts/models/politician.py` — `Politician` frozen dataclass + `tier`/`category` enum 검증 (§2)
- [X] **T011** [P] [FOUND] `src/dem_shorts/models/speech_segment.py` — `SpeechSegment` + 추천점수 공식 구현 (§3, FR-016)
- [X] **T012** [P] [FOUND] `src/dem_shorts/models/shorts_draft.py` — `ShortsDraft` + cut_duration≤60 검증 (§4)
- [X] **T013** [P] [FOUND] `src/dem_shorts/models/gate_result.py` — `ComplianceGateResult` (§5, FR-025)
- [X] **T014** [P] [FOUND] `src/dem_shorts/models/weekly_ranking.py` — `WeeklyRanking` (§6)
- [X] **T015** [P] [FOUND] `src/dem_shorts/models/uploaded_shorts.py` — `UploadedShorts` (§7)
- [X] **T016** [P] [FOUND] `src/dem_shorts/models/bias_report.py` — `BiasReport` (§8)
- [X] **T017** [P] [FOUND] `src/dem_shorts/models/__init__.py` — 8개 모델 re-export

### Data Model Tests (병렬)

- [X] **T018** [P] [FOUND] `tests/dem_shorts/test_models.py` — 8개 dataclass serialization + 검증 룰 테스트 (frozen, enum, cut_duration, char_count)

### Database Layer

- [X] **T019** [FOUND] `src/dem_shorts/db/migrations/001_init.sql` — data-model.md의 SQLite 스키마 전체 작성 (9개 테이블)
- [X] **T020** [FOUND] `src/dem_shorts/db.py` — `connect()`, `migrate()`, `seed_pinned_politicians()`(이재명·조국·정청래), `upsert_*`/`query_*` 래퍼 (T019 의존)
- [X] **T021** [FOUND] `tests/dem_shorts/test_db.py` — 마이그레이션 실행 + seed 검증 + CRUD 왕복 테스트 (T020 의존)

### Shared Utilities

- [X] **T022** [P] [FOUND] `src/dem_shorts/utils/logger.py` — 배치/파이프라인 JSON Lines 로그 포맷 (batch-jobs.md 모니터링 섹션)
- [X] **T023** [P] [FOUND] `src/dem_shorts/utils/paths.py` — `data/dem_shorts/*` 경로 헬퍼 (archive/transcripts/drafts/outputs 등)
- [X] **T024** [P] [FOUND] `src/dem_shorts/config.py` — `.env` 로딩 + 상수 집중화 (NATV_CHANNEL_ID, POLL_INTERVAL_MIN=30, CUT_MAX_SEC=60 등) — 원칙 VI 설정 중앙화
- [X] **T025** [FOUND] `src/dem_shorts/cli.py` — argparse 스켈레톤 + 서브커맨드 등록 (각 서브커맨드 본체는 후속 태스크에서 구현)

**Checkpoint**: 기반 준비 완료. US1/US2/US3은 이제 병렬 착수 가능. 단, US3는 US1·US2 산출물을 소비하므로 실제 End-to-End 검증은 US1·US2 완료 후.

---

## Phase 3: User Story 1 — NATV 신규 영상 민주당 우선순위 대시보드 (Priority: P1) 🎯 MVP

**Goal**: 운영자가 대시보드 진입 시 최근 24시간 NATV 영상이 민주당 점유도 순으로 표시.
**Independent Test**: 샘플 영상 3개 투입 → 점수 계산 → 대시보드 UI 렌더링 확인.

### Tests (TDD: RED 먼저)

- [X] **T026** [P] [US1] `tests/dem_shorts/test_source_collector.py` — `poll_natv()` mock (YouTube API 응답 샘플), 신규 감지/기존 스킵/쿼터 초과/6시간 초과 제외 시나리오
- [X] **T027** [P] [US1] `tests/dem_shorts/test_dem_scoring.py` — 점유도 공식 검증 (민주당 3명 감지 = 30점, +Whitelist 상위 20점, +이재명 15점, 6h 초과 -10점 등)
- [X] **T028** [P] [US1] `tests/dem_shorts/test_api_videos.py` — `GET /api/dem-shorts/videos` 정렬/필터/since_hours 계약 (contracts/rest-api.md §GET videos)

### Source Collection Implementation

- [X] **T029** [P] [US1] `src/dem_shorts/youtube_client.py` — YouTube Data API v3 래퍼 (channels.list, search.list, 쿼터 추적)
- [X] **T030** [P] [US1] `src/dem_shorts/source_collector.py::parse_session_type()` — 제목·설명에서 본회의/상임위/국감/청문회/기자회견/기타 분류 (FR-003)
- [X] **T031** [US1] `src/dem_shorts/source_collector.py::poll_natv()` — 신규 영상 감지 + SourceVideo upsert + 6시간 초과 제외 (FR-001/002, T029·T030 의존)
- [X] **T032** [US1] `src/dem_shorts/source_collector.py::download_video()` — yt-dlp로 `archive/{video_id}.mp4` 저장, 3회 재시도 백오프 (FR-002)
- [X] **T033** [US1] `src/dem_shorts/scoring.py::calculate_dem_score()` — research.md R-05 공식 구현 (FR-004)
- [X] **T034** [US1] `src/dem_shorts/source_collector.py::update_exclusion()` — dem_score=0 → excluded (FR-005)

### CLI

- [X] **T035** [US1] `cli.py` 서브커맨드 추가: `poll-natv`, `download`, `score` (contracts/cli-commands.md)

### API Routes (Next.js)

- [X] **T036** [P] [US1] `app/api/dem-shorts/videos/route.ts` — `GET` 파라미터(since_hours, min_score, include_excluded) + 정렬
- [X] **T037** [P] [US1] `app/api/dem-shorts/videos/[id]/route.ts` — `GET` 단일 영상 + segments join (segments 채우기는 US2에서)

### UI

- [X] **T038** [P] [US1] `app/dem-shorts/page.tsx` — 대시보드: 신규 영상 카드 그리드 + dem_score 뱃지 + 자동 제외 토글
- [X] **T039** [US1] `app/dem-shorts/components/VideoCard.tsx` — 썸네일/제목/게시일/세션타입/점수 카드 (T038에서 사용)

### Batch Setup

- [X] **T040** [US1] `docs/dem-shorts/cron.md` — B-01 NATV 폴링 배치 등록 안내 (`*/30 * * * *`)

**Checkpoint (MVP 1/3)**: 샘플 영상 투입 → 대시보드 표시까지 엔드투엔드 통과. US1 단독 데모 가능.

---

## Phase 4: User Story 2 — Whitelist 정치인 발언 구간 자동 하이라이트 (Priority: P1)

**Goal**: 영상 클릭 시 Whitelist 인물 발언 구간이 색상별로 타임라인에 표시, 추천 점수 순 정렬.
**Independent Test**: 2시간 샘플 영상 + Whitelist 3명 → 발언 구간 색상 하이라이트 + confidence/추천점수 확인.

### Tests (RED 먼저)

- [X] **T041** [P] [US2] `tests/dem_shorts/test_stt.py` — Whisper 래퍼 mock, 한국어 전사 결과 JSON 스키마 검증
- [X] **T042** [P] [US2] `tests/dem_shorts/test_diarization.py` — pyannote mock, 세그먼트 병합/분리 룰
- [X] **T043** [P] [US2] `tests/dem_shorts/test_speaker_id.py` — 호명 패턴 정규식 정확도 + confidence ≥0.7 필터 (FR-014)
- [X] **T044** [P] [US2] `tests/dem_shorts/test_recommendation_score.py` — 추천 점수 공식 (단독 발언, 이슈 키워드, 욕설 감점)

### STT + Diarization

- [X] **T045** [P] [US2] `src/dem_shorts/stt.py` — openai-whisper large-v3 래퍼, `data/dem_shorts/transcripts/{video_id}.json` 출력 (FR-012, R-02)
- [X] **T046** [P] [US2] `src/dem_shorts/diarization.py` — pyannote.audio 3.1 래퍼, `segments/{video_id}.json` 출력 (FR-013, R-03)
- [X] **T047** [US2] `src/dem_shorts/speaker_id/name_patterns.py` — `(?:[가-힣]{2,4})\s*(?:의원|대표|장관|위원장)` 정규식 + Whitelist 매칭 (FR-013)
- [X] **T048** [US2] `src/dem_shorts/speaker_id/identify.py` — diarization 클러스터 + 호명 패턴 결합, confidence 산출 → `speech_segments` 테이블 upsert (T046·T047 의존)

### Recommendation Scoring

- [X] **T049** [US2] `src/dem_shorts/scoring.py::calculate_recommendation_score()` — FR-016 공식: 발언 길이 적정성 + 감정 강도 + 이슈 키워드 + 단독 가중치 - 욕설 감점
- [X] **T050** [US2] `src/dem_shorts/scoring.py::detect_issue_keywords()` — 이슈 키워드 사전 기반 매칭
- [X] **T051** [US2] `src/dem_shorts/scoring.py::detect_profanity()` — 욕설 감지 (compliance keyword_dict 일부 재사용)

### CLI

- [X] **T052** [US2] `cli.py`에 `stt`, `diarize`, `identify`, `pipeline` 서브커맨드 추가

### API + UI

- [X] **T053** [US2] `app/api/dem-shorts/videos/[id]/route.ts` — segments 포함 응답 확장 (T037에서 이미 포함)
- [X] **T054** [P] [US2] `app/dem-shorts/[videoId]/page.tsx` — 타임라인 편집기: 비디오 플레이어 + 구간 하이라이트 오버레이
- [X] **T055** [P] [US2] `app/dem-shorts/components/TimelineTrack.tsx` — 인물별 색상 트랙, confidence 표시, (미식별) 처리 (FR-014, FR-015)
- [X] **T056** [P] [US2] `app/dem-shorts/components/SegmentCard.tsx` — 세그먼트 카드 + 추천 점수 + 자르기 버튼

**Checkpoint (MVP 2/3)**: US2 단독 테스트 가능. US1 + US2 결합 시 "영상 선택 → 발언자 하이라이트" 플로우 동작.

---

## Phase 5: User Story 3 — 해설 + TTS + 컴플라이언스 게이트 + 렌더 + 업로드 (Priority: P1)

**Goal**: 자른 구간에 해설 자막·TTS·BGM 얹고 **10개 우회 불가 게이트** 통과 후 YouTube 업로드.
**Independent Test**: 테스트 draft → 해설 50자 → 게이트 자동 8개 통과 → 수동 2개 체크 → 렌더 → 업로드까지 검증.

### Whitelist Management (게이트가 의존)

- [X] **T057** [P] [US3] `tests/dem_shorts/test_whitelist_api.py` — POST/PATCH/DELETE + tier=auto 직접 등록 거부
- [X] **T058** [P] [US3] `app/api/dem-shorts/whitelist/route.ts` — `GET/POST` (FR-007)
- [X] **T059** [P] [US3] `app/api/dem-shorts/whitelist/[id]/route.ts` — `PATCH/DELETE`
- [X] **T060** [P] [US3] `app/dem-shorts/whitelist/page.tsx` — CRUD UI + 등급/카테고리 편집 + 연합 토글 (FR-011)

### Editor: Segment Cut + Commentary Generation

- [X] **T061** [P] [US3] `tests/dem_shorts/test_segment_cutter.py` — cut_duration ≤60 검증, 9:16 포맷 변환 (FR-018)
- [X] **T062** [P] [US3] `tests/dem_shorts/test_commentary_gen.py` — Claude CLI mock, 3개 후보 JSON 파싱, 15자 이내 필터
- [X] **T063** [P] [US3] `src/dem_shorts/editor/segment_cutter.py` — ffmpeg로 구간 자르기 + 9:16 크롭/패딩 (FR-017, FR-018)
- [X] **T064** [P] [US3] `src/dem_shorts/editor/commentary_gen.py` — Claude CLI 호출 (`analyzer/claude_analyzer._call_claude` 재사용), 3개 후보 생성 (FR-020, R-09)
- [X] **T065** [P] [US3] `src/dem_shorts/editor/commentary_prompt.py` — 프롬프트 템플릿 (톤앤매너 주입, 팩트 기반, 15자 이내 강제)

### Subtitle Presets + TTS

- [X] **T066** [P] [US3] `src/dem_shorts/editor/subtitle_presets.py` — 5종 프리셋 정의 (leejaemyung/jungcheongrae/youth/hotissue/default) (FR-021)
- [X] **T067** [P] [US3] `src/video/remotion/src/DemShortsComposition.tsx` — 신규 Remotion composition (기존 BlindShorts 미변경) + preset prop (R-14)
- [X] **T068** [P] [US3] `src/video/remotion/src/components/SubtitleBlock.tsx` — 프리셋별 스타일 렌더
- [X] **T069** [P] [US3] `src/dem_shorts/editor/tts_integration.py` — edge-tts 4 보이스 프리셋 매핑 (male_strong/male_stable/female_calm/female_young), 기존 `src/tts/` 재사용 (FR-022, FR-023)

### BGM Management

- [X] **T070** [P] [US3] `src/dem_shorts/editor/bgm_manifest.py` — `bgm_manifest.json` 로드/검증 + `bgm-register` CLI (R-11, FR-035)
- [X] **T071** [P] [US3] `tests/dem_shorts/test_bgm_manifest.py` — 미등록 파일 거부 검증

### Guardrail Engine (편향·혐오·명예훼손 검출)

- [X] **T072** [P] [US3] `src/dem_shorts/compliance/keyword_dict.py` — 혐오/명예훼손/단정 키워드 사전 (정적 파일)
- [X] **T073** [P] [US3] `src/dem_shorts/compliance/guardrail_keyword.py` — 계층1 룰 기반 스캐너, 카테고리별 가중치 (FR-019, FR-027, R-09)
- [X] **T074** [P] [US3] `src/dem_shorts/compliance/guardrail_llm.py` — 계층2 Claude CLI 분류 (4카테고리 0~100점 JSON)
- [X] **T075** [US3] `src/dem_shorts/compliance/guardrail.py` — 계층1+2 통합, 최종 리스크 스코어 산출 (FR-026, T073·T074 의존)
- [X] **T076** [P] [US3] `tests/dem_shorts/test_guardrail.py` — 키워드·LLM 응답 mock, 카테고리별 점수, 임계값(30/60) 분류

### Election Guard (FR-030~032는 US4이지만 게이트가 선거 가드를 호출하므로 Stub 먼저)

- [X] **T077** [US3] `src/dem_shorts/compliance/election_guard.py::is_in_election_period()` Stub — 기본 False 반환 (US4에서 실제 구현)

### 10-Item Compliance Gate (⭐ CRITICAL: 우회 불가)

- [X] **T078** [P] [US3] `tests/dem_shorts/test_gate.py` — **우회 불가 검증 3가지 시나리오**: (1) 프론트엔드 건너뛰기 파라미터 (2) API 직접 호출 우회 (3) DB 수동 조작 — 모두 거부되는지 확인 (SC-005)
- [X] **T079** [US3] `src/dem_shorts/compliance/gate.py::GateChecker` — 10개 아이템 개별 검사 함수들 (item_1~item_10, FR-025)
- [X] **T080** [US3] `src/dem_shorts/compliance/gate.py::validate()` — 모든 항목 통과 AND 수동 서명 2개 NOT NULL iff `pass` (T079·T075·T077 의존)
- [X] **T081** [US3] `app/api/dem-shorts/drafts/[id]/gate/route.ts` — `POST` 게이트 실행 + 결과 저장 (contracts/rest-api.md §POST gate)

### Render Pipeline

- [X] **T082** [P] [US3] `tests/dem_shorts/test_renderer.py` — 게이트 미통과 draft 거부, 스마트 캐싱 검증
- [X] **T083** [US3] `src/dem_shorts/renderer.py` — Remotion `DemShortsComposition` 호출 + FFmpeg 자막/오디오 믹싱 + 스마트 캐싱 (FR-033, FR-034, R-14)
- [X] **T084** [US3] `app/api/dem-shorts/drafts/[id]/render/route.ts` — SSE 스트림 + 게이트 통과 재확인 (403 if not passed)

### YouTube Uploader

- [X] **T085** [P] [US3] `tests/dem_shorts/test_uploader.py` — 설명란 "NATV 국회방송" 누락 시 거부, 팩트 링크 <2개 거부, `operator_confirmed=false` 거부
- [X] **T086** [US3] `src/dem_shorts/uploader.py` — YouTube Data API v3 resumable upload + OAuth 토큰 관리 (R-13, FR-036)
- [X] **T087** [US3] `app/api/dem-shorts/drafts/[id]/upload/route.ts` — 운영자 확정 필수 + 게이트 재확인 (FR-037)

### Drafts CRUD + Commentary API

- [X] **T088** [P] [US3] `app/api/dem-shorts/drafts/route.ts` — `POST` draft 생성
- [X] **T089** [P] [US3] `app/api/dem-shorts/drafts/[id]/route.ts` — `PATCH` commentary_blocks·tts·bgm·fact_urls 업데이트
- [X] **T090** [P] [US3] `app/api/dem-shorts/drafts/[id]/commentary/route.ts` — `POST` AI 후보 3개 생성

### Editor UI + Gate UI

- [X] **T091** [US3] `app/dem-shorts/[videoId]/render/page.tsx` — 해설 자막 작성 + 실시간 글자 수 경고 + 팩트 URL 입력 + 게이트 실행 (FR-024, FR-029)
- [X] **T092** [P] [US3] `app/dem-shorts/components/CommentaryEditor.tsx` — 타임라인 기반 자막 블록 편집 (FR-019)
- [X] **T093** [P] [US3] `app/dem-shorts/components/GateChecklist.tsx` — 10개 항목 체크리스트 UI, 차단 항목 빨간색, 수동 2개 체크박스 (⚠️ 어떤 UI 조작으로도 미통과 항목이 있으면 "렌더링"/"업로드" 버튼 비활성 유지)
- [X] **T094** [P] [US3] `app/dem-shorts/components/UploadDialog.tsx` — 최종 확정 다이얼로그 (제목/설명/예약 확인)

### CLI Subcommands

- [X] **T095** [US3] `cli.py`에 `draft-create`, `commentary`, `gate`, `render`, `upload` 서브커맨드 추가

**Checkpoint (MVP 3/3 = 전체 MVP)**: US1+US2+US3 결합 시 **대시보드 → 구간 선택 → 해설 → 게이트 → 렌더 → 업로드** 전체 30분 이내 완료 가능 (SC-001).

**⚠️ MVP Gate**: T078 우회 시도 테스트 3가지 모두 통과 확인 **필수** (SC-005). 통과 못하면 MVP 릴리스 불가.

---

## Phase 6: User Story 4 — 선거기간 자동 감지 + 중립 모드 (Priority: P2)

**Goal**: D-180/D-120 경계 감지 시 경고 배너 + 편향 게이트 임계값 하향 + 해설 프롬프트 중립 전환.
**Independent Test**: 시스템 시각 조작 → 배너 + 임계값 자동 변경 확인.

### Tests

- [X] **T096** [P] [US4] `tests/dem_shorts/test_election_guard.py` — D-181/D-179 경계 전환, 대선 D-180·총선 D-120 구분, 배너 플래그 생성

### Implementation

- [X] **T097** [P] [US4] `src/dem_shorts/compliance/election_dates.py` — 선거 일정 하드코딩 테이블 (R-10)
- [X] **T098** [US4] `src/dem_shorts/compliance/election_guard.py` — T077 Stub을 실제 구현으로 교체 (FR-030, FR-031)
- [X] **T099** [P] [US4] `src/dem_shorts/editor/commentary_prompt.py` — 중립 모드 프롬프트 분기 ("정책 설명 중심, 후보 우호 표현 금지") (FR-032)
- [X] **T100** [P] [US4] `app/api/dem-shorts/election/route.ts` — `GET` 현재 선거 상태 + D-day
- [X] **T101** [P] [US4] `app/dem-shorts/components/ElectionBanner.tsx` — 대시보드 상단 배너, 활성 시 모든 페이지 노출
- [X] **T102** [US4] `cli.py::election-check` 서브커맨드 + B-07 배치 cron 등록 안내 (contracts/batch-jobs.md)

**Checkpoint**: US4 단독 테스트 가능. 선거기간 중 US3 게이트가 자동으로 엄격해짐.

---

## Phase 7: User Story 5 — 월간 편향 밸런스 리포트 + 주간 랭킹 (Priority: P3)

**Goal**: 매월 1일 인물별·정당별 비율 + 템플릿 분포 리포트 자동 생성. 매주 일요일 여성·청년 랭킹 갱신.
**Independent Test**: 지난달 30개 쇼츠 시뮬레이션 → 리포트에 30% 초과 경고 포함 확인.

### Tests

- [X] **T103** [P] [US5] `tests/dem_shorts/test_ranking_batch.py` — 5개 데이터 소스 mock, 점수 가중 합산, 상위 20 auto 등록, 2주 연속 대기 시 삭제
- [X] **T104** [P] [US5] `tests/dem_shorts/test_bias_report.py` — 30% 초과 권고, 3인 합계 60% 초과, 여성/청년 40% 미달 체크 (SC-011, SC-012)

### Ranking Batch (FR-008, FR-009)

- [X] **T105** [P] [US5] `src/dem_shorts/ranking/naver_news.py` — 네이버 뉴스 검색 크롤링 (robots.txt 준수, 5초 간격) (R-06)
- [X] **T106** [P] [US5] `src/dem_shorts/ranking/google_trends.py` — pytrends 래퍼
- [X] **T107** [P] [US5] `src/dem_shorts/ranking/youtube_metrics.py` — Data API search.list 기반 조회수·업로드 집계
- [X] **T108** [P] [US5] `src/dem_shorts/ranking/wikipedia_pageviews.py` — pageviews.toolforge.org 무료 API
- [X] **T109** [P] [US5] `src/dem_shorts/ranking/naver_datalab.py` — 네이버 데이터랩 공공 API
- [X] **T110** [US5] `src/dem_shorts/ranking_batch.py` — 5개 소스 가중 합산 + 0~100 클램핑 + WeeklyRanking upsert + Politician.tier 재배치 (T105~T109 의존)
- [X] **T111** [US5] `cli.py::ranking-batch` 서브커맨드 + B-03 cron 안내 (`0 22 * * 0`)

### Bias Report Batch (FR-038)

- [X] **T112** [US5] `src/dem_shorts/bias_report.py` — `UploadedShorts` 집계 → person_shares/party_shares/template_usage 계산 + 권고 메시지 생성
- [X] **T113** [US5] `cli.py::bias-report` 서브커맨드 + B-04 cron 안내 (`0 9 1 * *`)

### API + UI

- [X] **T114** [P] [US5] `app/api/dem-shorts/rankings/route.ts` — `GET` 주간 랭킹
- [X] **T115** [P] [US5] `app/api/dem-shorts/reports/route.ts` — `GET` 월간 리포트
- [X] **T116** [P] [US5] `app/dem-shorts/ranking/page.tsx` — 주간 랭킹 테이블 + 신규/급상승 뱃지
- [X] **T117** [P] [US5] `app/dem-shorts/reports/page.tsx` — 인물별 점유율 차트 + 권고 메시지 표시

**Checkpoint**: US5 단독 테스트 가능. 전체 5개 스토리 병합 시 완성 기능셋.

---

## Phase 8: Polish & Cross-Cutting Concerns

### Observability + Archive

- [x] **T118** [P] [POLISH] `src/dem_shorts/metrics_updater.py` + `cli.py::metrics-update` — YouTube 조회수·좋아요·수익 주기 갱신 (B-05)
- [x] **T119** [P] [POLISH] `src/dem_shorts/archive_rotator.py` + `cli.py::archive-rotate` — 3개월 이상 원본 콜드 스토리지 이동 (B-06)
- [x] **T120** [P] [POLISH] `src/dem_shorts/compliance/guardrail_learner.py` + `cli.py::guardrail-learn` — 월간 키워드 가중치 재학습 (FR-028, B-08)

### End-to-End Smoke Test (원칙 VII 강제)

- [x] **T121** [POLISH] `tests/fixtures/natv_sample.mp4` 준비 (10분 분량, git-ignored) — `tests/fixtures/README.md` 로 안내, 운영자 수동 배치
- [x] **T122** [POLISH] `tests/dem_shorts/test_e2e_smoke.py` — stub 모드 항상 실행 + real-models 는 fixture 있을 때만 (skip)
- [x] **T123** [POLISH] `cli.py::test-e2e` 서브커맨드 — `--real-models` 플래그로 stub/real 분기

### Full Test Gate (원칙 VIII)

- [x] **T124** [POLISH] `python3 -m pytest tests/dem_shorts/` — 273 passed, 1 skipped
- [x] **T125** [POLISH] `python3 -m pytest tests/` — 648 passed, 1 skipped (621 baseline → 648, 회귀 0건)

### Documentation

- [x] **T126** [P] [POLISH] `docs/dem-shorts/README.md` — 설치·CLI·API 한눈 보기
- [x] **T127** [P] [POLISH] `docs/dem-shorts/operations.md` — 일/주/월 루틴 + 트러블슈팅
- [x] **T128** [P] [POLISH] `CLAUDE.md` Recent Changes 에 Phase 8 신규 CLI 목록 반영

### Performance Validation (SC 검증)

- [x] **T129** [POLISH] SC-001 — `scripts/dem_shorts/measure_sc001.py` (phase timer + 15분 자동 단계 budget) + `e2e_smoke.py` 에 phase 별 elapsed_sec 계측. 운영자가 fixture 배치 후 1회 실행 → JSON 결과
- [x] **T130** [POLISH] SC-003 — `scripts/dem_shorts/measure_sc003.py` + `src/dem_shorts/sc003_comparator.py` (compute_accuracy + verdict 4종) + 11 단위 테스트. `tests/fixtures/sc003_ground_truth.example.json` 템플릿. 운영자가 라벨링 후 1회 실행
- [x] **T131** [POLISH] SC-005 — `tests/dem_shorts/test_gate.py::TestBypassResistance` 5/5 PASS (frontend skip / 서명 없음 / 빈 서명 / DB 조작 / risk 임계 초과)
- [x] **T132** [POLISH] SC-008 — 30개 draft skip_remotion 스트레스 → 0/30 fail (0.00% ≤ 5%)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup** (T001~T008): 의존성 없음 — 즉시 시작 가능
- **Phase 2 Foundational** (T009~T025): Setup 완료 후 — **모든 US 선행 필수**
- **Phase 3 US1** (T026~T040): Foundational 완료 후 — 다른 US와 병렬 가능
- **Phase 4 US2** (T041~T056): Foundational 완료 후 — 다른 US와 병렬 가능
- **Phase 5 US3** (T057~T095): Foundational 완료 후 시작 가능하되 **T077 Stub으로 Election 의존 해결** → US4와 실제 병렬 가능. T078 완료 = MVP 릴리스 Gate
- **Phase 6 US4** (T096~T102): Foundational 완료 후 가능. T098이 US3 T077 Stub을 교체
- **Phase 7 US5** (T103~T117): Foundational 완료 후 가능. T112는 UploadedShorts 데이터 필요 → US3 완료 권장
- **Phase 8 Polish** (T118~T132): 필요 기능들 완료 후

### User Story Dependencies

- **US1 → US2**: 약한 의존 (US2가 US1의 SourceVideo 사용). 병렬 개발 가능, 통합 시점만 동기화
- **US2 → US3**: US3는 US2의 SpeechSegment를 소비 → 완전 독립 개발은 어려우나 Stub으로 병렬 가능
- **US3 → US4**: T077 Stub으로 느슨한 결합. US4 완료 시 T098이 Stub 대체
- **US3 → US5**: 리포트(US5)가 UploadedShorts 필요 → US3 완료 후 리포트 집계 정확도 확보

### Within Each User Story

- 테스트(RED) → 구현(GREEN) → 통합 순서 (원칙 VII TDD)
- 모델 → 서비스 → API/UI 순서
- **T078 (우회 불가 게이트 테스트)**는 T079~T081 구현 전 반드시 작성·FAIL 확인 (SC-005 핵심)

### Parallel Opportunities

**Phase 1 전체 병렬**: T005/T006/T007/T008
**Phase 2 모델 병렬**: T009~T016, T017 → T018 → T019 → T020 → T021
**Phase 2 유틸 병렬**: T022/T023/T024 (T025는 cli 스켈레톤, 순차)
**Phase 3 병렬**: T026/T027/T028 테스트 + T029/T030 구현 → T031/T032/T033/T034 (순차 의존) → T036/T037/T038 UI 병렬
**Phase 5 최대 병렬**: T057~T071 대부분 병렬 가능, T072~T076 가드레일 병렬, T082~T090 API 병렬, T091~T094 UI 병렬

---

## Parallel Execution Examples

### Phase 2 Foundational — 모델 일괄 생성

```text
# T009~T016을 8명 동시 또는 1명 순차 (작업량 동일, 병렬 가능)
Task: "T009 SourceVideo frozen dataclass 작성 (data-model.md §1)"
Task: "T010 Politician frozen dataclass 작성 (§2)"
Task: "T011 SpeechSegment frozen dataclass 작성 (§3)"
Task: "T012 ShortsDraft frozen dataclass 작성 (§4)"
Task: "T013 ComplianceGateResult frozen dataclass 작성 (§5)"
Task: "T014 WeeklyRanking frozen dataclass 작성 (§6)"
Task: "T015 UploadedShorts frozen dataclass 작성 (§7)"
Task: "T016 BiasReport frozen dataclass 작성 (§8)"
```

### Phase 5 US3 — 가드레일 엔진 병렬

```text
Task: "T072 keyword_dict.py 작성"
Task: "T073 guardrail_keyword.py 작성 (T072 의존 — 약한 의존)"
Task: "T074 guardrail_llm.py 작성 (독립)"
Task: "T076 test_guardrail.py 작성 (TDD RED)"
```

T073·T074 병렬 → T075에서 통합.

---

## Implementation Strategy

### MVP First (US1 + US2 + US3만)

**목표**: T001~T095 완료. T078 우회 불가 게이트 테스트 통과.

1. Phase 1 Setup (T001~T008) — 1일
2. Phase 2 Foundational (T009~T025) — 2일 (모델 병렬 가능)
3. Phase 3 US1 (T026~T040) — 3일 → **MVP 1/3 검증** (샘플 영상 우선순위 대시보드)
4. Phase 4 US2 (T041~T056) — 4일 → **MVP 2/3 검증** (발언자 하이라이트)
5. Phase 5 US3 (T057~T095) — 7일 → **MVP 3/3 검증** (게이트 + 렌더 + 업로드)
6. **⭐ T078 우회 시도 3가지 모두 거부 확인 → MVP 릴리스 Gate**

MVP 완료 후 운영 시작 가능. US4/US5는 정식 운영(W8) 목표로 추가.

### Incremental Delivery

1. **Sprint 0~1 (W1~W3)**: Setup + Foundational + US1 → 대시보드 기본 동작
2. **Sprint 2 (W4~W5)**: US2 + US3 초기 → 수동 업로드 가능
3. **Sprint 3 (W6)**: US3 컴플라이언스 게이트 완성 → **MVP 릴리스**
4. **Sprint 4 (W7~W8)**: US4 선거 가드 + US5 리포트 + Polish → **정식 운영 전환**

---

## Notes

- `[P]`: 서로 다른 파일·독립 의존 → 병렬 실행 안전
- `[Story]` 태그로 MVP 범위 쉽게 추적
- 테스트는 TDD(RED→GREEN) 순서 강제 (원칙 VII)
- **T078 우회 불가 검증은 MVP 필수 게이트** (SC-005)
- **T125 기존 006 회귀 0건 확인은 FR-041 격리 증거** — 커밋 전 필수
- 각 Checkpoint 마다 독립 데모 가능한지 확인 (원칙 VII Evidence-Based)

**총 태스크 수**: 132개
**예상 총 작업**: 48 MD (기획서 산정 + 버퍼 20%)
**MVP 범위**: T001~T095 (95개, Phase 1~5) — 약 17일
**정식 운영 범위**: T096~T132 추가 (37개, Phase 6~8) — 추가 약 8일
