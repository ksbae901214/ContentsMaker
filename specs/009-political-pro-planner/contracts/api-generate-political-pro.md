# Contract: POST /api/generate (mode=political_pro)

**Purpose**: 사용자가 선택한 ShortsPlan을 받아 ShortsScript로 변환하고(Phase 1) 검수 완료 후 최종 영상을 생성(Phase 2).

**Spec Mapping**: FR-009 ~ FR-021

---

## Phase 1 — Plan → Script 변환 + 검수 화면 진입

### Request

```http
POST /api/generate
Content-Type: multipart/form-data
```

| 필드 | 값 | 설명 |
|------|-----|------|
| `mode` | `"political_pro"` | 신규 모드 식별자 |
| `stopAfter` | `"analyze"` | 검수 화면 진입을 위해 분석 후 중단 |
| `youtubeUrl` | `<url>` | 원본 URL |
| `videoPath` | `<path>` | Phase 0의 `videoPath` 그대로 전달 |
| `videoDurationSec` | `<float>` | Phase 0의 `videoDurationSec` |
| `selectedPlanIdx` | `0` / `1` / `2` | 사용자가 선택한 plan 인덱스 — FR-010 |
| `plansJson` | `<JSON string>` | `/api/political-pro/plans` 응답의 `plans` 배열 통째 |

### Response (SSE)

```
event: progress
data: {"stage": "convert_script", "message": "📝 스크립트 변환 중...", "expectedSeconds": 5}

event: done
data: {
  "phase": "analyzed",
  "title": "...",
  "emotion": "angry",
  "duration": 54,
  "scriptPath": "/.../data/scripts/20260513_...json",
  "scenes": [ ... ],
  "sourceType": "political_pro",
  "videoPath": "...",
  "clipStartSec": 45.0,
  "clipEndSec": 75.0
}
```

---

## Phase 2 — 검수 완료 후 영상 생성

### Request

```http
POST /api/generate
Content-Type: multipart/form-data
```

| 필드 | 값 | 설명 |
|------|-----|------|
| `mode` | `"script"` | 기존 분기 재사용 |
| `scriptPath` | `<path>` | Phase 1에서 받은 경로 (사용자 검수로 수정된 상태) |
| `politicalProMeta` | `<JSON string>` | `{"videoPath": "...", "clipStartSec": 45.0, "clipEndSec": 75.0, "youtubeUrl": "..."}` — 영상 클립 cut에 필요 |
| `useBgm` | `"on" / "off"` | 기존 BGM 토글 |
| `useTransitions` | `"on" / "off"` | 기존 트랜지션 토글 |
| `useSfx` | `"on" / "off"` | 기존 SFX 토글 |
| `dryRun` | `"true" / "false"` | 기존 드라이런 토글 |

### Response (SSE — Phase 2)

```
event: progress
data: {"stage": "scene_clip_cut", "message": "✂️ 씬 클립 분할 (9:16)", "expectedSeconds": 30}

event: progress
data: {"stage": "gemini_tts", "message": "🎙️ Gemini Charon 음성 합성", "expectedSeconds": 20}

event: progress
data: {"stage": "remotion_render", "message": "🎬 Remotion 렌더링", "expectedSeconds": 60}

event: done
data: {
  "phase": "rendered",
  "videoPath": "/.../data/outputs/20260513_...mp4",
  "thumbnailPath": "/.../data/outputs/20260513_....thumb.png",
  "sizeMb": 4.2,
  "durationSec": 54
}
```

---

## Error 케이스 (Phase 2)

| Code | `error` | 조건 | FR |
|------|---------|------|----|
| 422 | `tts_failed` | Gemini TTS API 호출 실패 또는 키 없음 | FR-019 |
| 422 | `clip_cut_failed` | ffmpeg cut/scale 실패 | spec Edge Case |
| 500 | `render_failed` | Remotion 렌더 실패 | spec Edge Case |

---

## 안전 가드 (FR-020, FR-021)

- 응답 본문에 `autoUpload: false` 명시 — 자동 업로드 차단.
- UI 단에서 결과 화면에 "출력은 자동 생성 결과이며 게시 전 사용자 검수가 필요합니다" 문구 렌더(컴포넌트 책임).

---

## Acceptance Tests

| 테스트 | 검증 항목 |
|--------|-----------|
| `T1: plan to script` | selectedPlanIdx=0 + plansJson → 200, phase=analyzed, scenes.length>=1 |
| `T2: script to video` | 검수 완료 scriptPath + politicalProMeta → 200, phase=rendered, videoPath exists |
| `T3: TTS key missing` | GEMINI_API_KEY 미설정 → 422 tts_failed (영상 생성 차단) |
| `T4: clip out of range` | clipEndSec > videoDurationSec → 자동 클램프 후 정상 진행 — FR-013 |
| `T5: scene > 5s` | Plan에 7초 narration → script 변환 시 자동 5초+2초 2씬 분할 — FR-012 |
| `T6: no auto upload` | 응답 본문에 `autoUpload: false` 포함, YouTube/TikTok API 호출 부재 — FR-020 |
