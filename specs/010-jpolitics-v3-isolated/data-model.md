# Phase 1 Data Model — 정치쇼츠 V3

**Date**: 2026-06-05
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

모든 엔티티는 **frozen dataclass** (Constitution VI 불변성). `to_dict()`/`from_dict()` 수동 직렬화로 snake_case ↔ camelCase 경계 처리.

## E1. JpoliticsScript

V3 전용 쇼츠 스크립트 1편. 영상 1개에 대응.

| 필드 | 타입 | 기본값 | 검증 | 비고 |
|---|---|---|---|---|
| `metadata` | `JpoliticsMetadata` | 필수 | — | 제목·소스·소스 URL·출처 라벨 |
| `scenes` | `tuple[JpoliticsScene, ...]` | 필수 | 3~10개 | 씬 리스트 (불변 tuple) |
| `audio` | `JpoliticsAudioConfig` | 필수 | — | TTS 락인 설정 (변경 불가) |
| `background` | `JpoliticsBackgroundConfig` | 필수 | — | 그라데이션 설정 |

### JpoliticsMetadata
| 필드 | 타입 | 기본값 | 검증 |
|---|---|---|---|
| `title` | `str` | 필수 | 1~50자 |
| `source_type` | `Literal["jpolitics_youtube", "jpolitics_topic"]` | 필수 | — |
| `source_url` | `str \| None` | None | YouTube URL (youtube 모드) |
| `source_label` | `str \| None` | None | 하단 출처 라벨 (FR-019) |
| `duration_sec` | `float` | 필수 | 30 ≤ d ≤ 60 |
| `created_at` | `str` (ISO8601) | 필수 | — |
| `topic` | `str \| None` | None | 주제 모드 입력값 |

### JpoliticsAudioConfig (락인 — 변경 불가)
| 필드 | 타입 | 값 | 비고 |
|---|---|---|---|
| `tts_voice` | `Literal["ko-KR-InJoonNeural"]` | `"ko-KR-InJoonNeural"` | V1 락인, 변경 불가 |
| `tts_rate` | `Literal["+22%"]` | `"+22%"` | V1 락인, 변경 불가 |
| `tts_script` | `str` | 필수 | 합성된 전체 텍스트 |
| `inter_scene_gap_ms` | `Literal[300]` | `300` | FR-036 씬 간 무음 0.3초 고정 |
| `sfx_enabled` | `Literal[False]` | `False` | FR-034 효과음 영구 비활성 (필드 자체가 락인 가드) |
| `bgm_enabled` | `Literal[False]` | `False` | V3는 BGM 미사용 (Out of Scope) |

### JpoliticsBackgroundConfig
| 필드 | 타입 | 기본값 | 검증 |
|---|---|---|---|
| `type` | `Literal["gradient"]` | `"gradient"` | V3 그라데이션 고정 |
| `colors` | `tuple[str, str]` | `("#1a1a2e", "#16213e")` | 헥스 컬러 2개 (시작/끝) |

## E2. JpoliticsScene

단일 씬 단위. 1초 ≤ duration ≤ 5초.

| 필드 | 타입 | 기본값 | 검증 | 비고 |
|---|---|---|---|---|
| `id` | `int` | 필수 | ≥ 0 (씬 ID), -1 (outro) | |
| `timestamp` | `float` | 필수 | ≥ 0 | 누적 시작 시간 (초) |
| `duration` | `float` | 필수 | 1 ≤ d ≤ 5 | MAX_SCENE_DURATION_SECONDS=5 |
| `type` | `Literal["title", "body", "comment"]` | 필수 | — | 씬 유형 |
| `text` | `str` | 필수 | 1~80자 | 자막 텍스트 |
| `voice_text` | `str` | 필수 | 1~200자 | TTS 원문 (자막보다 자연스러운 문장) |
| `visual_layout` | `Literal["normal", "vs_card", "grid_2x2", "data_card"]` | `"normal"` | — | 4종 레이아웃 (FR-010, FR-022) |
| `subtitle_color` | `Literal["white", "yellow", "red", "blue"]` | `"white"` | — | 자막 색 (V2 패턴) |
| `subtitle_emphasis` | `bool` | `False` | — | 강조 (폰트 1.4x) |
| `headline_pin` | `str \| None` | `None` | 8~14자 (씬 0만 설정) | 영상 전체 고정 헤드라인 (FR-011, FR-017) |
| `comparison_cards` | `tuple[PoliticianCard, ...] \| None` | `None` | 1~4개 (필요 시) | 인물 카드 리스트 |
| `data_emphasis_color` | `Literal["red", "yellow", "blue"]` | `"red"` | — | 데이터 강조색 (FR-023) |
| `clip_path` | `str \| None` | `None` | 파일 존재 | 원본 클립 경로 (talking_head, vs_card) |
| `clip_search_query` | `str \| None` | `None` | 1~100자 | Claude가 결정한 yt-dlp 검색어 (FR-037) |
| `clip_source_timestamp` | `tuple[float, float] \| None` | `None` | (start, end) sec | 원본 영상 cut 구간 (Gemini 추출 timestamp) |
| `transition_effect` | `Literal["none"]` | `"none"` | — | FR-035 전환 효과 영구 `none` (필드 자체가 락인 가드) |
| `sfx_trigger` | `Literal[None]` | `None` | — | FR-034 효과음 트리거 영구 None (필드 자체가 락인 가드) |

### 검증 규칙

- `visual_layout = "vs_card"` → `comparison_cards`는 2개 필수.
- `visual_layout = "grid_2x2"` → `comparison_cards`는 3~4개 필수.
- `visual_layout = "data_card"` → `comparison_cards`는 1개 필수, `comparison_cards[0].data_value` 필수.
- `visual_layout = "normal"` → `comparison_cards`는 None.
- `headline_pin`은 씬 0(첫 씬)에만 설정 가능. 다른 씬은 None.

### 상태 전이

```
[기획안 생성]
  → JpoliticsScene(layout="normal", comparison_cards=None)
[Stage A 레이아웃 분류]
  → visual_layout 4종 중 하나로 변경
[politician_card 페치]
  → comparison_cards 채워짐 (vs/grid/data_card 인 경우)
[사용자 검수 (FR-014, FR-015)]
  → layout/text/headline_pin 수정 가능
[TTS 합성]
  → 변경 불가 (immutable from here)
[Remotion 렌더]
  → MP4 출력
```

## E3. PoliticianCard

한 정치인의 시각 자료 1세트. `comparison_cards` 리스트의 원소.

| 필드 | 타입 | 기본값 | 검증 |
|---|---|---|---|
| `name` | `str` | 필수 | 1~20자 |
| `party` | `str` | 필수 | 정당명 (사전 매핑 키) |
| `party_color` | `str` | 필수 | 헥스 #RRGGBB (PARTY_COLORS 매핑) |
| `photo_path` | `str \| None` | `None` | 로컬 파일 경로 (없으면 회색 실루엣 폴백) |
| `data_label` | `str \| None` | `None` | 예: "재산", "세금 5년" |
| `data_value` | `str \| None` | `None` | 예: "127억", "0원" |

### 검증 규칙

- `party`가 `PARTY_COLORS` 매핑에 없으면 `party_color = "#888888"` (FR-028).
- `photo_path`가 None이면 렌더 시 회색 실루엣 + 이름만 표시 (FR-027).
- `data_label`과 `data_value`는 함께 설정 (한쪽만 있으면 무효).

## E4. JpoliticsPlan

기획안 1개. 한 입력에 대해 3개 생성됨.

| 필드 | 타입 | 기본값 | 검증 |
|---|---|---|---|
| `rank` | `int` | 필수 | 1, 2, 3 중 하나 |
| `angle` | `Literal["title_anchor", "audience_resonance", "comparison"]` | 필수 | 3개 각도 (FR-008) |
| `format_type` | `Literal["A", "B", "C"]` | `"A"` | A=인터뷰/논평, B=현장, C=대담 |
| `layout_classification` | `Literal["talking_head", "vs_2way", "comparison_grid", "data_comparison"]` | 필수 | Stage A 분류 결과 (FR-010) |
| `topic` | `str` | 필수 | 1~60자 |
| `hook` | `str` | 필수 | 1~80자 (도입 후크) |
| `clip_section` | `str` | 필수 | 핵심 클립 시간 구간 (예: "01:23~01:45") |
| `reason` | `str` | 필수 | 선택 이유 (검수 화면 표시) |
| `flow_intro` | `str` | 필수 | 도입 흐름 (1~3문장) |
| `flow_middle` | `str` | 필수 | 중간 흐름 |
| `flow_climax` | `str` | 필수 | 클라이맥스 흐름 |
| `narrations` | `tuple[Narration, ...]` | 필수 | 씬별 나레이션 3~10개 |
| `cta` | `str` | 필수 | CTA 문구 |
| `headline_pin` | `str` | 필수 | 영상 전체 고정 헤드라인 (8~14자) |
| `youtube_search_keywords` | `tuple[str, ...] \| None` | `None` | topic 모드만 (씬별 검색어) |

### Narration (sub-entity)

| 필드 | 타입 | 검증 |
|---|---|---|
| `scene_id` | `int` | ≥ 0 |
| `text` | `str` | 1~80자 (자막) |
| `voice_text` | `str` | 1~200자 (TTS 원문) |
| `visual_layout` | `Literal[...]` | 4종 중 하나 |
| `subtitle_color` | `Literal[...]` | 4색 중 하나 |
| `subtitle_emphasis` | `bool` | — |
| `cards_metadata` | `tuple[dict, ...] \| None` | LLM이 카드 후보 인물명/데이터 출력 (None=normal) |

## E5. JpoliticsThreePlansResult

3개 기획안 묶음 + 입력 메타데이터.

| 필드 | 타입 | 검증 |
|---|---|---|
| `plans` | `tuple[JpoliticsPlan, JpoliticsPlan, JpoliticsPlan]` | 정확히 3개 |
| `youtube_url` | `str \| None` | youtube 모드 |
| `topic` | `str \| None` | topic 모드 |
| `video_title` | `str` | 입력 영상 제목 또는 주제 |
| `video_duration_sec` | `float` | 원본 영상 길이 |
| `video_path` | `str \| None` | 다운로드된 원본 MP4 경로 (youtube 모드) |
| `transcript_path` | `str \| None` | transcript JSON 경로 |
| `output_dir` | `str` | `data/jpolitics/{ts}_{slug}/` |
| `created_at` | `str` (ISO8601) | — |

### 검증 규칙

- `plans`의 3개 angle은 서로 달라야 함 (중복 시 PlanValidationError).
- `youtube_url` 또는 `topic` 중 정확히 하나만 설정.

## 직렬화 (JSON)

모든 dataclass는 `to_dict()` / `from_dict()` 수동 구현:
- snake_case ↔ camelCase 자동 변환 (V2 패턴 모방).
- `None` 필드는 출력에서 제외 (옵셔널 보존).
- tuple은 list로 직렬화 후 복원.
- frozen dataclass라 `replace()` 사용하여 변경 (불변성 보장).

### 파일 위치
- `script.json` — JpoliticsScript 직렬화
- `plans.json` — JpoliticsThreePlansResult 직렬화
- `politician_cards/{name}.json` — PoliticianCard 직렬화 + 캐시 메타데이터

## 데이터 흐름 (격리 모드, FR-037 영상 추출 흐름 포함)

```
input (YouTube URL or topic)
  ↓ [1. Gemini Files API 멀티모달 분석]
     (input YouTube URL → Gemini 업로드 → transcript + 핵심 timestamp 추출)
gemini_analysis.json  {transcript, key_moments[{start, end, summary}]}
  ↓ [2. Stage A: Gemini 레이아웃 분류 + 3 angle 생성]
3 angle + layout_classification
  ↓ [3. Stage B: Claude 6요소 + clip_search_query 결정]
     (Claude가 씬별 yt-dlp 검색 키워드 결정 — FR-037 step 2)
JpoliticsThreePlansResult (3 plans, 각 plan에 narrations[].clip_search_query)
  ↓ [4. 사용자 선택]
JpoliticsPlan
  ↓ [5. politician_card 페치] (read-only import: naver_image_search)
PoliticianCard list
  ↓ [6. yt-dlp ytsearch1 다운로드] (Claude 결정 키워드 사용 — FR-037 step 3)
     (read-only import: youtube_news_searcher.build_scene_clips, crop_mode="letterbox")
씬별 clip_path
  ↓ [7. plan_to_script]
JpoliticsScript
  ↓ [8. 사용자 검수 (FR-013~015)]
JpoliticsScript (수정 반영)
  ↓ [9. TTS 합성] (voice/rate 락인 + 씬 간 gap 0.3s — FR-036)
audio.mp3 + scene_timings (각 SceneTiming.end_ms 다음 SceneTiming.start_ms = 정확 +300 ms)
  ↓ [10. Remotion V3 렌더] (효과음 0 + 전환 효과 0 + Outro 컷 등장 — FR-034/035)
video.mp4 + summary.txt (3줄 + 해시태그)
```
