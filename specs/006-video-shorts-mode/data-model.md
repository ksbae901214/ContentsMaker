# Data Model: 006-video-shorts-mode

**Date**: 2026-04-02

## 신규 엔티티

### TopicInput (frozen dataclass)

사용자가 입력한 자유 주제 정보. `src/scraper/topic_input.py`에 신규 생성.

| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| topic | str | (required) | min 5자 | 주제명 |
| style | str | "narration" | "narration" \| "skit" \| "review" | 콘텐츠 스타일 |
| tone | str | "" | - | 톤/분위기 (예: "재밌게", "심각하게") |
| details | str | "" | - | 부가 설명 |
| created_at | str | auto (KST) | ISO format | 생성 시각 |

**직렬화**: `to_dict()` / `from_dict()` (기존 패턴 준수)
**저장 경로**: `data/raw/{timestamp}_{topic_slug}.json`

### ImageStylePreset (상수 딕셔너리)

`src/illustrator/prompt_builder.py`에 `IMAGE_STYLE_PRESETS` 딕셔너리로 정의.

| Key | Description |
|-----|-------------|
| webtoon | 한국 웹툰 스타일 (기존 STYLE_PREFIX) |
| 3d_pixar | 3D Pixar/Disney 렌더링 스타일 |
| realistic | 포토리얼리스틱 디지털 일러스트 |
| anime | 일본 애니메 스타일 |

**참조 규칙**: `webtoon` 스타일만 `REFERENCE_STYLE_PREFIX` + `images.edit()` 사용. 나머지는 `images.generate()` 직접 사용.

## 기존 엔티티 확장

### Metadata (기존 frozen dataclass 확장)

`src/analyzer/script_models.py`의 `Metadata` 클래스에 필드 추가.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| source_type | str | "blind" | "blind" \| "topic" — 입력 소스 구분 |

**역호환**: 기본값 "blind"으로 기존 데이터/테스트 영향 없음. `from_dict()`에서 키 없으면 기본값 사용.

### ShortsScript (기존 frozen dataclass — 변경 없음)

`Metadata.source_type` 추가로 간접 확장. ShortsScript 자체 필드는 변경 없음.

### Scene (기존 frozen dataclass — 변경 없음)

이미 `visual_type: str` (default: "image", options: "image" | "video" | "none")과 `motion_prompt: str | None` 필드가 존재. 추가 변경 불필요.

## 데이터 흐름

```
[TopicInput]                    [BlindPost]
    ↓                               ↓
save_topic() → data/raw/       save_post() → data/raw/
    ↓                               ↓
build_topic_prompt()           build_prompt()
    ↓                               ↓
_call_claude() ←──────────────→ _call_claude()
    ↓                               ↓
ShortsScript (source_type="topic")  ShortsScript (source_type="blind")
    ↓                               ↓
    └──────── 공통 파이프라인 ────────┘
              ↓
         [visualMode 분기]
         ├─ "manga" → GPT Image (imageStyle 적용) → scene_images
         └─ "video" → Seedance API → scene_videos
              ↓
         TTS → render_video() → MP4
```

## 상태 전이

### VideoStatus (기존 frozen dataclass)

```
pending → processing → completed
                    → failed (→ 이미지 폴백)
```

- `pending`: Seedance API에 요청 제출됨
- `processing`: 영상 생성 중 (progress 0.0~1.0)
- `completed`: 영상 생성 완료, 다운로드 가능
- `failed`: 생성 실패 → 해당 씬 이미지 모드로 폴백
