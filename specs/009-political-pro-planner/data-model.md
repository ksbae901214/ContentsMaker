# Phase 1 — Data Model: Political Shorts Planner

**Branch**: `009-political-pro-planner`
**Date**: 2026-05-13

> 본 문서는 spec.md의 Key Entities를 구현 가능한 데이터 모델로 구체화한다. 모든 Python 데이터 클래스는 Constitution 원칙 VI(불변성)에 따라 `@dataclass(frozen=True)`이다.

---

## E1. ShortsPlan (숏츠 기획안)

영상생성지침 RTF 6요소 + angle 메타데이터를 담는 불변 객체.

### Fields

| 필드 | 타입 | 설명 | 검증 규칙 (FR 매핑) |
|------|------|------|---------------------|
| `topic` | `str` | (1) 한 줄 핵심 이슈 | 비어 있지 않음, 60자 이내 |
| `hook` | `str` | (2) 후킹 문구 (0~3초 정지 유도) | 비어 있지 않음, 40자 이내 — FR-005 |
| `clip_start_sec` | `float` | (3) 사용 구간 시작 (초) | `0 <= start < end`, `end <= video_duration` — FR-013 |
| `clip_end_sec` | `float` | (3) 사용 구간 종료 (초) | 동상 |
| `clip_reason` | `str` | (3) 선택 이유 | 비어 있지 않음 — FR-005 |
| `flow_intro` | `str` | (4) 시작 흐름 묘사 | 비어 있지 않음 — FR-005 |
| `flow_middle` | `str` | (4) 중간 흐름 묘사 | 비어 있지 않음 |
| `flow_climax` | `str` | (4) 클라이맥스 묘사 | 비어 있지 않음 |
| `narrations` | `tuple[Narration, ...]` | (5) 타이밍별 나레이션 | 1개 이상 — FR-005 |
| `cta` | `str` | (6) 마무리 유도 문구 | 비어 있지 않음 — FR-005 |
| `angle` | `Literal["title_anchor", "audience_resonance", "comparison"]` | 관점 라벨 | 3개 plan이 서로 달라야 함 — FR-006 |

### 직렬화
- `to_dict() -> dict` / `from_dict(data: dict) -> ShortsPlan` 수동 구현 — ContentsMaker 컨벤션 동일.

### 불변성
- `frozen=True` 강제. 수정 필요 시 `dataclasses.replace`로 새 인스턴스 생성.

---

## E2. Narration (타이밍별 나레이션)

`ShortsPlan` 내부에 다수 포함되는 sub-entity.

### Fields

| 필드 | 타입 | 설명 | 검증 규칙 |
|------|------|------|-----------|
| `start_sec` | `float` | 시작 시각(초, 영상 내 절대 시각) | `>= 0`, `< end_sec` |
| `end_sec` | `float` | 종료 시각 | `<= video_duration` |
| `text` | `str` | 대사 | 비어 있지 않음, transcript에서 확인 가능한 사실만 — FR-007 |

### Note
- `(start_sec, end_sec)`은 영상 절대 시각이 아니라 **clip 내 상대 시각**으로 저장된다. 즉 첫 나레이션은 `(0, 3)`처럼 0부터 시작. RTF 예시 `(0~3초): "지금 이 장면..."` 형식 일치.

---

## E3. ThreePlansResult (생성 결과 묶음)

Claude의 단일 응답을 파싱한 후 보관되는 컨테이너.

### Fields

| 필드 | 타입 | 설명 |
|------|------|------|
| `plans` | `tuple[ShortsPlan, ShortsPlan, ShortsPlan]` | 정확히 3개 — FR-004 |
| `youtube_url` | `str` | 원본 URL |
| `video_path` | `str` | 다운로드된 영상 파일 절대 경로 |
| `video_duration_sec` | `float` | 원본 영상 총 길이 |
| `transcript_path` | `str` | 저장된 transcript JSON 경로 |
| `video_title` | `str` | 영상 제목 (Claude에게 컨텍스트로 전달됨) |
| `generated_at` | `str` | ISO 8601 timestamp |

### 영속화
- 파일 경로: `data/political_pro/{timestamp}_{slug}/plans.json`
- 영상 파일: `data/political_pro/{timestamp}_{slug}/source.mp4`
- transcript: `data/political_pro/{timestamp}_{slug}/transcript.json`

---

## E4. ShortsScript (재사용)

기존 `src/analyzer/script_models.py` 그대로 사용. `plan_to_script()` 변환 시 다음 필드를 설정:

| 필드 | 매핑 |
|------|------|
| `metadata.source_type` | `"political_pro"` (신규 enum 값) |
| `metadata.source_url` | `ThreePlansResult.youtube_url` |
| `metadata.title` | `ShortsPlan.topic` |
| `metadata.emotion_type` | 자동 매핑 — Claude가 angle별로 선정한 값(기본 `angry` for 정치) |
| `scenes[0].text` | `ShortsPlan.hook` (첫 씬은 후킹) |
| `scenes[i].text` | `ShortsPlan.flow_intro/middle/climax` 흐름 텍스트 |
| `scenes[i].voice_text` | 대응 `Narration.text` |
| `scenes[i].duration` | `Narration.end_sec - Narration.start_sec` (자동 5초 cap — FR-012) |
| `scenes[-1].text` | `ShortsPlan.cta` (마지막 씬은 CTA) |

---

## E5. VideoClip (원본 클립)

| 필드 | 타입 | 설명 |
|------|------|------|
| `scene_id` | `int` | ShortsScript Scene id |
| `video_path` | `str` | 잘린 9:16 변환 mp4 파일 절대 경로 |
| `start_sec` | `float` | 원본 영상 내 시작 시각 |
| `end_sec` | `float` | 원본 영상 내 종료 시각 |

### 영속화
- 파일 경로: `data/political_pro/{timestamp}_{slug}/scene_{sid:02d}.mp4`

---

## E6. Transcript (음성 텍스트)

기존 자료 구조 그대로 재사용 — `list[dict]` 형식의 `{"start": float, "end": float, "text": str}`.

저장 시 `transcript.json`은 `{"segments": [{...}, ...], "source": "vtt" | "whisper"}` 래핑.

---

## State Transitions

```
[URL 입력]
   │
   ▼
[VIDEO_DOWNLOADING] ──▶ (실패: DOWNLOAD_FAILED, 종료)
   │
   ▼
[TRANSCRIBING] (VTT or Whisper) ──▶ (실패: TRANSCRIPT_UNAVAILABLE, 종료)
   │
   ▼
[PLANS_GENERATING] (Claude 1회 호출, 실패 시 1회 재시도)
   │
   ▼
[PLANS_READY] (사용자에게 3개 카드 표시)
   │
   ▼ (사용자가 1개 선택)
   │
[SCRIPT_CONVERTING] (plan_to_script)
   │
   ▼
[REVIEW_PENDING] (검수 화면, 사용자 입력 대기)
   │
   ▼ (검수 완료 + "영상 생성" 클릭)
   │
[CLIPPING] (씬별 9:16 cut)
   │
   ▼
[TTS_RENDERING] (Gemini TTS Charon)
   │
   ▼
[VIDEO_RENDERING] (Remotion)
   │
   ▼
[DONE] (MP4 산출)
```

각 transition의 실패 처리는 FR-003, FR-008, FR-019에 명시됨.

---

## 검증 매트릭스 (FR ↔ Entity)

| FR | Entity 필드 |
|----|------------|
| FR-004 | `ThreePlansResult.plans` (len == 3) |
| FR-005 | `ShortsPlan` 6 필드(topic, hook, clip_*, flow_*, narrations, cta) |
| FR-006 | `ShortsPlan.angle` (3개 plan에서 서로 다름) |
| FR-012 | `ShortsScript.scenes[i].duration <= 5.0` (변환 시 자동 분할) |
| FR-013 | `ShortsPlan.clip_end_sec <= video_duration` (변환 시 클램프) |
| FR-018 | 최종 산출 mp4 — 30~60s, 9:16 |
