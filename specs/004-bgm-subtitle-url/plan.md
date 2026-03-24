# Implementation Plan: BGM + 자막 줄바꿈 + URL 소스 확장

**Branch**: `004-bgm-subtitle-url` | **Date**: 2026-03-25 | **Spec**: [spec.md](./spec.md)

## Summary

3개 기능을 독립 모듈로 구현: (1) 감정별 BGM 자동 삽입 + 웹UI 체크박스, (2) 문맥 기반 자막 줄바꿈 + 키워드 하이라이트, (3) 디시인사이드/네이트판/네이버카페 URL 파싱 + 웹UI 탭.

## Technical Context

**Language/Version**: Python 3.11+ (백엔드), TypeScript + React (Remotion 영상)
**Primary Dependencies**: edge-tts, Remotion, Playwright, Next.js 16
**Storage**: JSON 파일 기반 (`data/` 디렉토리), MP3 BGM (`data/bgm/`)
**Testing**: pytest (Python), Remotion still 렌더링 (영상 확인)
**Target Platform**: macOS (개발), Cloudflare Tunnel (배포)
**Project Type**: web-service + cli + video-renderer
**Constraints**: 영상 생성 5분 이내, BGM 로열티프리만 사용
**Scale/Scope**: 3개 사이트 파서, 4개 BGM, 4개 하이라이트 색상

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 검증 | 결과 |
|------|------|------|
| I. Zero-Cost | BGM = Pixabay 무료, Playwright = 무료, 키워드색상 = CSS | PASS |
| II. Pipeline Integrity | BGM/줄바꿈은 기존 파이프라인 단계에 옵션 추가, URL은 새 입력 단계 | PASS |
| III. Text-First | 줄바꿈으로 가독성 향상, BGM은 배경 15% 볼륨 | PASS |
| IV. Content Safety | URL 크롤링 시 robots.txt 준수, 5초 간격 | PASS |
| V. Emotion-Driven | 감정별 BGM + 키워드 하이라이트 색상 매핑 | PASS |
| VI. Modularity | 각 기능 독립 모듈: bgm_config.py, url_scraper.py, parsers/ | PASS |
| VII. Evidence-Based | 3개 사이트 × 1개 URL 테스트 + BGM ON/OFF 영상 생성 확인 | PASS |

**전체 PASS — Phase 0 진행.**

## Project Structure

### Documentation (this feature)

```text
specs/004-bgm-subtitle-url/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── tts/
│   ├── voice_config.py        # 기존 — BGM 매핑 추가
│   └── edge_tts_generator.py  # 기존 유지
├── analyzer/
│   └── prompt_template.py     # 기존 — 줄바꿈 + 키워드 지시 추가
├── scraper/
│   ├── url_scraper.py         # 신규 — URL → BlindPost 변환 허브
│   └── parsers/               # 신규 — 사이트별 파서
│       ├── __init__.py
│       ├── dcinside.py
│       ├── natepann.py
│       └── naver_cafe.py
├── video/
│   ├── renderer.py            # 기존 — BGM 파일 복사 + props 전달
│   └── remotion/src/
│       ├── ShortsComposition.tsx  # 기존 — BGM Audio 레이어 추가
│       └── components/
│           └── SceneText.tsx      # 기존 — 키워드 하이라이트 렌더링
├── main.py                    # 기존 — url 서브커맨드 + --no-bgm 옵션 추가

app/
├── page.tsx                   # 기존 — BGM 체크박스 + URL 탭 추가
└── api/generate/route.ts      # 기존 — bgm/url 모드 처리 추가

data/
└── bgm/                       # 신규 — 감정별 BGM MP3 4개
    ├── funny.mp3
    ├── touching.mp3
    ├── angry.mp3
    └── relatable.mp3
```

**Structure Decision**: 기존 프로젝트 구조를 유지하며 신규 모듈만 추가. `src/scraper/parsers/`만 새 디렉토리.
