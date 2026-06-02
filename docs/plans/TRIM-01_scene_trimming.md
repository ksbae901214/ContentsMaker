# TRIM-01 · NATV 씬 구간 드래그 트리밍

> **상태**: 계획 확정 (2026-04-20)
> **범위**: NATV 클립 모드 전용. 다른 모드(image/manual/url/topic/political/video)는 무영향.
> **총 복잡도**: MEDIUM · 12-16h
> **관련 파일**: `src/analyzer/script_models.py`, `src/video/remotion/src/components/SceneWithVideo.tsx`, `app/api/generate/route.ts`, `app/api/scene/trim/route.ts`(신규), `app/components/TrimSlider.tsx`(신규), `app/components/SceneEditor.tsx`

---

## 개요

Vrew 스타일 **듀얼 핸들 프로그레스바**로 씬 영상의 앞/뒤 경계를 사용자가 직접 조정. 파일을 다시 자르지 않고 **Remotion `<Video startFrom endAt>`** + 오프셋 메타데이터로 해결해 저장·지연 비용을 최소화.

```
    0:00 ━━━■═══════════════■━━━━━━ 3:30      (원본 전체 길이)
              ↑ in          ↑ out
           선택 구간 0:45 — 1:08 (23초)
```

---

## 데이터 모델

### 새 필드 (Scene dataclass)

```python
source_video: str | None      # 원본 파일 경로 (씬 비디오 풀 소스)
source_start: float | None    # 초 — 원본에서의 시작
source_end:   float | None    # 초 — 원본에서의 끝
```

- 모두 Optional. 기존 스크립트와 후방 호환.
- NATV 모드에서만 채워짐. 다른 모드는 `None` 유지 → 기존 `scene_videos` 경로 그대로.

### 렌더링 분기 (`SceneWithVideo.tsx`)

```tsx
{scene.sourceStart !== undefined && scene.sourceEnd !== undefined ? (
  <Video
    src={staticFile(scene.sourceVideo)}
    startFrom={Math.round(scene.sourceStart * FPS)}
    endAt={Math.round(scene.sourceEnd * FPS)}
  />
) : (
  <Video src={staticFile(videoFile)} />  // 기존 경로
)}
```

Remotion이 재인코딩 없이 오프셋만큼 잘라 재생 → 트리밍 조정이 즉시 반영됨.

---

## Phase 1 — 백엔드: Scene 필드 + 렌더 파이프라인

### 목표
`Scene`에 3개 필드 추가, 직렬화·역직렬화, Remotion 컴포넌트에서 offset 재생.

### 작업 항목

| # | 파일 | 변경 |
|---|---|---|
| 1.1 | `src/analyzer/script_models.py` | `Scene`에 `source_video`, `source_start`, `source_end` Optional 필드 추가 |
| 1.2 | 동 파일 | `to_dict()` — 필드가 `None`이 아니면 직렬화에 포함 |
| 1.3 | 동 파일 | `from_dict()` — snake_case + camelCase 둘 다 허용 |
| 1.4 | `src/video/renderer.py` `_convert_to_camel_case` | 자동으로 sourceVideo/sourceStart/sourceEnd 변환됨 — 확인만 |
| 1.5 | `src/video/remotion/src/types.ts` | `Scene` TS 인터페이스에 `sourceVideo?/sourceStart?/sourceEnd?` 추가 |
| 1.6 | `src/video/remotion/src/components/SceneWithVideo.tsx` | offset 필드 존재 시 `startFrom/endAt` 사용하는 분기 |
| 1.7 | `src/video/renderer.py` | `source_video` 파일을 public/ 으로 복사 (sceneVideos 복사 로직과 동일 패턴) |

### 테스트 (TDD, 7개)

**tests/test_script_models_trim.py 신규**
- `test_scene_roundtrip_with_source_offsets`
- `test_scene_roundtrip_without_source_offsets` (후방 호환)
- `test_scene_from_dict_accepts_camelcase`
- `test_scene_to_dict_omits_none_offsets`

**tests/test_renderer.py 추가**
- `test_source_video_copied_to_public` — offset 씬의 `source_video`가 public/로 복사되는지
- `test_renderer_prefers_offsets_over_scene_videos` — 둘 다 있을 때 offset 우선
- `test_renderer_falls_back_to_scene_videos_when_no_offsets` — 기존 동작 보존

### 완료 조건
- 모든 테스트 통과
- `data/scripts/e2e_rerender_test.json`에 offset 수동 추가 → `/api/rerender` 호출 → 영상이 offset 범위만 보이는지 육안 확인

### 예상 소요: 3-4h

---

## Phase 2 — NATV cut 루프 리팩터

### 목표
`/api/generate` NATV 분할 루프가 **원본 + offset**을 기록. 사전 cut 파일은 프리뷰 캐시로만.

### 작업 항목

| # | 파일 | 변경 |
|---|---|---|
| 2.1 | `app/api/generate/route.ts` NATV 분할 루프 | `cut_segment` 호출은 유지(프리뷰), 추가로 스크립트 JSON의 각 씬에 `source_video=natv_video`, `source_start=ns`, `source_end=ne` 기록 |
| 2.2 | 동 루프 | Python 스니펫에서 `ShortsScript`를 load/modify/save 하는 로직 추가 |
| 2.3 | `/api/rerender` | `scene_videos` 대신 `source_video` 경로가 `data/natv_clips/` 허용되는지 재확인 (이미 OK) |

### 테스트 (3개)

**tests/dem_shorts/test_natv_cut_loop.py 신규** — API 통합 대신 파이썬 함수 형태로 추출해 단위 테스트
- `test_natv_cut_records_source_offsets` — 분할 후 각 씬에 source_video/start/end 기록 확인
- `test_natv_cut_preserves_existing_fields` — 다른 씬 필드 훼손되지 않음
- `test_natv_cut_monotonic_offsets` — scene 순서대로 start 증가

### 완료 조건
- NATV 모드로 영상 생성 → 결과 스크립트 JSON 확인 → 모든 씬에 offset 필드 존재
- `/api/rerender`가 offset 경로로 렌더

### 예상 소요: 2h

---

## Phase 3 — `/api/scene/trim` 엔드포인트

### 목표
사용자가 슬라이더로 조정한 offset을 스크립트에 저장.

### 작업 항목

| # | 파일 | 변경 |
|---|---|---|
| 3.1 | `app/api/scene/trim/route.ts` 신규 | POST: `{scriptPath, sceneId, sourceStart, sourceEnd}` 수신 |
| 3.2 | 동 파일 | 경로 allowlist (`data/scripts/`), sceneId 존재 확인 |
| 3.3 | 동 파일 | 유효성: `0 ≤ start < end`, 기존 `source_video`가 있어야 수락 (NATV 씬만) |
| 3.4 | 동 파일 | ffprobe로 원본 duration 확인해 `end <= duration` 검증 (선택) |
| 3.5 | 동 파일 | 스크립트 JSON 읽고 해당 씬 필드 업데이트 후 저장 |

### 테스트 (4개)

**tests/api/test_scene_trim.py 신규** (Python + fastapi-style 또는 라우트 수동 호출)
- `test_rejects_non_natv_scene` — source_video 없는 씬은 403
- `test_rejects_invalid_range` — start ≥ end 는 400
- `test_rejects_end_beyond_source` — end > duration 은 400 (ffprobe 가능 시)
- `test_saves_offsets_to_script` — 성공 케이스 파일 검증

### 응답 형식

```json
{
  "success": true,
  "scene": { "id": 3, "source_start": 1.2, "source_end": 5.8 }
}
```

### 예상 소요: 1.5h

---

## Phase 4 — TrimSlider 컴포넌트

### 목표
외부 의존성 없이 듀얼 핸들 range + 프리뷰 제공.

### 컴포넌트 계약

```tsx
interface TrimSliderProps {
  videoSrc: string;              // /api/download?path=... 다운로드 URL
  duration: number;              // 원본 전체 길이(초)
  start: number;                 // 현재 in 포인트
  end: number;                   // 현재 out 포인트
  ttsDurationHint?: number;      // TTS 길이 (경고 표시용)
  onChange: (s: number, e: number) => void;
  onCommit?: (s: number, e: number) => void;   // drag 끝 시
}
```

### UI 구성

```
┌──────────────────────────────────────────┐
│ [ <video controls> ]                     │  <- HTML <video>
│                                          │
│  0:00 ━━━■════════════■━━━━━━ 3:30       │  <- dual-handle track
│           ↑             ↑
│           핸들 A         핸들 B
│ ▶︎ 구간만 재생   [ 리셋 ]   [ 자동 맞춤 ]  │
│ 23초 선택됨 (TTS: 4.2초) ⚠️ 영상이 김    │
└──────────────────────────────────────────┘
```

### 구현 세부

- **핸들 드래그**: `pointerdown` → `pointermove` → `pointerup` 수동 처리 (range input 2개를 겹쳐 놓는 방식은 핸들 구분이 어려움)
- **스냅**: Shift 키 누르면 0.1s 단위, 기본 1s
- **키보드**: 핸들 포커스 후 ←/→ 로 1s, Shift+←/→ 로 0.1s
- **프리뷰 스크럽**: 핸들 drag 중 `video.currentTime = start` 로 시크 → 시각적 피드백
- **"구간만 재생"**: `video.play()` 후 `requestAnimationFrame`으로 end 도달 시 pause

### 테스트 (6개, React Testing Library)

**app/components/__tests__/TrimSlider.test.tsx 신규**
- `renders video with given src`
- `renders dual handles at start/end positions`
- `dragging start handle calls onChange with new start`
- `keyboard arrow keys move focused handle by 1 second`
- `Shift + arrow snaps to 0.1s`
- `warns when selection shorter than ttsDurationHint`

### 완료 조건
- Storybook 스타일로 단독 페이지 `/trim-preview`에서 수동 스모크
- 접근성: axe-core 경고 0

### 예상 소요: 4-5h

---

## Phase 5 — SceneEditor 통합

### 목표
씬 카드에 "🎬 구간 편집" 버튼 추가, NATV 씬만 노출, TrimSlider 연결.

### 작업 항목

| # | 파일 | 변경 |
|---|---|---|
| 5.1 | `app/components/SceneEditor.tsx` | 씬 카드 렌더 시 `scene.source_video` 존재하면 "🎬 구간 편집" 버튼 표시 |
| 5.2 | 동 파일 | 버튼 클릭 → 드로어 펼치고 `<TrimSlider>` 마운트 |
| 5.3 | 동 파일 | TrimSlider onCommit → `fetch("/api/scene/trim", ...)` → 성공 시 로컬 scenes 업데이트 + `hasChanges=true` |
| 5.4 | `app/api/download/route.ts` (없으면 신규) | `data/natv_clips/*.mp4` 안전 서빙 (path allowlist) |
| 5.5 | `app/page.tsx` | JobResult에 원본 `natv_video` 경로를 넘기거나 각 씬의 `source_video`를 그대로 사용 |

### 테스트 (2개)

**app/components/__tests__/SceneEditor.trim.test.tsx 신규**
- `shows trim button only for scenes with source_video`
- `saves trim via /api/scene/trim and updates local state`

### 완료 조건
- 실제 NATV 영상으로 씬 3개 생성 → 구간 편집 → 최종 렌더링 → 반영 확인
- 다른 모드(image) 씬에는 버튼 노출 안 됨

### 예상 소요: 3h

---

## Phase 6 — UX 보강

### 목표
사용 편의성 개선: 경고, 자동 맞춤, 스냅, 씬 간 겹침 감지.

### 기능

1. **TTS 길이 경고**
   - 선택 길이 < TTS 길이 → "⚠️ 영상이 TTS보다 짧음. 마지막 프레임 고정됨"
   - 선택 길이 > TTS 길이 1.5배 → "ℹ️ 영상이 TTS보다 {N}% 김"

2. **자동 맞춤 버튼**
   - "TTS에 맞춤" — start 유지, `end = start + tts_duration`
   - "영상에 맞춤" — end 유지, `start = max(0, end - tts_duration)`

3. **키보드 스냅**
   - 기본 1초, Shift 0.1초 (Phase 4에서 이미 구현 — 문서화)

4. **씬 간 겹침 경고** (같은 source_video 기준)
   - scene 2 end=10, scene 3 start=8 → "⚠️ Scene 2-3 구간 겹침"
   - SceneEditor 리스트에 배지 표시

### 테스트 (3개)
- `warns when selection shorter than tts`
- `fit-to-tts button sets end correctly`
- `detects overlap across scenes sharing source_video`

### 예상 소요: 2-3h

---

## 리스크 & 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| Remotion `<Video startFrom endAt>` 프레임 정확도 | LOW | 이미 다른 기능에서 검증됨 |
| 원본 파일 삭제 시 씬 복구 불가 | MED | `data/natv_clips/` 보존 정책 문서화 + 사전 cut 파일도 보조로 남김 |
| 씬 split/merge 시 offset 승계 | MED | 현재 scene_split은 text 기준 — 시간 기준으로 마이너 확장 (Phase 5에 포함) |
| 영상 < TTS 케이스 UX 혼란 | MED | Phase 6 경고 문구 + "자동 맞춤" 버튼 |
| `/api/download` 경로 공격 | LOW | resolve 후 allowlist 체크 |

---

## 완료 정의

- ✅ 모든 Phase 테스트 통과 (25개 신규)
- ✅ NATV 영상 E2E: URL → 생성 → 씬 3개 트리밍 → 렌더 → 육안 확인
- ✅ 다른 모드(image, manual) 회귀 없음 (pytest 전체 859+ 유지)
- ✅ `prompt_plan.md` 에 완료 기록
- ✅ CLAUDE.md에 `source_video/start/end` 필드 소개 1줄 추가

---

## 일정 견적

| Phase | 시간 | 누적 |
|---|---|---|
| 1. Scene 필드 + 렌더러 | 3-4h | 3-4h |
| 2. NATV cut 루프 리팩터 | 2h | 5-6h |
| 3. `/api/scene/trim` | 1.5h | 6.5-7.5h |
| 4. TrimSlider | 4-5h | 10.5-12.5h |
| 5. SceneEditor 통합 | 3h | 13.5-15.5h |
| 6. UX 보강 | 2-3h | **15.5-18.5h** |

---

## 착수 순서 (권장)

```
Phase 1 → Phase 2 (백엔드 선행) → Phase 3 (API)
                                      ↓
                              Phase 4 (TrimSlider 단독)
                                      ↓
                              Phase 5 (통합) → Phase 6 (폴리싱)
```

Phase 1-2는 외부 API 의존 없이 격리 가능 → 테스트 밀도 높게. Phase 4는 독립적이라 스토리북 스타일로 병렬 진행 가능.
