# Tasks: 영상 쇼츠 모드

**Input**: Design documents from `/specs/006-video-shorts-mode/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Constitution 원칙 III (TDD) + VIII (Full Test Gate) 요구에 따라 테스트 포함.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 의존성 추가 및 디렉토리/설정 준비

- [x] T001 Add httpx>=0.27.0 to requirements.txt
- [x] T002 Create data/videos/ directory and add .gitkeep
- [x] T003 Add DATA_VIDEOS_DIR constant in src/config/settings.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story가 의존하는 공통 데이터 모델 변경

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add source_type field ("blind" | "topic", default "blind") to Metadata frozen dataclass in src/analyzer/script_models.py — update to_dict() and from_dict() with backward compatibility
- [x] T005 Add source_type backward compatibility tests in tests/test_script_models.py — verify from_dict() without source_type returns "blind", verify round-trip with "topic"

**Checkpoint**: Foundation ready — Metadata.source_type available for all stories

---

## Phase 3: User Story 1 — 자유 주제로 이미지 쇼츠 영상 만들기 (Priority: P1) 🎯 MVP

**Goal**: 블라인드 외 자유 주제 입력으로 이미지 기반 Shorts 영상 생성

**Independent Test**: 주제 입력 탭에서 "즐겨 먹던 과자들의 배신" 나레이션 스타일 → 스크립트 분석 → 이미지 생성 → TTS → 영상 렌더링 완료

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T006 [P] [US1] Write TopicInput model tests in tests/test_topic_input.py — creation, validation (min 5 chars), to_dict/from_dict round-trip, save_topic() file output
- [x] T007 [P] [US1] Write topic prompt template tests in tests/test_prompt_template_topic.py — build_topic_prompt() output structure, style/tone/details inclusion, Rule 12 motion_prompt when visual_mode="video"
- [x] T008 [P] [US1] Write analyze_topic tests in tests/test_analyzer_topic.py — mock Claude call, verify ShortsScript with source_type="topic", verify _apply_voice_config and _ensure_line_breaks reuse

### Implementation for User Story 1

- [x] T009 [US1] Create TopicInput frozen dataclass + save_topic() in src/scraper/topic_input.py — fields: topic(str, min 5), style("narration"|"skit"|"review"), tone(str), details(str), created_at(auto KST). Follow BlindPost/manual_input patterns.
- [x] T010 [US1] Add TOPIC_ANALYZE_PROMPT template + build_topic_prompt(topic, style, tone, details) in src/analyzer/prompt_template.py — reuse common rules (emotion detection, line breaks, text length, highlight_words, pacing) from ANALYZE_PROMPT. Remove blind-specific rules (PII, comments). Add storytelling rules for topic mode.
- [x] T011 [US1] Add analyze_topic(topic_input: TopicInput, output_dir) -> tuple[ShortsScript, Path] in src/analyzer/claude_analyzer.py — call build_topic_prompt(), reuse _call_claude(), _parse_response(), _apply_voice_config(), _ensure_line_breaks(). Set source_type="topic" in Metadata.
- [x] T012 [US1] Add mode="topic" handling in app/api/generate/route.ts — extract topic/contentStyle/tone/details from FormData, call save_topic() then analyze_topic() via Python subprocess, continue existing image/TTS/render pipeline
- [x] T013 [US1] Add 주제 입력 탭 (4th tab) to app/page.tsx — topic input (min 5 chars), contentStyle select (narration/skit/review), tone input, details textarea. Wire to FormData with mode="topic".
- [x] T014 [US1] Run tests: python3 -m pytest tests/test_topic_input.py tests/test_prompt_template_topic.py tests/test_analyzer_topic.py -v

**Checkpoint**: 자유 주제 입력 → 이미지 쇼츠 생성 전체 파이프라인 동작. 기존 블라인드 모드 영향 없음.

---

## Phase 4: User Story 2 — 이미지 스타일 선택 (Priority: P1)

**Goal**: 4가지 이미지 스타일 프리셋(웹툰, 3D Pixar, 실사풍, 애니메)으로 다양한 스타일의 이미지 생성

**Independent Test**: 동일 주제를 웹툰/3D Pixar 스타일로 각각 생성 → 스타일이 시각적으로 구분됨

### Implementation for User Story 2

- [x] T015 [P] [US2] Add IMAGE_STYLE_PRESETS dictionary in src/illustrator/prompt_builder.py — 4 keys: webtoon (existing STYLE_PREFIX), 3d_pixar, realistic, anime. Each value is the full style prompt string.
- [x] T016 [US2] Add image_style="webtoon" parameter to build_image_prompts(script, image_style) and build_image_prompts_simple(script, image_style) in src/illustrator/prompt_builder.py — use IMAGE_STYLE_PRESETS[image_style] instead of STYLE_PREFIX. For non-webtoon styles, skip REFERENCE_STYLE_PREFIX.
- [x] T017 [US2] Add image_style parameter to generate_scene_images() and regenerate_single_image() in src/illustrator/image_generator.py — pass to build_image_prompts(). For non-webtoon styles, force use_references=False (use images.generate() instead of images.edit()).
- [x] T018 [US2] Add imageStyle parameter handling in app/api/generate/route.ts — extract from FormData (default "webtoon"), pass to generate_scene_images() Python subprocess call
- [x] T019 [US2] Add image style selector UI in app/page.tsx — 4 style buttons/cards (웹툰/3D Pixar/실사풍/애니메) visible when visualMode="manga". Default: webtoon. Wire to FormData imageStyle field.

**Checkpoint**: 이미지 모드에서 4가지 스타일 선택 → 각 스타일에 맞는 이미지 생성. 웹툰 기본값으로 기존 동작 유지.

---

## Phase 5: User Story 3 — AI 영상 클립 모드 (Priority: P2)

**Goal**: Seedance API로 씬별 3~5초 AI 영상 클립 생성, 최종 영상에 포함

**Independent Test**: 영상 쇼츠 모드 → 주제 입력 → Seedance 씬별 영상 클립 → TTS + 렌더링 완료

### Tests for User Story 3

- [x] T020 [P] [US3] Write Seedance generator tests in tests/test_seedance_gen.py — mock httpx, test generate/get_status/download/generate_and_wait flow, test estimate_cost calculation, test timeout and failure handling
- [x] T021 [P] [US3] Write renderer scene_videos tests in tests/test_renderer.py — verify scene_videos parameter adds sceneVideos to Remotion props JSON, verify video files copied to public/

### Implementation for User Story 3

- [x] T022 [US3] Add generate_and_wait(prompt, duration, resolution, source_image, output_path, poll_interval, max_wait) to VideoGeneratorBase in src/video_gen/base.py — default implementation: generate() → poll get_status() → download()
- [x] T023 [US3] Implement SeedanceGenerator fully in src/video_gen/seedance_gen.py — generate(): POST to API with httpx async client. get_status(): GET poll with task_id. download(): save video file. Use SEEDANCE_API_KEY from env. Handle timeout (10min max), HTTP errors.
- [x] T024 [US3] Add scene_videos parameter to render_video() in src/video/renderer.py — copy video files to public/vid_{timestamp}_scene_{id}.mp4, add sceneVideos: [{sceneId, videoFile}] to Remotion props. Existing sceneImages logic unchanged.
- [x] T025 [US3] Add visualMode="video" branch in app/api/generate/route.ts — check SEEDANCE_API_KEY existence, call SeedanceGenerator per scene via Python subprocess, collect scene_videos list, handle per-scene failure with image fallback, pass scene_videos to render_video()
- [x] T026 [US3] Add video generation progress messages in app/api/generate/route.ts — SSE progress: "씬 {n}/{total}: AI 영상 생성 중... ({percent}%)", handle fallback notification: "씬 {n} 영상 생성 실패 → 이미지 폴백"
- [x] T027 [US3] Run tests: python3 -m pytest tests/test_seedance_gen.py tests/test_renderer.py -v

**Checkpoint**: 영상 쇼츠 모드 → Seedance로 씬별 클립 생성 → Remotion 렌더링. 실패 시 이미지 폴백 동작.

---

## Phase 6: User Story 4 — 비주얼 모드와 비용 확인 (Priority: P2)

**Goal**: 이미지/영상 모드 토글 + 예상 비용 표시 + 결과 요약

**Independent Test**: 모드 토글 전환 시 비용 즉시 변경, 결과 화면에 모드별 요약 표시

### Implementation for User Story 4

- [x] T028 [US4] Add visualMode toggle UI in app/page.tsx — "[이미지 쇼츠 ~$0.005/씬] | [영상 쇼츠 ~$0.05/씬]" toggle. Default: manga. Wire to FormData visualMode. Disable video mode if SEEDANCE_API_KEY hint not configured.
- [x] T029 [US4] Add cost estimation display in app/page.tsx — calculate estimated cost based on visualMode × expected scene count. Update dynamically on mode change.
- [x] T030 [US4] Update result display in app/page.tsx — show visualMode, imageStyle, sourceType in result metadata. Show "이미지 N장" or "영상 N개" based on result. Add videoCount to JobResult interface.
- [x] T031 [US4] Add videoCount and visualMode/imageStyle/sourceType fields to done event response in app/api/generate/route.ts

**Checkpoint**: 모드 토글 동작, 비용 표시, 결과 화면 요약 확인.

---

## Phase 7: User Story 5 — 블라인드 모드에서도 영상 클립 사용 (Priority: P3)

**Goal**: 기존 블라인드 스크린샷/직접 입력에서도 visualMode 선택 가능

**Independent Test**: 블라인드 스크린샷 → 영상 쇼츠 모드 → AI 영상 클립 기반 렌더링

### Implementation for User Story 5

- [x] T032 [US5] Enable visualMode toggle for image/manual/url tabs in app/page.tsx — currently topic tab only. Show same toggle on all input tabs.
- [x] T033 [US5] Add visual_mode parameter to analyze() and build_prompt() in src/analyzer/claude_analyzer.py and src/analyzer/prompt_template.py — when visual_mode="video", include Rule 12 (motion_prompt generation) in ANALYZE_PROMPT. Default "manga" for backward compatibility.
- [x] T034 [US5] Wire visualMode from all modes (image/manual/url) through route.ts pipeline — pass to analyze() subprocess call, then to video generation branch

**Checkpoint**: 블라인드 모드 + 영상 쇼츠 파이프라인 완전 동작.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 전체 파이프라인 검증 + 회귀 테스트 + 테스트 영상 생성

- [x] T035 Run full test suite: python3 -m pytest tests/ -v — verify all existing + new tests pass (Constitution VIII) — 185 passed
- [ ] T036 E2E regression: 기존 웹툰 모드 (블라인드 스크린샷 → 만화 영상) 동작 확인 — 하위 호환성 검증 (SC-003)
- [ ] T037 Generate test video without images: python3 -m src.main manual --file data/raw/sample.json --no-images — verify TTS, timing, text overlay (Constitution VII)
- [ ] T038 [P] Add topic subcommand to CLI in src/main.py — --topic, --style, --tone, --details, --visual-mode, --image-style arguments. Call save_topic() → analyze_topic() → pipeline.
- [ ] T039 [P] Add --visual-mode and --image-style arguments to pipeline subcommand in src/main.py
- [ ] T040 SEEDANCE_API_KEY 미설정 시 영상 모드 선택 → 에러 메시지 + 이미지 모드 권장 확인 (FR-013)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — No dependencies on other stories
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — No dependencies on other stories, **can run in parallel with US1**
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — Depends on US2 for imageStyle fallback context, but independently testable
- **US4 (Phase 6)**: Depends on US1 + US2 (needs topic tab + style selector to add mode toggle alongside)
- **US5 (Phase 7)**: Depends on US3 (needs video pipeline working) + US4 (needs toggle UI)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (Metadata.source_type)
    ↓
    ├─→ Phase 3: US1 (주제 입력) ──┐
    │                               ├─→ Phase 6: US4 (모드 토글 + 비용) ─┐
    ├─→ Phase 4: US2 (스타일) ─────┘                                     │
    │                                                                     ├─→ Phase 8: Polish
    └─→ Phase 5: US3 (영상 클립) ──→ Phase 7: US5 (블라인드+영상) ───────┘
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services (TopicInput → analyze_topic)
- Backend before frontend (Python → route.ts → page.tsx)
- Core implementation before integration

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 can all run in parallel
- **Phase 2**: T004 then T005 (sequential — test validates model change)
- **Phase 3**: T006, T007, T008 tests in parallel → T009, T010 models in parallel → T011 → T012 → T013
- **Phase 4**: T015 → T016 → T017 → T018 → T019 (sequential — each depends on prior)
- **US1 and US2 can run in parallel** (different files, no shared dependencies)
- **US3 tests T020, T021 can run in parallel**
- **Phase 8**: T038 and T039 in parallel

---

## Parallel Example: Phase 3 (User Story 1)

```
# Launch all US1 tests in parallel (TDD RED):
Agent 1: tests/test_topic_input.py (T006)
Agent 2: tests/test_prompt_template_topic.py (T007)
Agent 3: tests/test_analyzer_topic.py (T008)

# After tests written, launch model + prompt in parallel:
Agent 1: src/scraper/topic_input.py (T009)
Agent 2: src/analyzer/prompt_template.py (T010)

# Sequential after models:
T011 (analyze_topic) → T012 (route.ts) → T013 (page.tsx) → T014 (verify tests)
```

## Parallel Example: US1 + US2 simultaneously

```
# US1 and US2 touch different files — can proceed in parallel:
Agent A (US1): topic_input.py → prompt_template.py → claude_analyzer.py → route.ts topic mode → page.tsx topic tab
Agent B (US2): prompt_builder.py → image_generator.py → route.ts imageStyle → page.tsx style selector
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T005)
3. Complete Phase 3: User Story 1 (T006-T014)
4. **STOP and VALIDATE**: 주제 "즐겨 먹던 과자들의 배신" → 이미지 쇼츠 생성 E2E 확인
5. Deploy if ready — 사용자가 자유 주제로 영상 만들기 가능

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. **US1 (주제 입력)** → 자유 주제로 웹툰 스타일 영상 생성 (MVP!)
3. **US2 (이미지 스타일)** → 4가지 스타일 선택 가능 (다양성 확보)
4. **US3 (영상 클립)** → Seedance AI 영상 클립 지원 (프리미엄 기능)
5. **US4 (비용 확인)** → 모드 토글 + 비용 투명성 (UX 완성)
6. **US5 (블라인드+영상)** → 기존 모드에서도 영상 지원 (완전성)
7. Polish → 전체 검증 + CLI 확장

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Constitution VII: 각 Phase 완료 후 테스트 영상 생성으로 검증
- Constitution VIII: Phase 8에서 전체 테스트 실행 필수
- Remotion sceneVideos + SceneWithVideo는 이미 구현됨 — Python/TS 측 연결만 필요
- 기존 블라인드 모드 회귀 방지: Phase 8 T036에서 별도 검증
