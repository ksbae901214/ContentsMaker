# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 / NATV / 정치 / 셀럽 영상을 YouTube Shorts로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-05-20

---

## ✅ 완료: 019 자막 분할/줄바꿈/그룹 TTS 전 영상 모드 확대 (2026-05-20)

**목표**: 018에서 정치_pro에만 적용한 자막 분할 + 명시적 줄바꿈 + 그룹 단위 TTS 합성을 blind / topic / manual / url / celebrity / political 모든 모드에 동일하게 적용.

**완료**:
- 분할 알고리즘을 `src/editor/subtitle_split.py`로 추출 (`_split_subtitle_segments`, `_insert_linebreak`, `_score_split_position`, `apply_subtitle_split(script)`)
- `political_planner.py`는 import로 마이그레이션 (회귀 없음, 20 테스트 통과)
- `claude_analyzer._ensure_line_breaks` → `apply_subtitle_split` 호출로 교체 → blind / topic / manual / url / celebrity / political 모드 모두 자동 적용
- 기존 단순 15자 greedy 분할의 V2 필드 누락 버그 함께 수정 (subtitle_color/emphasis/hook 등 보존)
- 신규 테스트: `tests/test_subtitle_split.py` 14건 (분할/그룹/V2 필드 보존/idempotent), `test_analyzer_extended.py` 보강
- e2e: blind 모드 합성 4씬 → 7씬 분할, group_id 2개 (이전 단순 분할에서 누락된 V2 필드도 보존), 영상 시각 확인 OK

**효과**:
- 모든 영상 모드에서 어색한 분할 위치·orphan 줄·씬 전환 자막 튐·TTS 텀 길이 일관 해소
- 정치_pro만 받았던 자막 품질이 다른 모드에도 동일 적용

---

## ✅ 완료: 018 정치 영상 자막 줄바꿈·애니메이션 업그레이드 (2026-05-20)

**완료 항목**:
- Phase 1 — `_score_split_position` + `_split_subtitle_segments` v2 (한국어 조사·종결어미·구두점 인식 + 균형 보너스). 25%(7자)부터 탐색 → 강한 구두점 경계도 포착.
- Phase 2 — `_insert_linebreak` 신규. 분할 세그먼트 + 단일 짧은 씬(15자+) 모두 14자 근처 명시적 `\n` 삽입. CSS keep-all 의존 제거.
- Phase 3 — `Scene.subtitle_group_id` / `subtitle_group_first` 필드 추가. `_add_split_scenes`가 분할 자식들에 동일 group_id 부여. `scene_split`도 V2 필드 전체 전파 (기존 누락 버그 부수 수정).
- Phase 4 — `SceneText.tsx` 애니메이션: fade 15→9프레임 + easeOutQuad, slide 40→16px, hook 줌 0.88→1.08→1.0 (overshoot 20%) → 0.96→1.02→1.0 (overshoot 2%), emphasis 펀치줌 제거. `group_first=false` 씬은 fade·slide 둘 다 생략(opacity=1, animateY=0) → 분할 자식 끊김 제거. `extrapolateLeft: clamp` 명시.
- Phase 5 — 단위 테스트 9건 신규(분할 6건 + 그룹 6건), 전체 1087 테스트 통과, 187개 기존 정치 스크립트 JSON 역호환, Remotion TSC 0 errors, e2e 영상 1편 렌더링 시각 검증 (data/outputs/20260520_142642_자막_업그레이드_e2e_검증.mp4).

**검증 결과** (5개 프레임 시각 확인):
- 명시적 `\n` 줄바꿈으로 모든 자막 2줄 깔끔 분할
- "후보자 4명 / 중 1명이" 같이 명사+조사 어절 보존
- group_first=false 자식 씬은 텍스트만 즉시 교체 (끊김 없음)
- 락인 포맷 보존: yellow/white/red 색, 폰트 56px, 검정 배경, 출처 하단 표시
- "…" 생략 0건, WebkitLineClamp:2 발동 없음

**파일 변경**:
- `src/analyzer/political_planner.py` (분할 알고리즘 v2 + 그룹 ID 전파)
- `src/analyzer/script_models.py` (Scene subtitle_group_id/group_first 필드 + serialization)
- `src/editor/scene_ops.py` (scene_split V2 필드 전파 부수 수정)
- `src/video/remotion/src/components/SceneText.tsx` (Easing import + 톤다운 곡선 + group_first 분기)
- `tests/test_political_planner.py` (분할 알고리즘 회귀 6건)
- `tests/test_script_models.py` (group 필드 6건)

---

## ✅ 완료: 017 Gem Labs 실제 등록 + 코드 연동 (2026-05-19)

**목표**: 016에서 설계한 Gem 시스템을 Gemini Gem Labs(Opal)에 실제 등록하고 자동화 코드와 연결.

**완료 항목**:
- Gem Labs 3개 생성 완료 (Playwright 자동화)
  - `Webtoonify` (이미지 웹툰) — ID: `16uKqRjySdvzERPXGyqxYm2uEgnVhwrTM`
  - `Veo3-뉴스` (영상 뉴스) — ID: `1Hlv0NjfVDlxotDEWCJmwYaJqU3414v3B`
  - `Veo3-드라마` (영상 드라마) — ID: `1CsQKuCLxFj58xyI978RtBnx4zGxBi8Lg`
- `gems_config.json` — `gem_id` 필드 추가 (실제 Gem Labs ID)
- `gem_navigator.py` — `/gems/view` 이름 탐색 → `gem-labs/{id}` 직접 URL + "Start" 클릭 방식으로 전면 개선. `navigate_to_gem(page, gem_cfg)` 반환값이 opal_frame으로 변경.
- `gemini_web_selectors.py` — `GEM_LABS_SELECTORS` 추가 (gem_chat_input, gem_send_button, image_in_opal, video_in_opal)
- `gemini_web_image_gen.py` — gem 모드: `_opal_frame` 저장, `_generate_one_gem_mode()` + `_capture_last_image_gem()` 추가, 이미지 도구 활성화 건너뜀
- `gemini_web_video_gen.py` — gem 모드: `_opal_frame` 저장, opal frame 셀렉터로 chat/send/video_locator 분기
- 1122 테스트 통과 (회귀 없음)

**알려진 제약**:
- Gem Labs(Opal)는 전통적 Gems와 다른 인터페이스 — opal._app iframe 내 Shadow DOM
- Veo 3 Gem Labs 지원 여부: 라이브 테스트 필요 (news/drama Gem의 Steps 미확인)
- 이미지 결과 selector(`img[src^='blob:']`)는 라이브 테스트로 최종 확정 필요

---

## ✅ 완료: 016 Gemini Gems 프롬프트 프리셋 시스템

**목표**: Nano Banana / Veo 3 생성 시 반복 프롬프트를 Gemini Gems로 저장, 씬 내용만 전송해 프롬프트 작성 부담 제거.

**완료 항목 (2026-05-19)**:
- `src/config/gem_prompts/image_webtoon.txt` — 웹툰 Gem 지침 템플릿
- `src/config/gem_prompts/video_news.txt` — 뉴스 앵커 Gem 지침 템플릿
- `src/config/gem_prompts/video_drama.txt` — 드라마 감성 Gem 지침 템플릿
- `src/config/gems_config.json` — Gem 키↔이름 매핑 (webtoon / news / drama)
- `src/illustrator/gem_navigator.py` — Gems 목록 탐색·클릭 자동화 (`navigate_to_gem`)
- `GeminiWebImageGenerator(gem_key=...)` — Gem 모드 지원 (navigate + 단문 프롬프트)
- `GeminiWebVideoGenerator(gem_key=...)` / `factory.create_generator(..., gem_key=...)` — 동일
- `python3 -m src.main gems list` — 등록 Gem 목록 출력
- `python3 -m src.main gems show-prompt <key> --kind <image|video>` — 지침 텍스트 출력
- `celebrity --image-gem` / `political-pro --video-gem` CLI 플래그
- 14개 신규 테스트 (1122 total passed)

**다음 단계**:
- gemini_login 후 Gems 목록 페이지 DOM selector 라이브 확인 → `gem_navigator.py` 반영
- Veo 3 Gem에서 "동영상 만들기" 도구 지원 여부 실사용 검증

---

## ✅ 완료: 015 Gemini AI Pro 통합 로드맵 (5 Phases)

**상태 (2026-05-19 종합)**:
- Phase 0, 1A, 1B, 2A, 2B 코드 + 테스트 + UI 통합 모두 완료
- Phase 3 (다중 화자, NotebookLM) 모듈 완료, UI 통합은 사용자 요청 시 추가
- Phase 4 (Deep Research) 모듈 완료, 정치_pro UI 통합은 사용자 요청 시 추가
- E2E 검증: Imagen 4 이미지 1장 생성 OK (data/images/gemini_*.png 367KB, 456×817)
- selector 라이브 탐색 완료 — `이미지 만들기` / `동영상 만들기` 한국어 UI 사용
- Veo 3 다운로드 인증 이슈 해결 — 브라우저 컨텍스트 fetch + base64 변환 패치
- 회귀 테스트: 1108 passed / 1 skipped / npm build OK

## 진행 기록

**확정일**: 2026-05-19 / **트리거**: 사용자 Gemini AI Pro 구독 시작 + Freepik 구독 해지

### 배경 / 제약
- ⚠️ **Freepik 이미 해지** → 현재 영상/이미지 기본 파이프라인 BREAKING
- ✅ Google AI Studio API는 **무료 한도만 사용** (billing 미활성)
- ✅ Gemini Pro 구독 = gemini.google.com 웹앱 Veo 3 / Imagen 4 활용 가능 → 브라우저 자동화로 통합
- 🛡️ **안전성 우선**: 점진 마이그레이션, 토글, A/B, 14일 안정 후 default 전환
- 🔒 **락인 포맷 보호**: 정치_pro 시각·자막·TTS 설정 불변 ([[political-pro-format-lockin]] 메모리)

### Phase 0: 🚨 긴급 패치 (TODAY)
**목표**: 깨진 파이프라인 즉시 복구 (Freepik 의존 제거)

- [ ] `app/page.tsx` `videoProvider` 기본값: `freepik` → `deevid`
- [ ] `app/page.tsx` `imageProvider`: Freepik 옵션 제거 또는 disabled 표시
- [ ] `app/page.tsx` `visualMode` 기본값: 만화 모드는 일시적으로 권장 안 함, 영상 모드(video) 우선
- [ ] `app/api/generate/route.ts`: `videoProvider` 기본값 `seedance` → `deevid` (env 키 없어도 동작)
- [ ] 만화 모드 사용 시 "Phase 2A(Imagen 4) 통합 전까지 일시 비활성" 경고 배너
- [ ] 정치_pro 영향 없음 ✅ (원본 클립 사용)

**복잡도**: LOW (1~2h)

### Phase 1: 분석 백본 Gemini 이주 (Week 1)
**1A. YouTube 멀티모달 직접 분석**
- 신규: `src/analyzer/gemini_youtube_analyzer.py`
- Gemini Files API에 YouTube URL 업로드 → 자막+영상 동시 분석
- 정치_pro: 90초 → 30초 단축
- Whisper STT는 폴백으로만 유지

**1B. Claude CLI → Gemini 2.5 Flash 백본**
- 우선: `claude_analyzer.py`, `celebrity_analyzer.py`
- 정치_pro Stage B는 마지막 (락인 보호)
- 환경변수 `ANALYZER_BACKEND=gemini|claude` 토글
- 14일 A/B 후 default 전환

**복잡도**: MEDIUM (5~7h) | **변동비**: $0 (Flash 무료 한도 1500/일)

### Phase 2: 웹앱 브라우저 자동화 (Week 2~3)
**2A. Imagen 4 (gemini.google.com)**
- 신규: `src/illustrator/gemini_web_image_gen.py`
- 패턴: `freepik_image_gen.py` 그대로
- CLI: `python3 -m src.main gemini_login`
- factory.py: gemini → seedance_image (폴백)

**2B. Veo 3 (gemini.google.com)**
- 신규: `src/video_gen/gemini_web_video_gen.py`
- 패턴: `deevid_gen.py` 그대로
- 8초 720p + 네이티브 오디오
- factory.py 우선순위: gemini → deevid → seedance

**복잡도**: HIGH (10~14h) | **리스크 완화**: 기존 deevid 폴백 유지, 일별 한도 모니터링

### Phase 3: 신규 기능 (Week 4)
**3A. 다중 화자 (정치_pro)**
- `--multi-voice` 플래그 (default OFF, 락인 보호)
- format_type=C 대화형: Charon(앵커) + Kore(현장기자)

**3B. NotebookLM 스타일** (별도 탭)
- 사용자 PDF/URL 5건 → Gemini 종합 → 쇼츠

**복잡도**: MEDIUM (6~8h)

### Phase 4: Deep Research 팩트체크 (Week 5)
**4A. 발언 grounding 검증** (정치_pro)
- Gemini Grounding with Google Search
- 검수 화면 🟢/🟡/🔴 배지

**4B. 출처 자동 첨부**
- YouTube description 자동 삽입
- 영상 마지막 "출처" 화면

**복잡도**: HIGH (10~15h)

### 안전성 가드 (전 Phase 공통)
1. 환경변수/UI 토글로 즉시 롤백 가능
2. 기존 백엔드 14일 병행 → A/B 후 default 전환
3. 정치_pro 락인 포맷 불변
4. 무료 한도 80% 알림 + 자동 폴백
5. Phase별 회귀 테스트 (시리즈 1~3탄 동일 입력 비교)

### 진행 순서
```
DAY 0  Phase 0  긴급 패치       ← NOW
WEEK 1 Phase 1  분석 백본
WEEK 2 Phase 2A Imagen 4
WEEK 3 Phase 2B Veo 3
WEEK 4 Phase 3  신규 기능
WEEK 5 Phase 4  팩트체크
```

---

## 이전 계획

(이전 prompt_plan.md는 prompt_plan.md.bak에 보관)

