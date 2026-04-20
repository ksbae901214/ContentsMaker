# API Contract: POST /api/scene/trim

**Feature**: TRIM-01
**Date**: 2026-04-20

## 목적

NATV 씬의 원본 영상 오프셋(`source_start`, `source_end`) 을 업데이트.

## Endpoint

```
POST /api/scene/trim
Content-Type: application/json
```

## Request

```json
{
  "scriptPath": "/Users/kyusik/ContentsMaker/data/scripts/<file>.json",
  "sceneId": 3,
  "sourceStart": 1.2,
  "sourceEnd": 5.8
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `scriptPath` | string | ✅ | 절대 경로. `data/scripts/` allowlist |
| `sceneId` | number | ✅ | 대상 씬 id (1-based) |
| `sourceStart` | number | ✅ | 초 단위, `≥ 0` |
| `sourceEnd` | number | ✅ | 초 단위, `> sourceStart` |

## Response

### 200 OK

```json
{
  "success": true,
  "scene": {
    "id": 3,
    "source_video": "/Users/kyusik/ContentsMaker/data/natv_clips/AU5Ymu6--Ao.mp4",
    "source_start": 1.2,
    "source_end": 5.8,
    "duration": 4.6
  }
}
```

### 400 Bad Request

- `sourceStart >= sourceEnd`
- `sourceStart < 0`
- `sourceEnd > probe(source_video).duration` (ffprobe 가능 시)

```json
{ "error": "sourceStart(5.0) must be less than sourceEnd(3.0)" }
```

### 403 Forbidden

- 대상 씬에 `source_video` 가 없음 (non-NATV 씬 보호)
- `scriptPath` 가 허용 경로 밖

```json
{ "error": "씬 3은 NATV 클립이 아니어서 트리밍할 수 없습니다" }
```

### 404 Not Found

- `scriptPath` 파일 없음
- `sceneId` 해당 씬 없음

```json
{ "error": "씬 99를 찾을 수 없습니다" }
```

## Side Effects

- 스크립트 JSON 파일을 read → modify → write (atomic 가능하면 rename)
- 다른 씬 / audio / background 은 **변경 없음**
- 로그: `INFO scene_trim sceneId=3 start=1.2 end=5.8`

## Security

- `scriptPath` 는 `resolve()` 후 `data/scripts/` prefix 필수 → 트래버설 방어
- 쓰기 권한은 프로세스 소유자만 (OS 레벨)
- 요청 body 크기 ≤ 2KB (숫자/경로만)

## Idempotency

- 같은 body 반복 호출 → 같은 결과 (파일 mtime 만 갱신)
- 클라이언트는 debounce 권장 (drag → commit 한 번)

## 테스트 계약 (Phase 3, 4개)

| 테스트 | 예상 상태 |
|---|---|
| `test_rejects_non_natv_scene` | 403 |
| `test_rejects_invalid_range` | 400 (start ≥ end) |
| `test_rejects_end_beyond_source` | 400 (ffprobe 가능 시) |
| `test_saves_offsets_to_script` | 200 + 파일 검증 |
