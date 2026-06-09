# Implementation Plan: 정치쇼츠 V3 — @김정치입니다 격리 모드

**Branch**: `010-jpolitics-v3-isolated` | **Date**: 2026-06-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-jpolitics-v3-isolated/spec.md`

## Summary

YouTube 채널 `@김정치입니다`의 영상 포맷(고정 노란 헤드라인 + 4종 레이아웃 + 인물 카드 + 정당 컬러)을 재현하는 정치 쇼츠 생성기를 **물리적 완전 격리 모드**로 구현한다. 신규 `src/jpolitics/` Python 패키지 + `src/video/remotion_v3/` 독립 Remotion 패키지 + `app/jpolitics/` Next.js 라우트로 구성되며, 기존 파일은 **read-only import**만 허용한다. **유일한 예외**: `app/page.tsx` 헤더에 V3 진입 버튼 1개 추가.

기존 V2(`political_pro`) Stage A/B 패턴을 모방한 독립 Planner가 영상 핵심 구조를 4종 레이아웃(talking_head / vs_2way / comparison_grid / data_comparison)으로 자동 분류하고, Naver 이미지 검색으로 인물 카드를 페치하며, TTS는 V1 락인 `ko-KR-InJoonNeural` +22%를 하드코딩한다. 자동 업로드는 영구 차단(V2와 동일 정책).

## Technical Context

**Language/Version**: Python 3.11+ (백엔드), TypeScript 5.x + React 19 / Next.js 16 (프론트엔드), Remotion 4.x (영상 렌더링, 독립 패키지)
**Primary Dependencies**:
- Python: `anthropic` (Claude 호출), `google-genai` (Gemini 호출), `edge-tts` (TTS), `requests` (Naver API), `yt-dlp` (영상/자막), `ffmpeg` (클립 cut, 시스템 바이너리)
- TypeScript: `remotion`, `@remotion/cli` (별도 `package.json`, 기존 `remotion/` 무수정)
- Next.js: 기존 프로젝트 의존성 재사용 (신규 추가 없음)
**Storage**: 로컬 JSON/MP4 파일 (`data/jpolitics/{ts}_{slug}/` — 영상·plans·script 보관, `data/politician_cards/{name}.json` — 인물 카드 캐시, `data/jpolitics_reference/` — 채널 샘플 키프레임). 데이터베이스 없음.
**Testing**: `pytest` (격리 디렉토리 `tests/jpolitics/`), Remotion preview 스크린샷 비교
**Target Platform**: macOS 개발 (Darwin 24.x) + Linux 배포 가능 (ffmpeg/Node.js/Python 표준 환경)
**Project Type**: Web 애플리케이션 (Next.js 프론트엔드 + Python 백엔드 + Remotion 영상 엔진)
**Performance Goals**:
- 영상 1편 입력→출력 7분 이내 (SC-001)
- 인물 카드 캐시 히트 200ms 이내 (SC-005)
- V3 입력 폼 노출 3초 이내 (SC-004)
**Constraints**:
- 변동비 $0 (Naver 무료 25,000건/일, Gemini 무료 250req/일, Edge TTS 무료, Claude 기존 한도)
- 기존 V1/V2 파일 0 수정 (유일한 예외: `app/page.tsx` 진입 버튼 1개)
- 기존 297+ 회귀 테스트 100% 통과 유지
- V1/V2 동일 입력 시 V3 도입 전후 영상 바이트 일치 (SC-010)
- TTS 보이스 `ko-KR-InJoonNeural` +22% 하드코딩 (V1 락인)
- 자동 업로드 UI 영구 차단 (FR-029)
- **효과음(SFX)·BGM 영구 0**: 오디오 트랙은 TTS 1개만 (FR-034, SC-011)
- **씬 전환 효과 영구 0**: 그라데이션·페이드·디졸브 미사용, 하드 컷만 (FR-035, SC-012)
- **TTS 씬 간 gap 300 ms 고정**: 그룹 경계에서만 (FR-036, SC-013)
- **영상 추출 흐름 Gemini → Claude → yt-dlp 3단계 분업**: 단일 LLM 흐름 금지 (FR-037, SC-014)
**Scale/Scope**:
- V3 신규 Python 모듈 ~12개, Remotion 컴포넌트 ~9개, Next.js 페이지 ~5개, 테스트 ~6개
- 신규 LOC ~2500 (Remotion 컴포넌트 복제분 ~1000 포함)
- 한 달 90편 영상 생성 가정 (3편/일 × 30일) — 무료 한도의 1% 이하 사용

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 평가 | 근거 / 격리 모드 영향 |
|---|---|---|
| **I. Zero-Cost Pipeline** | ✅ PASS | 모든 외부 호출은 무료 한도 내 (Naver 25K/일, Gemini 250/일, Edge TTS 무료, Claude 기존 한도). 신규 유료 의존성 0건. SC-006 변동비 $0 명시. |
| **II. Pipeline Integrity** | ✅ PASS | 격리 모드에서도 5단계(transcript→planner→tts→renderer→output) JSON 계약 유지. 각 단계 실패 시 다음 콘텐츠로 진행 (FR-008 3개 기획안 fallback). 중간 산출물 `data/jpolitics/{ts}_{slug}/` 보존. |
| **III. Text-First Video** | ✅ PASS | 고정 노란 헤드라인 + 하단 자막 박스 + 정당 컬러 카드 = 텍스트 중심. 9:16 1080×1920, 30~60초 (FR-016), 한국어 자막 필수 (FR-018). |
| **IV. Content Safety & Legal Compliance** | ✅ PASS | 자동 업로드 영구 차단 (FR-029), 검수 필수 배너 (FR-030), 원본 출처 메타데이터 보존 (FR-031). 정치인 사진·뉴스 인용은 보도·논평 목적으로 한정. |
| **V. Emotion-Driven Experience** | ⚠️ **부분 통과 → 정당화 필요** | V3는 감정 4종 (funny/touching/angry/relatable) 대신 **레이아웃 4종** (talking_head/vs_2way/comparison_grid/data_comparison)을 사용. 정치 콘텐츠는 단일 톤(`angry` 계열, V1 락인 InJoonNeural)으로 고정. → Complexity Tracking 표에 기록. |
| **VI. Modularity & Immutability** | ✅ PASS | 격리 모드는 모듈성을 **최대로 만족** (기존 V1/V2 무영향). frozen dataclass + 새 객체 생성 패턴 유지. 파일 800줄 한계, 함수 50줄 한계 준수 예정. |
| **VII. Evidence-Based Completion** | ✅ PASS | Phase 10에서 4종 레이아웃 각각 샘플 영상 1편 생성하여 시각 검증. 기존 297+ 회귀 테스트 100% 통과 증명. TypeScript `tsc --noEmit` 통과. **테스트 영상 자동 생성 mandate** = `python3 -m src.jpolitics.main` 격리 entry로 실행. |
| **VIII. Full Test Gate** | ✅ PASS | 신규 50+ 테스트 작성 (`tests/jpolitics/`). `pytest tests/ -v` 전체 통과. 격리로 인해 기존 테스트는 자동 보호. |

### Constitution Check 결과: ✅ PASS (V 원칙 정당화 필요)

V 원칙(Emotion-Driven)은 정치 콘텐츠 특성상 **감정 4종 대신 레이아웃 4종**으로 대체된다. 정치 쇼츠의 차별점은 감정 톤이 아니라 시각 구조(누가 vs 누구, 누구의 데이터)이며, V1 락인 InJoonNeural +22%로 톤은 단일 고정한다. Complexity Tracking 표에 기록.

## Project Structure

### Documentation (this feature)

```text
specs/010-jpolitics-v3-isolated/
├── plan.md                      # This file (/speckit.plan output)
├── research.md                  # Phase 0 output
├── data-model.md                # Phase 1 output (Entities 명세)
├── quickstart.md                # Phase 1 output (개발자 가이드)
├── contracts/
│   ├── cli.md                   # python3 -m src.jpolitics.main 인자/출력
│   ├── api.md                   # /api/jpolitics/plans, /render 스키마
│   └── remotion_v3.md           # Remotion composition props 스키마
├── checklists/
│   └── requirements.md          # /speckit.specify 산출 (이미 작성됨)
└── tasks.md                     # Phase 2 output (/speckit.tasks 출력, 본 명령 미생성)
```

### Source Code (repository root) — 격리 모드 디렉토리

```text
src/jpolitics/                   # 🆕 신규 독립 Python 패키지
├── __init__.py
├── main.py                      # CLI entry: python3 -m src.jpolitics.main
├── models/
│   ├── __init__.py
│   ├── script.py                # JpoliticsScript / JpoliticsScene (frozen)
│   └── plan.py                  # JpoliticsPlan / JpoliticsThreePlansResult
├── scraper/
│   ├── __init__.py
│   └── politician_card.py       # fetch_politician_card + PARTY_COLORS
├── analyzer/
│   ├── __init__.py
│   ├── prompts.py               # Stage A/B 프롬프트
│   └── planner.py               # generate_three_plans + plan_to_script
├── tts/
│   ├── __init__.py
│   └── voice.py                 # ko-KR-InJoonNeural +22% 락인
└── video/
    ├── __init__.py
    └── renderer.py              # Remotion V3 호출 wrapper

src/video/remotion_v3/           # 🆕 신규 독립 Remotion 패키지 (기존 remotion/ 무수정)
├── package.json
├── tsconfig.json
├── public/                      # V3 전용 자산 디렉토리
└── src/
    ├── index.ts                 # registerRoot(Root)
    ├── Root.tsx                 # Composition 등록
    ├── JpoliticsComposition.tsx # main composition
    └── components/
        ├── PinnedHeadline.tsx
        ├── TalkingHeadScene.tsx
        ├── VsCardScene.tsx
        ├── ComparisonGridScene.tsx
        ├── DataCardScene.tsx
        ├── SubtitleBlock.tsx     # V2 자막 패턴 복제
        ├── Background.tsx        # V2 패턴 복제
        ├── Outro.tsx             # V2 패턴 복제
        └── LetterboxFrame.tsx    # 하단 출처 라벨

app/jpolitics/                   # 🆕 신규 Next.js 라우트 (자동 라우팅 /jpolitics)
├── page.tsx                     # V3 전용 페이지
├── components/
│   ├── JpoliticsPlanPicker.tsx
│   └── JpoliticsScriptReviewer.tsx
└── api/
    ├── plans/route.ts
    └── render/route.ts

tests/jpolitics/                 # 🆕 격리 테스트 디렉토리
├── __init__.py
├── test_models.py
├── test_planner.py
├── test_politician_card.py
├── test_tts_voice_lockin.py
├── test_renderer.py
└── test_e2e.py

data/jpolitics/                  # 🆕 V3 출력 디렉토리 (격리)
data/politician_cards/           # 🆕 인물 카드 캐시
data/jpolitics_reference/        # 🆕 채널 샘플 키프레임 (lock-in 자료)

# 🔧 유일한 기존 파일 수정 (V3 진입 버튼 1개만)
app/page.tsx                     # 헤더 영역에 <button onClick={() => router.push("/jpolitics")}>...</button> 추가

# 📖 기존 파일 read-only import (편집 0)
src/scraper/youtube_news_searcher.py    # yt-dlp 검색·9:16 컷 재사용
src/scraper/naver_image_search.py       # Naver 이미지 검색 재사용
src/analyzer/claude_analyzer.py         # _call_claude 재사용
src/analyzer/gemini_backend.py          # Stage A Gemini 호출 재사용
src/editor/subtitle_split.py            # 자막 분할 알고리즘 재사용
```

**Structure Decision**:
**Option 2 (Web Application) + 격리 패키지 패턴**. 백엔드(`src/jpolitics/`), 프론트엔드(`app/jpolitics/`), 영상 엔진(`src/video/remotion_v3/`)을 모두 신규 디렉토리에 격리. 기존 V1/V2 파일은 0 수정 원칙, 유일한 예외는 사용자 명시 요청에 의한 `app/page.tsx` 진입 버튼 1개. Next.js의 파일 기반 라우팅이 `/jpolitics` URL을 자동 처리하므로 라우터 설정 변경도 불필요.

## Complexity Tracking

> Constitution Check에서 V 원칙(Emotion-Driven)이 부분 통과로 표시되어 정당화 필요.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| V 원칙 감정 4종 대신 **레이아웃 4종** 사용 | 정치 콘텐츠의 차별점은 시각 구조(누가 vs 누구, 데이터 비교)이지 감정 톤이 아님. 채널 @김정치입니다 분석 3편 모두 단일 톤(angry 계열) + 시각 구조 다양화 패턴. | 감정 4종으로 V3를 만들면 정치 쇼츠의 핵심 패턴(VS 카드, 비교 그리드)을 표현할 수 없음. V1 락인 InJoonNeural로 톤 통일은 사용자 명시 lock-in. |
| **격리 모드로 디스크 +35%, LOC +1000** | 기존 V1/V2 0 수정 원칙. Remotion 컴포넌트(Background/Outro/SubtitleBlock) 복제 불가피. | "통합 모드"로 기존 `script_models.py`·`Scene` 확장하면 LOC 절약되나, 297+ 회귀 테스트의 V1/V2 락인이 깨질 위험. 사용자 lock-in: 완전 격리. |
| **별도 Next.js 라우트 `/jpolitics`** + 진입 버튼 1개 추가 | V3는 입력 폼·검수 화면·렌더 API가 V2와 다르므로 기존 `app/page.tsx`의 8개 탭 union에 추가하면 union 타입·핸들러 분기·폼 컴포넌트 모두 수정 필요. | 메인 페이지 탭으로 통합하면 union 타입 + 폼 + API 핸들러 분기 모두 수정 → "완전 격리" 위배. 사용자 lock-in: 진입 버튼 1개만 추가. |
