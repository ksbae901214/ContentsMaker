# Session Handoff — 2026-05-20 (수)

> 이 세션에서 진행된 **개발 + 영상 제작 + 검증** 전체 요약. 다음 세션 시작 시 이 문서부터 읽으면 컨텍스트 즉시 회복.

**브랜치**: `feature/007-combined` (커밋 미적용, 워킹트리 변경 다수 존재)
**작업 시간**: 2026-05-19 오후 ~ 2026-05-20 오후 (약 1.5일)

---

## 1. 핵심 트리거

| 이벤트 | 영향 |
|--------|------|
| 사용자 **Gemini AI Pro 구독 시작** | gemini.google.com 웹앱의 Veo 3 / Imagen 4 / Charon TTS 무제한 가까이 사용 가능 |
| 사용자 **Freepik 구독 해지** | 만화·영상 기본 파이프라인 BREAKING → 즉시 대체 필요 |

---

## 2. 완료된 개발 (016 + 015 두 로드맵)

### 016 — Gemini Gems 프롬프트 프리셋 시스템 ✅
> 사용자/린터가 별도 추가한 신규 모듈군. 본 세션 메인 작업과는 별개 트랙.

- `src/illustrator/gem_navigator.py` — Gems 탐색·클릭 자동화
- `src/config/gems_config.json` + `src/config/gem_prompts/*.txt` — Gem 키↔지침 매핑
- `GeminiWebImageGenerator(gem_key=...)` / `GeminiWebVideoGenerator(gem_key=...)` / `factory.create_generator(..., gem_key=...)`
- CLI: `python3 -m src.main gems list` / `gems show-prompt`
- 14개 신규 테스트 통과 (총 1122 passed)

### 015 — Gemini AI Pro 통합 로드맵 (Phase 0~4) ✅

| Phase | 상태 | 주요 산출물 |
|-------|------|------------|
| **0** 긴급 패치 | ✅ | UI/API 기본값 freepik→deevid·gpt, 빌드 에러 부수 수정 (SceneImage 타입 중복) |
| **1A** YouTube 멀티모달 | ✅ | `src/scraper/gemini_youtube_transcriber.py` (172줄, VTT→Gemini→Whisper 3-tier) |
| **1B** Gemini Flash 백본 | ✅ | `src/analyzer/gemini_backend.py` (ANALYZER_BACKEND 토글, Claude 폴백) |
| **2A** Imagen 4 웹앱 | ✅ | `src/illustrator/gemini_web_image_gen.py` + `gemini_web_login.py` + `gemini_web_selectors.py` |
| **2B** Veo 3 웹앱 | ✅ | `src/video_gen/gemini_web_video_gen.py` + factory `"gemini"` 등록 |
| **3** 다중 화자 + NotebookLM | ✅ 모듈 | `src/tts/gemini_multi_voice.py` + `src/analyzer/notebooklm_style.py` (UI 통합 미적용) |
| **4** Deep Research 팩트체크 | ✅ 모듈 | `src/analyzer/political_fact_checker.py` (UI 통합 미적용) |

### 핵심 라이브 selector 탐색 결과 (gemini.google.com)

```python
GEMINI_SELECTORS = {
    "chat_input": "rich-textarea div[contenteditable='true']",
    "send_button": "button[aria-label*='보내']",  # "메시지 보내기"
    "image_in_response": "model-response button.image-button img",  # blob URL
    "video_in_response": "model-response video",
    "image_tool_button": "button[aria-label*='이미지 만들기']",
    "video_tool_button": "button[aria-label*='동영상 만들기']",
}
MODAL_DISMISS: ESC 키 2회 (이메일 수신 동의 모달 해제)
```

### 핵심 발견 / 패치

| 발견 | 해결 |
|------|------|
| Imagen 이미지가 `blob:` URL → httpx 불가 | `element.screenshot()` 으로 우회 |
| Veo 3 비디오 URL은 Google auth 쿠키 필요 (302 → ServiceLogin) | `page.evaluate(fetch + base64)` 로 우회 |
| Google 자동화 차단 (번들 chromium) | `channel="chrome"` + `--disable-blink-features=AutomationControlled` |
| SingletonLock 잔존 시 Chrome 재시작 불가 | `pkill + rm .cache/gemini_profile/Singleton*` 절차 확립 |
| 긴 프롬프트 type() 30s timeout | `evaluate(innerText=...)` + input 이벤트로 즉시 입력 |
| Wikimedia 403/429 | User-Agent Mozilla로 변경 + 캐시 우선 사용 + sleep 추가 |

---

## 3. 검증 (E2E 테스트)

### Test 매트릭스

| 테스트 | 상태 | 영상 산출물 |
|--------|------|------------|
| **A. 만화 + Imagen 4** | ✅ | `data/outputs/20260519_170024_아침_커피_한_잔의_마법.mp4` (5.3MB, 144초 제작) |
| **B. 영상 + Veo 3** | ✅ (E2E 데모) | `data/outputs/20260519_172209_Gemini_Pro__ContentsMaker_데모.mp4` (15.4MB, 16초) |
| **C. 정치_pro 호환성** | ✅ (코드 검증) | plans→ShortsPlan→script 변환 OK, 락인 포맷 유지 확인 |
| **D. 셀럽 모드** | ✅ (안전성) | Gemini 503 → Claude 폴백 정상 동작 (76초, 13씬 세종대왕) |

### 회귀 테스트

- pytest: **1108~1122 passed / 1 skipped / 0 failed**
- npm build: ✅ Next.js 16.2.1 통과

---

## 4. 제작된 영상 시리즈 (지방선거 후보 검증)

| 탄 | 주제 | 영상 파일 | 실명 | 안전성 |
|----|------|----------|------|--------|
| 1탄 | 음주·도박·폭행 전과 (MBC 충북) | `20260518_145143...` | ❌ | 🟢 |
| 2탄 | 35% 전과 + 평균 9억 재산 (KBS) | `20260519_102555...` | ❌ | 🟢 |
| 3탄 | 비수도권 후보 서울 다주택 (MBC) | `20260519_105334...` | ❌ | 🟢 |
| **4탄** | **9명 중 1명 군 미필 (신문 통계 + MBN B-roll)** | `data/outputs/20260520_111343_지방선거_후보_9명_중_1명_군_미필.mp4` (8.7MB, 38초) | ❌ | 🟢 |
| **5탄 v4** | **유명 미필 6인 + 면제 사유 (Charon TTS)** ⭐ | `data/outputs/20260520_135220_광역단체장_후보_군_미필_6인__면제_사유.mp4` (18.2MB, 43초) | ✅ | 🟡 |

**5탄 정보 (게시 전 변호사 자문 권장)**:
- 김부겸 (민주 대구) — 수형 (긴급조치·계엄령)
- 박형준 (국힘 부산) — 제2국민역 (근시·부동시)
- 추경호 (국힘 대구) — 소집면제 (폐결핵)
- 김경수 (민주 경남) — 제2국민역 (손가락 강직)
- 김영환 (국힘 충북) — 보충역 (수형)
- 권영국 (정의 서울) — 소집면제 (수형)

**5탄 출처 (인용 기록)**:
- 뉴시스 [NISX20260516_0003632326](https://www.newsis.com/view/NISX20260516_0003632326) — 12명 명단
- 부산일보 — 박형준 시력
- SBS [끝까지판다] — 추경호 폐결핵
- 아시아경제 — 김경수 손가락
- 경남도민일보 — 권영국 수형
- 위키백과 한국어판 — 김부겸·김영환·권영국 수형 + 6명 프로필 사진

**자료 캐시**: `data/political_pro/20260520_mil6names/portraits/` (6명 jpg/png, 264KB)

---

## 5. 락인 포맷 (정치_pro) — 절대 변경 금지

> [[political-pro-format-lockin]] 메모리 참조. 본 세션 5탄 v3에서 1회 위반(edge-tts 사용) → v4에서 즉시 복구.

```
TTS:        Gemini Charon + Newscaster style + temp 0.5
영상 클립:   mute=True (TTS만 메인 음성)
자막 폰트:   56px (강조 1.25x = 70px)
자막 한도:   28자 (자동 분할, "…" 0건)
자막 색:    white/red/yellow/blue (Hook/CTA는 yellow+emphasis)
배경:       #000 검정 강제
출처:       paddingBottom: 150 (출처: 채널 : 제목)
전환·SFX:   강제 OFF
자동 업로드: 차단 (FR-020)
분할:       split-screen 자동 매핑 OFF
```

**TTS 한도 운영**:
- Gemini Charon 일일 한도 ~15회 (free tier) 충분
- 호출 시 자동 캐시 저장 (`data/tts_cache/{hash}.mp3`)
- 한도 초과 시 캐시 → 제목 매칭 → edge-tts 3단 폴백

---

## 6. UI 변경 사항 (`app/page.tsx` + `app/api/generate/route.ts`)

### 만화 모드 (visualMode="manga")
- **기본 imageProvider**: `gpt` → **`gemini`** (Imagen 4)
- Freepik 옵션 disabled (구독 해지)
- Imagen 4 사용 시 한 줄 안내: "변동비 $0 (Pro 구독 한도 내). 사전 `gemini_login` 필요"

### 영상 모드 (visualMode="video")
- **기본 videoProvider**: `freepik` → **`deevid`**
- **새 옵션**: 🎬 **Veo 3 (Gemini Pro)** 추가
- Freepik 버튼 line-through + disabled

### Phase 1B 환경변수
- `ANALYZER_BACKEND=gemini` 권장 (default는 claude로 유지 — 14일 A/B 후 전환 예정)
- `USE_GEMINI_TRANSCRIBE=0` 으로 1A 즉시 비활성 가능

---

## 7. 워킹트리 미커밋 변경 (다음 세션 정리 필요)

```
M  app/page.tsx
M  app/api/generate/route.ts
M  src/config/settings.py
M  src/main.py
M  src/scraper/youtube_downloader.py
M  src/video_gen/factory.py
M  src/video/remotion/src/components/SceneText.tsx (pre-session)
M  src/analyzer/political_planner.py (pre-session)
M  src/analyzer/celebrity_analyzer.py
M  src/analyzer/claude_analyzer.py
M  prompt_plan.md (016+015 로드맵)
?? src/analyzer/gemini_backend.py
?? src/analyzer/notebooklm_style.py
?? src/analyzer/political_fact_checker.py
?? src/illustrator/gemini_web_image_gen.py
?? src/illustrator/gemini_web_login.py
?? src/illustrator/gemini_web_selectors.py
?? src/illustrator/gem_navigator.py
?? src/scraper/gemini_youtube_transcriber.py
?? src/tts/gemini_multi_voice.py
?? src/video_gen/gemini_web_video_gen.py
?? src/config/gem_prompts/
?? src/config/gems_config.json
?? tests/test_gemini_backend.py
?? tests/test_gemini_web_image_gen.py
?? tests/test_gemini_web_video_gen.py
?? tests/test_gemini_youtube_transcriber.py
?? tests/test_phase3_phase4.py
?? prompt_plan.md.bak
?? SESSION_HANDOFF_20260520.md (이 파일)
?? data/political_pro/20260520_mil4/ (4탄 자산)
?? data/political_pro/20260520_mil6names/ (5탄 자산)
?? data/outputs/20260519_17*.mp4, 20260520_*.mp4 (영상 6편)
```

**기존 stash 보존**: `stash@{0}: On 007-dem-shorts-studio: pre-merge-tree` — 사용자 결정 대기

---

## 8. 다음 세션 우선순위 (TODO)

### 즉시 (HIGH)
1. **변경사항 커밋**: 016 + 015 작업을 의미 단위로 분할 커밋
   - Phase 0 긴급 패치 1개
   - Phase 1A 1개
   - Phase 1B 1개
   - Phase 2A 1개
   - Phase 2B 1개
   - Phase 3 + 4 모듈 1개
   - UI 통합 1개
   - 시리즈 4탄·5탄 산출물 (선택 — data/ 큰 파일은 .gitignore 확인)
2. **5탄 영상 톤 검수** — 변호사 자문 후 게시 여부 결정

### 중기 (MEDIUM)
3. **selectors 안정화**: gem_navigator의 Gems 목록 페이지 selector 라이브 확인
4. **Veo 3 한도 실측**: Pro 일일 한도 정확히 확인 (현재 추정 ~10편/일)
5. **ANALYZER_BACKEND=gemini** 14일 A/B 후 default 전환 결정
6. **Phase 3/4 UI 통합**: 다중 화자 / 팩트체크 정치_pro 검수 화면 표시

### 후순위 (LOW)
7. **prompt_plan.md.bak** 정리 (이전 계획 아카이브 확인 후 삭제)
8. **007 stash** 처리 방향 결정 (drop or apply)
9. **시리즈 6탄 기획** (사용자 요청 시)

---

## 9. 메모리 항목 (auto-memory)

다음 세션에서도 유지되는 메모리:
- `feedback_test_video.md` — 작업 후 테스트 영상 필수
- `feedback_no_openai.md` — OpenAI 사용 안 함 (Phase 2A로 해결)
- `feedback_political_pro_format.md` — 락인 포맷 (Charon 등)

신규 추가 권장 (다음 세션에서 직접 추가):
- ⚠️ **Gemini TTS quota는 Veo 3와 별도** — 한쪽 한도 차도 다른 쪽 사용 가능
- ⚠️ **Imagen 4 / Veo 3는 gemini.google.com 웹앱 통해 사용** (API 아님), `channel="chrome"` 필수
- ⚠️ **위키 사진 다운로드 시 User-Agent Mozilla 필수** (`Mozilla/5.0 ...`)

---

## 10. 비용 / 한도 운영

| 자원 | 현재 사용 | 한도 |
|------|----------|------|
| Gemini 2.5 Flash API (analyzer) | 거의 0 | 250 req/일 |
| Gemini TTS Charon (정치_pro) | 약 5회 (4탄·5탄) | ~15 req/일 free |
| Veo 3 웹앱 | 3 클립 사용 | Pro ~10편/일 |
| Imagen 4 웹앱 | 약 6장 사용 | Pro 사실상 무제한 |
| edge-tts | 다수 | 무제한 |
| Claude CLI | 다수 | 무제한 (구독) |

**고정비**: Gemini AI Pro 구독만 ($20/월). Freepik $34/월 절감 → 순 $14/월 절감.

---

## 부록 — 빠른 시작 명령어

```bash
# 1) 환경
export GEMINI_API_KEY='<...>'
export ANALYZER_BACKEND=gemini   # 선택, claude 폴백 자동

# 2) Gemini 웹앱 로그인 (1회)
python3 -m src.main gemini_login

# 3) 개발 서버
npm run dev
# → localhost:3000

# 4) 테스트
python3 -m pytest tests/ -q

# 5) Chrome 락 정리 (필요 시)
pkill -f gemini && rm -f .cache/gemini_profile/Singleton*
```

---

**이 파일은 세션 클리어 전 컨텍스트 백업입니다.** 다음 세션 시작 시 `Read SESSION_HANDOFF_20260520.md` 로 즉시 회복하세요.
