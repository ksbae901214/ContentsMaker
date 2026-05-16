# API Contract: POST /api/generate (Phase 6 확장)

## Request

**Content-Type**: `multipart/form-data`

### 기존 필드 (변경 없음)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| mode | string | yes | `"image"` \| `"manual"` \| `"url"` \| `"topic"` |
| bgm | string | no | `"on"` \| `"off"` |
| yt | string | no | `"on"` \| `"off"` |
| tt | string | no | `"on"` \| `"off"` |
| dryRun | string | no | `"on"` \| `"off"` |
| customTitle | string | no | 사용자 지정 제목 |

### 신규 필드

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| visualMode | string | no | `"manga"` | `"manga"` \| `"video"` |
| imageStyle | string | no | `"webtoon"` | `"webtoon"` \| `"3d_pixar"` \| `"realistic"` \| `"anime"` |

### mode="topic" 전용 필드

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| topic | string | yes | 주제명 (최소 5자) |
| contentStyle | string | no | `"narration"` \| `"skit"` \| `"review"` (기본: narration) |
| tone | string | no | 톤/분위기 |
| details | string | no | 부가 설명 |

## Response (SSE Stream)

### Progress 이벤트 (변경 없음)

```
data: {"type": "progress", "message": "분석 중..."}
```

### 신규 Progress 메시지 (영상 모드)

```
data: {"type": "progress", "message": "씬 2/5: AI 영상 생성 중... (45%)"}
```

### Done 이벤트 (확장)

```json
{
  "type": "done",
  "videoPath": "/path/to/output.mp4",
  "title": "...",
  "emotion": "funny",
  "duration": 45.2,
  "imageCount": 5,
  "videoCount": 0,
  "cost": 0.025,
  "visualMode": "manga",
  "imageStyle": "3d_pixar",
  "sourceType": "topic",
  "sceneImages": [{"scene_id": 1, "image_path": "..."}],
  "sceneVideos": [{"scene_id": 1, "video_path": "..."}],
  "scenes": [{"id": 1, "timestamp": 0, "duration": 5, "...": "..."}],
  "scriptPath": "...",
  "audioPath": "..."
}
```

### 신규 필드 설명

| Field | Type | Description |
|-------|------|-------------|
| videoCount | number | AI 영상 클립 수 (manga 모드: 0) |
| visualMode | string | 사용된 비주얼 모드 |
| imageStyle | string | 사용된 이미지 스타일 |
| sourceType | string | 입력 소스 (`"blind"` \| `"topic"`) |
| sceneVideos | array | 씬별 영상 파일 정보 (video 모드) |

## Error 이벤트

```json
{
  "type": "error",
  "message": "SEEDANCE_API_KEY가 설정되지 않았습니다. 이미지 모드를 사용해주세요."
}
```

## 검증 규칙

1. `mode="topic"` + `topic` 미입력 또는 5자 미만 → 400 에러
2. `visualMode="video"` + `SEEDANCE_API_KEY` 미설정 → 에러 이벤트 + 이미지 모드 권장
3. `imageStyle`은 `visualMode="manga"`일 때만 유효. `visualMode="video"`일 때 무시.
4. 기존 mode(`"image"`, `"manual"`, `"url"`)에서도 `visualMode`, `imageStyle` 사용 가능.
