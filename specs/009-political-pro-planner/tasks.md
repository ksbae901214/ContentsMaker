---

description: "Task list for 009-political-pro-planner"
---

# Tasks: Political Shorts Planner (정치 숏츠 기획자)

**Input**: Design documents from `/specs/009-political-pro-planner/`
**Prerequisites**: plan.md, spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: ✅ INCLUDED — spec.md 수용 기준 #7("프롬프트에 절대 준수 4항목이 명시되어 있음 — 테스트로 검증")과 #8("pytest tests/test_political*.py 모두 통과")이 명시적으로 테스트를 요구함. 따라서 본 태스크 리스트는 TDD 사이클(RED → GREEN)을 따른다.

**Organization**: 태스크는 user story 단위로 묶여 있어 각각 독립적으로 구현·검증·증분 배포할 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능(다른 파일, 미완 태스크 의존성 없음)
- **[Story]**: 소속 user story (US1, US2, US3)
- 모든 설명에 정확한 파일 경로 포함

## Path Conventions

ContentsMaker는 하이브리드 구조(Python `src/` + Next.js `app/` + Remotion). 모든 경로는 repo root 기준 상대 경로(절대 경로는 `/Users/kyusik/ContentsMaker/` 접두사).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 디렉토리·환경변수 등 본 기능 전용 인프라 초기화

- [X] T001 Create `data/political_pro/` directory at repo root with a `.gitkeep` placeholder (per data-model.md E3 영속화 규약)
- [X] T002 [P] Document `GEMINI_API_KEY` requirement in `CLAUDE.md` Environment Variables section — add 1 line: `GEMINI_API_KEY — required for political_pro mode (Gemini TTS Charon). Free tier: 5 RPM.`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 user story가 의존하는 핵심 인프라. **이 단계 완료 전에는 어떤 user story도 시작 불가**.

**⚠️ CRITICAL**: T003, T004는 US1/US2/US3 모두에 영향을 주므로 반드시 먼저 완료.

- [X] T003 [P] Extend `ShortsScript.metadata.source_type` enum to allow `"political_pro"` in `src/analyzer/script_models.py` — update validation comment/docstring per data-model.md E4
- [X] T004 [P] Extend `src/tts/gemini_tts_generator.py`: add `style_prompt: str | None = None` and `temperature: float | None = None` parameters to `_call_gemini_tts()` and `generate_voice_with_timing_gemini()`; thread them into `types.GenerateContentConfig` (`temperature` field) and prepend `style_prompt` to text payload — per research.md R2 + D2

**Checkpoint**: Foundation 완료 — user story 구현 시작 가능.

---

## Phase 3: User Story 1 — 3개 기획안 비교 후 1개 선택 (Priority: P1) 🎯 MVP

**Goal**: 정치 YouTube URL 입력 → 90초 이내 3개 카드(RTF 6요소 + 서로 다른 angle) 표시 → 사용자가 1개 선택 가능

**Independent Test**: `python3 -m src.main political-pro <url> --plans-only` 실행 시 stdout에 `plans.length === 3`이고 3개 angle이 서로 다른 JSON 출력 (quickstart.md "5분 데모 CLI 경로 A" 시나리오)

### Tests for User Story 1 (TDD — RED First) ⚠️

> **NOTE**: 아래 테스트들을 먼저 작성하고 **반드시 실패하는 것을 확인**한 후 구현 진행

- [X] T005 [P] [US1] Write `tests/test_political_plan_models.py` — `ShortsPlan` / `Narration` / `ThreePlansResult` 라운드트립(to_dict→from_dict 동일성) + 검증 규칙(필수 필드 비어있지 않음, `clip_start < clip_end ≤ video_duration`, `angle` Literal 타입) per data-model.md E1/E2/E3
- [X] T006 [P] [US1] Write `tests/test_political_planner_prompt.py` — `political_planner_prompt.py`의 시스템 프롬프트 문자열에 4가지 절대 준수 항목이 **모두 문자열로 포함**되어 있는지 검증: ("영상에서 확인 가능한 사실만", "개인 의견·해석·추측·루머 금지", "정치적 편향" + "지지/비판 금지", "왜곡 금지") — FR-007, SC-005
- [X] T007 [P] [US1] Write `tests/test_political_planner.py` — `generate_three_plans()` Claude subprocess 모킹: (a) 정상 응답 → 3개 `ShortsPlan` 파싱, (b) 첫 호출 JSON 파싱 실패 → 1회 자동 재시도 후 성공, (c) 2회 모두 실패 → `PoliticalPlannerError` 발생, (d) 3개 plan의 `angle` 필드가 서로 다름 검증 — FR-004, FR-006, FR-008

### Implementation for User Story 1

- [X] T008 [P] [US1] Create `src/analyzer/political_plan_models.py` — `Narration`, `ShortsPlan`, `ThreePlansResult` `@dataclass(frozen=True)` + `to_dict()` / `from_dict()` 수동 구현 + 검증 로직 (필수 필드 비어있지 않음, 시간 범위 체크, angle Literal) per data-model.md E1/E2/E3 — T005 통과
- [X] T009 [US1] Create `src/analyzer/political_planner_prompt.py` — RTF 6요소 구조 시스템 프롬프트 + 4가지 절대 준수 항목(FR-007) + JSON 출력 스키마 strict + 김정치입니다 채널 톤 가이드(중립 유지) — T006 통과
- [X] T010 [US1] Create `src/analyzer/political_planner.py` — `generate_three_plans(youtube_url, transcript, video_title, video_duration_sec) -> ThreePlansResult`: (a) Claude CLI subprocess 단일 호출(research.md R1, 기존 `claude_analyzer.py` 패턴 차용), (b) JSON 응답 파싱 → 3개 `ShortsPlan`, (c) 파싱 실패 시 1회 자동 재시도, (d) 영상 길이 초과 클램프(FR-013) — T007 통과
- [X] T011 [US1] Create `app/api/political-pro/plans/route.ts` — `POST /api/political-pro/plans` (contract `api-political-pro-plans.md`): (a) URL 검증 → invalid_url, (b) `src.scraper.youtube_downloader.download_video` 호출, (c) `transcribe_video_or_fallback` 호출(transcript_unavailable 매핑), (d) `generate_three_plans` 호출(claude_plan_generation_failed 매핑), (e) JSON 응답 본문에 plans/videoPath/videoDurationSec/transcriptPath/videoTitle 포함 — Acceptance T1~T7
- [X] T012 [P] [US1] Create `app/components/PoliticalPlanPicker.tsx` — 3개 ShortsPlan 카드 그리드(모바일은 세로): angle 배지 / hook 강조 / `mm:ss~mm:ss + clipReason` / flow_intro·middle·climax / narrations 접기 / cta + "이 기획안으로 진행" 버튼 → `onSelect(planIdx: 0|1|2)` 콜백
- [X] T013 [US1] Modify `app/page.tsx` — 탭 union 타입에 `"political_pro"` 추가 + 신규 탭 UI(YouTube URL 입력 + "3 기획안 생성" 버튼) + `/api/political-pro/plans` 호출 + `PoliticalPlanPicker` 렌더 + 선택 콜백으로 `selectedPlanIdx` / `plansJson` / `videoPath` / `videoDurationSec` 상태 보관 (영상 생성은 US2)

**Checkpoint**: User Story 1 완전 동작 — 3개 기획안 표시까지 검증 가능. 영상 생성은 US2.

---

## Phase 4: User Story 2 — 변환된 스크립트 검수 및 영상 생성 (Priority: P1)

**Goal**: 선택된 ShortsPlan → ShortsScript 변환 → 검수 화면(기존 `ScriptReviewer` 재사용) → 원본 9:16 클립 + Gemini TTS Charon → 30~60초 MP4 출력

**Independent Test**: 임의 ShortsPlan JSON을 직접 제공 → `mode=political_pro`로 `/api/generate` 호출 → 최종 mp4가 30~60초이고 9:16 비율로 출력 (quickstart.md 검증 체크리스트)

### Tests for User Story 2 (TDD — RED First) ⚠️

- [X] T014 [P] [US2] Write `tests/test_gemini_tts_style_prompt.py` — `_call_gemini_tts` 모킹: (a) `voice_name="Charon"` 전달 검증, (b) `temperature=0.5` 전달 검증, (c) `style_prompt="Newscaster, British RP, rapid pace"` 가 텍스트 prefix로 결합되었는지 검증, (d) `style_prompt=None` 일 때는 prefix 미결합 검증 — T004의 확장 인터페이스 검증
- [X] T015 [P] [US2] Add `tests/test_political_planner.py::test_plan_to_script` — `plan_to_script(plan, video_title, video_duration_sec)`: (a) `ShortsPlan` → `ShortsScript` 변환, (b) 첫 씬 text == plan.hook, (c) 마지막 씬 text == plan.cta, (d) 각 씬 duration ≤ 5.0 자동 분할(`MAX_SCENE_DURATION_SECONDS`) — FR-011, FR-012, FR-013

### Implementation for User Story 2

- [X] T016 [US2] Add `plan_to_script(plan, video_title, video_duration_sec) -> ShortsScript` to `src/analyzer/political_planner.py` — Narration → Scene 매핑 + `source_type="political_pro"` + emotion auto-pick(기본 `angry`) + `MAX_SCENE_DURATION_SECONDS=5.0` 자동 분할(기존 `src/editor/scene_ops.split_scenes_to_max_duration` 재사용) + `clip_end_sec` 영상 길이 클램프 — T015 통과
- [X] T017 [US2] Modify `app/api/generate/route.ts` — `mode === "political_pro"` 분기 Phase 1 추가: (a) FormData에서 `selectedPlanIdx`/`plansJson`/`youtubeUrl`/`videoPath`/`videoDurationSec` 수신, (b) Python subprocess로 `plan_to_script` 호출 → ShortsScript 파일 저장, (c) `stopAfter === "analyze"` 시 `done` 이벤트로 scriptPath + scenes + videoPath + clipStartSec/clipEndSec 반환 — contract `api-generate-political-pro.md` Phase 1
- [X] T018 [US2] Modify `app/api/generate/route.ts` — `mode === "political_pro"` 분기 Phase 2 추가 (`mode === "script"` + `politicalProMeta` 입력): (a) `segment_cutter.cut_segment` 호출하여 씬별 9:16 클립 분할(기존 natv_clip 분기의 `scene_clip_cut` 로직 차용), (b) `generate_voice_with_timing_gemini(script, voice_name="Charon", style_prompt="Read in a British RP newscaster voice at a rapid pace, neutral political tone", temperature=0.5, ...)`, (c) `render_video(script, audio_path, scene_videos, ...)` Remotion 호출 — contract Phase 2 + research.md D2/D3
- [X] T019 [US2] Modify `app/page.tsx` — `political_pro` 탭의 PoliticalPlanPicker `onSelect` 핸들러에서 `/api/generate` (mode=political_pro, stopAfter=analyze) 호출 → 결과로 기존 `ScriptReviewer` 컴포넌트 렌더(재사용, 별도 신규 컴포넌트 없음) → 검수 완료 시 `/api/generate` (mode=script + politicalProMeta) 재호출 → 결과 화면
- [X] T020 [US2] Modify `app/page.tsx` — 결과 화면에서 `sourceType === "political_pro"` 일 때 (a) "⚠️ 출력은 자동 생성 결과이며 게시 전 사용자 검수가 필요합니다" 경고 배너 표시(FR-021), (b) YouTube/TikTok 자동 업로드 버튼 숨김 또는 비활성화(FR-020)
- [X] T021 [US2] Add `political-pro` subcommand to `src/main.py` — CLI 진입점 per contract `cli-political-pro.md`: 옵션(`--plans-only`, `--interactive`, `--plan-idx`, `--no-bgm`, `--no-transitions`, `--no-sfx`, `--output-dir`) + exit code 매핑(0/2/3/4/5/6/7) + 인터랙티브 모드 stdin 입력 → 영상 생성까지 일괄 실행

**Checkpoint**: US1 + US2 모두 독립 동작 — 정치 영상 1편 e2e 생성 가능.

---

## Phase 5: User Story 3 — 정치 중립성 보장 (Priority: P2)

**Goal**: 시스템 프롬프트에 4종 절대 준수 항목 인코딩 + 사용자 검수 의무 안내 + 자동 업로드 차단

**Independent Test**: (a) `pytest tests/test_political_planner_prompt.py` 통과 → 4종 항목 모두 발견 (SC-005), (b) 샘플 정치 영상 3개로 생성된 9개 기획안 사람 검토 시 명시적 편향 0건 (SC-006), (c) 결과 화면 자동 업로드 버튼 부재

### Implementation for User Story 3

> **Note**: 핵심 구현 작업은 US1의 T009(프롬프트)와 US2의 T020(UI 가드)에 이미 포함됨. US3 단독 태스크는 검증·문서·운영 가드.

- [X] T022 [US3] Run `pytest tests/test_political_planner_prompt.py -v` → 4종 항목 검증 통과 확인 (SC-005). 실패 시 T009의 `political_planner_prompt.py`를 수정하여 재실행
- [X] T023 [P] [US3] Add operator-facing checklist to `quickstart.md` — "샘플 영상 3개로 9개 기획안 사람 검토" 실행 가이드 + 편향 표현 점검 기준 (SC-006 운영 절차)
- [X] T024 [P] [US3] Verify `app/page.tsx` political_pro 결과 화면이 다른 모드와 분리되어 YouTube/TikTok 업로드 토글을 노출하지 않는지 시각적 확인(브라우저 e2e) — FR-020

**Checkpoint**: US1 + US2 + US3 모두 독립 동작 — 신뢰성·중립성 가드 완료.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Constitution 원칙 VII(증거 기반 완료) / VIII(전체 테스트) 충족 + 문서 업데이트

- [X] T025 [P] Update `CLAUDE.md` "Input Modes" 표에 `political_pro` 행 추가: `| political_pro | YouTube URL | analyze + generate_three_plans + plan_to_script | 3 기획안 비교 후 선택 |` (CLAUDE.md:148-156 부근)
- [X] T026 [P] Update `CLAUDE.md` "Recent Changes" 섹션 상단에 `- 011: Political Shorts Planner — RTF 6요소 3 기획안 + Gemini TTS Charon (정치 모드)` 1행 추가
- [X] T027 Run full pytest gate: `python3 -m pytest tests/ -v` → 0 failures 확인 (Constitution 원칙 VIII, SC-008)
- [X] T028 Run Next.js build: `npm run build` → 0 errors 확인 (spec.md 수용 기준 #8)
- [X] T029 [P] Run ruff lint: `ruff check src/analyzer/political_planner.py src/analyzer/political_plan_models.py src/analyzer/political_planner_prompt.py src/tts/gemini_tts_generator.py src/main.py` → 0 warnings
- [X] T030 **MANDATORY** Generate test video per user memory `feedback_test_video.md` (작업 완료 시 GPT 이미지 제외 테스트 영상 생성): `python3 -m src.main manual --file data/raw/sample.json --no-images` → 결과 MP4 경로·길이 첨부 (Constitution 원칙 VII)
- [X] T031 Run quickstart.md 검증 체크리스트(정치 영상 1편): 30~60초 / 9:16 / Hook 1~3초 / CTA 마지막 / Charon 음성 / 자동 업로드 토글 부재 — 6개 항목 모두 OK 확인 (SC-001~SC-008)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup: T001, T002)
   │
   ▼
Phase 2 (Foundational: T003, T004) — BLOCKS all user stories
   │
   ├─▶ Phase 3 (US1: T005~T013) — MVP
   │      │
   │      └─▶ Phase 4 (US2: T014~T021) — extends US1's state
   │             │
   │             └─▶ Phase 5 (US3: T022~T024) — validates US1 prompts + US2 UI
   │                    │
   │                    ▼
   │             Phase 6 (Polish: T025~T031)
```

### User Story Dependencies

- **US1 (P1)** ← Phase 2 완료. 다른 스토리 의존 없음.
- **US2 (P1)** ← Phase 2 + US1의 데이터 모델(T008) + 컴포넌트 상태(T013) 필요. 단 검수 → 영상 흐름 자체는 독립 테스트 가능(임의 plan JSON 주입).
- **US3 (P2)** ← US1의 T009(프롬프트) + US2의 T020(UI 가드) 산출물에 대한 검증. 신규 구현 거의 없음.

### Within Each User Story

- 테스트(T005, T006, T007, T014, T015) **반드시 먼저 RED 확인** 후 구현(T008, T009, T010, T016, ...) 진행 — Constitution 원칙 III(TDD)
- 모델(T008) 먼저, 그 뒤 서비스(T010), 그 뒤 엔드포인트(T011)
- 백엔드(T011, T016) 그 뒤 프론트엔드(T013, T019)

### Parallel Opportunities

- **Phase 1**: T001과 T002 병렬 가능
- **Phase 2**: T003과 T004 병렬 가능 (서로 다른 파일)
- **US1 테스트**: T005, T006, T007 모두 병렬 (서로 다른 테스트 파일)
- **US1 구현 (테스트 통과 후)**: T008 + T012 병렬 가능 (모델 vs UI 컴포넌트 — 서로 다른 파일). T009·T010·T011은 순차(같은 모듈/연쇄 의존).
- **US2 테스트**: T014와 T015 병렬 가능
- **US3**: T023과 T024 병렬 가능
- **Polish**: T025·T026·T029 병렬 가능. T027·T028·T030·T031은 순차(증거 수집)

---

## Parallel Example: User Story 1 (TDD RED phase)

```bash
# Phase 2 완료 후, US1 테스트 3개 병렬 작성 (모두 실패해야 함)
Task: "Write tests/test_political_plan_models.py — round-trip + validation"
Task: "Write tests/test_political_planner_prompt.py — 4 rules detection"
Task: "Write tests/test_political_planner.py — Claude mock + 3-plan parse + retry"

# 3개 모두 RED 확인 후, 구현 2개 병렬 가능 (서로 다른 파일):
Task: "Create src/analyzer/political_plan_models.py"
Task: "Create app/components/PoliticalPlanPicker.tsx"
# 나머지(T009, T010, T011, T013)는 순차 — 같은 모듈 또는 의존 체인
```

---

## Implementation Strategy

### MVP First (User Story 1만)

1. Phase 1 (T001~T002) 완료 — 30분
2. Phase 2 (T003~T004) 완료 — 1시간
3. Phase 3 (T005~T013) 완료 — 3~4시간
4. **STOP & VALIDATE**: `python3 -m src.main political-pro <url> --plans-only` 실행 → 3개 plan JSON 출력 확인
5. 데모 가능 — 영상 생성 없이도 "비교 검토" 가치 제공

### Incremental Delivery

1. **MVP (US1)**: 3 기획안 비교 카드 → 정성 검증 → 사용자 피드백 받기
2. **+ US2**: 검수 + 영상 생성 → 자체 정치 영상 1편 e2e 검증
3. **+ US3**: 중립성 자동 검증 + 운영 가드
4. **+ Polish**: 회귀 테스트 + 빌드 + 테스트 영상 → 커밋·PR

### Parallel Team Strategy

본 프로젝트는 1인 운영이므로 병렬 인력 불필요. 단 도구 차원의 병렬은 위 "Parallel Opportunities"에 명시.

---

## Validation Gates (Constitution 원칙 VII·VIII)

작업 완료 신고 전 다음 증거 모두 첨부:

- [ ] `python3 -m pytest tests/ -v` → 0 failures (T027) — Full Test Gate
- [ ] `npm run build` → 0 errors (T028)
- [ ] `ruff check ...` → 0 warnings (T029)
- [ ] 테스트 영상 1편 MP4 경로 + 길이 (T030) — 사용자 메모리 `feedback_test_video.md`
- [ ] 실제 정치 영상 1편 e2e 결과 mp4 (T031) — 30~60초 / 9:16 / Charon 음성

추측성 완료 선언 금지(원칙 VII). 위 5건 모두 실행 출력으로 입증.

---

## Notes

- [P] 태스크는 서로 다른 파일이고 미완 태스크에 의존하지 않음.
- [Story] 라벨로 traceability 유지 — US1=비교 선택, US2=영상 생성, US3=중립성.
- 모든 신규 데이터 모델은 `@dataclass(frozen=True)` (Constitution 원칙 VI).
- 본 기능은 변동비 $0 운영 (무료 한도 내 Gemini TTS — research.md R2).
- Constitution 원칙 IV(정치 자동 스킵) 예외는 plan.md Complexity Tracking #2 참조.
- 매 태스크 또는 논리 단위 완료 시 커밋 권장 (`feat(political-pro): ...` 컨벤션).
