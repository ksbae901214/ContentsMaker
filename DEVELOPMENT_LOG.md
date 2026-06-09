# ContentsMaker 개발 로그

> 정치/유명인/주제 쇼츠 자동 생성 파이프라인 — 주요 변경 이력 + 검증된 패턴 + 영상 제작 기록

**최종 업데이트**: 2026-05-28

---

## 🎯 검증된 lock-in 패턴 (2026-05-27 사용자 확정)

### 정치 쇼츠 (source_type=political) — 직접 작성 워크플로우

| 항목 | 확정값 |
|------|------|
| 워크플로우 | 사실 확인(WebSearch) → 3 기획안 → 사용자 선택 → ShortsScript JSON 수동 작성 → YouTube 클립 다운로드 → letterbox 컷 → 렌더 |
| 씬 수·길이 | 5~7씬, 45~55초 |
| TTS | `ko-KR-InJoonNeural`, `rate: "+22%"`, `pitch: "+0Hz"` |
| TTS 합성 방식 | **씬별 별도 합성** + `_trim_audio_silence` 자동 (keep_tail_ms=200ms = 쉼표 수준 0.2초 호흡) |
| 시각 처리 | **Letterbox**: `scale=1080:-2,pad=1080:1920:0:(1920-ih)/2:color=black` (좌우 안 잘림, 후보 다 보임) |
| 출처 표시 | `metadata.source_label`만 사용 → 모든 본 영상 씬 하단 작은 글씨 자동 표시. **별도 출처 씬 만들지 않음** |
| 자막 | 3줄, 14자×3줄 분할, '...' 금지 |
| 옵션 | `use_bgm=False`, `enable_sfx=False`, `enable_transitions=False` |
| 결과 보고 | 3줄 요약 + 해시태그 자동 제공 |

### 유명인 쇼츠 (source_type=celebrity)
- TTS: `ko-KR-HyunsuMultilingualNeural` (다국어 남성, 외국 이름 발음 자연)
- BGM: celebrity 전용 풀 (celebrity_1/2/3.mp3), 볼륨 0.28 (다른 모드 0.15의 약 2배)
- 콘텐츠: 인물 소개·업적 내레이션 중심
- 학습 목적 전용 (Namuwiki CC BY-NC-SA 3.0, YouTube/TikTok 업로드 UI 차단)

### 정치쇼츠 V2 (Feature 023) — 자동 생성 워크플로우
- UI에서 정치_pro 탭 → `✏️ 주제 입력` 토글 → 주제·톤·상세 입력
- `generate_three_plans_from_topic()` (Stage A Gemini + Stage B Claude×3 병렬)
- PoliticalPlanPicker로 3안 비교 후 선택 → ScriptReviewer 수정 → 렌더
- YouTube 키워드 자동 검색 (yt-dlp ytsearch1 + ffmpeg letterbox)

---

## 📦 주요 신규 기능 + 버그 수정

### 023 Feature: 정치쇼츠 V2 주제 입력 모드 (2026-05-26)
**커밋**: `1b30c91 feat(political_pro): 주제 입력 모드 + Stage B 병렬화로 60s timeout 회피`

| 변경 | 파일 |
|------|------|
| ShortsPlan 모델에 `source_type` + `youtube_search_keywords` 필드 | `src/analyzer/political_plan_models.py` |
| `generate_three_plans_from_topic()` + `_stage_a_topic_gemini` + `_stage_b_topic_claude` | `src/analyzer/political_planner.py` |
| topic 모드 Stage A/B 프롬프트 | `political_planner_stage_a_prompt.py`, `political_planner_stage_b_prompt.py` |
| YouTube 뉴스 자동 검색·다운로드 (yt-dlp + ffmpeg letterbox) | `src/scraper/youtube_news_searcher.py` (신규) |
| API: sourceType=topic 분기 | `app/api/political-pro/plans/route.ts`, `app/api/generate/route.ts` |
| CLI 인자 `--source-type {youtube,topic}` | `src/main.py` |
| UI 토글 + 주제·톤·상세 입력 폼 | `app/page.tsx` |
| 단위 테스트 25개 (topic plans 10 + youtube searcher 15) | `tests/test_political_topic_plans.py`, `tests/test_youtube_news_search.py` |

### Bug fix: Safari "Load failed" timeout (2026-05-26)
**원인**: Stage B 3회 Claude 호출 순차 실행 (~60s) → Safari fetch 60초 timeout

**수정**:
- `_generate_three_plans_topic_hybrid`에 `ThreadPoolExecutor(max_workers=3)` 적용
- Stage B 응답 ~60s → **~20s** 단축
- UI catch에 timeout 진단 + 새로고침/Chrome 안내 추가

### Bug fix: TTS / 영상 sync 불일치 (2026-05-26)
**원인**: `_get_mp3_duration_ms()`가 file_size/bitrate 추정으로 MPEG1 Layer3(`HyunsuMultilingualNeural` 출력)에서 실제 duration의 ~50%만 반환

**수정**:
- `edge_tts_generator.py`와 `video/renderer.py`의 duration 측정을 **ffprobe** 기반으로 교체
- 영상 길이 정확화 + 씬-TTS 동기화

### 신규: `_trim_audio_silence()` — 양끝 silence 정리 (2026-05-27)
**원인**: edge-tts가 각 호출마다 음성 앞뒤로 ~0.5초 silence 자동 삽입 → 씬별 합성 후 concat 시 누적

**수정**:
- `src/tts/edge_tts_generator.py`에 `_trim_audio_silence()` 추가
- ffmpeg `silenceremove` (threshold -45dB) 양끝 무음 제거 후 `keep_tail_ms` 만큼만 자연 호흡 유지
- 측정으로 검증: 쉼표 1개 추가 silence ≈ 200ms → default `keep_tail_ms=200`
- 효과: 8씬 영상 90s → 50s, 씬 사이 gap이 일정한 자연 휴지로 통일

### 신규: 영상 하단 출처 라벨 시스템 (2026-05-27)
**Metadata에 `source_label: str = ""` 필드 추가** — 명시되면 우선 사용

| 파일 | 변경 |
|------|------|
| `src/analyzer/script_models.py` | Metadata에 `source_label` 필드 |
| `src/video/renderer.py` | source_label 우선순위 처리 + political 모드도 자동 표시 (이전엔 political_pro만) |

효과: 모든 본 영상 씬 하단에 "출처: MBC, 헤럴드경제, ..." 같은 명시 라벨 일관 표시 → 별도 출처 씬 제거 가능

### Composition durationInFrames 90초 → 120초 (2026-05-27)
- `src/video/remotion/src/Root.tsx`: `FPS * 90` → `FPS * 120`
- 60초 넘는 정치 쇼츠도 렌더 가능 (이전 90초 초과 시 frame range 에러)

### Celebrity BGM 볼륨 강화 (2026-05-28)
- `src/video/remotion/src/ShortsComposition.tsx:160`: `volume={isCelebrity ? 0.28 : 0.15}`
- 인물 소개·업적 내레이션 모드 BGM 존재감 약 2배 강화

---

## 🎬 제작 영상 기록 (2026-05-26 ~ 2026-05-27)

### 정치 쇼츠 — 검증된 letterbox + 씬별 합성 패턴 적용

| 영상 | 길이 | 핵심 내용 | 비고 |
|------|------|---------|------|
| **스타벅스 5·18 탱크데이 논란** | ~63s | 3중 우연(5/18+탱크+책상에 탁) 추적 검증형 | 검증된 워크플로우 최초 적용 (앞은 cover crop) |
| **박근혜 9년 침묵의 컴백** | 46s | 탄핵 후 첫 현장 유세 (대구 칠성시장 → 옥천 → 부산) | 출처 씬 제거 + source_label 하단 표시 최초 |
| **추경호 vs 김부겸 토론회** | 50s | 대구MBC 토론회 "대한민국 주적이 누구냐" 색깔론 공방 | letterbox 최초 적용 (후보 2명 한 화면) |

전부 정치 쇼츠 lock-in 패턴 (씬별 별도 합성 + silence trim + source_label 하단 + letterbox + InJoonNeural +22%)

---

## 📐 영향 받은 파일 종합

### Backend (Python)
- `src/analyzer/political_planner.py` — `generate_three_plans_from_topic()` + Stage B 병렬화
- `src/analyzer/political_plan_models.py` — `source_type` + `youtube_search_keywords`
- `src/analyzer/political_planner_stage_a_prompt.py` — `build_stage_a_topic_prompt()`
- `src/analyzer/political_planner_stage_b_prompt.py` — `build_stage_b_topic_prompt()`
- `src/analyzer/script_models.py` — Metadata에 `source_label`
- `src/scraper/youtube_news_searcher.py` — 신규 (yt-dlp + ffmpeg letterbox)
- `src/tts/edge_tts_generator.py` — `_trim_audio_silence()` + ffprobe duration
- `src/video/renderer.py` — `source_label` 처리 + ffprobe duration
- `src/main.py` — political-pro `--source-type` 인자

### Frontend (TypeScript)
- `app/page.tsx` — political_pro 탭 토글 + 주제 입력 폼
- `app/api/political-pro/plans/route.ts` — sourceType 분기
- `app/api/generate/route.ts` — political_pro + sourceType=topic 분기
- `src/video/remotion/src/Root.tsx` — Composition durationInFrames 120s
- `src/video/remotion/src/ShortsComposition.tsx` — celebrity BGM 볼륨

### Tests
- `tests/test_political_topic_plans.py` — 12 테스트 (모델 + Stage 병렬화 + 라운드트립)
- `tests/test_youtube_news_search.py` — 15 테스트 (검색·다운로드·letterbox)

---

## 🔄 검증 결과 (2026-05-28 시점)

- 단위 테스트: 27/27 통과 (test_political_topic_plans + test_youtube_news_search)
- TypeScript 컴파일: 통과 (`tsc --noEmit` Next.js + Remotion)
- Next.js 프로덕션 빌드: 통과 (`npm run build`)
- Dev API endpoint: 동작 확인
- 정치_pro YouTube 모드 회귀: 84 테스트 통과

---

## 📚 관련 메모리

| 메모리 | 내용 |
|------|------|
| `feedback_political_shorts_lockin.md` | 정치 쇼츠 완전 lock-in 패턴 (이번 세션 최종 합의) |
| `feedback_political_pro_format.md` | 정치_pro 모드 포맷 (자막 2줄·Charon TTS 등) |
| `feedback_political_topic_format.md` | political/topic 모드 (3줄자막·뉴스클립 인셋·효과음없음) |
| `feedback_video_summary_hashtags.md` | 영상 1편 만들 때마다 3줄 요약 + 해시태그 고정 룰 |
| `feedback_test_video.md` | 작업 완료 시 테스트 영상 생성 필수 |
| `feedback_no_openai.md` | 이미지/영상 생성 Freepik만 사용, OpenAI 미사용 |
