# Tasks: 영상 제작/편집 기능 고도화

**Input**: Design documents from `/specs/005-video-editor-upgrade/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested — test tasks omitted.

**Organization**: Tasks grouped by user story for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1-US11)
- Exact file paths included

---

## Phase 1: Setup

**Purpose**: 프로젝트 초기화, 새 의존성 설치, 공통 인프라 구축

- [x] T001 Install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities in package.json
- [x] T002 [P] Create src/editor/ directory and __init__.py for Python editor module
- [x] T003 [P] Create data/sfx/ data/projects/ data/templates/ directories
- [x] T004 [P] Add SEEDANCE_API_KEY to .env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story가 공유하는 데이터 모델 확장

**⚠️ CRITICAL**: User Story 구현 전에 완료 필요

- [x] T005 Add SubtitleStyle dataclass to src/analyzer/script_models.py with font_family, font_size, color, position_y, bg_color, bg_opacity fields
- [x] T006 [P] Add TransitionConfig dataclass to src/analyzer/script_models.py with type and duration fields
- [x] T007 [P] Add SfxConfig dataclass to src/analyzer/script_models.py with name, category, offset_ms, volume fields
- [x] T008 Extend Scene dataclass in src/analyzer/script_models.py with visual_type, motion_prompt, subtitle_style, transition, sfx fields (backward compatible defaults)
- [x] T009 Update ShortsScript.load() and .save() in src/analyzer/script_models.py to handle new optional fields
- [x] T010 [P] Add SubtitleStyle type to src/video/remotion/src/types.ts with matching TypeScript interface
- [x] T011 [P] Add TransitionConfig type to src/video/remotion/src/types.ts
- [x] T012 [P] Add SfxConfig type to src/video/remotion/src/types.ts

**Checkpoint**: 데이터 모델 확장 완료 — User Story 구현 시작 가능

---

## Phase 3: User Story 1 — 타임라인 기반 씬 편집 (P1) 🎯 MVP

**Goal**: 씬 순서 변경, 길이 조절, 분할, 병합을 타임라인 UI에서 수행

**Independent Test**: 기존 script.json을 열어 씬 순서 변경/분할/병합 후 리렌더링하여 반영 확인

- [x] T013 [US1] Implement scene_split() immutable function in src/editor/scene_ops.py — splits Scene at text position into two Scenes
- [x] T014 [P] [US1] Implement scene_merge() immutable function in src/editor/scene_ops.py — merges two adjacent Scenes into one
- [x] T015 [P] [US1] Implement scene_reorder() immutable function in src/editor/scene_ops.py — reorders scenes and recalculates timestamps
- [x] T016 [P] [US1] Implement scene_resize() immutable function in src/editor/scene_ops.py — changes scene duration and adjusts subsequent timestamps
- [x] T017 [US1] Create POST /api/scene/split endpoint in app/api/scene/split/route.ts — calls Python scene_split, returns updated scenes
- [x] T018 [P] [US1] Create POST /api/scene/merge endpoint in app/api/scene/merge/route.ts — calls Python scene_merge, returns merged scene
- [x] T019 [US1] Create Timeline component in app/components/Timeline.tsx — horizontal bar per scene, @dnd-kit sortable, drag-to-resize handles
- [x] T020 [US1] Add view toggle (card/timeline) to app/components/SceneEditor.tsx — toggle between existing SceneCard list and new Timeline
- [x] T021 [US1] Add split button to SceneCard in app/components/SceneCard.tsx — opens text cursor position picker for split point
- [x] T022 [US1] Add merge button to SceneCard in app/components/SceneCard.tsx — merges with next adjacent scene

**Checkpoint**: 타임라인 편집 기능 완료 — 씬 순서/길이/분할/병합 모두 동작

---

## Phase 4: User Story 2 — 자막 스타일 커스터마이즈 (P1)

**Goal**: 씬별 자막 폰트, 크기, 색상, 위치, 배경을 설정하고 프리셋 적용

**Independent Test**: 자막 스타일을 변경 후 리렌더링하여 영상에 반영되는지 확인

- [x] T023 [US2] Create SubtitleStyleEditor component in app/components/SubtitleStyleEditor.tsx — font, size, color, position, bg controls
- [x] T024 [P] [US2] Create 3 preset definitions (news, humor, emotional) in app/components/SubtitleStyleEditor.tsx as constants
- [x] T025 [US2] Create PUT /api/scene/style endpoint in app/api/scene/style/route.ts — updates scene subtitle_style in script JSON
- [x] T026 [US2] Update SceneText component in src/video/remotion/src/components/SceneText.tsx — apply SubtitleStyle props dynamically instead of hardcoded values
- [x] T027 [US2] Pass subtitle_style from script JSON through renderer.py props to Remotion in src/video/renderer.py
- [x] T028 [US2] Add "스타일" button to SceneCard in app/components/SceneCard.tsx — opens SubtitleStyleEditor for that scene
- [x] T029 [US2] Add "전체 적용" option to SubtitleStyleEditor — applies style to all scenes at once

**Checkpoint**: 자막 스타일 커스터마이즈 완료 — 프리셋 및 커스텀 스타일 동작

---

## Phase 5: User Story 3 — AI 영상 클립 생성 (P2)

**Goal**: Seedance 2.0으로 AI 영상 클립을 생성하여 씬 배경으로 사용

**Independent Test**: "영상 모드" 선택 후 생성하여 움직이는 배경이 재생되는지 확인

- [x] T030 [US3] Create VideoGeneratorBase ABC in src/video_gen/base.py — generate(), get_status(), download() abstract methods
- [x] T031 [US3] Implement SeedanceGenerator in src/video_gen/seedance_gen.py — Seedance 2.0 API integration (async POST/GET/download)
- [x] T032 [US3] Create generator factory in src/video_gen/factory.py — returns SeedanceGenerator by default based on config
- [x] T033 [US3] Create POST /api/video-gen endpoint in app/api/video-gen/route.ts — SSE streaming for per-scene generation status
- [ ] T034 [US3] Add visual mode selector (image/video/hybrid) to app/page.tsx generation form
- [x] T035 [US3] Create SceneWithVideo component in src/video/remotion/src/components/SceneWithVideo.tsx — renders <OffthreadVideo> for video clips
- [x] T036 [US3] Update ShortsComposition.tsx to conditionally render SceneWithImage or SceneWithVideo based on scene.visual_type
- [ ] T037 [US3] Update renderer.py to copy video clips to Remotion public dir and pass video paths as props
- [x] T038 [US3] Add cost estimation display before video generation — show estimated cost per scene and total
- [ ] T039 [US3] Implement auto-fallback to static image when video generation fails in src/video_gen/seedance_gen.py

**Checkpoint**: AI 영상 클립 생성 완료 — Seedance I2V/T2V 모두 동작, 폴백 작동

---

## Phase 6: User Story 4 — 트랜지션 효과 (P2)

**Goal**: 씬 전환 시 다양한 애니메이션 효과 적용

**Independent Test**: 각 씬에 서로 다른 트랜지션을 적용 후 렌더링하여 효과 확인

- [x] T040 [US4] Create Transition component in src/video/remotion/src/components/Transition.tsx — 6 effects (fade, slide-left, slide-up, zoom, dissolve, wipe) using interpolate/spring
- [x] T041 [US4] Integrate Transition component into ShortsComposition.tsx — apply between consecutive scenes based on scene.transition config
- [x] T042 [US4] Create TransitionPicker component in app/components/TransitionPicker.tsx — visual selector for 6 effect types + duration slider
- [x] T043 [US4] Create PUT /api/scene/transition endpoint in app/api/scene/transition/route.ts — updates scene transition config
- [x] T044 [US4] Add "전체 적용" button to TransitionPicker — applies same transition to all scenes
- [x] T045 [US4] Pass transition config through renderer.py to Remotion props

**Checkpoint**: 트랜지션 효과 완료 — 6종 효과 모두 렌더링 가능

---

## Phase 7: User Story 5 — 음성 선택 및 미리듣기 (P2)

**Goal**: edge-tts 한국어 음성 중 원하는 음성 선택 및 미리듣기

**Independent Test**: 다른 음성 선택 후 렌더링하여 변경된 음성 확인

- [x] T046 [US5] Add Korean voice list with metadata (gender, tone, description) to src/tts/voice_config.py
- [x] T047 [US5] Create POST /api/tts/preview endpoint in app/api/tts/preview/route.ts — generates short sample audio for selected voice
- [x] T048 [US5] Create VoicePicker component in app/components/VoicePicker.tsx — voice list with play preview button, gender/tone filters
- [x] T049 [US5] Add VoicePicker to SceneEditor in app/components/SceneEditor.tsx — voice selection applies to entire script

**Checkpoint**: 음성 선택 완료 — 미리듣기 및 적용 동작

---

## Phase 8: User Story 6 — 실시간 미리보기 (P3)

**Goal**: 리렌더링 없이 브라우저에서 편집 결과 즉시 미리보기

**Independent Test**: 텍스트 수정 후 플레이어에서 3초 이내 반영 확인

- [x] T050 [US6] Install @remotion/player in package.json
- [x] T051 [US6] Create VideoPreview component in app/components/VideoPreview.tsx — wraps Remotion Player with current script props
- [x] T052 [US6] Integrate VideoPreview into SceneEditor page in app/components/SceneEditor.tsx — side-by-side with edit panel
- [x] T053 [US6] Wire edit state changes to VideoPreview props — text, subtitle style, transition changes reflect in player immediately
- [x] T054 [US6] Add "최종 렌더링" button separate from preview — triggers actual MP4 render via existing /api/rerender

**Checkpoint**: 실시간 미리보기 완료 — 편집 내용이 플레이어에 즉시 반영

---

## Phase 9: User Story 7 — 프로젝트 저장/불러오기 (P3)

**Goal**: 편집 상태를 프로젝트로 저장하고 나중에 복원

**Independent Test**: 프로젝트 저장 → 브라우저 닫기 → 불러오기 → 편집 상태 100% 복원

- [x] T055 [US7] Create Project dataclass in src/editor/project.py — id, name, script, paths, timestamps
- [x] T056 [US7] Implement save_project() and load_project() in src/editor/project.py — JSON serialize to data/projects/{id}.json
- [x] T057 [US7] Create POST /api/project/save endpoint in app/api/project/save/route.ts
- [x] T058 [P] [US7] Create GET /api/project/load endpoint in app/api/project/load/route.ts
- [x] T059 [P] [US7] Create GET /api/project/list endpoint in app/api/project/list/route.ts
- [x] T060 [P] [US7] Create DELETE /api/project/delete endpoint in app/api/project/delete/route.ts
- [x] T061 [US7] Create ProjectList component in app/components/ProjectList.tsx — shows recent projects with name, date, thumbnail
- [x] T062 [US7] Add "프로젝트 저장" and "불러오기" buttons to app/page.tsx

**Checkpoint**: 프로젝트 관리 완료 — 저장/불러오기/삭제 동작

---

## Phase 10: User Story 8 — 효과음 삽입 (P3)

**Goal**: 씬에 효과음을 추가하여 몰입감 향상

**Independent Test**: 특정 씬에 효과음 추가 후 렌더링하여 재생 확인

- [ ] T063 [US8] Download and place 13 royalty-free sound effects in data/sfx/ (surprise×3, laugh×3, touching×2, emphasis×3, ui×2)
- [x] T064 [US8] Create sfx manifest file data/sfx/manifest.json — name, category, filename, duration_ms for each effect
- [x] T065 [US8] Create SfxPicker component in app/components/SfxPicker.tsx — category filter, preview playback, volume slider
- [x] T066 [US8] Add <Audio> component rendering to ShortsComposition.tsx — play sfx at scene.sfx[].offset_ms timing
- [x] T067 [US8] Update renderer.py to copy sfx files to Remotion public dir and pass sfx config as props

**Checkpoint**: 효과음 완료 — 카테고리 선택, 미리듣기, 영상 내 재생 동작

---

## Phase 11: User Story 9 — 일괄 생성 (P4)

**Goal**: 여러 URL/텍스트를 큐에 넣고 순차 자동 생성

**Independent Test**: 3개 URL 입력 → 일괄 생성 → 3개 영상 순차 생성 확인

- [x] T068 [US9] Create BatchJob dataclass in src/editor/batch.py — id, input_type, input_data, status, progress, error
- [x] T069 [US9] Implement batch_processor() in src/editor/batch.py — sequential processing with per-job error isolation
- [x] T070 [US9] Create POST /api/batch endpoint in app/api/batch/route.ts — SSE streaming for batch progress
- [x] T071 [US9] Create BatchQueue component in app/components/BatchQueue.tsx — input list, per-job status, progress bars

**Checkpoint**: 일괄 생성 완료 — 다수 작업 순차 처리, 개별 실패 격리

---

## Phase 12: User Story 10 — 템플릿 시스템 (P4)

**Goal**: 스타일 조합을 템플릿으로 저장하고 재사용

**Independent Test**: 템플릿 생성 → 새 영상에 적용 → 스타일 자동 적용 확인

- [x] T072 [US10] Create Template dataclass in src/editor/template.py — name, subtitle_style, transition, voice, bgm_enabled
- [x] T073 [US10] Implement save_template() and load_templates() in src/editor/template.py — JSON to data/templates/
- [x] T074 [US10] Create 3 built-in templates (humor, emotional, news) in data/templates/
- [x] T075 [US10] Create TemplatePicker component in app/components/TemplatePicker.tsx — preset list + custom save
- [x] T076 [US10] Integrate TemplatePicker into generation flow in app/page.tsx — apply template before rendering

**Checkpoint**: 템플릿 시스템 완료 — 기본 3종 + 커스텀 저장/적용

---

## Phase 13: User Story 11 — 다국어 자막 (P4)

**Goal**: 한국어 자막을 영어/일본어로 번역하여 이중 자막 표시

**Independent Test**: 영어 자막 추가 옵션 ON → 렌더링 → 이중 자막 표시 확인

- [x] T077 [US11] Implement translate_subtitles() in src/editor/translator.py — calls OpenAI GPT-4o-mini for en/ja translation
- [x] T078 [US11] Create POST /api/translate endpoint in app/api/translate/route.ts — translates scene texts
- [x] T079 [US11] Add dual subtitle rendering to SceneText in src/video/remotion/src/components/SceneText.tsx — secondary subtitle below primary
- [x] T080 [US11] Add language selection UI to SceneEditor in app/components/SceneEditor.tsx — enable/disable + language picker (en/ja)
- [x] T081 [US11] Allow manual edit of translated text in SceneCard

**Checkpoint**: 다국어 자막 완료 — 한/영 또는 한/일 이중 자막 렌더링

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: 전체 기능 통합 품질 개선

- [ ] T082 Update README.md with new features documentation
- [ ] T083 [P] Update CLAUDE.md with new commands and project structure
- [x] T084 [P] Add error handling for all new API endpoints — consistent error response format
- [x] T085 Run full pipeline test with all features enabled — generate test video (no GPT images)
- [ ] T086 Performance check — verify preview updates within 3 seconds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3-4 (US1, US2)**: P1 priority — can run in parallel after Phase 2
- **Phase 5-7 (US3, US4, US5)**: P2 priority — can run in parallel after Phase 2
- **Phase 8-10 (US6, US7, US8)**: P3 priority — US6 benefits from US1+US2 completion
- **Phase 11-13 (US9, US10, US11)**: P4 priority — independent after Phase 2
- **Phase 14 (Polish)**: After all desired user stories complete

### User Story Dependencies

- **US1 (타임라인)**: Independent — no story dependencies
- **US2 (자막 스타일)**: Independent — no story dependencies
- **US3 (AI 영상)**: Independent — no story dependencies
- **US4 (트랜지션)**: Independent — no story dependencies
- **US5 (음성 선택)**: Independent — no story dependencies
- **US6 (실시간 미리보기)**: Benefits from US1+US2+US4 (more features to preview)
- **US7 (프로젝트 저장)**: Benefits from US1+US2 (more state to save)
- **US8 (효과음)**: Independent — no story dependencies
- **US9 (일괄 생성)**: Independent — no story dependencies
- **US10 (템플릿)**: Requires US2 (subtitle_style) and US4 (transition) for full value
- **US11 (다국어 자막)**: Independent — no story dependencies

### Parallel Opportunities

Phase 3 + Phase 4 can run in parallel (US1 + US2, different files)
Phase 5 + Phase 6 + Phase 7 can run in parallel (US3 + US4 + US5, different modules)
Phase 8 + Phase 9 + Phase 10 can run in parallel (US6 + US7 + US8, different areas)

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Phase 1: Setup
2. Phase 2: Foundational (data model extension)
3. Phase 3: US1 — 타임라인 편집
4. Phase 4: US2 — 자막 스타일
5. **STOP and VALIDATE**: 테스트 영상 생성으로 검증

### Incremental Delivery

1. Setup + Foundational → 기반 완료
2. US1 + US2 → 편집 기본 기능 (MVP)
3. US3 + US4 + US5 → AI 영상 + 트랜지션 + 음성
4. US6 + US7 + US8 → 실시간 미리보기 + 프로젝트 관리 + 효과음
5. US9 + US10 + US11 → 대량 생산 + 템플릿 + 다국어

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- 테스트 영상 생성: `OPENAI_API_KEY="" python3 -m src.main pipeline --file data/raw/sample.json`
