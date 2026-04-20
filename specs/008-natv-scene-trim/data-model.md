# Data Model: TRIM-01

**Feature**: NATV 씬 구간 드래그 트리밍
**Date**: 2026-04-20

## Scene 확장 필드

기존 `Scene` dataclass (`src/analyzer/script_models.py`) 에 3 필드 추가.

### 필드 정의

```python
@dataclass(frozen=True)
class Scene:
    # ... existing fields ...

    # TRIM-01: NATV 원본 오프셋 (optional, 후방 호환)
    source_video: str | None = None       # 원본 MP4 경로 (예: "data/natv_clips/AU5Ymu6--Ao.mp4")
    source_start: float | None = None     # 원본에서의 시작 (초)
    source_end:   float | None = None     # 원본에서의 끝 (초)
```

### 유효성 규칙

| 규칙 | 적용 시점 |
|---|---|
| 세 필드는 **all-or-none** — 하나라도 set 이면 나머지 둘도 set 되어야 함 | 역직렬화 시 검증 |
| `source_start >= 0` | 저장 전 검증 |
| `source_start < source_end` | 저장 전 검증 |
| `source_end <= probe(source_video).duration` | `/api/scene/trim` 에서 ffprobe 가능 시 검증 |
| 상대경로는 프로젝트 루트 기준 | 렌더 시 해석 |

### 직렬화 (`to_dict`)

```python
# 모두 None 이면 키 생략 (기존 스크립트와 동일)
# 하나라도 not None 이면 세 키 모두 포함
if self.source_video is not None:
    d["source_video"] = self.source_video
    d["source_start"] = self.source_start
    d["source_end"]   = self.source_end
```

### 역직렬화 (`from_dict`)

```python
# snake_case + camelCase 양방향 허용 (기존 관례)
source_video = data.get("source_video") or data.get("sourceVideo")
source_start = data.get("source_start") if "source_start" in data else data.get("sourceStart")
source_end   = data.get("source_end")   if "source_end"   in data else data.get("sourceEnd")
```

## TypeScript 타입 (Remotion)

`src/video/remotion/src/types.ts` 에 동일 필드 추가 (camelCase):

```ts
export interface Scene {
  // ... existing ...
  sourceVideo?: string;
  sourceStart?: number;  // seconds
  sourceEnd?: number;    // seconds
}
```

`_convert_to_camel_case()` (renderer.py) 가 자동 변환하므로 Python 측에서 snake_case 로 저장해도 Remotion 은 camelCase 로 받는다.

## 상태 전이

```
[initial] ── NATV cut loop (Phase 2) ──► [offsets set]
[offsets set] ── /api/scene/trim (Phase 3) ──► [offsets modified]
[offsets set] ── scene_split ──► [offsets halved by duration ratio]
[offsets set] ── scene_merge (같은 source_video) ──► [offsets merged (start_a, end_b)]
```

## 관계

- `Scene.source_video` → `data/natv_clips/*.mp4` (물리 파일)
- 여러 `Scene` 이 같은 `source_video` 참조 가능 (한 원본에서 여러 구간 추출)
- 렌더 시 Remotion public 디렉토리로 **한 번만** 복사 (중복 방지)

## 마이그레이션

기존 스크립트 JSON 은 이 필드가 없으므로 역직렬화 시 자동으로 `None` 이 된다. **별도 마이그레이션 스크립트 불필요**.

NATV 모드에서 생성된 과거 스크립트는 재-생성해야 오프셋이 채워진다. `/api/scene/trim` 은 `source_video=None` 인 씬에 대해 **403** 반환 (non-NATV 씬 보호).
