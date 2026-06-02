# Implementation Plan: 영상 쇼츠 모드

**Branch**: `006-video-shorts-mode` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-video-shorts-mode/spec.md`

## Summary

ContentsMaker를 블라인드 전용에서 범용 주제 지원으로 확장하고, 이미지 스타일 프리셋(4종)과 AI 영상 클립 모드를 추가한다. 기존 파이프라인의 JSON 계약과 모듈 독립성을 유지하면서, 입력(blind/topic) × 비주얼(manga/video) × 스타일(webtoon/3d_pixar/realistic/anime) 조합을 지원한다.

## Technical Context

**Language/Version**: Python 3.11+ (백엔드), TypeScript + React (Remotion 영상, Next.js 16 프론트엔드)
**Primary Dependencies**: edge-tts, openai, remotion, httpx (신규)
**Storage**: JSON 파일 기반 (`data/raw/`, `data/scripts/`, `data/audio/`, `data/images/`, `data/videos/` 신규)
**Testing**: pytest (Python), 수동 E2E (영상 확인)
**Target Platform**: macOS (개발), Cloudflare Tunnel 배포
**Project Type**: Web application (Next.js + Python 백엔드 파이프라인)
**Performance Goals**: 이미지 모드 3분 이내 영상 생성, 영상 모드 10분 이내
**Constraints**: 이미지 모드 영상당 $0.03 이하, 영상 모드 $0.25 이하 (720p 5씬)
**Scale/Scope**: 단일 사용자, 로컬 실행

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Check

| 원칙 | 상태 | 비고 |
|------|------|------|
| I. Zero-Cost Pipeline | **위반 (정당화됨)** | Seedance API는 유료. Phase 1-2 금지 범위 외(Phase 6). 선택적(opt-in), 기본값 이미지 모드. [R-007 참조](research.md) |
| II. Pipeline Integrity | **통과** | TopicInput → ShortsScript 동일 JSON 계약. Seedance 실패 시 이미지 폴백. |
| III. Text-First Video | **통과** | AI 영상 클립은 배경 역할. SceneWithVideo에 텍스트 오버레이 + 다크 그래디언트 유지. |
| IV. Content Safety | **통과** | 주제 입력도 Claude 분석 시 동일한 PII/부적절 콘텐츠 필터링 적용. |
| V. Emotion-Driven | **통과** | analyze_topic()도 감정 감지 + 감정별 스타일 적용 동일. |
| VI. Modularity & Immutability | **통과** | TopicInput은 frozen dataclass. 신규 모듈은 독립 실행/테스트 가능. |
| VII. Evidence-Based | **통과** | 작업 완료 시 테스트 영상 생성 의무. |
| VIII. Full Test Gate | **통과** | 각 신규 모듈별 테스트 + 전체 테스트 통과 필수. |

### Post-Design Check

| 원칙 | 상태 | 비고 |
|------|------|------|
| I. Zero-Cost Pipeline | **위반 (정당화됨)** | 변경 없음. Complexity Tracking 섹션에 상세 기록. |
| II. Pipeline Integrity | **통과** | data-model.md 데이터 흐름 다이어그램 확인. |
| VI. Modularity & Immutability | **통과** | topic_input.py 독립 모듈, image_style은 파라미터 주입 방식. |

## Project Structure

### Documentation (this feature)

```text
specs/006-video-shorts-mode/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research decisions
├── data-model.md        # Entity definitions
├── quickstart.md        # Development quickstart
├── contracts/
│   ├── api-generate.md  # POST /api/generate 확장 계약
│   └── cli-commands.md  # CLI 커맨드 확장 계약
└── tasks.md             # (Phase 2 — /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── scraper/
│   ├── models.py              # BlindPost (기존)
│   ├── topic_input.py         # ★ 신규: TopicInput 모델 + save_topic()
│   ├── manual_input.py        # (기존, 변경 없음)
│   └── validator.py           # (기존, 변경 없음)
├── analyzer/
│   ├── script_models.py       # ★ 수정: Metadata.source_type 추가
│   ├── prompt_template.py     # ★ 수정: TOPIC_ANALYZE_PROMPT, build_topic_prompt()
│   └── claude_analyzer.py     # ★ 수정: analyze_topic() 추가
├── illustrator/
│   ├── prompt_builder.py      # ★ 수정: IMAGE_STYLE_PRESETS, image_style 파라미터
│   └── image_generator.py     # ★ 수정: image_style 전달
├── video_gen/
│   ├── base.py                # ★ 수정: generate_and_wait() 추가
│   ├── seedance_gen.py        # ★ 수정: TODO 구현 완성
│   └── factory.py             # (기존, 변경 없음)
├── video/
│   ├── renderer.py            # ★ 수정: scene_videos 파라미터 추가
│   └── remotion/src/
│       ├── ShortsComposition.tsx  # (기존, 변경 없음 — sceneVideos 이미 지원)
│       └── components/
│           └── SceneWithVideo.tsx  # (기존, 변경 없음 — 이미 완성)
├── tts/                       # (기존, 변경 없음)
└── config/
    └── settings.py            # ★ 수정: DATA_VIDEOS_DIR 추가

app/
├── page.tsx                   # ★ 수정: 주제 탭, 모드 토글, 스타일 선택
└── api/
    └── generate/
        └── route.ts           # ★ 수정: topic 모드 + visualMode 분기

tests/
├── test_topic_input.py        # ★ 신규
├── test_prompt_template_topic.py  # ★ 신규
├── test_analyzer_topic.py     # ★ 신규
├── test_seedance_gen.py       # ★ 신규
├── test_script_models.py      # ★ 수정: source_type 역호환
└── test_renderer.py           # ★ 수정: scene_videos props

data/
└── videos/                    # ★ 신규 디렉토리 (Seedance 출력)
```

**Structure Decision**: 기존 프로젝트 구조 유지. Python 백엔드(`src/`) + Next.js 프론트엔드(`app/`) + Remotion 영상(`src/video/remotion/`) 3분할 구조. 신규 모듈(`topic_input.py`)은 기존 디렉토리에 추가.

## Complexity Tracking

> **원칙 I 위반 정당화**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Seedance API 유료 사용 ($0.05/5초 720p) | AI 영상 클립 생성은 Phase 6 핵심 기능(User Story 3). 영상 모드로 역동적 쇼츠 제작 가능. | 로컬 Stable Video Diffusion은 GPU 필요(M1 Mac 비실용적). GIF/정적 이미지 연결은 "영상 쇼츠" 품질 미달. |

**완화 조치**:
- 영상 모드는 선택적(opt-in), 기본값은 이미지 모드 (기존 비용 유지)
- 사용자에게 생성 전 예상 비용 표시 (FR-006)
- SEEDANCE_API_KEY 미설정 시 영상 모드 비활성화, 이미지 모드 권장 (FR-013)
