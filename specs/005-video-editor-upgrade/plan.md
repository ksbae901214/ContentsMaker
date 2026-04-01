# Implementation Plan: 영상 제작/편집 기능 고도화

**Branch**: `005-video-editor-upgrade` | **Date**: 2026-03-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-video-editor-upgrade/spec.md`

## Summary

ContentsMaker의 영상 편집 기능을 Vrew 수준으로 고도화하고, Seedance 2.0 기반 AI 영상 클립 생성을 통합한다. 타임라인 편집, 자막 스타일링, 트랜지션 효과, 음성 선택(Phase 1) → AI 영상 클립 통합(Phase 2) → 실시간 미리보기, 프로젝트 관리(Phase 3) → 일괄 생성, 템플릿, 다국어(Phase 4) 순서로 구현한다.

## Technical Context

**Language/Version**: Python 3.11+ (백엔드), TypeScript 5.9+ (프론트엔드/Remotion)
**Primary Dependencies**: Next.js 16, Remotion 4.x, React 19, edge-tts, @dnd-kit/core (드래그앤드롭), @remotion/player (미리보기)
**Storage**: 로컬 파일 시스템 (JSON 기반 프로젝트 파일)
**Testing**: pytest (Python), vitest (TypeScript)
**Target Platform**: macOS/Linux 로컬 서버, 웹 브라우저 클라이언트
**Project Type**: Web application (Next.js 프론트엔드 + Python 백엔드 하이브리드)
**Performance Goals**: 미리보기 변경 반영 3초 이내, AI 영상 생성 5분 이내/씬
**Constraints**: AI 영상 생성 비용 $2.00 이하/영상(5씬), 영상 길이 30-60초, 1080x1920
**Scale/Scope**: 단일 사용자 로컬 환경, 프로젝트 수 무제한

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 상태 | 비고 |
|------|------|------|
| I. Zero-Cost Pipeline | ⚠️ | AI 영상 클립은 유료(Seedance ~$0.25/씬). 무료 대안 없음 증명 필요 |
| II. Pipeline Integrity | ✅ | 각 단계 독립 실행, JSON 기반 데이터 교환 유지 |
| III. Text-First Video | ✅ | 자막 고도화로 텍스트 가독성 강화 |
| IV. Content Safety | ✅ | 기존 필터링 유지, 새 기능에 영향 없음 |
| V. Emotion-Driven | ✅ | 감정별 트랜지션/효과음 매핑 추가 |
| VI. Modularity | ✅ | 영상 생성 추상화 레이어로 모듈 분리 |
| VII. Evidence-Based | ✅ | 테스트 영상 자동 생성 규칙 준수 |
| VIII. Full Test Gate | ✅ | 각 Phase별 테스트 작성 |

**원칙 I 위반 정당화**: Seedance 2.0 AI 영상 클립은 무료 대안이 존재하지 않는다. 사용자가 "이미지 모드"를 선택하면 기존 무료 파이프라인이 유지되며, "영상 모드"는 사용자가 명시적으로 선택하고 비용을 확인한 후에만 실행된다. 비용 표시 및 사전 확인 UI가 필수이다.

## Project Structure

### Documentation (this feature)

```text
specs/005-video-editor-upgrade/
├── plan.md              # This file
├── research.md          # Phase 0: Seedance API, Remotion Player, 드래그앤드롭
├── data-model.md        # Phase 1: 확장된 Scene, Project, Template 모델
├── quickstart.md        # Phase 1: 개발 환경 설정 가이드
├── contracts/           # Phase 1: API 엔드포인트 명세
└── tasks.md             # Phase 2: /speckit.tasks 출력
```

### Source Code (repository root)

```text
# Frontend (Next.js)
app/
├── components/
│   ├── Timeline.tsx              # 타임라인 편집기 (P1)
│   ├── SubtitleStyleEditor.tsx   # 자막 스타일 설정 (P1)
│   ├── TransitionPicker.tsx      # 트랜지션 선택 (P2)
│   ├── VoicePicker.tsx           # 음성 선택 (P2)
│   ├── VideoPreview.tsx          # 실시간 미리보기 (P3)
│   ├── SfxPicker.tsx             # 효과음 선택 (P3)
│   ├── ProjectList.tsx           # 프로젝트 목록 (P3)
│   ├── BatchQueue.tsx            # 일괄 생성 큐 (P4)
│   └── TemplatePicker.tsx        # 템플릿 선택 (P4)
├── api/
│   ├── scene/split/route.ts      # 씬 분할 (P1)
│   ├── scene/merge/route.ts      # 씬 병합 (P1)
│   ├── tts/preview/route.ts      # 음성 미리듣기 (P2)
│   ├── video-gen/route.ts        # AI 영상 생성 (P2)
│   ├── project/save/route.ts     # 프로젝트 저장 (P3)
│   ├── project/load/route.ts     # 프로젝트 불러오기 (P3)
│   ├── batch/route.ts            # 일괄 생성 (P4)
│   └── translate/route.ts        # 번역 (P4)

# Backend (Python)
src/
├── editor/
│   └── scene_ops.py              # 씬 분할/병합 (P1, 불변 변환)
├── video_gen/
│   ├── base.py                   # VideoGeneratorBase ABC (P2)
│   ├── seedance_gen.py           # Seedance 2.0 구현 (P2)
│   └── factory.py                # 생성기 팩토리 (P2)

# Remotion (영상 렌더링)
src/video/remotion/src/
├── components/
│   ├── Transition.tsx            # 트랜지션 효과 (P2)
│   └── SceneWithVideo.tsx        # 영상 클립 렌더링 (P2)

# Data
data/
├── sfx/                          # 효과음 라이브러리 (P3)
├── projects/                     # 프로젝트 저장 (P3)
└── templates/                    # 스타일 템플릿 (P4)
```

**Structure Decision**: 기존 프로젝트 구조(Next.js app/ + Python src/)를 확장한다. 새 Python 모듈(`editor/`, `video_gen/`)을 추가하고, Remotion 컴포넌트와 Next.js API 라우트를 각 Phase별로 추가한다.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 원칙 I: AI 영상 유료 | 무료 AI 영상 생성 도구 없음 | 정적 이미지는 동적 영상 대체 불가. 사용자 선택제로 비용 통제 |
