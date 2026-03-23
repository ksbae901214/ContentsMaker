# ContentsMaker 전체 개발 계획

> 블라인드 인기글을 1분 쇼츠 영상으로 자동 변환하는 파이프라인 시스템

## 시스템 아키텍처

```
[Blind URL] → [Scraper] → [Analyzer] → [TTS] → [Video] → [Upload]
                 ↓            ↓           ↓         ↓         ↓
           raw_content    script.json  voice.mp3  final.mp4  YouTube URL
              .json
```

## 기술 스택 (Constitution 원칙 I 준수: 전부 무료)

| 모듈 | 기술 | 비용 |
|------|------|------|
| Scraper | Playwright (Python) | $0 |
| Analyzer | Claude Code (Sonnet 4.6) | $0 |
| TTS | edge-tts | $0 |
| Video | Remotion (React, 로컬 렌더링) | $0 |
| Upload | YouTube Data API v3 | $0 |

---

## Phase 1: Foundation (기반 구축)

### 목표
프로젝트 초기화 + 핵심 타입 스키마 + Scraper 모듈

### Speckit 워크플로우
```
/speckit.specify  → "프로젝트 초기화 + Scraper 모듈"
/speckit.plan     → 기술 설계 + Constitution Check
/speckit.tasks    → 태스크 분해
/speckit.implement → 구현
```

### 구현 항목

#### 1-1. 프로젝트 초기화
- [ ] Python 환경 설정 (pyproject.toml 또는 requirements.txt)
- [ ] Node.js 환경 설정 (Remotion 프로젝트)
- [ ] 디렉토리 구조 생성
- [ ] .gitignore 작성
- [ ] .env.example 작성

#### 1-2. 핵심 타입 스키마 정의
- [ ] `BlindPost` — 크롤링 결과 (raw_content.json)
- [ ] `ShortsScript` — AI 분석 결과 (script.json)
- [ ] `AudioConfig` — TTS 설정
- [ ] `VideoConfig` — 영상 렌더링 설정

```python
# types.py (Python 측)
@dataclass(frozen=True)
class BlindPost:
    title: str
    author: str       # 익명 (직장명 + 닉네임)
    body: str
    comments: list[dict]  # [{text, likes}]
    url: str

@dataclass(frozen=True)
class ShortsScript:
    metadata: dict    # {title, emotionType, duration}
    scenes: list[dict]  # [{timestamp, duration, type, text, voiceText, emphasis}]
    audio: dict       # {ttsScript, voice, rate, pitch}
    background: dict  # {type, colors}
```

```typescript
// types.ts (Remotion 측)
interface ShortsScript {
  metadata: {
    title: string
    emotionType: 'funny' | 'touching' | 'angry' | 'relatable'
    duration: number
  }
  scenes: Array<{
    id: number
    timestamp: number
    duration: number
    type: 'title' | 'body' | 'comment'
    text: string
    emphasis: 'high' | 'medium' | 'low'
    animation: 'fadeIn' | 'slideUp' | 'typewriter'
  }>
  audio: {
    ttsScript: string
    voice: string
    rate: string
    pitch: string
  }
  background: {
    type: 'gradient'
    colors: string[]
  }
}
```

#### 1-3. Scraper 모듈
- [ ] Playwright 크롤러 구현 (blind_scraper.py)
- [ ] 제목, 본문, 댓글(좋아요순), 작성자 정보 추출
- [ ] raw_content.json 저장
- [ ] 에러 핸들링 (페이지 로드 실패, 요소 미발견)
- [ ] Rate limiting (5초/요청, Constitution 원칙 IV 준수)
- [ ] 테스트: 실제 블라인드 URL 3개로 크롤링 성공 확인

### Phase 1 완료 기준 (Constitution 원칙 VII)
- [ ] `python src/scraper/blind_scraper.py --url <URL>` 실행 → `data/raw/*.json` 생성
- [ ] JSON 파일이 BlindPost 스키마와 일치
- [ ] 3개 이상 URL로 성공 테스트

---

## Phase 2: Analyzer + TTS 모듈

### 목표
Claude Code로 콘텐츠 분석 + edge-tts로 음성 생성

### Speckit 워크플로우
```
/speckit.specify  → "Analyzer + TTS 모듈"
/speckit.plan     → 기술 설계
/speckit.tasks    → 태스크 분해
/speckit.implement → 구현
```

### 구현 항목

#### 2-1. Analyzer 모듈 (Claude Code 연동)
- [ ] 프롬프트 템플릿 작성 (블라인드 글 → ShortsScript JSON)
- [ ] Claude Code headless 모드 호출 (`claude -p`)
- [ ] 감정 분석 (funny/touching/angry/relatable)
- [ ] 60초 분량 요약 + 타임라인 자동 생성
- [ ] 핵심 댓글 2-3개 자동 선별
- [ ] 개인정보 마스킹 (Constitution 원칙 IV)
- [ ] 부적절 콘텐츠 필터링
- [ ] script.json 저장

프롬프트 템플릿 예시:
```
다음 블라인드 게시글을 쇼츠 영상용 스크립트로 변환하세요.

[규칙]
1. 감정 타입 자동 감지 (funny/touching/angry/relatable)
2. 30-60초 분량으로 편집 (도입 5초, 전개 40초, 클라이맥스 10초, 결말 5초)
3. 핵심 메시지만 추출 (제목 + 본문 요약 + 베스트 댓글 1-2개)
4. TTS 친화적으로 텍스트 변환
5. 실명, 직급, 부서명 등 개인정보 제거
6. 욕설, 비속어 순화

[원본 데이터]
{raw_content.json 내용}

[출력 형식]
ShortsScript JSON
```

#### 2-2. TTS 모듈 (edge-tts)
- [ ] edge-tts Python 래퍼 구현
- [ ] 감정별 음성 설정 (Constitution 원칙 V)
  - funny: `ko-KR-BongJinNeural` (+15% 속도)
  - touching: `ko-KR-SunHiNeural` (-10% 속도)
  - angry: `ko-KR-InJoonNeural` (+5% 속도)
  - relatable: `ko-KR-SeoHyeonNeural` (기본)
- [ ] voice.mp3 저장
- [ ] 음성 길이 검증 (30-60초)
- [ ] 에러 핸들링 (네트워크 실패, 텍스트 길이 초과)

```python
# edge_tts_generator.py 핵심 로직
VOICE_CONFIG = {
    'funny': {'voice': 'ko-KR-BongJinNeural', 'rate': '+15%', 'pitch': '+5Hz'},
    'touching': {'voice': 'ko-KR-SunHiNeural', 'rate': '-10%', 'pitch': '-3Hz'},
    'angry': {'voice': 'ko-KR-InJoonNeural', 'rate': '+5%', 'pitch': '-10Hz'},
    'relatable': {'voice': 'ko-KR-SeoHyeonNeural', 'rate': '+0%', 'pitch': '+0Hz'},
}
```

### Phase 2 완료 기준
- [ ] `raw_content.json` → Claude Code → `script.json` 성공 생성
- [ ] `script.json` → edge-tts → `voice.mp3` 성공 생성
- [ ] 음성 재생 확인 (30-60초, 한국어 자연스러움)
- [ ] 3개 이상 샘플로 파이프라인 테스트

---

## Phase 3: Video 모듈 (Remotion)

### 목표
Remotion으로 텍스트 애니메이션 영상 생성 (9:16 세로)

### Speckit 워크플로우
```
/speckit.specify  → "Video 렌더링 모듈"
/speckit.plan     → Remotion 컴포넌트 설계
/speckit.tasks    → 태스크 분해
/speckit.implement → 구현
```

### 구현 항목

#### 3-1. Remotion 프로젝트 초기화
- [ ] `npm create remotion@latest` 실행
- [ ] TypeScript 설정
- [ ] Noto Sans KR 폰트 설정

#### 3-2. 컴포넌트 구현
- [ ] `ShortsComposition.tsx` — 메인 컴포지션 (9:16, 30fps)
- [ ] `TitleScene.tsx` — 제목 표시 (0-5초)
- [ ] `BodyScene.tsx` — 본문 텍스트 (5-50초)
- [ ] `CommentScene.tsx` — 댓글 표시 (50-60초)
- [ ] `Background.tsx` — 감정별 그라데이션 배경
- [ ] `Subtitle.tsx` — 하단 자막

감정별 그라데이션 (Constitution 원칙 V):
```typescript
const GRADIENTS = {
  funny: ['#FF6B6B', '#FFA500', '#FFD93D'],
  touching: ['#6A5ACD', '#9370DB', '#DDA0DD'],
  angry: ['#DC143C', '#8B0000', '#B22222'],
  relatable: ['#4169E1', '#1E90FF', '#87CEEB'],
}
```

#### 3-3. 렌더링 파이프라인
- [ ] Python → Remotion 호출 (subprocess)
- [ ] script.json + voice.mp3 입력 → final.mp4 출력
- [ ] 렌더링 설정: 1080x1920, 30fps, h264 codec

### Phase 3 완료 기준
- [ ] `script.json` + `voice.mp3` → Remotion → `final.mp4` 성공 생성
- [ ] 영상 재생 확인 (9:16, 30-60초, 텍스트 가독성)
- [ ] 음성과 텍스트 동기화 확인 (±1초 이내)
- [ ] 4종 감정 각 1개씩 총 4개 영상 생성 테스트

---

## Phase 4: 통합 파이프라인

### 목표
전체 파이프라인 통합 + CLI 인터페이스

### Speckit 워크플로우
```
/speckit.specify  → "통합 파이프라인 + CLI"
/speckit.plan     → 통합 설계
/speckit.tasks    → 태스크 분해
/speckit.implement → 구현
```

### 구현 항목

#### 4-1. 통합 실행 스크립트
- [ ] `main.py` — 전체 파이프라인 통합
- [ ] CLI 인터페이스 (argparse)
  - `python main.py --url <BLIND_URL>` — 단일 URL
  - `python main.py --batch <URLS_FILE>` — 배치 처리
  - `python main.py --from-json <SCRIPT_JSON>` — 특정 단계부터 실행
- [ ] 에러 핸들링 + 로깅

#### 4-2. 배치 처리
- [ ] 여러 URL 순차 처리
- [ ] 실패한 URL 스킵 + 로그 기록
- [ ] 중간 산출물 보존 (Constitution 원칙 II)

### Phase 4 완료 기준
- [ ] `python main.py --url <URL>` → `data/outputs/*.mp4` 자동 생성
- [ ] 5개 URL 배치 테스트 성공
- [ ] 실패 케이스 포함 시에도 나머지 정상 처리

---

## Phase 5: 자동화 + 업로드 (선택)

### 목표
크롤링 자동화 + YouTube 자동 업로드

### 구현 항목

#### 5-1. 크롤링 자동화
- [ ] 블라인드 인기글 자동 수집 (cron/스케줄러)
- [ ] 인기도 기준 필터링 (좋아요 N개 이상)
- [ ] 중복 방지 (이미 생성한 글 스킵)

#### 5-2. YouTube 업로드
- [ ] YouTube Data API v3 OAuth 인증
- [ ] 자동 업로드 + 메타데이터 설정
- [ ] 썸네일 자동 생성 (Pillow)

#### 5-3. Pexels 스톡 배경 (Phase 2 배경 업그레이드)
- [ ] Pexels API 통합
- [ ] 감정별 검색 키워드 매핑
- [ ] 배경 영상 다운로드 + 블러 처리

---

## 프로젝트 디렉토리 구조

```
ContentsMaker/
├── .claude/
│   └── commands/
│       └── speckit.*.md          # Speckit 명령어 (9개)
│
├── .specify/
│   ├── memory/
│   │   └── constitution.md       # 프로젝트 헌법
│   ├── templates/                # 명세 템플릿
│   ├── scripts/bash/             # 유틸리티 스크립트
│   └── features/                 # 기능별 명세
│       ├── 001-scraper/
│       │   ├── spec.md
│       │   ├── plan.md
│       │   └── tasks.md
│       ├── 002-analyzer-tts/
│       ├── 003-video/
│       ├── 004-pipeline/
│       └── 005-automation/
│
├── src/
│   ├── scraper/
│   │   ├── __init__.py
│   │   └── blind_scraper.py      # Playwright 크롤러
│   │
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── claude_analyzer.py    # Claude Code 호출
│   │   └── prompt_templates.py   # 프롬프트 템플릿
│   │
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── edge_tts_generator.py # edge-tts 래퍼
│   │   └── voice_config.py       # 감정별 음성 설정
│   │
│   ├── video/
│   │   └── remotion/             # Remotion 프로젝트
│   │       ├── package.json
│   │       ├── tsconfig.json
│   │       └── src/
│   │           ├── Root.tsx
│   │           ├── ShortsComposition.tsx
│   │           ├── components/
│   │           │   ├── TitleScene.tsx
│   │           │   ├── BodyScene.tsx
│   │           │   ├── CommentScene.tsx
│   │           │   ├── Background.tsx
│   │           │   └── Subtitle.tsx
│   │           └── types.ts
│   │
│   ├── upload/
│   │   ├── __init__.py
│   │   └── youtube_uploader.py   # YouTube API (Phase 5)
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── emotions.py           # 감정별 설정
│   │   └── settings.py           # 전역 설정
│   │
│   └── main.py                   # CLI 진입점
│
├── data/
│   ├── raw/                      # raw_content.json
│   ├── scripts/                  # script.json
│   ├── audio/                    # voice.mp3
│   ├── backgrounds/              # 배경 영상/이미지
│   └── outputs/                  # final.mp4
│
├── assets/
│   └── bgm/                      # 배경음악 (Phase 2)
│
├── tests/
│   ├── test_scraper.py
│   ├── test_analyzer.py
│   ├── test_tts.py
│   └── test_pipeline.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── prompt_plan.md                # 이 파일
└── README.md
```

---

## 비용 요약

| Phase | 영상 1개당 비용 | 월간 (일 5개) |
|-------|----------------|--------------|
| Phase 1-4 | **$0** | **$0** |
| Phase 5 (Lambda 사용 시) | $0.02 | $3 |

---

## 개발 순서 요약

```
Phase 1: Foundation
  /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
  결과: Scraper 동작, raw_content.json 생성

Phase 2: Analyzer + TTS
  /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
  결과: script.json + voice.mp3 생성

Phase 3: Video
  /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
  결과: final.mp4 생성

Phase 4: Pipeline
  /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
  결과: URL → MP4 원커맨드 실행

Phase 5: Automation (선택)
  /speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
  결과: 크롤링 자동화 + YouTube 업로드
```

---

**작성일**: 2026-03-23
**Constitution 버전**: 1.0.0
**다음 단계**: `/speckit.specify` → Phase 1 기능 명세 작성
