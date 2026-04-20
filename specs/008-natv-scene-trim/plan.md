# Implementation Plan: NATV 씬 구간 드래그 트리밍 (TRIM-01)

**Branch**: `008-natv-scene-trim` (계획 · 미생성) | **Date**: 2026-04-20 | **Source**: `docs/plans/TRIM-01_scene_trimming.md`
**Input**: `docs/plans/TRIM-01_scene_trimming.md` (비공식 계획을 speckit 양식으로 포팅)

## Summary

NATV(국회방송) YouTube 소스로 생성된 쇼츠의 **각 씬 영상 구간을 UI에서 드래그로 조정** 가능하게 한다. 파일을 다시 인코딩하지 않고 **Remotion `<Video startFrom endAt>`** 와 `Scene.source_video/source_start/source_end` 메타데이터만으로 해결한다.

**핵심 기술 선택**: 재인코딩 회피 → 오프셋 메타데이터 + Remotion 재생시 트리밍. 씬 split/merge 시 오프셋 자동 승계.

**적용 범위**: NATV 클립 모드 한정. image / manual / url / topic / political / video 모드는 현재 동작 그대로.

## Technical Context

**Language/Version**: Python 3.11+ (백엔드 배치·파이프라인), TypeScript 5+ / React (Next.js 16 UI), TypeScript / React (Remotion 렌더)
**Primary Dependencies**:
- Python: 기존 `src/analyzer/script_models.py` 프로즌 데이터클래스, `ffmpeg` CLI (already in use)
- Remotion `<Video startFrom endAt>` — 프레임 단위 offset 재생
- Next.js 16 App Router (API route + Client Component)
- UI: Tailwind CSS, 외부 슬라이더 라이브러리 없음 (직접 구현)

**Storage**:
- 스크립트 JSON (`data/scripts/*.json`) — 씬별 `source_video`, `source_start`, `source_end` 필드
- 원본 소스 파일 (`data/natv_clips/*.mp4`) — 보존 필수 (offset 해석 기준)

**Testing**:
- Python: pytest (기존 859 passed 기준 + 17 신규)
- TypeScript: React Testing Library (`TrimSlider`, `SceneEditor.trim` 각각 단위 테스트)
- E2E: 실제 YouTube URL (`https://www.youtube.com/watch?v=AU5Ymu6--Ao`) 수동 검증

**Target Platform**: macOS / Linux 로컬 (Next.js dev server + Python 3.10+)
**Project Type**: Web application — Python backend (pipeline) + Next.js frontend + Remotion 렌더 컴포넌트
**Performance Goals**:
- 트리밍 저장 P95 < 200ms (스크립트 JSON write)
- 슬라이더 drag 시 프리뷰 시크 지연 < 50ms
- 최종 렌더는 기존 대비 차이 없음 (ffmpeg 재인코딩 추가 없음)

**Constraints**:
- **제로 비용**: 유료 API / SaaS 도입 금지 (constitution I)
- **파일 비파괴**: 사전 cut 파일 제거하지 않음 (프리뷰 캐시 + 폴백)
- **후방 호환**: offset 없는 기존 스크립트는 기존 렌더 경로 유지
- **다른 모드 무영향**: 체크 `scene.source_video is not None`

**Scale/Scope**:
- 한 영상 당 씬 3~15개
- 원본 영상 최대 10분 (600초)
- 트리밍 핸들 조작 빈도: 씬당 2~5회 조정

## Constitution Check

*GATE: Phase 0 research 이전 필수 통과.*

| 원칙 | 체크 | 메모 |
|---|---|---|
| I. Zero-Cost Pipeline | ✅ 통과 | 외부 API 도입 없음. 기존 ffmpeg / Remotion 재사용 |
| II. Pipeline Integrity | ✅ 통과 | 오프셋 필드는 JSON 계약 확장, 기존 단계 비파괴 |
| III. TDD (각 Phase RED→GREEN) | ✅ 통과 | 17개 신규 테스트 계획 |
| IV. Surgical Changes | ✅ 통과 | Scene 필드 3개 추가, 렌더 분기 1곳 |
| V. Evidence-Based Completion | ✅ 통과 | E2E 실제 URL 테스트 의무화 |
| VI. Immutability | ✅ 통과 | frozen dataclass 유지, 신규 필드 Optional |
| VII. Test Video Generation | ✅ 통과 | Phase 2 / 5 완료 시 실영상 생성 + 육안 검증 |

**Gate 결과**: 모든 원칙 통과. Phase 0 research 진행 가능.

## Project Structure

### Documentation (this feature)

```text
specs/008-natv-scene-trim/
├── plan.md              # This file (/speckit.plan 출력)
├── research.md          # Phase 0 — 대안 조사 결과
├── data-model.md        # Phase 1 — Scene 확장 필드 계약
├── quickstart.md        # Phase 1 — E2E 실행 가이드
├── contracts/
│   └── api-scene-trim.md   # /api/scene/trim 계약
└── tasks.md             # Phase 2 — /speckit.tasks 출력 (이 커맨드에선 생성 안 함)
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   └── script_models.py        # Scene 에 source_video/start/end 추가 (Phase 1)
├── video/
│   ├── renderer.py             # 원본+offset 경로 분기 (Phase 1)
│   └── remotion/src/
│       ├── components/
│       │   └── SceneWithVideo.tsx   # <Video startFrom endAt> 분기
│       └── types.ts                 # Scene TS 인터페이스 확장

app/
├── api/
│   ├── generate/route.ts       # NATV cut 루프 — offset 기록 (Phase 2)
│   └── scene/
│       ├── trim/route.ts       # 신규 POST /api/scene/trim (Phase 3)
│       └── download/route.ts   # 신규 — 안전 파일 서빙 (Phase 5)
├── components/
│   ├── TrimSlider.tsx          # 신규 듀얼 핸들 슬라이더 (Phase 4)
│   └── SceneEditor.tsx         # "구간 편집" 버튼 + 드로어 (Phase 5)
└── page.tsx                    # (수정 없음 — 씬 데이터만 전달)

tests/
├── test_script_models_trim.py  # Phase 1 — 4 tests
├── test_renderer.py            # Phase 1 — 3 tests 추가
├── dem_shorts/
│   └── test_natv_cut_loop.py   # Phase 2 — 3 tests
└── api/
    └── test_scene_trim.py      # Phase 3 — 4 tests

app/components/__tests__/
├── TrimSlider.test.tsx         # Phase 4 — 6 tests (React Testing Library)
└── SceneEditor.trim.test.tsx   # Phase 5 — 2 tests

docs/plans/
└── TRIM-01_scene_trimming.md   # 원본 상세 기획 (이미 작성됨)
```

**Structure Decision**: **Option 2 (Web application)** — `src/` 가 Python 백엔드 + Remotion 렌더 컴포넌트, `app/` 가 Next.js frontend. 이 레포의 기존 관습을 그대로 따른다.

## Phase 0 — Outline & Research

### 해소 대상

기술 컨텍스트에 NEEDS CLARIFICATION 없음. 남은 조사 주제는 "대안 검토"뿐이며 모두 `research.md` 에 기록.

### Research Tasks

1. **R-1** Vrew / CapCut / Descript / Premiere 트리밍 UX 비교 → 우리 모델 적합성
2. **R-2** Remotion `<Video startFrom endAt>` 프레임 정확도 · VFR 대응 확인
3. **R-3** 듀얼 레인지 슬라이더 접근성 패턴 (WAI-ARIA dual-thumb slider)
4. **R-4** 씬 split/merge 시 오프셋 승계 알고리즘

**Output**: `specs/008-natv-scene-trim/research.md`

## Phase 1 — Design & Contracts

### Data Model (요약)

`Scene` dataclass 에 3 필드 추가 (모두 Optional, 후방 호환):
- `source_video: str | None` — 원본 MP4 경로
- `source_start: float | None` — 원본에서의 시작(초)
- `source_end: float | None` — 원본에서의 끝(초)

직렬화 규칙: `None` 이면 JSON 키 생략, camelCase / snake_case 양방향 허용. 상세: `data-model.md`.

### API Contract

`POST /api/scene/trim` — 상세: `contracts/api-scene-trim.md`

| 상태 | 조건 |
|---|---|
| 200 | 성공, 씬 JSON 업데이트 |
| 400 | `sourceStart >= sourceEnd`, 음수, 원본 길이 초과 |
| 403 | `source_video` 없는 씬 (non-NATV) |
| 404 | 해당 sceneId 없음 |

### Quickstart

1. dev server 기동 (`npm run dev`, Python venv)
2. NATV URL 로 영상 1회 생성
3. SceneEditor 에서 씬 3개 구간 편집
4. "최종 렌더링" → 결과 MP4 육안 확인
- 상세: `quickstart.md`

### Phase 분할 (요약)

| Phase | 산출물 | 테스트 | 시간 |
|---|---|---|---|
| 1. Scene 필드 + 렌더러 | `script_models.py`, `SceneWithVideo.tsx`, `renderer.py` | 7 tests | 3-4h |
| 2. NATV cut 루프 리팩터 | `/api/generate/route.ts` NATV 분기 | 3 tests | 2h |
| 3. `/api/scene/trim` | 신규 라우트 | 4 tests | 1.5h |
| 4. TrimSlider 컴포넌트 | `TrimSlider.tsx` | 6 tests (RTL) | 4-5h |
| 5. SceneEditor 통합 | `SceneEditor.tsx`, `/api/download` | 2 tests (RTL) | 3h |
| 6. UX 보강 | 경고·자동맞춤·스냅 | 3 tests | 2-3h |
| **합계** | | **25 tests** | **15.5-18.5h** |

### Agent Context Update

Phase 1 완료 시 `.specify/scripts/bash/update-agent-context.sh claude` 실행 → `CLAUDE.md` 에 `Scene.source_video/source_start/source_end` 필드 1줄 소개 추가.

## Complexity Tracking

> Constitution 위반 없음 — 표 비움.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | — |

## Risks & Mitigations

| 리스크 | 영향 | 완화 |
|---|---|---|
| Remotion `<Video startFrom>` 프레임 정확도 | LOW | 기존 기능에서 검증됨 (dem-shorts 리그레션 없음) |
| 원본 파일 삭제 시 씬 복구 불가 | MED | Phase 2 에서 cut 파일도 보조로 유지 (이중 안전망) |
| 씬 split/merge 시 offset 승계 | MED | Phase 1 에서 `scene_split` 시간 비율 분할 포함 |
| 영상 < TTS 케이스 UX 혼란 | MED | Phase 6 경고 + "자동 맞춤" 버튼 |
| `/api/download` 경로 트래버설 | LOW | `resolve()` 후 `data/natv_clips/` allowlist |

## Exit Criteria

- ✅ 25 신규 테스트 전부 통과
- ✅ 전체 pytest 저하 없음 (859 → ≥ 859)
- ✅ E2E: `https://www.youtube.com/watch?v=AU5Ymu6--Ao` → 씬 3개 트리밍 → 최종 렌더 → 육안 확인
- ✅ 타 모드(image / manual / url / topic / political / video) 회귀 없음
- ✅ `prompt_plan.md` 완료 체크
- ✅ CLAUDE.md 에 `source_video/start/end` 필드 1줄 소개

## Hand-off

| 다음 | 커맨드 |
|---|---|
| Phase 단위 태스크 분해 | `/speckit.tasks` |
| 도메인별 체크리스트 | `/speckit.checklist` |
| Phase 1 자동 구현 착수 | `/auto` |
