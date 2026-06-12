# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 / NATV / 정치 / 셀럽 영상을 YouTube Shorts로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-06-12

---

## ✅ 완료: 029 SFX(씬 전환 효과음) 소프트 비활성화 (2026-06-12)

> 사용자 요청: "씬이 바뀔때마다 효과음 넣는 기능이 있는데 효과음을 아예 빼고 싶어"
> 결정: 소프트 비활성화(코드·에셋·테스트 보존, 자동 할당·렌더만 OFF) — 향후 복구 가능
> 정치 모드(jpolitics V3 / political_pro / 정치쇼츠 V2)는 이미 SFX OFF로 락인되어 있어 영향 없음

### 변경 사항
- **`src/video/renderer.py`** — `render_video()` 진입 직후 `enable_sfx = False; auto_sfx = False` 강제. CLI/API에서 어떤 값을 보내도 SFX는 들어가지 않음. `_strip_scene_effects(drop_sfx=True)`가 모든 씬의 `sfx`를 빈 튜플로 치환.
- **`src/video/remotion/src/ShortsComposition.tsx`** — Per-scene SFX 재생 블록 제거(이중 안전망). `SfxConfig` TS 타입은 보존.
- **`app/api/generate/route.ts`** — `useSfx = false` 고정, 클라이언트 토글 무시.
- **`app/api/rerender/route.ts`** — `safeSfx = false` 고정.
- **`app/page.tsx`** — `sfx` 초기값 `false`, "🔊 효과음" 체크박스 6곳 모두 숨김(주석 처리). state는 FormData 호환을 위해 보존.

### 보존 항목 (재활성화 대비)
- `SfxConfig` dataclass / `Scene.sfx` 필드 (`src/analyzer/script_models.py`)
- `src/video/sfx_matcher.py` (자동 할당 모듈)
- `app/components/SfxPicker.tsx` (수동 선택 UI)
- `data/sfx/` (14개 합성 SFX) + `public/sfx/` (5개 QW-04 프로덕션 SFX + LICENSES.md)
- `tests/test_sfx_matcher.py` (단위 테스트)
- `scripts/generate_sfx.py`

### 복구 방법
1. `src/video/renderer.py`에서 `# SFX globally disabled` 주석 블록 3줄 제거
2. `src/video/remotion/src/ShortsComposition.tsx`의 SFX 주석을 원래 `scriptData.scenes.map(...)` 블록으로 복원 (git log 참조)
3. `app/api/generate/route.ts`와 `app/api/rerender/route.ts`의 `useSfx`/`safeSfx` 강제 라인 원복
4. `app/page.tsx`의 `sfx` 초기값을 `true`로, 6개 체크박스 라벨 복원

---

## 🚧 진행 중: 028 AI 인플루언서 — `influencer` 모드 신설 (2026-06-12)

> 기획 세션: 2026-06-12. 사용자 확정: "higgsfield를 사용하는 방식으로 진행" (fal.ai LoRA 스택 대신 Higgsfield 채택)
> 근거: deep-research 2회 — ① 성공사례·플랫폼정책·수익화 (98개 주장 추출, 정책 6건 공식문서 3-0 확정) ② 프리미엄 캐릭터 일관성 기술 비교

### 콘셉트 (확정)
- **"힙업 루틴 전문 피트니스 + 오피스룩 직장인 일상" 듀얼 콘셉트**, 사실적 여성 AI 캐릭터, 성인 팔로워 타깃
- **SFW 수위 고정** — Instagram 추천 제외(섀도밴)가 **계정 단위**로 작동함이 공식 확인됨(help.instagram.com/313829416281232). 비치는 옷 등 suggestive 판정 요소 금지를 코드 상수로 강제
- 벤치마크: @fit_aitana (6개월 23.6만 팔로워, 월 평균 €3k·피크 €10k, 협찬 ~$1k/포스트 + Fanvue 구독). 전략 핵심 = 백스토리 있는 '인생 서사' 주간 대본화
- 플랫폼: Instagram 주력(수동 업로드) + YouTube Shorts/TikTok 보조(기존 업로더 재사용, AI 라벨 의무 처리)

### 기술 스택 (Higgsfield 단일 플랫폼)
- **캐릭터 고정**: Soul ID 학습 (~$3/회, 15~20장) — LoRA 대체
- **이미지 양산**: Soul 2.0 + Soul ID (패션/일상 프리셋 80+), 편집은 플랫폼 내 Nano Banana Pro
- **영상 i2v**: 허브 내 Seedance 2.0(히어로 씬 — 멀티씬 캐릭터 일관성 1위) / Kling(대량 b-roll — 저단가)
- **통합**: Higgsfield Cloud API (cloud.higgsfield.ai), 폴백 공식 MCP (higgsfield.ai/mcp)
- 비용: 구독 Plus ~$34-49/월 (물량 증가 시 Ultra ~$84-129), Soul ID 학습 $3
- OpenAI 미사용 (기존 방침 유지)

### Phase
- [ ] **Phase 0 — 셋업 + 캐릭터 캐스팅 (코드 최소)**: ① Higgsfield 구독 + Cloud API 키 발급(사용자 작업) + API 커버리지 확인(Soul ID 학습/Soul 2.0/영상이 API로 노출되는지 — 미노출 항목은 웹 UI 1회성 수동 + 생성만 API) ② 캐릭터 설정 문서(이름·백스토리·정체성 앵커 3종: 헤어/시그니처 패션/컬러 + SFW 수위 가이드라인) ③ 후보 시안 3~5종 생성 → 사용자 선택 → Soul ID 학습 → 일관성 실측 ④ 같은 캐릭터 컷으로 Seedance 2.0 vs Kling 영상 실측 비교
- [ ] **Phase 1 — 이미지 파이프라인** (`src/influencer/`): `higgsfield_client.py`(Cloud API), `persona.py`(frozen dataclass, 수위 가드 상수), `content_planner.py`(주간 콘텐츠 캘린더 — Claude, 힙업 루틴 N + 오피스 일상 M + 서사 포스트), CLI `influencer` 서브커맨드
- [ ] **Phase 2 — 영상 파이프라인**: i2v(Seedance 2.0/Kling) + 기존 Remotion 쇼츠 조립 재사용(정지컷 캐러셀 + 5초 모션 b-roll 혼합 포맷 — 운동 시연 양산은 AI 물리 한계로 회피)
- [ ] **Phase 3 — 운영 도구**: 웹 UI 탭, YouTube/TikTok 업로더 연동 + AI 라벨 자동 처리, 자동 업로드 차단 가드(검수 필수, jpolitics 패턴 계승), 3줄 요약+해시태그 규칙 적용

### 리스크
- HIGH: Instagram 계정 단위 추천 제외(공식 확정) → 수위 상수 강제 + 게시 전 검수 게이트
- HIGH: 계정 정지 — AI 라벨 명시에도 셀카 본인인증 단계 영구정지 사례(포럼) → 자연스러운 성장 패턴, 플랫폼별 계정 분리
- MEDIUM: Higgsfield API 커버리지 불확실(Soul ID 학습이 API 미노출 가능성) → Phase 0에서 확인 후 통합 범위 확정
- MEDIUM: 운동 동작 영상 물리 오류(Veo-3 스포츠 성공률 60%, arXiv 2512.14691) → Seedance 우선 + 승인 게이트
- LOW: 크레딧 소진 → Ultra 전환 (Kling 무제한 옵션)

---

## 🚧 진행 중: 027 정치쇼츠 V3 재구축 — "모먼트 직캠" 포맷 (2026-06-11)

> 기획 세션: 2026-06-11. 사용자 확정: "네" (결정사항 1~3 권고안 채택)
> 근거: 벤치마크 실측 분석 — 겸손은힘들다 쇼츠(24만~280만뷰) 2편 프레임 분석, YTN 청문회 모먼트(26만뷰), 국회직캠(구독 207, 중앙값 1,200뷰)과 비교

### 핵심 결정
- **V2(political_pro) 무수정** — 안정 운영, lock-in 유지
- **기존 V3(jpolitics, @김정치입니다 포맷) 전체 삭제** — 6,834줄 (src 2,209 + app 970 + tests 2,541 + remotion_v3 1,114)
- **신규 V3 = 모먼트 직캠 포맷**: ①풀블리드(여백0) ②원본 음성(TTS 제거, --tts-bridge 옵션만) ③질문형 떡밥 훅 타이포 카드(첫 1~2초) ④감정 모먼트 검출(웃음·충돌·언성) ⑤실시간 발언 자막 ⑥질문형 제목+해시태그 설명란 분리
- 격리 원칙 계승: V1/V2 파일 0 수정, read-only import만, page.tsx 버튼 1개
- 데이터: data/jpolitics 산출물 보관 / data/jpolitics_reference 백업 후 삭제
- 기존 V3 lock-in 메모리 7항목 폐기 (출처라벨 하단·효과음0·전환0은 신규에 계승)

### 파이프라인
YouTube URL → 다운로드+transcript(youtube_downloader 재사용) → Gemini 멀티모달 모먼트 검출 톱5 → 사용자 선택 → ffmpeg 컷+9:16 풀블리드 센터크롭(--crop-x 보정) → Remotion: 풀블리드+훅 타이포 카드+실시간 자막+출처 라벨 → 질문형 제목 3안+설명란 해시태그+고정댓글 질문 (업로드 수동)

### Phase
- [x] **Phase 0 (완료 2026-06-11)**: 기존 V3 삭제 (6,834줄 + reference 6.1MB, git 복구 가능), page.tsx 버튼 주석 처리(Phase 4에서 복원), lock-in 메모리 갱신. 회귀: 1283 passed + 빌드 성공
- [x] **Phase 1 (완료 2026-06-11)**: 모먼트 검출 엔진 — `src/jpolitics/` 신규 (models/moment.py, analyzer/moment_detector.py + prompts.py, main.py CLI). 17 신규 테스트, 전체 1300 passed. **실 영상 E2E 검증**: YTN 청문회 영상에서 멀티모달이 웃음 모먼트(22~32s, conf 1.0) 정확 검출 + 질문형 훅 생성 확인. transcript 폴백 체인 동작 확인. Files API 간헐 FAILED 실측 → 2회 재시도 추가. 부수 수정: python-dotenv 미설치로 CLI에서 .env.local 미로딩이던 잠복 버그 해결(requirements.txt 추가)
- [x] **Phase 2 (완료 2026-06-11)**: 클립 가공 — `src/jpolitics/video/clip_maker.py`(ffmpeg 재인코딩 9:16 크롭, ClipResult), `src/jpolitics/video/captions.py`(VTT→transcribe 폴백 체인, 구간 필터·상대화·중복제거). `src/jpolitics/models/clip.py`(CaptionCue+ClipResult frozen dataclass). `cut` CLI 서브커맨드. 27 신규 테스트, 63 jpolitics passed. Next.js 빌드 성공 (tsconfig.json exclude 추가).
- [x] **Phase 3 (완료 2026-06-11)**: Remotion V3 신규 컴포지션 — `src/video/remotion_v3/`(MomentShorts composition, HookCard·LiveCaption·SourceLabel 컴포넌트). `src/jpolitics/video/renderer.py`(render_moment_short). `render`/`run` CLI 서브커맨드. 19 신규 테스트. 전체 63 jpolitics passed + 빌드 성공.
- [x] **Phase 4 (완료 2026-06-11)**: 메타+웹 UI — `src/jpolitics/analyzer/meta_generator.py`(MetaResult: 제목 3안·해시태그·고정댓글, Claude 1-shot), `src/jpolitics/api_bridge.py`(detect/cut/render/meta JSON 어댑터), `app/jpolitics/page.tsx`(5단계 state machine: idle→detecting→moments→processing→done), API 라우트 3개(detect/render/meta SSE), `app/page.tsx` V3 버튼 주석 해제. 31 신규 테스트, 전체 94 jpolitics passed + Next.js 빌드 성공.
- [ ] **Phase 5**: E2E — 실제 영상 1편 생성 + 전체 회귀

### 리스크
- HIGH: 모먼트 검출 품질 — Gemini 멀티모달로 해결, 무료 티어 10 req/day 병목. 폴백: transcript 기반 검출
- MEDIUM: 센터 크롭 화자 잘림 → --crop-x 수동 보정, 얼굴 인식은 후속
- MEDIUM: 원본 음성 저작권 — V2와 동일 수준, 출처 라벨 필수
- LOW: 회귀 — 격리 구조

---

## 이전 계획


## 🚧 진행 중: 026 운영 안정성 + 미완성 기능 정리 (2026-06-11)

> 기획 세션: 2026-06-11 (/plan — 프로젝트 전체 분석 후 개선 로드맵)
> 사용자 확정: "진행" (Phase 1부터, Phase 2B는 UI 토글 숨김 권고안 채택)
>
> **상태 (2026-06-11)**: Phase 1 완료 + Phase 2 항목 4(2B 숨김) 완료.
> - cleanup CLI: `src/maintenance/cleanup.py` + `python3 -m src.main cleanup` (dry-run 기본, 실측 743파일/1.69GB 식별)
> - 업로드 재시도: `src/upload/retry.py`(backoff) + `src/upload/upload_history.py`(이력 JSON) — YouTube/TikTok 연결
> - 브라우저 진단: `src/video_gen/browser_diagnostics.py` — freepik/deevid 실패 시 세션만료/DOM변경/네트워크 구분 메시지
> - Veo 3 토글: `app/page.tsx`에서 숨김 (코드 보존, 주석으로 복원 위치 표기)
> - 검증: pytest 1382 passed/0 failed, 신규 파일 ruff clean, Next.js 빌드 성공
> - 잔여: Phase 2 항목 5(팩트체크 통합)·6(NotebookLM), Phase 3(UI 편의), Phase 4(부채)

### 현황 진단 (탐색 에이전트 2개 분석 결과)

| 영역 | 상태 | 근거 |
|------|------|------|
| Phase 1A/1B/2A (Gemini transcript·분석·이미지) | ✅ 통합 완료 | youtube_downloader.py:352, route.ts:1054 |
| Phase 2B (Veo 3 영상) | ⚠️ 골격만, selector 미검증 | gemini_web_video_gen.py:1-13 "초안" 명시 |
| Phase 3A/3B/4 (멀티보이스·NotebookLM·팩트체크) | ⚠️ 코드만 존재, 호출처 0 | main.py/route.ts에서 미사용 |
| 브라우저 자동화 안정성 | ⚠️ generic 에러, 세션 만료 자동복구 없음 | freepik_gen.py:298-301 |
| 데이터 관리 | ❌ 정리 정책 없음, 6.8GB 누적 | data/political_pro 1.5GB 등 |
| 웹 UI 운영성 | ⚠️ 재시도 버튼·히스토리 목록 없음 | page.tsx:271 에러 시 reset만 |
| 업로드 | ⚠️ 즉시 업로드만, 재시도·예약·이력 없음 | youtube_uploader.py |
| 기술 부채 | main.py 1735줄, bare pass×3, 테스트 공백(editor/upload) | political_planner.py:864-878 |

### Phase 1: 운영 안정성 (이번 세션)
1. **브라우저 자동화 공통 안전장치** — selector 미발견 시 원인 구분 로깅(DOM 변경/세션 만료/네트워크), 공통 헬퍼를 freepik/deevid/gemini generator에 적용. 세션 만료 감지 → 명확한 재로그인 안내.
2. **데이터 정리 CLI** — `python3 -m src.main cleanup [--dry-run]`. temp 24시간, 중간산출물(images/videos/audio) N일 보관, 최종 outputs 보존. dry-run 기본.
3. **업로드 재시도** — YouTube/TikTok 업로드 exponential backoff + 업로드 이력 JSON 기록.

### Phase 2: 미완성 Gemini 기능 정리
4. **Phase 2B (Veo 3)**: UI 토글 숨김 처리 (완성 보류 — gemini.google.com selector 유지보수 부담 HIGH 리스크). 코드는 보존, 추후 완성 결정 시 재노출.
5. **Phase 4 (팩트체크) political_pro 통합**: 기획안 검수 단계에 🟢/🟡/🔴 배지 표시. 정치쇼츠 lock-in 포맷 불변(영상 출력 무변경, 검수 화면에만 추가).
6. **Phase 3B (NotebookLM 스타일)**: 보류 (우선순위 낮음).

### Phase 3: 웹 UI 운영 편의
7. 실패 시 "같은 설정으로 재시도" 버튼 (reviewSnapshot 확장)
8. 프로젝트 히스토리 페이지 (/projects)
9. 진행률 개선 (고정 8단계 → 실제 단계 기반 + 경과 시간)

### Phase 4: 기술 부채 (여유 시)
10. main.py 명령별 모듈 분리, political_planner.py bare pass 로깅, editor/upload 테스트 보강

### 리스크
- HIGH: Phase 2B selector 유지보수 → 숨김으로 회피
- MEDIUM: cleanup CLI 삭제 작업 → dry-run 기본 + outputs 제외
- LOW: 모든 Phase에서 정치쇼츠 V1/V2/V3 lock-in 포맷 불변

---

## 이전 계획

# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 / NATV / 정치 / 셀럽 영상을 YouTube Shorts로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-06-05

---

## ✅ 완료: 025 정치쇼츠 V3 — "@김정치입니다" 포맷 도입 (2026-06-05)

> 상태: **E2E 4종 레이아웃 시각 검수 PASS** — Phase 1~7 + E2E (T041/T055/T063/T071) + T082 quickstart 검증 완료. 잔존: T074 V1/V2 byte-equality baseline (V1/V2 영상 새로 생성 필요, 옵션).
> 기획 세션: 2026-06-05
> 참고 채널: [@김정치입니다](https://www.youtube.com/@김정치입니다)
> **아키텍처 모드: 완전 격리 (Total Isolation)** — 기존 파일 0 수정 원칙, 단 진입 버튼 1개 예외
>
> **검증 결과 (2026-06-05)**:
> - jpolitics 테스트: 99 passed, 3 skipped (regression baseline 미생성, SKIP OK)
> - V1/V2 회귀 테스트: **1254 passed, 1 skipped** (SC-003 297+ 한참 초과)
> - V1/V2 Remotion tsc: 0 errors (회귀 0건)
> - V3 Remotion tsc: 0 errors
> - Next.js 빌드: 47/47 페이지 컴파일 성공 (`/jpolitics` + 3 API 라우트 포함)
> - 격리 가드: 3/3 통과 (V1/V2 보호 파일 무수정 + read-only import만 + `app/page.tsx` 버튼만 추가)
> - **E2E 4종 레이아웃 (T041/T055/T063/T071)**: 모두 30.06초 영상 시각 검수 PASS
>   - talking_head: 조국 사퇴 영상 (노란 헤드라인 + 자막 + 출처 라벨 3요소)
>   - vs_card: 양향자 vs 추미애 (좌 빨강 국힘 + 우 파랑 더민주 + 인물 사진)
>   - grid_2x2: 평택을 후보 4명 (2×2 그리드 + 인물 사진 + 정당 컬러 테두리)
>   - data_card: 조국 재산 56억 (인물 사진 720×720 + 거대 빨강 "56억 원" 144px)
> - 락인 검증 (T041a): 오디오 트랙 1개 ✓ / 씬 경계 무음 검출 ✓ / clip_search_query 메타 ✓

### 요구사항
YouTube 채널 `@김정치입니다`의 영상 제작 방식을 분석하고, 그 포맷을 자동으로 재현하는 **"정치쇼츠 V3"** 탭을 신설한다. 기존 V1(`political`) / V2(`political_pro`)와 공존, 옵트인 탭.

### 🔒 격리 원칙 (사용자 lock-in)
- **모든 V3 코드는 독립 디렉토리에 격리** — `src/jpolitics/`, `src/video/remotion_v3/`, `app/jpolitics/`, `tests/jpolitics/`
- **기존 파일 편집 0** — 유일한 예외: `app/page.tsx`에 V3 진입 버튼 1개 추가 (사용자 요청)
- **기존 코드는 read-only import만** — `youtube_news_searcher`, `naver_image_search`, `_call_claude`, `gemini_backend` 등 재사용은 import만 (편집 X)
- **회귀 0 보장** — 기존 V1/V2/celebrity/briefing 297+ 테스트 자동 무회귀

### 채널 포맷 분석 결과 (샘플 3편 검증)

| 샘플 | 주제 | 레이아웃 | 데이터 패턴 |
|---|---|---|---|
| **S1** 조국 사퇴 (nPOJYSXdICI) | 1인 연설/인터뷰 | Talking Head (원본 풀스크린) + 페북 글 인서트 | 상단 노란 헤드라인 / 하단 자막 박스 / 출처 라벨 |
| **S2** 양향자 vs 추미애 (fBJH4SX02Ig) | 2인 대결/논평 | VS 카드 (좌·파랑 / 우·빨강 정당 컬러) → Talking Head | 정당 컬러 카드 + MBC 라디오 출처 |
| **S3** 평택을 후보 4명 (_eGbiXgBI6E) | 다인 비교 | 2x2 그리드 (4명 사진) + 시간별 데이터 슬라이드 | 빨강 강조 데이터 (재산/세금/공약) |

### 공통 시각 패턴 (7요소)
1. **고정 헤드라인 (Hook Title)** — 영상 전체 노란 박스 + 검정 두꺼운 한글 폰트 2줄
2. **하단 자막 박스** — 흰 라이트박스 + 실시간 캡션, 빨강 강조 가능
3. ~~채널 워터마크~~ — **본 프로젝트는 제외 (사용자 lock-in)**
4. **출처 라벨** — 하단 "출처 : XXX / YYYY.MM.DD" (외부 인용 시)
5. **레이아웃 다양화** — Talking Head / VS 카드 / 2x2 그리드 / 데이터 슬라이드
6. **정당 컬러 코드** — 민주(파랑) / 국힘(빨강) 정확 매칭
7. **데이터 강조** — 큰 빨간 숫자 (재산/세금/연도 등 비교 수치)

### 사용자 Lock-in 결정 (2026-06-05)
| 항목 | 결정 |
|------|------|
| TTS 보이스 | **V1 락인 유지 — `ko-KR-InJoonNeural` +22%** (Charon 사용 안 함) |
| 채널 워터마크 | **제외** (V3는 워터마크 없음, 출처 라벨만 유지) |
| 레이아웃 범위 | **4종 모두 구현** — `normal` / `vs_card` / `grid_2x2` / `data_card` |
| 효과음(SFX) | **영구 0** — 어떤 씬에도 효과음·BGM 삽입 금지 (FR-034, SC-011) |
| 씬 전환 효과 | **하드 컷만** — 그라데이션·페이드·디졸브 미사용 (FR-035, SC-012) |
| TTS 씬 간 gap | **300 ms 고정** — 그룹 경계에서만 0.3초 무음 (FR-036, SC-013) |
| 영상 추출 흐름 | **Gemini Files API → Claude 검색 키워드 결정 → yt-dlp 다운로드** 3단계 분업 (FR-037, SC-014) |

### V1/V2/V3 차별점

| | V1 (political) | V2 (political_pro) | **V3 (jpolitics)** |
|---|---|---|---|
| 기획 | 1단 Claude 분석 | RTF 6요소 3안 비교 | RTF + **레이아웃 자동 분류** (TH/VS/GRID/DATA) |
| 레이아웃 | 풀스크린 1종 | normal / split 2종 | **normal / vs_card / grid_2x2 / data_card 4종** |
| 자막 | 3줄 (단일색) | 1줄 4색 + emphasis | 1줄 4색 + **고정 헤드라인 노란 박스** |
| 데이터 시각화 | 없음 | 없음 | **인물 카드 + 빨강 강조 수치** |
| TTS | InJoonNeural +22% | Gemini Charon Newscaster | **InJoonNeural +22% (V1 락인 유지)** |
| 출처 라벨 | metadata만 | 하단 letterbox | 하단 letterbox **(워터마크 제외)** |
| 이미지 소스 | 원본 클립 | 원본 클립 | **원본 클립 + Naver 인물 사진 + 정당 로고 자동 페치** |

---

### 구현 단계 (완전 격리 — 10 Phase)

**Phase 1 — Spec 문서 + 샘플 보관 (read-only)**
1. `specs/010-jpolitics-v3-format/{spec,plan,tasks,data-model,research,quickstart}.md` 작성
2. `data/jpolitics_reference/` — 샘플 3편 키프레임 보관 (`/tmp/jpolitics_analysis/`에서 이동)
3. lock-in 항목: TTS=InJoonNeural+22%, 워터마크 없음, 레이아웃 4종, 진입은 메인 페이지 버튼 1개

**Phase 2 — `src/jpolitics/` 패키지 골격 + 독립 모델 (TDD)**
4. `src/jpolitics/__init__.py`, `src/jpolitics/models/__init__.py`
5. `src/jpolitics/models/script.py` — **독립 `JpoliticsScript` / `JpoliticsScene` frozen dataclass**
   - 필드: `id`, `timestamp`, `duration`, `type`, `text`, `voice_text`, `visual_layout` (`normal`/`vs_card`/`grid_2x2`/`data_card`), `subtitle_color`, `subtitle_emphasis`, `headline_pin`, `comparison_cards`, `data_emphasis_color`, `clip_path`, `clip_query`
   - Scene 상속 없음, 완전 독립 클래스
6. `src/jpolitics/models/plan.py` — 독립 `JpoliticsPlan` / `JpoliticsThreePlansResult`
7. 테스트: `tests/jpolitics/test_models.py` — 라운드트립, 카드 1~4개, 4종 layout 검증

**Phase 3 — 인물 카드 페치 모듈 (독립)**
8. `src/jpolitics/scraper/politician_card.py`:
   - `from src.scraper.naver_image_search import search_image` (read-only import)
   - `fetch_politician_card(name) -> dict` — Naver 검색 → 정면 사진 1장 → `data/politician_cards/{name}.json` 캐시
   - `PARTY_COLORS` 상수 (민주 #004EA2 / 국힘 #E61E2B / 조국혁신당 #0073CF / 개혁신당 #FF7920 / 무소속 #888)
   - `infer_party(name)` — Claude 1-shot 추론 (claude_analyzer._call_claude read-only import)
9. 테스트: 캐시 히트/미스, 무소속 회색 폴백, Naver 미발견 폴백

**Phase 4 — Planner (독립 Stage A/B)**
10. `src/jpolitics/analyzer/prompts.py` — `build_stage_a_prompt()`, `build_stage_b_prompt()`
    - Stage A: 영상 분석 + **레이아웃 분류** (`talking_head` / `vs_2way` / `comparison_grid` / `data_comparison`)
    - Stage B: 씬별 `visual_layout` + `comparison_cards` (필요시) + 첫 씬 `headline_pin` (8~14자)
11. `src/jpolitics/analyzer/planner.py`:
    - `from src.analyzer.claude_analyzer import _call_claude` (read-only import)
    - `from src.analyzer.gemini_backend import call_gemini` (read-only import)
    - `generate_three_plans(youtube_url, transcript, ...) -> JpoliticsThreePlansResult`
    - `plan_to_script(plan) -> JpoliticsScript` (카드 씬에 politician_card 페치 + 정당 컬러 주입)
12. 테스트: 4종 레이아웃 분류, 카드 페치 mock, 헤드라인 ≤14자

**Phase 5 — TTS wrapper (V1 락인 하드코딩)**
13. `src/jpolitics/tts/voice.py`:
    - `VOICE = "ko-KR-InJoonNeural"`, `RATE = "+22%"` 모듈 상수 락인
    - `synthesize(script: JpoliticsScript) -> tuple[Path, list[SceneTiming]]` — edge-tts 직접 호출
14. 테스트: 보이스 상수 변경 불가 검증, scene_timings 생성 검증

**Phase 6 — `src/video/remotion_v3/` 독립 Remotion 패키지**
15. 디렉토리 생성 + `package.json` (remotion 의존성만), `tsconfig.json`
16. `src/index.ts` → `registerRoot(Root)`
17. `Root.tsx` — V3 전용 composition 등록 (`<Composition id="JpoliticsShorts" ...>`)
18. `JpoliticsComposition.tsx` — main composition (background + PinnedHeadline + scene routing + outro + audio)
19. 컴포넌트 8종 (모두 신규):
    - `components/PinnedHeadline.tsx` — 영상 전체 상단 노란 박스 + 검정 두꺼운 폰트 2줄
    - `components/TalkingHeadScene.tsx` — 원본 클립 풀스크린
    - `components/VsCardScene.tsx` — 좌·우 분할, 정당 컬러 배경
    - `components/ComparisonGridScene.tsx` — 2x2 그리드 + 데이터 빨강 강조
    - `components/DataCardScene.tsx` — 단일 인물 카드 + 큰 데이터
    - `components/SubtitleBlock.tsx` — V2 자막 패턴 복제 (4색 + emphasis)
    - `components/Background.tsx` — V2 패턴 복제 (그라데이션)
    - `components/Outro.tsx` — V2 패턴 복제
    - `components/LetterboxFrame.tsx` — 하단 출처 라벨 영역
20. 테스트: `npx tsc --noEmit` 통과, preview 4종 스크린샷

**Phase 7 — Python renderer wrapper (독립)**
21. `src/jpolitics/video/renderer.py`:
    - `render(script: JpoliticsScript, audio_path: Path, scene_timings, output_path)` — `npx remotion render` 호출 with `src/video/remotion_v3/`
    - 자산 복사: 클립/오디오/인물 카드 → `src/video/remotion_v3/public/` (격리)
22. 테스트: subprocess mock + 자산 복사 검증

**Phase 8 — CLI entry (독립 모듈)**
23. `src/jpolitics/main.py`:
    - argparse: `python3 -m src.jpolitics.main <youtube_url>` / `--source-type topic --topic "..."`
    - 흐름: transcript → planner → 사용자 선택 (CLI prompt) → tts → renderer
24. 테스트: argparse 분기, e2e (transcript fixture)

**Phase 9 — Next.js 독립 페이지 + API (`app/jpolitics/`)**
25. `app/jpolitics/page.tsx` — V3 전용 페이지 (URL `/jpolitics`)
26. `app/jpolitics/components/JpoliticsPlanPicker.tsx`, `JpoliticsScriptReviewer.tsx`
27. `app/jpolitics/api/plans/route.ts` — V2 패턴 복제, jpolitics_main 호출
28. `app/jpolitics/api/render/route.ts` — V2 패턴 복제
29. **FR-020 업로드 차단 + FR-021 검수 필수 배너** (rose-amber)
30. 테스트: API smoke + 3줄 요약 + 해시태그

**Phase 10 — 진입 버튼 + E2E 검증 + lock-in (유일한 예외 수정)**
31. ⚠️ **유일한 기존 파일 수정**: `app/page.tsx` 헤더 영역에 V3 진입 버튼 1개 추가
    - 예: `<button onClick={() => router.push("/jpolitics")}>🟡 정치 V3</button>`
    - 기존 8개 탭 union 타입·로직·폼 모두 무수정 — 헤더 버튼만 추가
32. 4종 레이아웃(`normal`/`vs_card`/`grid_2x2`/`data_card`) 각각 샘플 영상 1편씩 생성
33. 회귀 검증: 기존 297+ 테스트 무회귀 + 신규 50+ 통과 + Next.js 빌드 + `cd remotion_v3 && npx tsc --noEmit`
34. 3줄 요약 + 해시태그 자동 첨부 검증

---

### 영향 받는 파일 (격리 모드)

**🆕 신규 파일만** (편집 0):
```
src/jpolitics/                       (Python 패키지 신규 ~12 파일)
  __init__.py, main.py
  models/{__init__,script,plan}.py
  scraper/{__init__,politician_card}.py
  analyzer/{__init__,prompts,planner}.py
  tts/{__init__,voice}.py
  video/{__init__,renderer}.py

src/video/remotion_v3/               (독립 Remotion 패키지 신규 ~12 파일)
  package.json, tsconfig.json
  src/index.ts, Root.tsx, JpoliticsComposition.tsx
  src/components/{PinnedHeadline,TalkingHeadScene,VsCardScene,
                  ComparisonGridScene,DataCardScene,SubtitleBlock,
                  Background,Outro,LetterboxFrame}.tsx

app/jpolitics/                       (Next.js 라우트 신규 ~5 파일)
  page.tsx
  components/{JpoliticsPlanPicker,JpoliticsScriptReviewer}.tsx
  api/plans/route.ts
  api/render/route.ts

tests/jpolitics/                     (격리 테스트 신규 ~6 파일)
  test_models.py, test_planner.py, test_politician_card.py,
  test_tts_voice_lockin.py, test_renderer.py, test_e2e.py

specs/010-jpolitics-v3-format/       (사양 문서 6 파일)

data/jpolitics_reference/            (샘플 키프레임)
data/politician_cards/               (인물 카드 캐시)
data/jpolitics/                      (V3 영상 출력 격리 디렉토리)
```

**🔧 기존 파일 수정** (1개만):
- `app/page.tsx` — **V3 진입 버튼 1개 추가** (헤더 영역, 기존 탭 로직 무수정)

**📖 기존 파일 read-only import** (편집 0):
- `src/scraper/youtube_news_searcher.py` — yt-dlp 검색·9:16 컷 재사용
- `src/scraper/naver_image_search.py` — Naver 이미지 검색 재사용
- `src/analyzer/claude_analyzer.py` — `_call_claude` 재사용
- `src/analyzer/gemini_backend.py` — Stage A Gemini 호출 재사용

---

### 의존성 / 사전 조건
- ✅ `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` (셀럽 모드용 이미 존재) — 인물 사진 검색에 재사용
- ✅ `MS-Hannah-NotoSans-Bold` / `Noto Sans KR Black` — 노란 헤드라인용 (Remotion 이미 설치됨)
- ✅ `data/jpolitics_reference/` — 샘플 키프레임 보관 (lock-in 확인용)
- ❌ ~~채널 워터마크 PNG~~ — **사용자 lock-in: 제외**

---

### 리스크

| 등급 | 항목 | 완화책 |
|---|---|---|
| 🔴 **HIGH** | **저작권** — 정치인 사진(Naver)·뉴스 클립 인용 = 제3자 저작물 | V2와 동일: 업로드 UI 차단(FR-020) + "검수 필수" 배너(FR-021), 보도·논평 목적 명시 |
| 🟡 **MED** | **레이아웃 오분류** — LLM이 talking_head를 grid로 잘못 분류 시 부자연 | Stage A 프롬프트에 4종 명확 예시 + 사용자 수정 가능 UI (선택 드롭다운) |
| 🟡 **MED** | **카드 데이터 환각** — Claude가 "127억" 같은 데이터를 LLM hallucination 출력 | data_card 씬은 transcript에 명시된 숫자만 인용 + 출처 라벨 강제 |
| 🟢 **LOW** | **정당 매핑 누락** — 무소속/신생 정당 헥스 컬러 미정 | `infer_party` 폴백 시 회색(#888) + 경고 로그 |
| 🟢 **LOW** | **Naver 사진 누락** — 인물명 검색 실패 | 그라데이션 폴백 + 콘솔 경고 |

---

### 비용·복잡도 (격리 모드)
- **변동비**: $0 (Naver 무료 25,000건/일, Gemini 무료 250req/일, Edge TTS 무료, Claude 기존 한도)
- **복잡도**: **HIGH (격리 모드 +5h)**
  - Phase 1 Spec: 1-2h
  - Phase 2-5 백엔드 독립 패키지: 8-10h
  - Phase 6 Remotion V3 독립 패키지 (컴포넌트 8종 + 공통 복제): 6-8h
  - Phase 7-9 Renderer + CLI + Next.js: 4-5h
  - Phase 10 진입 버튼 + E2E: 2-3h
  - TDD 테스트: 4-5h
  - **합계: 25-33h** (vs. 통합 안 18-23h, 격리 모드 +7-10h 트레이드오프)
- **신규 LOC**: ~2500 (Remotion 컴포넌트 복제분 ~1000 포함)
- **격리 가치**: 기존 297+ 테스트 자동 무회귀 + V1/V2 락인 100% 보장

---

### 검증 기준 (DoD)
- [ ] 4종 레이아웃(`normal`/`vs_card`/`grid_2x2`/`data_card`) 각각 샘플 영상 1편씩 생성 → 사용자 OK
- [ ] 고정 헤드라인 + 출처 라벨 2요소 모든 씬 노출 확인 (워터마크 제외)
- [ ] TTS = InJoonNeural +22% 하드코딩 검증 (변경 시도 시 테스트 실패)
- [ ] 단위 테스트 신규 50+ 통과 / 회귀 테스트 297+ 유지 (격리로 자동 보장)
- [ ] Next.js 빌드 success + V3 TypeScript `cd src/video/remotion_v3 && npx tsc --noEmit` 통과
- [ ] 기존 V1/V2 Remotion 빌드도 무회귀 (`cd src/video/remotion && npx tsc --noEmit`)
- [ ] 메인 페이지 V3 진입 버튼 동작 + `/jpolitics` 라우팅 확인
- [ ] 기존 V1/V2/celebrity/briefing 탭 무회귀 (탭 union 타입 무수정)
- [ ] 3줄 요약 + 해시태그 자동 첨부

---

### 참고 코드 위치 (read-only 참고용 — 편집 X)
- V2 layout split 패턴 참고: `src/analyzer/script_models.py:135-142` (필드 구조만 참조하여 JpoliticsScene 독립 작성)
- V2 SplitScreenScene 참고: `src/video/remotion/src/components/SplitScreenScene.tsx` (분할 화면 로직 참조)
- 정치_pro Stage A/B 흐름 참고: `src/analyzer/political_planner.py` (병렬 패턴 모방, import는 `_call_claude`만)
- TTS edge-tts 호출 패턴: `src/tts/edge_tts_synth.py` (구현 패턴 참조)
- Naver 이미지 검색 import: `from src.scraper.naver_image_search import search_image`
- Remotion 자산 복사 패턴: `src/video/renderer.py` (격리된 `remotion_v3/public/`로 동일 패턴 적용)
- V2 API route 구조 참고: `app/api/political-pro/plans/route.ts` (구조만 참조하여 독립 작성)
- V2 자막 분할 알고리즘: `src/editor/subtitle_split.py` (read-only import 가능, 자막 품질 동일 유지)

---

## ✅ 완료: 024 유명인 쇼츠 — 유튜브 클립 소스 추가 (2026-05-28)

> 상태: **구현 완료** (커밋: dcb20ea)
> 기획 세션: 2026-05-28 | 구현 세션: 2026-05-28

### 요구사항
유명인 쇼츠에서, 정치 topic 모드처럼 **유튜브에서 해당 인물의 실제 영상을 씬별로 검색·다운로드·9:16 컷**하여 씬 배경 영상으로 쓰는 새 옵션을 추가한다. 기존 동작(Freepik 이미지→영상 / 이미지)은 그대로 유지하고 **옵트인**으로 붙인다.

### 확정된 설계 결정 (사용자 합의)
| 항목 | 결정 |
|------|------|
| 검색어 소스 | **새 `clip_query` LLM 필드** — celebrity 프롬프트가 씬별 영상 검색어 출력("손흥민 골 장면" 등), 미출력 시 `{name} {image_query}` → `{name}` 폴백 |
| 다운로드 | **씬별 ytsearch1** — `youtube_news_searcher.build_scene_clips()` 그대로 재사용 (새 스크래핑 코드 없음) |
| 9:16 처리 | **crop·letterbox 둘 다 구현** → 동일 씬으로 샘플 2종 생성 → 사용자가 보고 lock-in (미정) |
| 기본 동작 | **새 옵션 옵트인** (`--video-source youtube`), 기본값은 현행 유지 |

### 핵심 인사이트
`src/scraper/youtube_news_searcher.py`의 검색·다운로드·컷 로직(`build_scene_clips`, `cut_scene_clip`, `search_and_download_news_clips`)이 **완전히 재사용 가능**. 새 다운로드 코드 0. 작업 본질 = "유명인 파이프라인에 클립 소스 분기 + 씬별 검색어 1필드 + UI 토글".

### 구현 단계

**Phase 1 — 데이터 모델 + 컷 모드 (TDD)**
1. `Scene`에 `clip_query: str | None = None` 추가 (`src/analyzer/script_models.py`) — `to_dict`/`from_dict` 직렬화(값 있을 때만, camelCase `clipQuery` 호환), `image_query`와 동일 패턴
2. `cut_scene_clip()`에 letterbox 모드 추가 (`src/scraper/youtube_news_searcher.py`): `crop_9x16: bool` → `crop_mode: Literal["crop","letterbox"]` (기본 `"crop"`, 하위호환). letterbox vf = `scale=1080:-2,pad=1080:1920:0:(1920-ih)/2:color=black`. `build_scene_clips()`에 `crop_mode` 전달
3. 테스트: `clip_query` 라운드트립, `cut_scene_clip` letterbox vf 인자 생성(ffmpeg mock)

**Phase 2 — 유명인 유튜브 클립 헬퍼 (TDD)**
4. `_build_celebrity_clip_keywords(name, script)` (`src/main.py`): 씬별 검색어. 우선순위 `scene.clip_query` → `f"{name} {scene.image_query}"` → `f"{name}"`. `safe_search_keyword()`로 정리
5. `_run_celebrity_youtube_clips(name, script, *, scene_timings=None, crop_mode="crop")`: scene_durations = timing 있으면 timing 기반 else `scene.duration`. `build_scene_clips()` → `data/videos/celebrity/{ts}_{name}/`. 결과 `[{scene_id, video_path}]` 매핑(None 스킵)
6. 테스트: 검색어 빌더 폴백 체인, scene_id 매핑/None 처리(`build_scene_clips` mock)

**Phase 3 — CLI 배선**
7. `cmd_celebrity` 분기 (`src/main.py`): 새 인자 `--video-source {freepik,youtube}`(기본 freepik), `--clip-crop {crop,letterbox}`(기본 crop). `video-source=youtube`면 Step 5(TTS) 먼저 → scene_timings로 클립 컷 → render(정치_pro와 동일 순서, 싱크 정확). `metadata.source_label` 미설정 시 `"출처: YouTube"` 주입(하단 라벨 시스템 재사용)
8. 테스트: argparse 파싱 + 분기 선택

**Phase 4 — UI / API 배선**
9. celebrity 탭 토글 (`app/page.tsx`): 영상 소스 `이미지 / Freepik 영상 / 유튜브 클립` + crop 옵션
10. `app/api/generate/route.ts`: `celebrityVideoSource`/`celebrityClipCrop` → `--video-source`/`--clip-crop`
11. `app/api/celebrity-rerender/route.ts`: 동일 옵션

**Phase 5 — 샘플 검증 + lock-in**
12. 같은 인물로 crop/letterbox 샘플 2편 생성 → 비교 → 확정안 lock-in (메모리 기록)
13. 3줄 요약 + 해시태그 동반 제공 (고정 룰)

---

## ✅ 완료: 023 정치쇼츠 V2 — 주제 입력 모드 추가 (2026-05-26)

(상세는 prompt_plan.md.bak3 참조)

---

## 이전 계획

(이전 prompt_plan.md는 prompt_plan.md.bak3에 보관)
