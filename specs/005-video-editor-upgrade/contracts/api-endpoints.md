# API Contracts: 영상 제작/편집 기능 고도화

## Phase 1 API

### POST /api/scene/split
씬을 두 개로 분할한다.

**Request**: `{ scene_id: number, split_position: number, script_path: string }`
- split_position: 텍스트에서 분할할 문자 인덱스

**Response**: `{ scenes: Scene[], script_path: string }`

### POST /api/scene/merge
인접한 두 씬을 병합한다.

**Request**: `{ scene_id_1: number, scene_id_2: number, script_path: string }`

**Response**: `{ scene: Scene, script_path: string }`

### PUT /api/scene/style
씬의 자막 스타일을 변경한다.

**Request**: `{ scene_id: number, subtitle_style: SubtitleStyle, script_path: string }`

**Response**: `{ scene: Scene }`

### PUT /api/scene/transition
씬의 트랜지션을 설정한다.

**Request**: `{ scene_id: number, transition: TransitionConfig, script_path: string }`

**Response**: `{ scene: Scene }`

## Phase 2 API

### POST /api/tts/preview
음성 미리듣기를 생성한다.

**Request**: `{ voice: string, text?: string }`
- text 미지정 시 기본 샘플 문장 사용

**Response**: `{ audio_url: string, duration_ms: number }`

### POST /api/video-gen
AI 영상 클립을 생성한다. SSE 스트리밍으로 진행 상태를 전달한다.

**Request**: `{ scene_id: number, prompt: string, source_image?: string, resolution: "720p"|"1080p", duration: number }`

**Response (SSE)**: `{ event: "progress"|"complete"|"error", data: { scene_id, status, progress?, path?, error? } }`

## Phase 3 API

### POST /api/project/save
프로젝트를 저장한다.

**Request**: `{ project: Project }`

**Response**: `{ project_id: string, saved_at: string }`

### GET /api/project/load?id={project_id}
프로젝트를 불러온다.

**Response**: `{ project: Project }`

### GET /api/project/list
프로젝트 목록을 조회한다.

**Response**: `{ projects: { id, name, updated_at, thumbnail? }[] }`

### DELETE /api/project/delete?id={project_id}
프로젝트를 삭제한다.

**Response**: `{ deleted: true }`

## Phase 4 API

### POST /api/batch
일괄 생성을 시작한다.

**Request**: `{ items: { input_type, input_data }[], template?: string }`

**Response (SSE)**: `{ event: "job_update"|"complete", data: { job_id, status, progress? } }`

### POST /api/translate
자막을 번역한다.

**Request**: `{ scenes: { id, text }[], target_language: "en"|"ja" }`

**Response**: `{ translations: { scene_id, translated_text }[] }`
