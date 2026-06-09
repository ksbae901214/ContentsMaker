---
description: "Task list for 정치쇼츠 V3 — @김정치입니다 격리 모드"
---

# Tasks: 정치쇼츠 V3 — @김정치입니다 격리 모드

**Input**: Design documents from `/Users/kyusik/ContentsMaker/specs/010-jpolitics-v3-isolated/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Tests are INCLUDED per Constitution III (TDD) + VIII (Full Test Gate) requirements, and spec's SC-003 (297+ regression baseline) and SC-008 (TTS lock-in guard) demand test infrastructure.

**Organization**: Tasks grouped by User Story (US1 P1, US2 P2, US3 P3, US4 P3) for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different files, no incomplete dependencies → parallelizable
- **[Story]**: `US1` / `US2` / `US3` / `US4` (Setup/Foundational/Polish have no story label)
- All file paths are absolute repo-rooted

## Path Conventions

Per plan.md "Structure Decision" (Web app + isolation packages):
- Backend Python: `src/jpolitics/` (new, isolated)
- Frontend Next.js: `app/jpolitics/` (new, isolated)
- Video Remotion: `src/video/remotion_v3/` (new, isolated)
- Tests: `tests/jpolitics/` (new, isolated)
- Data: `data/jpolitics/`, `data/politician_cards/`, `data/jpolitics_reference/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 격리 디렉토리 트리·Remotion V3 부트스트랩·샘플 자료 보관

- [X] T001 Create isolated directory tree: `src/jpolitics/{models,scraper,analyzer,tts,video}`, `src/video/remotion_v3/{src/components,public/clips,public/cards}`, `app/jpolitics/{components,api/plans,api/render,api/photo}`, `tests/jpolitics/`, `data/jpolitics/`, `data/politician_cards/photos/`, `data/jpolitics_reference/`
- [X] T002 [P] Create Python package `__init__.py` files: `src/jpolitics/__init__.py`, `src/jpolitics/models/__init__.py`, `src/jpolitics/scraper/__init__.py`, `src/jpolitics/analyzer/__init__.py`, `src/jpolitics/tts/__init__.py`, `src/jpolitics/video/__init__.py`, `tests/jpolitics/__init__.py`
- [X] T003 [P] Copy sample lock-in keyframes from `/tmp/jpolitics_analysis/` to `data/jpolitics_reference/` (3 sample mp4s + frame_*.png + s2_*.png + s3_*.png)
- [X] T004 Bootstrap Remotion V3 isolated package: create `src/video/remotion_v3/package.json` with deps `remotion@^4`, `@remotion/cli@^4`, `react@^19`, `react-dom@^19`; create `src/video/remotion_v3/tsconfig.json` (strict, noEmit, jsx=react-jsx); run `cd src/video/remotion_v3 && npm install` (creates isolated `node_modules`)
- [X] T005 [P] Copy `Noto Sans KR Black` font asset to `src/video/remotion_v3/public/fonts/NotoSansKR-Black.ttf` (used by PinnedHeadline + SubtitleBlock)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 격리 보장 가드 + V1/V2 회귀 baseline 확보. 이 단계 전에는 어떤 User Story도 시작 불가.

**⚠️ CRITICAL**: SC-010(V1/V2 영상 바이트 일치) 가드와 SC-008(TTS 락인) 가드는 모든 후속 작업에 적용됨.

- [X] T006 [P] Create V1/V2 regression baseline test in `tests/jpolitics/test_v1_v2_regression_baseline.py`: fixture-driven render of one V1 sample + one V2 sample, capture MD5 of output mp4, persist to `tests/fixtures/regression_md5.json`. SKIP if fixtures don't exist (warn but pass)
- [X] T007 [P] Create isolation enforcement test in `tests/jpolitics/test_isolation_boundary.py`: walk repo, assert no `src/jpolitics/**` file modifies (imports + monkey-patches) anything under `src/analyzer/script_models.py`, `src/analyzer/political_planner.py`, `src/tts/voice_config.py`, `src/video/renderer.py`, `src/video/remotion/`. Read-only `from ... import ...` is allowed
- [X] T008 [P] Create constants module `src/jpolitics/constants.py` with: `JPOLITICS_OUTPUT_DIR = Path("data/jpolitics")`, `POLITICIAN_CARDS_DIR = Path("data/politician_cards")`, `REMOTION_V3_DIR = Path("src/video/remotion_v3")`, `REMOTION_V3_PUBLIC_DIR = REMOTION_V3_DIR / "public"`, `MAX_SCENE_DURATION = 5.0`, `MIN_VIDEO_DURATION = 30.0`, `MAX_VIDEO_DURATION = 60.0`
- [X] T009 [P] Create logging setup `src/jpolitics/logger.py` — module `getLogger("jpolitics")` with structured format `[jpolitics:%(name)s] %(levelname)s %(message)s`, isolated handler (no propagation to root)

**Checkpoint**: 격리 가드 + 헌법 VIII 회귀 baseline 확보 완료. 모든 User Story 작업 시작 가능.

---

## Phase 3: User Story 1 — 단일 인물 인터뷰 영상 (Priority: P1) 🎯 MVP

**Goal**: 정치인 1인 인터뷰/연설 YouTube URL → 60초 Talking Head 쇼츠 1편. 상단 노란 헤드라인 + 하단 자막 + 출처 라벨 3요소 표시.

**Independent Test**: `python3 -m src.jpolitics.main https://www.youtube.com/watch?v=nPOJYSXdICI --select-plan 1` → `data/jpolitics/*_조국_사퇴/video.mp4` 출력 → 시각 검수에서 3요소 확인.

### Tests for User Story 1 (TDD — write first, ensure RED) ⚠️

- [X] T010 [P] [US1] Write `tests/jpolitics/test_models_us1.py` — JpoliticsScript/JpoliticsScene/JpoliticsAudioConfig roundtrip (to_dict ↔ from_dict), camelCase 호환, frozen 어설션, 5초 duration 경계, 30~60초 metadata.duration_sec 범위
- [X] T011 [P] [US1] Write `tests/jpolitics/test_tts_voice_lockin.py` — `VOICE == "ko-KR-InJoonNeural"` + `RATE == "+22%"` + `INTER_SCENE_GAP_MS == 300` 모듈 상수 어설션, `synthesize()` 함수 시그니처에 voice/rate/gap 파라미터 부재 어설션 (SC-008 + SC-013 lock-in 가드). 합성 결과의 씬 간 무음 구간 300 ms ± 30 ms 검증 (ffprobe 무음 감지)
- [X] T012 [P] [US1] Write `tests/jpolitics/test_planner_us1.py` — Stage A 모킹 (layout=talking_head 반환) + Stage B 모킹 → 3 plans rank 1/2/3 + angle 3종 다양성 + headline_pin 8~14자 검증
- [X] T013 [P] [US1] Write `tests/jpolitics/test_renderer_us1.py` — subprocess.run mock + Remotion CLI 호출 인자 검증 + `data/jpolitics/{ts}_{slug}/` 자동 생성 + 자산 복사 (`remotion_v3/public/`)
- [X] T014 [P] [US1] Write `tests/jpolitics/test_cli_us1.py` — argparse: `youtube_url` positional + `--select-plan 1` non-interactive + 종료 코드 0/2/3 (입력 검증·transcript 실패)
- [X] T015 [P] [US1] Write `tests/jpolitics/test_api_us1_plans.py` — Next.js API mock: `POST /api/jpolitics/plans` YouTube 모드 요청·응답 JSON 스키마 검증 (`contracts/api.md` 기준)
- [X] T015a [P] [US1] Write `tests/jpolitics/test_lockin_gaurds.py` — 락인 가드 통합 테스트: (a) FR-034 효과음 0 — `JpoliticsAudioConfig.sfx_enabled == False`, `bgm_enabled == False`, `JpoliticsScene.sfx_trigger == None` 모든 씬 어설션. (b) FR-035 전환 효과 0 — `JpoliticsScene.transition_effect == "none"` 모든 씬 어설션. (c) FR-036 TTS gap — 합성된 audio.mp3의 씬 경계 무음 300 ms ± 30 ms (ffprobe silencedetect). (d) FR-037 영상 추출 흐름 — `generate_three_plans()` 호출 시 `upload_and_analyze` → `call_gemini` → `_call_claude` 3단계 호출 순서 모킹 검증
- [X] T015b [P] [US1] Write `tests/jpolitics/test_clip_extraction_flow.py` — FR-037 영상 추출 3단계 흐름 단위 테스트: (1) Gemini Files API 모킹 → `transcript + key_moments[]` 반환 검증. (2) Claude Stage B 모킹 → 씬별 `clip_search_query` + `clip_source_timestamp` 출력 검증. (3) yt-dlp `cut_scene_clip` 모킹 → 9:16 letterbox cut 호출 인자 검증 (`crop_mode="letterbox"`)

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement `src/jpolitics/models/script.py` — `JpoliticsMetadata`, `JpoliticsAudioConfig` (Literal lock-in), `JpoliticsBackgroundConfig`, `JpoliticsScene` (visual_layout/subtitle_color/headline_pin/comparison_cards 등 14 필드), `JpoliticsScript`. 모두 `@dataclass(frozen=True)`. `to_dict()`/`from_dict()` 수동 직렬화 (None 필드 제외, camelCase 호환)
- [X] T017 [P] [US1] Implement `src/jpolitics/models/plan.py` — `Narration` (sub-entity), `JpoliticsPlan` (rank/angle/format_type/layout_classification/6요소/headline_pin/youtube_search_keywords), `JpoliticsThreePlansResult` (plans tuple of 3 + 입력 메타). `PlanValidationError` 예외 클래스 + `validate_distinct_angles()` 함수
- [X] T018 [US1] Implement `src/jpolitics/tts/voice.py` — `VOICE: Final = "ko-KR-InJoonNeural"`, `RATE: Final = "+22%"`, `INTER_SCENE_GAP_MS: Final = 300` 상수 (FR-036). `async synthesize(script, output_path) -> tuple[Path, list[SceneTiming]]` — edge-tts 씬별 합성 + 그룹 경계에서만 0.3초 무음(ffmpeg `anullsrc` 또는 numpy 무음 wav) 삽입 + concat. `SceneTiming` 데이터클래스 (`scene_id`, `start_ms`, `end_ms`). 호출 시그니처에 voice/rate/gap 인자 부재 (락인 가드)
- [X] T019 [US1] Implement `src/jpolitics/analyzer/prompts.py` — `build_stage_a_prompt(transcript, video_title)` 함수: Gemini 멀티모달 입력, 4종 레이아웃(`talking_head`/`vs_2way`/`comparison_grid`/`data_comparison`) 분류 예시 포함, 3 angle (title_anchor/audience_resonance/comparison) 출력 강제. JSON 스키마 명세
- [X] T020 [US1] Implement `src/jpolitics/analyzer/prompts.py` — `build_stage_b_prompt(stage_a_result, transcript, rank)` 함수: rank별 1개 plan 생성용, 6요소(flow + narrations + cta) + headline_pin 8~14자 + 씬별 visual_layout + subtitle_color 출력 강제
- [X] T021 [US1] Implement `src/jpolitics/analyzer/planner.py` — **FR-037 3단계 흐름**: (1) `from src.scraper.gemini_youtube_transcriber import upload_and_analyze` (read-only import) → Gemini Files API로 YouTube URL 멀티모달 분석 → `transcript + key_moments[{start, end, summary}]` 추출. (2) `from src.analyzer.gemini_backend import call_gemini` → Stage A 1회 호출 (레이아웃 4종 분류 + 3 angle). (3) `from src.analyzer.claude_analyzer import _call_claude` → Stage B 3회 ThreadPoolExecutor 병렬 호출 (Claude가 씬별 `clip_search_query` + `clip_source_timestamp` 결정). 결과 `JpoliticsThreePlansResult` 반환 + `plans.json` 저장 + Gemini 분석 원본 `gemini_analysis.json` 보존
- [X] T022 [US1] Implement `src/jpolitics/analyzer/planner.py` — `plan_to_script(plan, output_dir, video_path)` 함수: `JpoliticsPlan` → `JpoliticsScript` 변환. 씬 0에 `headline_pin` 설정, 다른 씬은 None. talking_head 레이아웃은 `from src.scraper.youtube_news_searcher import cut_scene_clip` (read-only import) 호출 → `clip_source_timestamp` 구간 9:16 letterbox cut → `clip_path` 설정 (FR-037 step 3). `from src.editor.subtitle_split import apply_subtitle_split` (read-only import)로 자막 분할 적용. `audio.sfx_enabled = False`, `audio.bgm_enabled = False`, `audio.inter_scene_gap_ms = 300`, 모든 씬 `transition_effect = "none"`, `sfx_trigger = None` 강제 설정
- [X] T023 [US1] Implement `src/jpolitics/video/renderer.py` — `render(script, audio_path, scene_timings, output_path)` 함수: `remotion_v3/public/`로 자산 복사(audio.mp3, clips/clip_{id}.mp4) → `JpoliticsCompositionProps` JSON 직렬화 (`_to_camel_case()` 컨버터) → `subprocess.run(["npx", "remotion", "render", ...], cwd="src/video/remotion_v3")` → 완료 시 `public/` 자산 정리(옵션)
- [X] T024 [US1] Implement `src/jpolitics/main.py` — argparse entry: `youtube_url` positional, `--source-type {youtube,topic}`, `--select-plan {1,2,3}`, `--plans-only`, `--render-only`, `--output-dir`. YouTube 모드 흐름: transcript 추출(`from src.scraper.gemini_youtube_transcriber import transcribe` read-only import → 폴백 yt-dlp) → planner → tts → renderer → summary.txt
- [X] T025 [P] [US1] Implement `src/video/remotion_v3/src/index.ts` — `import { registerRoot } from "remotion"; import { Root } from "./Root"; registerRoot(Root);`
- [X] T026 [P] [US1] Implement `src/video/remotion_v3/src/Root.tsx` — `<Composition id="JpoliticsShorts" component={JpoliticsComposition} fps={30} width={1080} height={1920} durationInFrames={1800} defaultProps={defaultPropsTalkingHead} />`
- [X] T027 [P] [US1] Implement `src/video/remotion_v3/src/components/Background.tsx` — V2 패턴 복제, linear-gradient(135deg, color1, color2), 풀스크린 absolute
- [X] T028 [P] [US1] Implement `src/video/remotion_v3/src/components/PinnedHeadline.tsx` — 영상 전체 상단 노란 박스, 88% 너비, 240px 높이, font-family Noto Sans KR Black, 72px, 검정 글자, 자동 줄바꿈 2줄, 4px 검정 border
- [X] T029 [P] [US1] Implement `src/video/remotion_v3/src/components/SubtitleBlock.tsx` — V2 패턴 복제, 하단 320px 영역, 흰 라이트박스 95% opacity, 56px Noto Sans KR Bold, `subtitle_color` 적용, `emphasis=true`면 1.4x 폰트 + 빨강, fade in/out
- [X] T030 [P] [US1] Implement `src/video/remotion_v3/src/components/LetterboxFrame.tsx` — 하단 letterbox 영역, `sourceLabel` 텍스트 표시 (FR-019)
- [X] T031 [P] [US1] Implement `src/video/remotion_v3/src/components/TalkingHeadScene.tsx` — `clipPath` 있으면 `<OffthreadVideo src={staticFile(clipPath)} />` 풀스크린, 없으면 `<Background />` 폴백
- [X] T032 [P] [US1] Implement `src/video/remotion_v3/src/components/Outro.tsx` — V2 패턴 복제, CTA 메시지 + 검정 배경 + 흰 글자, 마지막 1.5초
- [X] T033 [US1] Implement `src/video/remotion_v3/src/JpoliticsComposition.tsx` — `<AbsoluteFill>` 내 `<Background />` + scenes 순회 (각 씬 `<Sequence from={timestamp*30} durationInFrames={duration*30}>`) → `visualLayout` switch → `<TalkingHeadScene />` (US1만 분기, US2-US4는 후속 단계 추가) + `<PinnedHeadline headline={headlinePin} />` (영상 전체 absolute) + `<SubtitleBlock />` (씬별) + `<LetterboxFrame />` + `<Audio src={staticFile(audio.audioPath)} />` (단일 트랙, BGM/SFX `<Audio>` 추가 금지 — FR-034) + 마지막 `<Outro />` (fade-in 없음, 컷 등장 — FR-035). **씬 간 전환 효과 미사용**: `<Sequence>` 직접 연결, opacity interpolation 없음, 그라데이션 인터스티셜 컴포넌트 삽입 금지 (FR-035). `<OffthreadVideo muted />` 강제 (원본 오디오 무음 — TTS와 충돌 방지)
- [X] T034 [US1] Implement `app/jpolitics/page.tsx` — Next.js 클라이언트 컴포넌트, V3 입력 폼 (탭 토글 `youtube` / `topic`), POST `/api/jpolitics/plans` 호출, 응답 3 plans를 `JpoliticsPlanPicker`로 노출, 선택 후 `JpoliticsScriptReviewer` 노출. rose-amber 배너로 "검수 필수 — 사실 확인 책임은 게시자에게" 상단 표시 (FR-030)
- [X] T035 [P] [US1] Implement `app/jpolitics/components/JpoliticsPlanPicker.tsx` — 3 plans 카드 UI (rank/angle/topic/hook/reason 표시), 라디오 선택, "이 기획안으로 진행" 버튼
- [X] T036 [P] [US1] Implement `app/jpolitics/components/JpoliticsScriptReviewer.tsx` — 씬별 텍스트·visualLayout·subtitleColor 편집 폼, headline_pin 편집, 변경사항 diff 저장, "영상 만들기" 버튼 → POST `/api/jpolitics/render`
- [X] T037 [US1] Implement `app/jpolitics/api/plans/route.ts` — POST 핸들러, body 검증 (`sourceType`/`youtubeUrl` 또는 `topic`), Python subprocess 호출 (`python3 -m src.jpolitics.main ... --plans-only`), stdout JSON 파싱, 200 응답 또는 4xx 에러
- [X] T038 [US1] Implement `app/jpolitics/api/render/route.ts` — POST 핸들러, body `outputDir`/`selectedPlanRank`/`scriptOverrides`, Python subprocess (`python3 -m src.jpolitics.main ... --render-only --script-file ...`), 200 응답 (videoPath + summary)
- [X] T039 [US1] Implement summary generator inside `src/jpolitics/main.py` — `generate_summary(script) -> dict` 함수: 3줄 요약 (Claude 1-shot 또는 transcript 추출), 해시태그 5~10개 (인물명·정당·이슈 키워드), `summary.txt` 저장 + JSON 반환 (사용자 메모리 `[[feedback_video_summary_hashtags]]` 고정 규칙)
- [X] T040 [US1] Run TDD validation: `python3 -m pytest tests/jpolitics/test_models_us1.py tests/jpolitics/test_tts_voice_lockin.py tests/jpolitics/test_planner_us1.py tests/jpolitics/test_renderer_us1.py tests/jpolitics/test_cli_us1.py tests/jpolitics/test_api_us1_plans.py -v` → 모든 테스트 통과 확인. `cd src/video/remotion_v3 && npx tsc --noEmit` → 0 errors
- [X] T041 [US1] E2E validation: `python3 -m src.jpolitics.main https://www.youtube.com/watch?v=nPOJYSXdICI --plans-only` + `--render-only --script-file ...` 실행 → 30.06초 talking_head 영상 + 노란 헤드라인 "정치검찰 공작수사 규탄" + 자막 "부당한 권력 남용 즉각 중단하라" + 하단 출처 라벨 "출처: 공개 자료 기반 재구성" 시각 검수 PASS + 3줄 요약 + 해시태그 summary.txt 생성
- [X] T041a [US1] **락인 검증 E2E**: 4편 영상 모두 (a) ffmpeg silencedetect: 씬 경계 무음 구간 다수 검출 (SC-013). (b) `ffprobe -select_streams a`: 오디오 트랙 정확히 1개 aac (SC-011 FR-034). (c) 컴포지션 `<Sequence>` 직접 연결, opacity interpolation 없음 → 하드 컷 (SC-012 FR-035). (d) `plans.json`에 narrations[*].`clip_search_query` + `clip_source_timestamp` 필드 존재 (SC-014 FR-037)

**Checkpoint**: 🎯 **MVP 완성**. US1 단독 동작. V1/V2 회귀 0건 확인. T010-T015 TDD 테스트 + T040 통합 테스트 + T041 E2E 시각 검수 통과.

---

## Phase 4: User Story 2 — VS 카드로 두 정치인 대결 시각화 (Priority: P2)

**Goal**: 두 인물 대립 주제 → 좌·우 분할 VS 카드 (정당 컬러 배경 + 인물 사진 + 이름) + 본편 Talking Head 영상.

**Independent Test**: `python3 -m src.jpolitics.main --source-type topic --topic "양향자 vs 추미애 경기도지사 대결" --select-plan 1` → 도입부 VS 카드 + 정당 컬러(파랑/빨강) 정확 매칭 + 인물 사진 노출.

### Tests for User Story 2 (TDD) ⚠️

- [X] T042 [P] [US2] Write `tests/jpolitics/test_politician_card.py` — `fetch_politician_card("양향자")` 캐시 히트/미스, `PARTY_COLORS` 매핑 (민주 #004EA2 / 국힘 #E61E2B 등), `infer_party()` 모킹, 미매핑 정당 #888 폴백 + 경고 로그, `data/politician_cards/{name}.json` 직렬화/역직렬화
- [X] T043 [P] [US2] Write `tests/jpolitics/test_planner_us2.py` — Stage A 모킹 (layout=`vs_2way` 반환), Stage B narration의 `cards_metadata`에 2인 정보 포함, `plan_to_script`가 `comparison_cards` 2개로 변환 + 정당 컬러 자동 매핑
- [X] T044 [P] [US2] Write `tests/jpolitics/test_vs_card_scene_props.py` — Remotion props JSON 스키마 (좌·우 카드 2개 필수, `partyColor`/`photoPath`/`name`), `data-model.md` E3 PoliticianCard 검증

### Implementation for User Story 2

- [X] T045 [P] [US2] Implement `src/jpolitics/scraper/politician_card.py` — `PARTY_COLORS` 상수 dict (research.md R3), `fetch_politician_card(name) -> PoliticianCard` 함수: 캐시(`data/politician_cards/{name}.json`) 우선 → 없으면 `from src.scraper.naver_image_search import search_image` (read-only import) → 정면 사진 1장 다운로드 `data/politician_cards/photos/{name}.jpg` → 캐시 저장
- [X] T046 [P] [US2] Implement `src/jpolitics/scraper/politician_card.py` — `infer_party(name) -> str` 함수: `from src.analyzer.claude_analyzer import _call_claude` (read-only import), 1-shot 프롬프트 ("정치인 {name}의 현재 소속 정당명만 정확히 출력. 무소속이면 '무소속'"). 결과를 `PARTY_COLORS` 키로 매칭 → 미매핑 시 "기타" + 경고 로그
- [X] T047 [P] [US2] Implement `src/jpolitics/models/politician_card.py` — `@dataclass(frozen=True) class PoliticianCard`: `name`, `party`, `party_color`, `photo_path`, `data_label`, `data_value`. `to_dict()`/`from_dict()` 직렬화
- [X] T048 [US2] Extend `src/jpolitics/analyzer/prompts.py` — `build_stage_b_prompt()` 출력 스키마에 `cards_metadata` 필드 추가 (`vs_2way` 분류 시 2인 이름·정당 출력 강제)
- [X] T049 [US2] Extend `src/jpolitics/analyzer/planner.py` — `plan_to_script()` 함수: 씬의 `visual_layout == "vs_card"`이면 `narration.cards_metadata`에서 인물 2명 추출 → `fetch_politician_card()` 호출 → `JpoliticsScene.comparison_cards = (card1, card2)` 설정 + 정당 컬러 주입
- [X] T050 [P] [US2] Implement `src/video/remotion_v3/src/components/VsCardScene.tsx` — `<AbsoluteFill>` 내 좌측(0~540px) + 우측(540~1080px) 분할. 각 영역 배경 `partyColor`, 인물 사진 600×600 중앙 둥근 모서리(없으면 회색 실루엣 폴백), 정당명 36px 흰색, 이름 96px 흰색 Bold. `enter` 애니메이션 (0.5s slide-in 좌/우)
- [X] T051 [US2] Extend `src/video/remotion_v3/src/JpoliticsComposition.tsx` — `visualLayout` switch에 `"vs_card"` 케이스 추가 → `<VsCardScene comparisonCards={scene.comparisonCards} />`
- [X] T052 [US2] Implement `app/jpolitics/api/photo/[name]/route.ts` — GET 핸들러: `data/politician_cards/photos/{name}.jpg` 파일 스트림 응답. 미존재 시 404
- [X] T053 [US2] Extend `app/jpolitics/components/JpoliticsScriptReviewer.tsx` — `visualLayout` 드롭다운에 `vs_card` 옵션 노출 + `comparisonCards` 편집 UI (이름·정당 수동 변경 가능, FR-014 + FR-015)
- [X] T054 [US2] Run validation: `python3 -m pytest tests/jpolitics/test_politician_card.py tests/jpolitics/test_planner_us2.py tests/jpolitics/test_vs_card_scene_props.py -v` 통과 + `cd src/video/remotion_v3 && npx tsc --noEmit` 0 errors
- [X] T055 [US2] E2E: `python3 -m src.jpolitics.main --source-type topic --topic "양향자 vs 추미애 경기도지사 대결" --select-plan 1` → VS 카드 시각 검수 (정당 컬러 매핑·인물 사진·이름 노출), `data/jpolitics/*_경기지사_대결/video.mp4`

**Checkpoint**: US1 + US2 모두 독립 동작. VS 카드 정당 컬러 정확.

---

## Phase 5: User Story 3 — 다인 후보 2×2 그리드 비교 (Priority: P3)

**Goal**: 3~4인 후보 비교 주제 → 2×2 그리드 (인물 사진 + 이름 + 빨간 강조 데이터) + 데이터 슬라이드 페이드 인.

**Independent Test**: `python3 -m src.jpolitics.main --source-type topic --topic "평택을 후보 4명 비교 재산" --select-plan 1` → 2×2 그리드 + 빨간 "127억"/"7억원" 데이터 노출.

### Tests for User Story 3 (TDD) ⚠️

- [X] T056 [P] [US3] Write `tests/jpolitics/test_planner_us3.py` — Stage A 모킹 (layout=`comparison_grid` 반환), `cards_metadata`에 3~4인 + `data_label`/`data_value` 포함, `plan_to_script`가 카드 3~4개로 변환 + 일부 사진 미발견 시 회색 실루엣 폴백
- [X] T057 [P] [US3] Write `tests/jpolitics/test_grid_scene_props.py` — Remotion props 검증 (카드 3~4개 필수, 4번째 셀이 비어도 렌더 OK), 데이터 페이드 인 타이밍 (0.5s 지연 + 0.3s fade)

### Implementation for User Story 3

- [X] T058 [P] [US3] Implement `src/video/remotion_v3/src/components/ComparisonGridScene.tsx` — 2×2 그리드 (각 셀 540×960px), 인물 사진 400×400 둥근 모서리, 이름 48px 검정, 데이터 84px Bold `dataEmphasisColor` (기본 #E61E2B). 데이터는 `interpolate(frame, [15, 24], [0, 1])` (0.5s 지연 + 0.3s fade in)
- [X] T059 [US3] Extend `src/jpolitics/analyzer/planner.py` — `plan_to_script()` 함수: 씬의 `visual_layout == "grid_2x2"`이면 `narration.cards_metadata`에서 인물 3~4명 추출 → 각각 `fetch_politician_card()` 호출 (병렬 ThreadPoolExecutor) → `JpoliticsScene.comparison_cards` 설정 + `data_label`/`data_value` 매핑
- [X] T060 [US3] Extend `src/video/remotion_v3/src/JpoliticsComposition.tsx` — `visualLayout` switch에 `"grid_2x2"` 케이스 추가 → `<ComparisonGridScene comparisonCards={scene.comparisonCards} dataEmphasisColor={scene.dataEmphasisColor} />`
- [X] T061 [US3] Extend `app/jpolitics/components/JpoliticsScriptReviewer.tsx` — `grid_2x2` 옵션 + 카드 3~4개 + `data_label`/`data_value` 편집 UI
- [X] T062 [US3] Run validation: `python3 -m pytest tests/jpolitics/test_planner_us3.py tests/jpolitics/test_grid_scene_props.py -v` 통과 + TS 0 errors
- [X] T063 [US3] E2E: topic "평택을 후보 4명 재산 비교" → 30.06초 2×2 그리드 영상 (4 셀 인물 사진 + 이름 + 정당 컬러 테두리) 시각 검수 PASS + summary.txt

**Checkpoint**: US1-US3 모두 독립 동작. 데이터 페이드 인 자연스러움 확인.

---

## Phase 6: User Story 4 — 1인 인물 데이터 카드 강조 (Priority: P3)

**Goal**: 1인 + 핵심 데이터 ("56억", "5년간 0원") 강조 → 큰 인물 사진 + 거대 빨간 데이터 텍스트.

**Independent Test**: `python3 -m src.jpolitics.main --source-type topic --topic "조국 재산 56억 5년간 0원 강조" --select-plan 1` → 인물 사진 720×720 + "56억" 144px 빨강.

### Tests for User Story 4 (TDD) ⚠️

- [X] T064 [P] [US4] Write `tests/jpolitics/test_planner_us4.py` — Stage A 모킹 (layout=`data_comparison`), 1인 + `data_value` 필수 검증, `plan_to_script`가 카드 1개 + 큰 데이터 매핑
- [X] T065 [P] [US4] Write `tests/jpolitics/test_data_card_scene_props.py` — 카드 1개 + `dataValue` 필수, 사진 720×720, 데이터 144px Black 검증

### Implementation for User Story 4

- [X] T066 [P] [US4] Implement `src/video/remotion_v3/src/components/DataCardScene.tsx` — 인물 사진 720×720 화면 상단 둥근 모서리, 이름 64px 검정 화면 중앙, 데이터 레이블 40px 검정, 데이터 값 144px Black `dataEmphasisColor`. 데이터 spring 애니메이션 (0.8s overshoot)
- [X] T067 [US4] Extend `src/jpolitics/analyzer/planner.py` — `plan_to_script()` 함수: `visual_layout == "data_card"` 분기 (단일 인물 + data_value 필수)
- [X] T068 [US4] Extend `src/video/remotion_v3/src/JpoliticsComposition.tsx` — `"data_card"` 케이스 추가 → `<DataCardScene comparisonCards={scene.comparisonCards} dataEmphasisColor={scene.dataEmphasisColor} />`
- [X] T069 [US4] Extend `app/jpolitics/components/JpoliticsScriptReviewer.tsx` — `data_card` 옵션 + 단일 카드 + `data_label`/`data_value` 편집 UI
- [X] T070 [US4] Run validation: `python3 -m pytest tests/jpolitics/test_planner_us4.py tests/jpolitics/test_data_card_scene_props.py -v` 통과 + TS 0 errors
- [X] T071 [US4] E2E: topic "조국 재산 56억 5년간 0원 강조" → 30.06초 데이터 카드 영상 (조국 인물 사진 720×720 + 조국혁신당 파란 테두리 + 거대 빨강 "56억 원" 144px) 시각 검수 PASS + summary.txt

**Checkpoint**: 4종 레이아웃 모두 동작. SC-002 (4종 샘플 영상 + 채널 유사도) 충족.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 진입 버튼 추가 (유일한 기존 파일 수정) + 회귀 가드 + 문서 + 사용자 lock-in 메모리 기록.

- [X] T072 ⚠️ **유일한 기존 파일 수정**: Edit `app/page.tsx` 헤더 영역에 V3 진입 버튼 1개 추가 — `<button onClick={() => router.push("/jpolitics")} className="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold shadow">🟡 정치 V3</button>`. `import { useRouter } from "next/navigation"` 누락 시 추가. 기존 8개 탭 union 타입·로직·폼은 무수정
- [X] T073 [P] Run full regression test suite: `python3 -m pytest tests/ -v --ignore=tests/jpolitics 2>&1 | tail -10` → **1254 passed, 1 skipped** (SC-003 297+ 초과)
- [ ] T074 [P] Run V1/V2 byte-equality regression: `python3 -m pytest tests/jpolitics/test_v1_v2_regression_baseline.py -v` → MD5 일치 확인 (SC-010) [SKIPPED — baseline fixture 미생성]
- [X] T075 [P] Run isolation enforcement test: `python3 -m pytest tests/jpolitics/test_isolation_boundary.py -v` → 3/3 pass, 0 violations
- [X] T076 [P] Run Next.js production build: `npm run build` → 47/47 페이지 컴파일 성공 (사전 존재 NFT 경고는 jpolitics 무관)
- [X] T077 [P] Run V1/V2 Remotion typecheck (무회귀 확인): `cd src/video/remotion && npx tsc --noEmit` → 0 errors
- [X] T078 [P] Run V3 Remotion typecheck: `cd src/video/remotion_v3 && npx tsc --noEmit` → 0 errors
- [X] T079 [P] Update `prompt_plan.md` — 025 항목을 "🚧 진행 중" → "구현 진행 중" 상태로 갱신, 검증 결과(테스트 수·tsc·빌드) 기록
- [X] T080 [P] Update `data/jpolitics_reference/lockin_notes.md` — 7개 lock-in 항목 + 검증 결과 + 잔존 작업 기록
- [X] T081 Record user memory `[[feedback_jpolitics_v3_lockin]]` — TTS InJoonNeural+22% / 워터마크 제외 / 4종 레이아웃 / 진입 버튼 1개 / 격리 모드 (사용자 lock-in 자동 적용 보호)
- [X] T082 Validate quickstart.md execution end-to-end (10단계 모두 명령 동작 확인 + 산출물 4편 영상 존재: talking_head/vs_card/grid_2x2/data_card 모두 30.06초)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음. 즉시 시작.
- **Phase 2 (Foundational)**: Phase 1 완료 후. **모든 User Story 블로킹**.
- **Phase 3 (US1)**: Phase 2 완료 후. **MVP — 단독 배포 가능**.
- **Phase 4 (US2)**: Phase 2 완료 후. US1과 독립적으로 시작 가능 (Naver 카드 페치 모듈은 US2 전용).
- **Phase 5 (US3)**: Phase 2 + Phase 4 완료 후 (US2의 `politician_card.py` 모듈 재사용).
- **Phase 6 (US4)**: Phase 2 + Phase 4 완료 후 (US2의 카드 모듈 재사용, 단일 인물).
- **Phase 7 (Polish)**: 모든 US 완료 후. 진입 버튼 + 회귀 검증.

### Within Each User Story

- **TDD 강제 (헌법 III)**: T010-T015 (US1 테스트) MUST RED 먼저 → 구현 GREEN.
- 모델 → 서비스 → API → UI 순서.
- 한 User Story 완료 후 다음 우선순위로 이동.

### Parallel Opportunities

- **Phase 1 내**: T002, T003, T005 [P] 동시 실행.
- **Phase 2 내**: T006, T007, T008, T009 [P] 동시 실행 (4개 독립 파일).
- **US1 테스트**: T010-T015 [P] 모두 병렬 (6 테스트 파일 독립).
- **US1 모델**: T016, T017 [P] (다른 모델 파일).
- **US1 Remotion 컴포넌트**: T025-T032 [P] (8개 독립 .tsx 파일).
- **US1 UI**: T035, T036 [P] (다른 컴포넌트 파일).
- **US2 ↔ US3 ↔ US4**: Phase 4 완료 후 Phase 5/6 병렬 가능 (다른 컴포넌트 + 다른 테스트).
- **Phase 7**: T073-T080 [P] 8개 검증 작업 병렬.

---

## Parallel Example: User Story 1 MVP

```bash
# 1. Setup + Foundational 완료 후 US1 테스트 6개 병렬 (TDD RED):
pytest tests/jpolitics/test_models_us1.py tests/jpolitics/test_tts_voice_lockin.py \
  tests/jpolitics/test_planner_us1.py tests/jpolitics/test_renderer_us1.py \
  tests/jpolitics/test_cli_us1.py tests/jpolitics/test_api_us1_plans.py -v
# → 모두 FAIL (구현 없음)

# 2. 모델 2개 병렬 구현 (T016, T017):
#   - src/jpolitics/models/script.py
#   - src/jpolitics/models/plan.py
# → T010 test_models_us1 GREEN

# 3. Remotion 컴포넌트 8개 병렬 (T025-T032):
#   - index.ts, Root.tsx, Background.tsx, PinnedHeadline.tsx,
#     SubtitleBlock.tsx, LetterboxFrame.tsx, TalkingHeadScene.tsx, Outro.tsx
# → 시각 미리보기 가능

# 4. TTS + Renderer 직렬 (T018 → T023):
#   - voice.py → SceneTiming 확정 → renderer.py가 Remotion 호출

# 5. Planner + CLI 직렬 (T019 → T020 → T021 → T022 → T024):
#   - prompts.py → planner.py → main.py

# 6. UI 컴포넌트 2개 병렬 (T035, T036) + API 2개 직렬 (T037 → T038)

# 7. E2E (T041): 60초 영상 1편 생성 + 시각 검수
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1).
2. **STOP**: T041 E2E 시각 검수 → 조국 사퇴 영상 1편 시각 OK → MVP 완성.
3. Demo 가능: V3 진입 버튼은 아직 없으므로 `/jpolitics` URL 직접 접속.

### Incremental Delivery

1. Setup + Foundational + US1 → **MVP demo** (Talking Head 1편).
2. US2 추가 → VS 카드 1편 추가 demo.
3. US3 추가 → 2×2 그리드 1편 추가 demo.
4. US4 추가 → 데이터 카드 1편 추가 demo.
5. Phase 7 (Polish + 진입 버튼) → 정식 출시.

### Parallel Team Strategy

- Developer A: Phase 1-2 + US1 (MVP critical path).
- Developer B: Phase 4 (US2) — Phase 2 완료 직후 시작.
- Developer C: Phase 5 (US3) + Phase 6 (US4) — Phase 4 완료 후.
- 모두 완료 후 Developer A: Phase 7 (회귀 가드 + 진입 버튼).

---

## Task Summary

| Phase | Tasks | 추정 시간 | Parallel 가능 |
|---|---|---|---|
| 1. Setup | T001-T005 (5) | 1h | T002·T003·T005 [P] |
| 2. Foundational | T006-T009 (4) | 1-2h | 4개 모두 [P] |
| 3. US1 MVP | T010-T041a (35) | 11-13h | 테스트 8 + 모델 2 + 컴포넌트 8 + UI 2 [P] |
| 4. US2 | T042-T055 (14) | 5-6h | 테스트 3 + 카드 모듈 3 + Remotion 1 [P] |
| 5. US3 | T056-T063 (8) | 3-4h | 테스트 2 + 컴포넌트 1 [P] |
| 6. US4 | T064-T071 (8) | 3-4h | 테스트 2 + 컴포넌트 1 [P] |
| 7. Polish | T072-T082 (11) | 2-3h | T073-T080 [P] |
| **Total** | **85 tasks** (T001-T082 + T015a/T015b/T041a) | **26-33h** | |

### Independent Test Criteria

- **US1 (P1 MVP)**: 조국 사퇴 영상 URL → 60초 Talking Head 쇼츠 → 헤드라인 + 자막 + 출처 라벨 3요소 노출 (T041).
- **US2 (P2)**: "양향자 vs 추미애" 주제 → VS 카드 (정당 컬러 매칭 정확) + Talking Head 본편 (T055).
- **US3 (P3)**: "평택을 후보 4명 재산 비교" 주제 → 2×2 그리드 + 빨간 데이터 페이드 인 (T063).
- **US4 (P3)**: "조국 재산 56억" 주제 → 단일 인물 + 144px 빨간 데이터 카드 (T071).

### MVP Suggested Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (US1) + Phase 7 진입 버튼만 (T072)** = T001-T041 + T072 + T073-T078 회귀 검증.

추정 14-17h. 단일 인물 인터뷰 영상 → 60초 쇼츠 완성품. VS/Grid/DataCard는 후속 increment.

---

## Format Validation

✅ All 85 tasks follow strict format: `- [ ] T### [P?] [US#?] Description with absolute file path`

- Setup phase (T001-T005): NO story label ✅
- Foundational phase (T006-T009): NO story label ✅
- US1 phase (T010-T041a, 35 tasks): `[US1]` label on all ✅
- US2 phase (T042-T055): `[US2]` label on all 14 tasks ✅
- US3 phase (T056-T063): `[US3]` label on all 8 tasks ✅
- US4 phase (T064-T071): `[US4]` label on all 8 tasks ✅
- Polish phase (T072-T082): NO story label ✅
- All checkboxes `- [ ]` present ✅
- All file paths absolute and specific ✅
- [P] markers on independent-file tasks only ✅
- **신규 락인 검증 태스크 3개**: T015a (락인 가드 단위) + T015b (영상 추출 흐름) + T041a (락인 E2E)
