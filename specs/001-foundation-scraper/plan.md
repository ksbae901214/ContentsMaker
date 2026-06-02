# Implementation Plan: Foundation - Project Init + Blind Scraper

**Branch**: `001-foundation-scraper` | **Date**: 2026-03-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-foundation-scraper/spec.md`

## Summary

프로젝트 초기화 + 수동/자동 2가지 방식의 블라인드 글 수집 모듈 구현. **수동 입력(P1)**을 먼저 구현하여 파이프라인 개발을 즉시 시작할 수 있게 하고, **자동 크롤링(P2)**은 이후 추가한다. 핵심은 두 방식 모두 동일한 BlindPost JSON 스키마를 출력하는 것.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: dataclasses (내장), argparse (내장), Playwright (P2 자동 크롤링용)
**Storage**: JSON 파일 (`data/raw/` 디렉토리)
**Testing**: pytest
**Target Platform**: macOS (로컬 개발), Linux 호환
**Project Type**: CLI 도구 (파이프라인의 첫 모듈)
**Performance Goals**: 단일 게시글 처리 30초 이내
**Constraints**: Python 표준 라이브러리 최대한 활용, 외부 의존성 최소화 (P1은 외부 패키지 0개)
**Scale/Scope**: 일 10-50개 게시글 처리

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 상태 | 근거 |
|------|------|------|
| I. Zero-Cost Pipeline | ✅ Pass | P1 수동 입력: 외부 패키지 0개, 비용 $0. P2 Playwright: 무료 오픈소스 |
| II. Pipeline Integrity | ✅ Pass | JSON 파일 기반 데이터 교환. 수동/자동 모두 동일 스키마 출력 |
| III. Text-First Video | ✅ N/A | Scraper 모듈에 해당 없음 (영상 모듈에서 적용) |
| IV. Content Safety | ✅ Pass | P2에서 크롤링 윤리 준수 (5초 간격, User-Agent). 필터링은 Analyzer 모듈 담당 |
| V. Emotion-Driven | ✅ N/A | Scraper에 해당 없음 (Analyzer에서 감정 분석) |
| VI. Modularity | ✅ Pass | 모듈 독립 실행 가능. 수동/자동 입력은 별도 파일로 분리 |
| VII. Evidence-Based | ✅ Pass | 샘플 JSON 5개 이상으로 검증 예정 |

## Project Structure

### Documentation (this feature)

```text
specs/001-foundation-scraper/
├── spec.md
├── plan.md              # 이 파일
├── data-model.md
├── tasks.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/
├── scraper/
│   ├── __init__.py
│   ├── models.py          # BlindPost, Comment 데이터 클래스
│   ├── validator.py       # JSON 스키마 검증
│   ├── manual_input.py    # P1: 수동 입력 (JSON 파일 / 대화형)
│   └── auto_crawler.py    # P2: Playwright 자동 크롤링
├── config/
│   ├── __init__.py
│   └── settings.py        # 경로, 상수 설정
└── main.py                # CLI 진입점

data/
└── raw/                   # 출력 JSON 파일

tests/
├── test_models.py
├── test_validator.py
├── test_manual_input.py
└── samples/               # 테스트용 샘플 JSON
    ├── valid_post.json
    ├── valid_no_comments.json
    ├── invalid_missing_title.json
    └── invalid_bad_json.json
```

**Structure Decision**: CLI 파이프라인 도구이므로 단일 프로젝트(Option 1) 구조 선택. `src/scraper/` 하위에 수동 입력과 자동 크롤링을 별도 파일로 분리하여 독립 실행 가능하게 한다.

## Data Model

### BlindPost

```python
@dataclass(frozen=True)
class Comment:
    text: str               # 댓글 내용
    likes: int              # 좋아요 수
    author: str             # "직장명 · 닉네임"

@dataclass(frozen=True)
class BlindPost:
    title: str              # 게시글 제목
    author: str             # "직장명 · 닉네임"
    body: str               # 본문 전체 텍스트
    comments: list[Comment] # 좋아요순 상위 10개
    url: str                # 원본 URL (수동 입력 시 빈 문자열)
    created_at: str         # ISO 8601 (크롤링/입력 시각)
```

### JSON 출력 예시

```json
{
  "title": "곧 부동산 피바람 불 거다",
  "author": "부동산 · 빵코코",
  "body": "미국 부채를 돌려막기 하고있는 시점에서...",
  "comments": [
    {"text": "ㅋㅋ", "likes": 7, "author": "DB하이텍 · qRPi60"},
    {"text": "어그로나?", "likes": 3, "author": "NH농협은행 · ljdhiljili"}
  ],
  "url": "",
  "created_at": "2026-03-23T16:13:00+09:00"
}
```

## CLI Interface

```bash
# P1: 수동 입력 - JSON 파일 직접 지정
python src/main.py manual --file path/to/post.json

# P1: 수동 입력 - 대화형 모드
python src/main.py manual --interactive

# P2: 자동 크롤링
python src/main.py crawl --url "https://www.teamblind.com/kr/post/..."

# P2: 자동 크롤링 - 배치
python src/main.py crawl --urls-file urls.txt
```

## Complexity Tracking

> Constitution Check 위반 없음. 추가 정당화 불필요.
