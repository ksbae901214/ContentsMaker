# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 인기글을 만화 스타일 YouTube Shorts 영상으로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-04-02

---

## 시스템 아키텍처

```
스크린샷/텍스트/주제 → [Scraper] → [Analyzer] → [Illustrator/VideoGen] → [TTS] → [Video] → MP4
                         ↓            ↓              ↓                    ↓         ↓
                    raw.json     script.json    scene_XX.png/mp4      voice.mp3  final.mp4
```

## 기술 스택

| 모듈 | 기술 | 비용 |
|------|------|------|
| OCR | Claude Code (Sonnet 4.6) | $0 |
| 분석 | Claude Code (headless) | $0 |
| 이미지 | GPT Image (`gpt-image-1`, low) | ~$0.005/장 |
| AI 영상 | Seedance 2.0 API | ~$0.05/클립 (720p) |
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

## Phase 5: 씬 편집기 + 데이터 확장 ✅ 완료

**브랜치**: `005-video-editor-upgrade`

### 완료 항목
- [x] SubtitleStyle, TransitionConfig, SfxConfig 데이터 모델
- [x] scene_ops.py (split, merge, reorder, resize)
- [x] Scene editing API endpoints
- [x] Punctuation-based speech pacing (Rule 11)
- [x] Per-scene TTS timing

---

## Phase 6: 영상 쇼츠 모드 ✅ 구현 완료

**참고 영상**: [사물의 잔소리 - 즐겨 먹던 과자들의 배신](https://youtube.com/shorts/tdG-XNOzigM)

**핵심 변경 2가지:**
1. **범용 주제 입력** — 블라인드 외 자유 주제(과자, 일상 등) 지원
2. **AI 영상 생성** — Seedance API로 씬마다 3-5초 동영상 클립 생성

**기존 인프라 활용:** `visual_type`/`motion_prompt` 필드, `SceneWithVideo.tsx`, `video_gen/` 모듈, `ShortsComposition`의 `sceneVideos` prop이 이미 스켈레톤으로 존재.

### 6-1. 범용 주제 입력 ✅

- [x] `TopicInput` 모델 (`src/scraper/topic_input.py` 신규)
  - frozen dataclass: topic, style(narration/skit/review), tone, details
  - `save_topic()` → `data/raw/{timestamp}_{topic}.json`
- [x] `TOPIC_ANALYZE_PROMPT` + `build_topic_prompt()` (`src/analyzer/prompt_template.py`)
  - 블라인드 전용 규칙 제거, 스토리텔링 규칙으로 대체
  - 10개 규칙 (text 줄바꿈, highlight_words, 발화 리듬, 스토리텔링 등)
- [x] `analyze_topic()` 함수 (`src/analyzer/claude_analyzer.py`)
  - 기존 `_parse_response()`, `_apply_voice_config()` 재사용
- [x] `Metadata.source_type` 추가 (`src/analyzer/script_models.py`)
  - `"blind" | "topic"`, 기본값 "blind" (역호환)

### 6-2. 이미지 스타일 프리셋 ✅

- [x] `IMAGE_STYLE_PRESETS` 딕셔너리 추가 (`src/illustrator/prompt_builder.py`)
  - webtoon (기존 STYLE_PREFIX), 3d_pixar, realistic, anime 4종
  - 각 프리셋에 "NO text/letters/numbers" 안전장치 포함
- [x] `build_image_prompts(script, image_style="webtoon")` 파라미터 추가
- [x] `build_image_prompts_simple()`에도 동일 적용
- [x] 스타일에 따라 프롬프트 프리픽스 동적 변경
- [x] 레퍼런스 이미지는 webtoon 스타일에서만 적용 (비-웹툰은 `use_references=False`)
- [x] `generate_scene_images()`에 `image_style` 파라미터 추가

### 6-3. Seedance API 구현 ✅

- [x] `SeedanceGenerator` 완전 구현 (`src/video_gen/seedance_gen.py`)
  - `generate()`: httpx POST, API 키 검증, 에러 핸들링
  - `get_status()`: 폴링, 상태/진행률/에러 반환
  - `download()`: 스트리밍 다운로드, 파일 저장
  - lazy httpx.AsyncClient (Base URL + Bearer Auth)
- [x] `VideoGeneratorBase.generate_and_wait()` 기본 구현 추가 (`src/video_gen/base.py`)
  - generate → poll → download 통합 루프
  - `VideoGenerationError` 예외 클래스 추가
  - 타임아웃(max_wait), 폴링 간격(poll_interval) 지원
- [x] `httpx>=0.27.0` 의존성 추가 (`requirements.txt`)
- **참고**: 실제 API 호출은 `SEEDANCE_API_KEY` 발급 후 E2E 테스트 필요

**비용 모델:**
| 해상도 | 5초 클립 | 5씬 영상 |
|--------|---------|---------|
| 720p   | $0.05   | $0.25   |
| 1080p  | $0.25   | $1.25   |

### 6-4. 파이프라인 분기 ✅

- [x] `generate/route.ts`에 `mode="topic"` + `visualMode="manga"|"video"` + `imageStyle` 분기
  - topic → save_topic() → analyze_topic()
  - 기존 → 기존 로직 → analyze()
  - video → Seedance per scene → scene_videos (실패 시 폴백 메시지)
  - manga → GPT Image (imageStyle 적용) → scene_images
- [x] `generate/route.ts`에서 `imageStyle` 파라미터를 `generate_scene_images()`에 전달
- [x] `renderer.py`에 `scene_videos` 파라미터 + public/ 복사 로직
- [x] `DATA_VIDEOS_DIR` 추가 (`src/config/settings.py`)
- [x] 결과 done 이벤트에 `videoCount`, `visualMode`, `imageStyle`, `sourceType` 포함

### 6-5. UI 업데이트 ✅

- [x] 비주얼 모드 토글: `[🖼️ 이미지 쇼츠 ~$0.005/씬] | [🎥 영상 쇼츠 ~$0.05/씬]`
- [x] 이미지 스타일 선택 (이미지 모드일 때): 웹툰 | 3D Pixar | 실사풍 | 애니메
- [x] 주제 입력 탭 (4번째 탭): 주제, 콘텐츠 스타일(나레이션/스킷/리뷰), 톤, 추가 설명
- [x] 결과 화면: 비주얼 모드별 표시 ("이미지 X장" vs "영상 클립 X개")
- [x] 헤더 변경: "인기글/자유주제 → 만화 쇼츠 자동 생성"
- [x] 모든 탭(image/manual/url/topic)에 visualMode + imageStyle FormData 전달

### 6-6. 테스트 ✅

- [x] `tests/test_topic_input.py` — TopicInput 모델, 직렬화, save_topic() (신규)
- [x] `tests/test_seedance_gen.py` — httpx mock, estimate_cost, polling (신규)
- [x] `tests/test_prompt_template_topic.py` — build_topic_prompt() 검증 (신규)
- [x] `tests/test_analyzer_topic.py` — analyze_topic() mock, source_type (신규)
- [x] `tests/test_script_models.py` 수정 — source_type 역호환, camelCase, 라운드트립
- [x] `tests/test_renderer.py` 수정 — scene_videos props, 이미지+비디오 동시, public/ 복사
- [x] `tests/test_analyzer_extended.py` 수정 — analyze() 반환값 (script, path) 튜플 대응

### E2E 검증 체크리스트
- [ ] 기존 웹툰 모드: 스크린샷 → 만화 영상 (변경 없이 동작)
- [ ] 3D Pixar 스타일: 주제 입력 → 3D 이미지 → 영상 렌더링
- [ ] 주제 모드 + 이미지: 주제 입력 → 스타일별 이미지 → 영상 렌더링
- [ ] 주제 모드 + 영상: 주제 입력 → Seedance 영상 클립 → 영상 렌더링
- [ ] 블라인드 모드 + 영상: 스크린샷 → Seedance 영상 클립 → 영상 렌더링
- [ ] 이미지 스타일 전환 시 프롬프트 올바르게 변경
- [ ] 비용 표시 정확성
- [ ] SEEDANCE_API_KEY 미설정 시 에러 메시지
- [ ] 영상 생성 실패 시 이미지 모드 폴백 제안

### 수정 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `src/scraper/topic_input.py` | **신규** — TopicInput 모델 + save_topic() |
| `src/analyzer/prompt_template.py` | TOPIC_ANALYZE_PROMPT, build_topic_prompt(), Rule 12 |
| `src/analyzer/claude_analyzer.py` | analyze_topic(), visual_mode 파라미터 |
| `src/analyzer/script_models.py` | Metadata.source_type 추가 |
| `src/illustrator/prompt_builder.py` | IMAGE_STYLE_PRESETS 딕셔너리, image_style 파라미터 |
| `src/video_gen/seedance_gen.py` | Seedance API 완전 구현 (API 키 발급 후) |
| `src/video_gen/base.py` | generate_and_wait() 추가 |
| `requirements.txt` | httpx 추가 |
| `app/api/generate/route.ts` | topic 모드 + video 분기 + imageStyle 전달 |
| `src/video/renderer.py` | scene_videos 파라미터 + 복사 로직 |
| `app/page.tsx` | 모드 토글, 이미지 스타일 선택, 주제 탭, 진행 표시 |

### 구현 순서

```
6-1 (주제 입력) ──┐
6-2 (이미지 스타일)┼──→ 6-4 (파이프라인 분기) → 6-5 (UI) → 6-6 (테스트)
6-3 (Seedance) ──┘
```

- **6-1 + 6-2는 API 키 없이 바로 착수 가능** (우선순위 높음)
- **6-3(Seedance)은 API 키 발급 후 구현**
- 6-4는 6-1+6-2 완료 후 (Seedance는 나중에 연결)
- 6-5(UI), 6-6(테스트)은 순차 진행

---

## Phase 7: deevid.ai 브라우저 자동화 (Veo 3.1) ✅ 구현 완료

**배경**: Seedance 2.0 API는 2026-03 할리우드 저작권 이슈로 해외 채널이 대거 중단됨 (laozhang.ai 503, 공식 Volcengine은 중국 ID 필요). deevid.ai는 무료 20 크레딧으로 Veo 3.1 (Master V2.0)을 제공하므로 브라우저 자동화로 활용한다.

**제약**: 무료 티어 (워터마크 + 720p, 20 크레딧 일회성), 1회 수동 로그인 필요, ToS 미명시 (개인용 사용 전제).

### 7-1. 기반 설정 ✅
- [x] `playwright>=1.49.0` 의존성 추가
- [x] `DEEVID_PROFILE_DIR`, `DEEVID_URL`, `DEEVID_HEADLESS` 설정 추가
- [x] `.gitignore`에 `.cache/` 추가

### 7-2. DeevidGenerator ✅
- [x] `src/video_gen/deevid_gen.py` (신규) — `generate_and_wait()` 직접 오버라이드 방식
- [x] `src/video_gen/deevid_selectors.py` (신규) — UI selector 외부화 (Mantine framework 기반)
- [x] 추상 메서드 `generate/get_status/download`는 `NotImplementedError` (브라우저 세션은 호출당 단일)
- [x] `_ensure_logged_in`, `_submit_prompt`, `_wait_for_completion`, `_download_video` 헬퍼
- [x] 9:16 aspect ratio 자동 선택 시도, 실패 시 16:9로 진행
- [x] "Out of credits" 감지 → 친절한 에러 메시지

### 7-3. CLI 로그인 도우미 ✅
- [x] `python3 -m src.main deevid_login` 서브커맨드
- [x] headed 브라우저로 deevid.ai 열기 → 사용자 수동 로그인 → Enter로 종료
- [x] persistent context를 `.cache/deevid_profile/`에 저장

### 7-4. 팩토리 + 파이프라인 통합 ✅
- [x] `src/video_gen/factory.py` — lazy import로 `deevid` 등록 (playwright는 무거우니 필요할 때만)
- [x] `app/api/generate/route.ts` — `videoProvider` FormData 분기, deevid 선택 시 프로필 존재 확인
- [x] `app/page.tsx` — 영상 모드 시 provider 토글 UI (deevid / seedance)
- [x] 모든 탭(image/manual/url/topic) FormData에 `videoProvider` 전달

### 7-5. 테스트 ✅
- [x] `tests/test_deevid_gen.py` (신규, 12개)
  - estimate_cost 0.0 검증
  - stub 메서드 NotImplementedError 검증
  - precondition (output_path, profile_dir) 검증
  - playwright 완전 mock으로 success flow + no_credits flow E2E
  - selectors 모듈 임포트 가능 검증
- [x] `tests/test_seedance_gen.py` 수정 — `asyncio.get_event_loop()` → `asyncio.run()` (deprecation 정리)
- [x] **197/197 통과** (기존 185 + 신규 12)

### 7-6. 사용 흐름

```bash
# 1. 의존성 설치 (최초 1회)
pip install -r requirements.txt
playwright install chromium

# 2. deevid.ai 로그인 (최초 1회)
python3 -m src.main deevid_login
# → 브라우저 창에서 Google OAuth 로그인 → 터미널에서 Enter

# 3. 영상 생성
# 웹 UI: 비주얼 모드 "영상" → 제공업체 "deevid.ai" 선택 → 생성
```

### 수정/신규 파일 요약

| 파일 | 변경 |
|------|------|
| `requirements.txt` | + playwright>=1.49.0 |
| `.gitignore` | + .cache/ |
| `src/config/settings.py` | + DEEVID_PROFILE_DIR, DEEVID_URL, DEEVID_HEADLESS |
| `src/video_gen/deevid_gen.py` | **신규** — DeevidGenerator + interactive_login |
| `src/video_gen/deevid_selectors.py` | **신규** — UI selector dict |
| `src/video_gen/factory.py` | + deevid lazy import 등록 |
| `src/main.py` | + deevid_login 서브커맨드 |
| `app/api/generate/route.ts` | + videoProvider 분기, profile 존재 사전 체크 |
| `app/page.tsx` | + videoProvider 토글 UI (영상 모드 시) |
| `tests/test_deevid_gen.py` | **신규** — 12개 mocked tests |
| `tests/test_seedance_gen.py` | asyncio.run() 마이그레이션 |

### 알려진 제약 / 후속 작업

- **Selector 안정성**: deevid.ai UI 변경 시 `deevid_selectors.py`만 수정하면 됨
- **Cloudflare/봇 탐지**: 현재는 미적용. 문제 발생 시 `playwright-stealth` 통합 검토
- **download_button selector**: 로그인 + 실제 생성 후 검증 필요 (현재는 best-guess)
- **무료 크레딧 소진**: 20 크레딧 → 약 3개 영상 분량. 소진 시 재가입 또는 유료 전환

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
