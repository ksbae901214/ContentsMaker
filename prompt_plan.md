# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 인기글을 만화 스타일 YouTube Shorts 영상으로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-04-20

---

## 🚧 진행 중: TRIM-01 NATV 씬 구간 드래그 트리밍 (2026-04-20 확정)

### 목표
Vrew 스타일 듀얼 핸들 프로그레스바로 씬 영상의 앞/뒤 경계를 조정.
**NATV 클립 모드에만** 적용. 다른 모드(image/manual/url/topic/political/video)는 현재 동작 유지.

### 아키텍처 요약
- 재인코딩 없이 **Remotion `<Video startFrom endAt>` + 오프셋 메타데이터**로 해결
- 사전 cut된 파일은 프리뷰 캐시로만 사용, 최종 렌더는 원본 + offset
- `Scene` 에 `source_video/source_start/source_end` 3개 Optional 필드 추가 (후방 호환)

### 단계

- **Phase 1** 백엔드 — Scene 필드 + 직렬화 + SceneWithVideo.tsx `<Video startFrom endAt>` 전환
- **Phase 2** NATV cut 루프 리팩터 — offset 기록, 렌더 시 원본+offset 경로 사용
- **Phase 3** `/api/scene/trim` API — 유효성 + 스크립트 저장
- **Phase 4** TrimSlider 컴포넌트 — 듀얼 핸들 range + `<video>` 프리뷰
- **Phase 5** SceneEditor 통합 — NATV 씬에만 "구간 편집" 버튼 노출
- **Phase 6** UX 보강 — TTS 길이 경고, 자동 맞춤, 키보드 스냅

### 복잡도: MEDIUM (12-16h)

---

## ✅ 완료: MID-05 썸네일 자동 생성 (2026-04-17 확정)

**출처**: `docs/dem-shorts/political-youtube-style-plan.md` §5.1, §8.2 MID-05
**목표**: 정치 유튜브 표준 썸네일(hook 씬 프레임 + 빨강/노랑 텍스트)을 자동 생성해 CTR 향상.

### 확정 사항 (2026-04-17)
- **Q1 이미지 소스**: A안 — hook 씬 프레임 캡처 (ffmpeg `-ss 0.8 -frames 1`)
- **Q2 텍스트 오버레이**: Pretendard ExtraBold, **상단 25% + 100px 오프셋** (사용자 조정), 빨강(#DC143C)/노랑(#FFD93D) 2행, 외곽선 10px 검정
- **Q3 화살표/동그라미**: v1 제외 (opt-in 자리만 남김, v3 예정)
- **Q4 YouTube 업로드**: v1 로컬 PNG만 저장 + `--upload-thumbnail` 플래그 자리 준비

### 해상도
- **1280x720 (16:9) 고정** — Shorts 피드와 일반 비디오 모두 호환

### 영향 파일 (6개)
1. **신규** `src/upload/thumbnail_generator.py`
2. `src/video/renderer.py` — `auto_thumbnail` 플래그
3. `app/api/generate/route.ts` — done 이벤트에 `thumbnailPath`
4. `app/page.tsx` — 썸네일 미리보기 + 다운로드
5. **신규** `tests/test_thumbnail_generator.py`
6. **신규 자산** `assets/fonts/Pretendard-ExtraBold.otf` (SIL OFL)

### 단계
1. **Phase 1 (2h)**: TDD RED → GREEN, thumbnail_generator.py (capture_hook_frame / compose_thumbnail / generate_thumbnail_from_script)
2. **Phase 2 (1h)**: renderer.py auto_thumbnail=True 통합
3. **Phase 3 (0.5h)**: Pretendard 자산 다운로드
4. **Phase 4 (1h)**: UI/CLI 노출
5. **Phase 5 (1h)**: 5개 쇼츠 시각 검증 (메모리 규칙: Freepik 전용)

### 총 예상: 5.5h

### 리스크
- HIGH: Pretendard 폰트 라이선스 → SIL OFL 1.1 OK, LICENSE.txt 병행
- MEDIUM: 짧은 hook 씬 프레임 추출 실패 → `-ss 0.3` fallback
- MEDIUM: PIL 한글 자동 줄바꿈 미지원 → highlight_words 2~4글자 제한

### 진행 상태
- [x] 코드 진단 + 옵션 확정 (A/Pretendard+100px/opt-in/로컬만)
- [x] Phase 1 TDD RED (19 tests)
- [x] Phase 1 GREEN (19/19 passed, 835 total)
- [x] Phase 2 renderer 통합 (auto_thumbnail=True 플래그 + 4 TDD 테스트)
- [x] Phase 3 폰트 자산 (Pretendard-ExtraBold.otf 1.5MB, SIL OFL)
- [x] Phase 4 UI/CLI (thumbnailPath done 이벤트 + 미리보기 + 다운로드 버튼)
- [x] Phase 5 시각 검증 (5개 영상 1280×720 썸네일, Pretendard 렌더 확인)
- [x] 커밋 (25f45c5)

---

## ✅ 완료: 정치 유튜브 패턴 Quick Win 8개 (2026-04-17)

| QW | 커밋 | 설명 |
|---|---|---|
| QW-01 | 09e8586 | 후킹 자막 첫 1.5~2.5초 강제 (hook 씬 + 1.4x 폰트 + 펀치 줌) |
| QW-02 | 0aee398 | 키워드 색 카테고리 매핑 (fact 노랑 / criticism 빨강) |
| QW-03 | 04af8c4 | 자막 외곽선 강화 (B안 시그니처 + 6px) |
| QW-04 | 4e021d4 | 컷 전환 효과음 자동 매칭 (whoosh / impact) |
| QW-05 | e1d184f | CTA 아웃트로 표준화 (음성·자막 단일 출처) |
| QW-06 | d39d2f9 | punch-zoom 트랜지션 자동 매칭 (hook + emphasis high) |
| QW-07 | fb613a9 | hook 씬 인트로 빌드업 BGM 자동 합성 |
| QW-08 | 82efd7a | 클릭베이트 가드 + 사실형 fallback 제목 |
| MID-08 (Phase 1) | 9ffcd02 | highlight_words 기반 해시태그 자동 추출 + E2E 스모크 |

E2E 통합 검증 완료. 8개 QW 모두 단일 ShortsScript에 적용해도 충돌·회귀 0.

---

## 🚧 진행 중: QW-01 후킹 자막 첫 1.5초 강제 (2026-04-17)

**출처**: `docs/dem-shorts/political-youtube-style-plan.md` §1.2(쇼츠 후킹), §8.2 QW-01
**선행 결정 (2026-04-17)**: A/A/A — 고정 1.5~2.5초 / voice_text 그대로 / 강한 펀치 줌

### 결정 사항
- **Q1 duration**: A안 — hook 씬은 1.5~2.5초 고정 (LLM에 강제). 본 내용은 2번째 씬부터
- **Q2 voice_text**: A안 — 그대로 읽음. 프롬프트에 "음절 8자 이내" 강제로 1.5~2.5초 안에 맞춤
- **Q3 펀치 줌**: A안 — scale 0.88 → 1.08 → 1.0 (30fps 기준 frame 0/3/9). 강한 pop

### 영향 파일 (6개)
1. `src/analyzer/script_models.py` — Scene에 `hook: bool = False` 필드 (호환)
2. `src/analyzer/prompt_template.py` — ANALYZE/TOPIC/POLITICAL 3개 프롬프트에 후킹 규칙 + 금지어
3. `src/video/remotion/src/types.ts` — SceneData에 `hook?: boolean`
4. `src/video/remotion/src/components/SceneText.tsx` — hook 시 1.4x 폰트 + 중앙 + 펀치 줌
5. `src/video/remotion/src/components/SubtitleBlock.tsx` — `isHook?: boolean` prop
6. `tests/test_prompt_template.py` (신규/수정), `tests/test_models.py` (Scene hook 라운드트립)

### 단계
1. **TDD RED**: 프롬프트 후킹 가이드/금지어 검증 + Scene.hook 라운드트립 테스트 추가
2. **GREEN**: 모델 → 프롬프트 → Remotion 컴포넌트 순서로 구현
3. **시각 검증**: data/qw01_preview/ Playwright 캡처
4. **회귀**: pytest 전체 + tsc (root + Remotion)
5. **커밋 + 푸시** (병렬 QW-08과 충돌 0 확인)

### 진행 상태
- [x] 코드 진단
- [x] 옵션 결정 (A/A/A)
- [ ] TDD RED
- [ ] GREEN
- [ ] 시각 검증
- [ ] 커밋

### QW-08과 협조
- 금지어 리스트는 prompt_template.py 인라인 정의
- QW-08 머지 후 `src/upload/metadata_generator.py`의 금지어와 공통화 (별도 PR)

---

## ✅ 완료: QW-03 자막 외곽선 강화 (2026-04-17, 04af8c4)

**출처**: `docs/dem-shorts/political-youtube-style-plan.md` §8.2 QW-03
**선행 결정**: B안 (시그니처 색 유지) + 6px 두께 + 약한 drop shadow

### 결정 사항
- **stroke_color**: 프리셋별 시그니처 색 유지 (예: leejaemyung=#1A237E 블루, hotissue=#000000 검정). SceneText.tsx는 프리셋 없으니 기본 `#000000`.
- **stroke_width**: 모든 프리셋 + SceneText 기본값 **6px** 통일 (현재 3·3·4·5·5)
- **drop shadow**: 기존 `3px 3px 8px rgba(0,0,0,0.7)` (약) 유지 — 외곽선이 강해지므로 그림자는 약하게

### 영향 파일 (6개)
1. `src/dem_shorts/editor/subtitle_presets.py` — 5개 프리셋 stroke_width=6 + drop_shadow 필드 추가
2. `src/video/remotion/src/components/SubtitleBlock.tsx` — textShadow에 stroke + drop shadow 합성
3. `src/video/remotion/src/components/SceneText.tsx` — 외곽선 신규 도입 (4-corner textShadow)
4. `src/video/remotion/src/types.ts` — `SubtitleStyle`에 `stroke_color?`, `stroke_width?` 추가
5. `tests/dem_shorts/test_subtitle_presets.py` — drop_shadow 필드 + stroke_width≥6 assert
6. Remotion 컴포넌트 단위 테스트 (신규)

### 단계
1. **TDD RED**: 테스트 추가 (stroke_width≥6, drop_shadow 필드 존재, textShadow 빌더 stroke+shadow 합성)
2. **GREEN**: 5개 프리셋 + 두 컴포넌트 + types 수정
3. **시각 검증**: NATV 클립 1개로 짧은 테스트 영상 렌더 → 가독성 확인
4. **회귀 검증**: 기존 `tests/dem_shorts/` 287건 + tsc 통과
5. **커밋 + 푸시**

### 진행 상태
- [x] 코드 진단 + 미리보기 (data/qw03_preview/)
- [x] 옵션 결정 (B/6px/약한 그림자)
- [ ] TDD RED
- [ ] GREEN
- [ ] 시각 검증
- [ ] 커밋

### 비고
- 후속 Quick Win 순서: QW-01 후킹 자막 → QW-08 클릭베이트 가드 → QW-05 CTA 아웃트로 → ...
- 미리보기 자산: `data/qw03_preview/preview.html` + 4개 PNG

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

## Phase 8: 정치 해설 쇼츠 + 인기 의원 영상 검색 ✅ 구현 완료

**브랜치**: `006-video-shorts-mode`

### 8-1. 정치 교차편집 파이프라인 ✅

- `src/scraper/political_input.py` — PoliticalInput 모델
- `src/scraper/youtube_downloader.py` — yt-dlp 다운로드 + VTT 파싱
- `src/tts/audio_stitcher.py` — 클립 오디오 + TTS 스티칭
- `src/analyzer/script_models.py` — Scene에 clip/commentary 타입 추가
- `src/analyzer/prompt_template.py` — POLITICAL_ANALYZE_PROMPT
- `src/analyzer/claude_analyzer.py` — analyze_political()
- `app/api/generate/route.ts` — political 모드 분기
- `app/page.tsx` — 정치 해설 탭 추가

### 8-2. 인기 의원 영상 검색 ✅

- `src/data/popular_female_lawmakers.py` — 인기 여성의원 데이터 (8명, 양당)
- `src/scraper/lawmaker_video_finder.py` — yt-dlp 기반 YouTube 영상 검색
- `src/analyzer/clip_selector.py` — 자막 키워드 분석으로 자동 구간 선택
- `app/api/lawmaker/list/route.ts` — 의원 목록 API (정적)
- `app/api/lawmaker/videos/route.ts` — 영상 검색 API (yt-dlp 호출)
- `app/page.tsx` — 3단계 UI (의원 선택 → 영상 목록 → 생성 폼)

### 8-3. 테스트 ✅

- `tests/test_political_input.py` — 11개
- `tests/test_youtube_downloader.py` — 9개
- `tests/test_audio_stitcher.py` — 3개
- `tests/test_political_prompt.py` — 6개
- `tests/test_lawmaker_finder.py` — 17개 (신규)
- `tests/test_clip_selector.py` — 6개 (신규)
- **총 70개 통과**

### 의원 데이터 (22대 국회)

| 의원명 | 정당 | 특징 |
|-------|------|------|
| 나경원 | 국민의힘 | 전 원내대표, 중진 |
| 배현진 | 국민의힘 | 전 MBC 앵커 |
| 김예지 | 국민의힘 | 올림픽 펜싱 은메달 |
| 한지아 | 국민의힘 | 의사 출신 |
| 진선미 | 민주당 | 전 장관 |
| 남인순 | 민주당 | 복지위 베테랑 |
| 서영교 | 민주당 | 4선 의원 |
| 고민정 | 민주당 | 전 청와대 대변인 |

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
