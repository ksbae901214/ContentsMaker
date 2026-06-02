---

description: "Task list for TRIM-01 — NATV 씬 구간 드래그 트리밍"
---

# Tasks: NATV 씬 구간 드래그 트리밍 (TRIM-01)

**Input**: Design documents from `/specs/008-natv-scene-trim/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/api-scene-trim.md ✅

**Tests**: **INCLUDED** — constitution III (TDD mandatory) 에 따라 각 Phase RED→GREEN 강제.

**Organization**: 3개 User Story 로 구성. US1(P1, MVP 인프라) → US2(P2, 실제 트리밍 UX) → US3(P3, 폴리싱). 각 스토리는 독립 테스트 가능.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3) — Setup/Foundational/Polish 는 라벨 없음

## Path Conventions

- Web app: Python `src/`, Next.js `app/`, Remotion `src/video/remotion/src/`, tests `tests/` + `app/components/__tests__/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 기존 레포 구조 활용 — 신규 의존성 없음.

- [X] T001 Create spec feature directory stubs at `specs/008-natv-scene-trim/` (plan.md, research.md, data-model.md, contracts/, quickstart.md) — **이미 완료** ✅ (체크 확인만)
- [X] T002 [P] Verify React Testing Library 사용 가능 — `package.json` 에 `@testing-library/react`, `@testing-library/user-event`, `vitest` 또는 `jest` 존재 여부 확인; 없으면 vitest 로컬 설치 (`npm i -D vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom`)
- [X] T003 [P] Add `vitest` config: `vitest.config.ts` with jsdom env, `tests/setup.ts` import `@testing-library/jest-dom`
- [X] T004 Add npm script `"test:ui": "vitest run app/components/__tests__"` in `package.json`

**Checkpoint**: 테스트 러너 준비 — UI 테스트 실행 가능

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 데이터 모델 확장 — US1/US2 전부 이 필드에 의존.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests (RED — 먼저 실패)

- [ ] T005 [P] Write failing test `tests/test_script_models_trim.py::test_scene_roundtrip_with_source_offsets` — `source_video/start/end` 가진 Scene 을 `to_dict/from_dict` 왕복 시 보존되는지
- [ ] T006 [P] Write failing test `tests/test_script_models_trim.py::test_scene_roundtrip_without_source_offsets` — 기존 스크립트와 후방 호환 (세 필드 모두 None)
- [ ] T007 [P] Write failing test `tests/test_script_models_trim.py::test_scene_from_dict_accepts_camelcase` — `sourceVideo`/`sourceStart`/`sourceEnd` 도 수용
- [ ] T008 [P] Write failing test `tests/test_script_models_trim.py::test_scene_to_dict_omits_none_offsets` — None 이면 JSON 에 키 생략

### Implementation (GREEN)

- [ ] T009 Add `source_video: str | None`, `source_start: float | None`, `source_end: float | None` fields to `src/analyzer/script_models.py` `Scene` frozen dataclass (defaults None, all-or-none validation in `__post_init__` 선택)
- [ ] T010 Extend `Scene.to_dict()` to include offset keys only when `source_video is not None`
- [ ] T011 Extend `Scene.from_dict()` to accept both snake_case and camelCase (`sourceVideo`/`sourceStart`/`sourceEnd`) mirroring existing pattern
- [ ] T012 Run pytest `tests/test_script_models_trim.py` — expect 4 pass, 0 fail

**Checkpoint**: Scene 모델 확장 완료 — US1/US2 에서 offset 필드 참조 가능

---

## Phase 3: User Story 1 — Offset-aware rendering (Priority: P1) 🎯 MVP 인프라

**Goal**: 스크립트에 offset 이 있으면 Remotion 이 원본 + `startFrom/endAt` 로 재생. 파일을 다시 자르지 않고도 구간만 보이는 영상이 나와야 함. **사용자 UI 변화 없음 — 내부 동작만 개선**.

**Independent Test**: `data/scripts/e2e_rerender_test.json` 에 offset 수동 삽입 → `/api/rerender` 호출 → 결과 MP4 해당 씬에서 offset 범위만 재생되는지 프레임 추출해 육안 확인.

### Tests (RED)

- [ ] T013 [P] [US1] Failing test `tests/test_renderer.py::test_source_video_copied_to_public` — offset 씬의 `source_video` 가 Remotion `public/` 으로 복사되는지
- [ ] T014 [P] [US1] Failing test `tests/test_renderer.py::test_renderer_prefers_offsets_over_scene_videos` — offset + scene_videos 둘 다 있으면 offset 경로 우선
- [ ] T015 [P] [US1] Failing test `tests/test_renderer.py::test_renderer_falls_back_to_scene_videos_when_no_offsets` — 기존 동작 보존
- [ ] T016 [P] [US1] Failing test `tests/dem_shorts/test_natv_cut_loop.py::test_natv_cut_records_source_offsets` — NATV 루프가 씬마다 `source_video/start/end` 기록
- [ ] T017 [P] [US1] Failing test `tests/dem_shorts/test_natv_cut_loop.py::test_natv_cut_preserves_existing_fields` — 다른 씬 필드 훼손 없음
- [ ] T018 [P] [US1] Failing test `tests/dem_shorts/test_natv_cut_loop.py::test_natv_cut_monotonic_offsets` — 씬 순서대로 source_start 증가

### Implementation (GREEN)

- [ ] T019 [US1] Add `sourceVideo?/sourceStart?/sourceEnd?` to Scene TS interface in `src/video/remotion/src/types.ts`
- [ ] T020 [US1] Edit `src/video/remotion/src/components/SceneWithVideo.tsx` — offset 필드 있으면 `<Video src={staticFile(sourceVideo)} startFrom={Math.round(sourceStart*FPS)} endAt={Math.round(sourceEnd*FPS)} />`, 없으면 기존 `<Video src={staticFile(videoFile)} />`
- [ ] T021 [US1] Edit `src/video/renderer.py` — `script.scenes` 순회하며 `scene.source_video` 가 not None 이면 그 파일을 `public/` 로 복사 (중복 복사 방지: 이미 존재하면 스킵), temp_files 목록에 추가
- [ ] T022 [US1] Edit `app/api/generate/route.ts` NATV cut 루프 (현 `mode === "natv_clip"` 분기 내 Python 스니펫) — 씬 cut 생성 후 `ShortsScript.load` → 각 씬 `source_video = natv_video`, `source_start = ns`, `source_end = ne` 설정 → `script.save`
- [ ] T023 [US1] Extract NATV cut loop Python 스니펫을 순수 함수로 `src/dem_shorts/editor/natv_cut_loop.py::annotate_scenes_with_offsets(script, timings, natv_video, clip_start, clip_end)` 로 추출 (단위 테스트 용이)
- [ ] T024 [US1] Run pytest `tests/test_renderer.py tests/dem_shorts/test_natv_cut_loop.py` — 6 pass
- [ ] T025 [US1] E2E verify: `https://www.youtube.com/watch?v=AU5Ymu6--Ao` 로 NATV 영상 생성 → 결과 script JSON 에 offset 필드 존재 확인 → `/api/rerender` 결과 MP4 프레임 육안 검증

**Checkpoint**: 렌더 파이프라인이 offset 를 이해. US2 에서 UI 로 offset 수정 가능.

---

## Phase 4: User Story 2 — User-facing scene trimming (Priority: P2) 🎯 Primary Feature

**Goal**: 사용자가 NATV 씬 카드에서 "🎬 구간 편집" 버튼을 눌러 듀얼 핸들 슬라이더로 start/end 를 조정하고 저장. 최종 렌더링 시 반영.

**Independent Test**:
1. `/api/scene/trim` 에 invalid/valid payload 각각 보내 상태코드 검증
2. SceneEditor 에 NATV 씬 / non-NATV 씬 각각 렌더해 버튼 노출 여부 검증
3. TrimSlider 단독 페이지에서 드래그 → onChange 콜백 호출 검증

### Tests (RED)

- [ ] T026 [P] [US2] Failing test `tests/api/test_scene_trim.py::test_rejects_non_natv_scene` — `source_video=None` 인 씬 → 403
- [ ] T027 [P] [US2] Failing test `tests/api/test_scene_trim.py::test_rejects_invalid_range` — `sourceStart >= sourceEnd` → 400
- [ ] T028 [P] [US2] Failing test `tests/api/test_scene_trim.py::test_rejects_end_beyond_source` — `sourceEnd > probe(source).duration` → 400 (ffprobe 가능 시)
- [ ] T029 [P] [US2] Failing test `tests/api/test_scene_trim.py::test_saves_offsets_to_script` — 성공 케이스 JSON 파일 검증
- [ ] T030 [P] [US2] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::renders_video_with_given_src`
- [ ] T031 [P] [US2] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::renders_dual_handles_at_start_end`
- [ ] T032 [P] [US2] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::drag_start_handle_calls_onChange`
- [ ] T033 [P] [US2] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::arrow_keys_move_focused_handle_by_1s`
- [ ] T034 [P] [US2] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::shift_arrow_snaps_to_0_1s`
- [ ] T035 [P] [US2] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::warns_when_selection_shorter_than_tts`
- [ ] T036 [P] [US2] Failing RTL test `app/components/__tests__/SceneEditor.trim.test.tsx::shows_trim_button_only_for_scenes_with_source_video`
- [ ] T037 [P] [US2] Failing RTL test `app/components/__tests__/SceneEditor.trim.test.tsx::saves_trim_via_api_and_updates_local_state`

### Implementation — API (GREEN, backend first)

- [ ] T038 [US2] Create `app/api/scene/trim/route.ts` — POST handler, `scriptPath` / `sceneId` / `sourceStart` / `sourceEnd` 수신, `data/scripts/` allowlist, Scene.source_video null 체크(403), 범위 검증(400), ffprobe duration 체크(있을 때만), JSON read-modify-write, 200 응답 (contract `specs/008-natv-scene-trim/contracts/api-scene-trim.md` 준수)
- [ ] T039 [US2] Create `app/api/download/route.ts` — GET handler, `path` query 받아 `data/natv_clips/*.mp4` allowlist 후 stream. TrimSlider `<video src={...}>` 에서 사용
- [ ] T040 [US2] Run pytest `tests/api/test_scene_trim.py` — 4 pass

### Implementation — UI (GREEN)

- [ ] T041 [US2] Create `app/components/TrimSlider.tsx` — props: `videoSrc, duration, start, end, ttsDurationHint?, onChange, onCommit?`. 내부 구조: `<video>` + 트랙 + 두 개의 `role="slider"` 핸들(`aria-valuemin/max/now/valuetext`). `pointerdown/move/up` 수동 처리, 핸들 drag 시 `video.currentTime=start`. 키보드 ← → 1s, Shift+← → 0.1s
- [ ] T042 [US2] Add "구간만 재생" 버튼 to TrimSlider — `video.play()` + `requestAnimationFrame` 에서 `currentTime >= end` 시 pause
- [ ] T043 [US2] Run `npm run test:ui -- TrimSlider` — 6 pass
- [ ] T044 [US2] Edit `app/components/SceneEditor.tsx` — 씬 카드 렌더 시 `scene.source_video` truthy 면 "🎬 구간 편집" 버튼 추가. 클릭 시 해당 씬 하단에 드로어 펼치고 `<TrimSlider>` 마운트
- [ ] T045 [US2] Wire TrimSlider `onCommit={(s,e) => fetch('/api/scene/trim', {...})}` → 성공 시 로컬 `scenes` state 업데이트 + `setHasChanges(true)`
- [ ] T046 [US2] Pass `scene.source_video` via `/api/download?path=...` to TrimSlider `videoSrc`
- [ ] T047 [US2] Ensure `app/page.tsx` JobResult scene 데이터에 `source_video/start/end` 포함됨 (Phase 3 US1 완료 후 자동). 필요 시 types 보강
- [ ] T048 [US2] Run `npm run test:ui -- SceneEditor.trim` — 2 pass
- [ ] T049 [US2] E2E verify: 실제 NATV 영상 생성 → 씬 3개 구간 편집 → 최종 렌더 → 반영 프레임 확인

**Checkpoint**: 사용자가 브라우저에서 드래그로 구간 조정 가능. MVP 완료.

---

## Phase 5: User Story 3 — UX polish (Priority: P3)

**Goal**: 경고 · 자동 맞춤 · 씬 간 겹침 감지. 실사용 피드백 사이클 단축.

**Independent Test**:
1. 선택 길이 < TTS → 경고 메시지 DOM 존재
2. "TTS에 맞춤" 버튼 클릭 → `end = start + ttsDurationHint` 로 onChange 호출
3. 같은 source_video 씬 2개가 offset 겹칠 때 SceneEditor 리스트 배지 표시

### Tests (RED)

- [ ] T050 [P] [US3] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::warns_when_selection_shorter_than_tts` (이미 T035 와 중복 — T035 와 통합)
- [ ] T051 [P] [US3] Failing RTL test `app/components/__tests__/TrimSlider.test.tsx::fit_to_tts_sets_end_correctly`
- [ ] T052 [P] [US3] Failing RTL test `app/components/__tests__/SceneEditor.trim.test.tsx::detects_overlap_across_scenes_sharing_source_video`

### Implementation (GREEN)

- [ ] T053 [US3] Add "TTS에 맞춤" button to `app/components/TrimSlider.tsx` — click handler: `onChange(start, Math.min(start + ttsDurationHint, duration))`
- [ ] T054 [US3] Add "영상에 맞춤" button — `onChange(Math.max(0, end - ttsDurationHint), end)`
- [ ] T055 [US3] Add warning banner in TrimSlider — selection < ttsDurationHint 시 "⚠️ 영상이 TTS보다 짧음 — 마지막 프레임 고정", > 1.5× 시 "ℹ️ 영상이 TTS보다 N% 김"
- [ ] T056 [US3] Add overlap detection in `app/components/SceneEditor.tsx` — 같은 `source_video` 씬들의 offset 범위 비교해 겹치면 씬 카드에 `⚠️ 겹침` 배지 표시
- [ ] T057 [US3] Run `npm run test:ui` — 전체 ui 테스트 pass
- [ ] T058 [US3] Manual check: 짧은/긴/겹침 시나리오 각각 수동 확인

**Checkpoint**: UX 개선 완료.

---

## Phase 6: Polish & Cross-cutting concerns

**Purpose**: 문서 동기화, 회귀 검증, 커밋/PR.

- [ ] T059 [P] Update `CLAUDE.md` — "Recent Changes" 섹션에 `Scene.source_video/source_start/source_end` 필드 1줄 소개 추가
- [ ] T060 [P] Update `prompt_plan.md` — "TRIM-01 NATV 씬 구간 드래그 트리밍" 섹션을 완료(✅) 로 표시, 완료일 추가
- [ ] T061 [P] Update `docs/plans/TRIM-01_scene_trimming.md` — 구현 중 발견된 편차 반영 (있으면)
- [ ] T062 Run full `python3 -m pytest tests/ -q` — 859 → ≥ 876 (14 신규 + 기존) 확인. 저하 없음
- [ ] T063 Run `npx tsc --noEmit` — 0 errors
- [ ] T064 Run `npm run test:ui` — 전체 UI 테스트 pass
- [ ] T065 Git commit 3단계: (a) Phase 2 foundational (Scene 필드), (b) Phase 3 US1 (rendering + cut loop), (c) Phase 4 US2 + Phase 5 US3 (UI + UX polish)
- [ ] T066 Check completion against `specs/008-natv-scene-trim/plan.md` Exit Criteria 6개

---

## Dependencies & Execution Order

```
Phase 1 (Setup) ─► Phase 2 (Foundational) ─► Phase 3 (US1) ─┬─► Phase 4 (US2) ─► Phase 5 (US3) ─► Phase 6 (Polish)
                                                             │
                                                             └─ (US1 완료 이후 US2/US3 병렬 가능)
```

- **US1 독립**: Phase 2 완료 후 단독 구현 가능. UI 변경 없이 머지 가능 (무해한 리팩토링).
- **US2 의존**: US1 완료 필수. API + UI 컴포넌트는 서로 독립이라 T038(API) / T041(TrimSlider) / T044(SceneEditor) 는 병렬 가능.
- **US3 의존**: US2 완료 필수.

## Parallel Execution Examples

### 세션 A: Foundational 병렬 (Phase 2)
```
T005 T006 T007 T008 [P]  — 4개 테스트 동시 작성 (다른 함수)
   └─► T009 T010 T011 (순차, 같은 파일)
       └─► T012 (검증)
```

### 세션 B: US1 테스트 병렬 (Phase 3)
```
T013 T014 T015 [P]         — renderer.py tests (같은 파일, 순차적이지만 독립적 함수라 가능)
T016 T017 T018 [P]         — natv_cut_loop.py tests (별도 파일)
                           └─► T019 T020 T021 T022 T023 (구현)
                               └─► T024 T025 (검증)
```

### 세션 C: US2 테스트 병렬 (Phase 4)
```
T026~T029 [P]              — API 4 tests (같은 파일, 독립적)
T030~T037 [P]              — UI 8 tests (2개 파일, 전부 독립)
                           └─► T038 T039 T040 (API 구현)
                           └─► T041~T048 (UI 구현, 순차)
                               └─► T049 (E2E)
```

---

## Implementation Strategy

### MVP 정의 (가장 먼저 머지)

**Phase 2 + Phase 3 (US1)** 까지. 외부 동작 변화 없지만 **`SceneWithVideo` 가 offset 필드를 이해**하게 됨. 향후 US2 가 쌓일 기반.

### 단계적 배포

- **PR #1**: Phase 2 + Phase 3 (US1) — "렌더 파이프라인 offset 지원" 리팩토링, 숨겨진 버그 방지
- **PR #2**: Phase 4 (US2) — 실제 트리밍 기능. 사용자 공개
- **PR #3**: Phase 5 (US3) + Phase 6 — 폴리싱 + 문서

### 리스크 헷지

- US1 가 머지되면 기존 사용자 영상 생성에 영향 없음 (offset 필드가 null 이라 기존 경로)
- US2 머지 후에도 다른 모드(image/manual 등) 는 "구간 편집" 버튼 미노출이므로 격리 확실

---

## Validation Checklist

- [x] 모든 태스크가 `- [ ] T### ...` 체크리스트 형식
- [x] User Story 태스크는 [US1]/[US2]/[US3] 라벨
- [x] Setup/Foundational/Polish 는 라벨 없음
- [x] 각 태스크에 파일 경로 명시
- [x] 테스트 태스크가 구현 태스크보다 먼저 (RED → GREEN)
- [x] 독립 테스트 기준이 각 User Story 마다 명시됨
- [x] MVP scope 식별 (US1 = MVP 인프라, US2 = MVP 기능)
- [x] 병렬 실행 가능 작업에 [P] 표기

---

## Total Count

| Phase | Tasks | Tests | Impl | Notes |
|---|---|---|---|---|
| 1 Setup | 4 | 0 | 4 | 대부분 확인만 |
| 2 Foundational | 8 | 4 | 4 | Scene 필드 |
| 3 US1 | 13 | 6 | 7 | offset-aware render |
| 4 US2 | 24 | 12 | 12 | API + TrimSlider + SceneEditor |
| 5 US3 | 9 | 3 | 6 | UX polish |
| 6 Polish | 8 | 0 | 8 | 문서 + 회귀 |
| **Total** | **66** | **25** | **41** | |

**MVP 제안**: US1 (Phase 2 + 3, T001-T025, 25 tasks) — 가시적 변화 없지만 인프라 완비. 그 다음 US2 로 실제 UX 배포.
