# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 인기글을 만화 스타일 YouTube Shorts 영상으로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-03-24

---

## 시스템 아키텍처

```
스크린샷/텍스트 → [Scraper] → [Analyzer] → [Illustrator] → [TTS] → [Video] → MP4
                    ↓            ↓              ↓             ↓         ↓
               raw.json     script.json    scene_XX.png   voice.mp3  final.mp4
```

## 기술 스택

| 모듈 | 기술 | 비용 |
|------|------|------|
| OCR | Claude Code (Sonnet 4.6) | $0 |
| 분석 | Claude Code (headless) | $0 |
| 이미지 | GPT Image (`gpt-image-1`, low) | ~$0.005/장 |
| TTS | edge-tts (Microsoft Edge) | $0 |
| 영상 | Remotion (React, 로컬) | $0 |
| 웹 UI | Next.js 16 + Tailwind | $0 |

---

## Phase 1: Foundation ✅ 완료

**브랜치**: `001-foundation-scraper`

### 완료 항목
- [x] Python 프로젝트 구조 + 설정
- [x] `BlindPost` 데이터 모델 (frozen dataclass)
- [x] 수동 입력 모듈 (`manual_input.py`)
- [x] JSON 파일 로드/저장
- [x] 입력 검증 (`validator.py`)
- [x] 테스트: models, manual_input, validator

---

## Phase 2: Analyzer + TTS ✅ 완료

**브랜치**: `002-analyzer-tts`

### 완료 항목
- [x] Claude Code headless 분석 (`claude -p --output-format json`)
- [x] 프롬프트 템플릿 (감정 감지, 씬 분할, 개인정보 마스킹)
- [x] `ShortsScript` 모델 (Metadata, Scene, AudioConfig, BackgroundConfig)
- [x] edge-tts 음성 생성 (async)
- [x] 감정별 음성/그라데이션 설정 (`voice_config.py`)
- [x] 테스트: analyzer, script_models, tts

---

## Phase 3: Video + 이미지 + 웹 UI ✅ 완료

**브랜치**: `003-video-remotion`

### 완료 항목

#### 영상 렌더링 (Remotion)
- [x] Remotion 프로젝트 초기화 (`src/video/remotion/`)
- [x] `ShortsComposition.tsx` — 메인 컴포지션 (1080x1920, 30fps)
- [x] `SceneText.tsx` — 텍스트 오버레이 (55px 균일, 중앙 10% 하단)
- [x] `Background.tsx` — 감정별 그라데이션 애니메이션
- [x] `renderer.py` — Python → Remotion CLI 래퍼
- [x] 1.2배속 재생 (TTS + 영상 동기화)

#### 만화 이미지 생성 (GPT Image)
- [x] `image_generator.py` — GPT Image API (`gpt-image-1`, 1024x1536, low)
- [x] `prompt_builder.py` — 씬별 웹툰 스타일 프롬프트 (Claude Code 생성)
- [x] `reference_manager.py` — 레퍼런스 이미지 자동 선택
- [x] `images.edit()` API로 스타일 일관성 (레퍼런스 있을 때)
- [x] `images.generate()` 폴백 (레퍼런스 없을 때)

#### 웹 UI (Next.js)
- [x] 메인 페이지 (스크린샷 드래그 앤 드롭 + 직접 입력)
- [x] `/api/generate` — SSE 스트리밍 진행상황
- [x] `/api/download` — 영상 다운로드
- [x] `/api/stats` — 사용 통계
- [x] 이미지 경로 직접 전달 (glob 재탐색 버그 수정)

#### CLI 통합
- [x] `image` 서브커맨드 — 스크린샷 → 영상 풀 파이프라인
- [x] `manual` 서브커맨드 — 수동 입력
- [x] `analyze`, `tts`, `render` 개별 실행
- [x] `pipeline` 서브커맨드 — raw JSON → 영상
- [x] `--no-references` 옵션

#### TTS/영상 튜닝 (2026-03-24)
- [x] TTS: 모든 감정 → `ko-KR-SunHiNeural` (젊은 여성)
- [x] TTS 속도: 모든 감정 → `+20%` (1.2배속)
- [x] 영상 속도: `SPEED_FACTOR=1.2` (씬 타이밍 1/1.2 압축)
- [x] 텍스트: 55px 균일 크기 (emphasis 무관)
- [x] 텍스트 위치: 화면 중앙에서 10% 아래 (192px offset)

#### 배포
- [x] GitHub Private 레포: `ksbae901214/ContentsMaker`
- [x] Cloudflare Tunnel → `cmaker.store-daehaeng.com`

---

## Phase 4: 자동화 + 업로드 📋 미착수

### 계획 항목
- [ ] 블라인드 인기글 자동 수집 (cron)
- [ ] 인기도 기준 필터링
- [ ] YouTube Data API v3 OAuth + 자동 업로드
- [ ] 썸네일 자동 생성

---

## 현재 설정 요약

### 영상 출력
- 해상도: 1080x1920 (9:16 세로)
- FPS: 30
- 속도: 1.2배속
- 코덱: H.264

### TTS
- 음성: `ko-KR-SunHiNeural` (젊은 여성, 모든 감정 동일)
- 속도: `+20%` (1.2배속)

### 이미지
- 모델: `gpt-image-1`
- 크기: 1024x1536 (2:3)
- 품질: low ($0.005/장)
- 스타일: 한국 웹툰/소셜툰

### 텍스트 오버레이
- 크기: 55px (균일)
- 위치: 화면 중앙 + 10% 아래
- 색상: 흰색 (#FFFFFF)
- 그림자: 3px 3px 8px rgba(0,0,0,0.7)

### 감정별 그라데이션
| 감정 | 색상 |
|------|------|
| funny | #FF6B6B → #FFA500 → #FFD93D |
| touching | #6A5ACD → #9370DB → #DDA0DD |
| angry | #DC143C → #8B0000 → #B22222 |
| relatable | #4169E1 → #1E90FF → #87CEEB |
