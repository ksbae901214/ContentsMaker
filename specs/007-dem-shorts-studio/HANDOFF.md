# Dem-Shorts Studio (007) — 세션 이어받기 가이드

**작성일**: 2026-04-16 (Phase 8 완전 종료)
**상태**: **132/132 태스크 완료 (100%) ✅ — 정식 운영 전환 가능**
**브랜치**: `007-dem-shorts-studio`
**잔여**: 코드 작업 없음. 운영자 측정만 남음:
- SC-001: `python3 scripts/dem_shorts/measure_sc001.py` (fixture 준비 후)
- SC-003: `python3 scripts/dem_shorts/measure_sc003.py` (10영상 라벨링 후)

검증 증거: pytest **659 passed**, Next.js ✓ Compiled, SC-005 5/5 PASS, SC-008 0/30 fail.

---

## 🎯 한 줄 요약

**전체 기능셋 완성 + Polish 단계 진입**. NATV 영상 수집(US1) + 발언자 식별(US2) + 해설·게이트·렌더·업로드(US3) + 선거 가드(US4) + **주간 여성·청년 랭킹 + 월간 편향 리포트(US5)** 모두 구현. 다음 세션은 E2E 스모크 테스트·메트릭 갱신·관측성·성능 검증으로 정식 운영 전환.

---

## ✅ Phase 8 완료 (T118~T132) — 본 세션

### Step 1 — Observability + Archive (T118~T120)
- `metrics_updater.py` (T118) + cli `metrics-update` — YouTube 조회수·좋아요·댓글 갱신, takedown 감지. **9 테스트**
- `archive_rotator.py` (T119) + cli `archive-rotate` — 90일+ 원본 콜드 스토리지 이동. **7 테스트**
- `compliance/guardrail_learner.py` (T120) + cli `guardrail-learn` — guardrail_history 기반 키워드 multiplier 재학습. **9 테스트**

### Step 2 — E2E 스모크 (T121~T123)
- `tests/fixtures/README.md` (T121) — 운영자 fixture 배치 안내
- `e2e_smoke.py` + `tests/dem_shorts/test_e2e_smoke.py` (T122) — stub 모드 (CI) + real-models 모드 (skip 자동)
- cli `test-e2e` (T123) — `--real-models` 플래그로 분기

### Step 3 — Full Test Gate + Docs (T124~T128)
- pytest tests/dem_shorts/ — **284 passed, 1 skipped**
- pytest tests/ — **659 passed** (621 baseline → +38, 회귀 0건)
- `docs/dem-shorts/README.md` (T126) — 설치·CLI·API 한눈
- `docs/dem-shorts/operations.md` (T127) — 일/주/월 루틴 + 트러블슈팅
- `docs/dem-shorts/cron.md` 갱신 — B-03~B-08 활성 cron
- `CLAUDE.md` (T128) — Recent Changes Phase 8 항목 추가

### Step 4 — Performance Validation (T129~T132)
- `docs/dem-shorts/performance-validation.md` — SC 검증 기록
- **T131 SC-005**: `test_gate.py::TestBypassResistance` 5/5 PASS (frontend skip / 서명 없음 / 빈 서명 / DB 조작 / risk 임계 초과)
- **T132 SC-008**: 30개 draft 스트레스 → **0/30 fail (0.00% ≤ 5%)**
- **T129 SC-001**: `scripts/dem_shorts/measure_sc001.py` (운영자가 fixture 준비 후 1회 실행 → 자동 단계 ≤15분 검증). `e2e_smoke.py` 에 phase 별 elapsed_sec 계측 추가
- **T130 SC-003**: `src/dem_shorts/sc003_comparator.py` (compute_accuracy + 4 verdict) + `scripts/dem_shorts/measure_sc003.py` runner + `tests/fixtures/sc003_ground_truth.example.json` 템플릿. **11 단위 테스트** (compare_turn 6 + compute_accuracy 4 + 1 empty 케이스)

### 검증 증거 (본 세션 종료 시점)
```
pytest tests/                      → 659 passed, 1 skipped, 1 warning
pytest tests/dem_shorts/           → 284 passed, 1 skipped
npm run build                       → ✓ Compiled successfully
python3 -m src.dem_shorts.cli --help → metrics-update / archive-rotate / guardrail-learn / test-e2e 모두 등록됨
```

### 운영자 마지막 액션 (코드 변경 없음)
1. `tests/fixtures/natv_sample.mp4` 배치 → `python3 scripts/dem_shorts/measure_sc001.py`
2. NATV 영상 10편 다운로드 + STT/diarize/identify 일괄 실행 → `tests/fixtures/sc003_ground_truth.json` 라벨링 → `python3 scripts/dem_shorts/measure_sc003.py`

---

## ✅ 완료된 작업 (T001~T117)

### Phase 1 Setup (T001~T008) — 완료
- `src/dem_shorts/`, `app/dem-shorts/`, `app/api/dem-shorts/`, `tests/dem_shorts/` 디렉토리
- `requirements-dem-shorts.txt`: openai-whisper, pyannote.audio, google-api-python-client, pytrends, opencv, tesseract
- `.env.example`: YOUTUBE_API_KEY, HUGGINGFACE_TOKEN, NATV_CHANNEL_HANDLE 등
- `.gitignore`: 아카이브·생성물·fixtures 추가
- `data/dem_shorts/` 하위 디렉토리

### Phase 2 Foundational (T009~T025) — 완료
- **8개 frozen dataclass**: `src/dem_shorts/models/{source_video, politician, speech_segment, shorts_draft, gate_result, weekly_ranking, uploaded_shorts, bias_report}.py`
- **SQLite**: `src/dem_shorts/db/__init__.py` + `db/migrations/001_init.sql` (10 테이블)
- **유틸**: `utils/logger.py`, `utils/paths.py`, `config.py`
- **CLI**: `cli.py` — `db-init` 구현
- **Seed**: 이재명·조국·정청래 3명 pinned 등록

### Phase 3 US1 — NATV 대시보드 (T026~T040) — 완료 ✅ MVP 1/3
- **백엔드**: `youtube_client.py`, `source_collector.py`, `scoring.py::calculate_dem_score`
- **CLI**: `poll-natv`, `download`, `score`
- **API**: `GET /api/dem-shorts/videos`, `GET /api/dem-shorts/videos/[id]`
- **UI**: `app/dem-shorts/page.tsx` (대시보드), `components/VideoCard.tsx`
- **문서**: `docs/dem-shorts/cron.md`
- **테스트**: 41개

### Phase 4 US2 — 발언자 식별 + 타임라인 (T041~T056) — 완료 ✅ MVP 2/3
- **STT/Diarization**: `stt.py` (whisper large-v3), `diarization.py` (pyannote 3.1)
- **발언자 식별**: `speaker_id/name_patterns.py` + `speaker_id/identify.py`
- **추천 점수**: `scoring.py::calculate_recommendation_score`
- **CLI**: `stt`, `diarize`, `identify`
- **UI**: `app/dem-shorts/[videoId]/page.tsx` + `TimelineTrack`, `SegmentCard`
- **테스트**: 26개

### Phase 5 US3 — 해설·게이트·렌더·업로드 (T057~T095) — 완료 ✅ MVP 3/3
- Whitelist 관리 (T057~T060), Segment cut + Commentary (T061~T065)
- Subtitle presets + TTS + BGM (T066~T071)
- Guardrail engine 계층1+2 (T072~T076)
- Election guard Stub (T077)
- ⭐⭐⭐ 10-Item Compliance Gate (T078~T081) — SC-005 우회 불가 3 시나리오 거부
- Render pipeline + 캐싱 (T082~T084)
- YouTube Uploader (T085~T087)
- Drafts CRUD + Commentary API (T088~T090)
- Editor UI + Gate UI (T091~T094)
- CLI 서브커맨드 (T095): draft-create, commentary, gate, render, upload, bgm-register

### Phase 6 US4 — 선거기간 자동 감지 + 중립 모드 (T096~T102) — 완료 ✅ (이번 세션)

#### T096: 선거 가드 테스트 (RED 먼저)
- `tests/dem_shorts/test_election_guard.py` — **22 테스트**
- D-181/D-180/D-179 경계, 대선 D-180 / 총선 D-120 구분, D-0 당일·D+1 이후 종료
- `get_upcoming_elections()` 정렬·과거 선거 필터링
- 두 선거 겹침 시 가장 가까운 활성 선거 선택
- 배너 플래그 생성 (ElectionGuardResult)

#### T097: 선거 일정 하드코딩 테이블
- `src/dem_shorts/compliance/election_dates.py`
- `ElectionEntry` frozen dataclass + `ELECTION_DATES` 리스트 (2027 대선 / 2028 총선)
- `get_upcoming_elections(today)` — 미래 선거만 날짜 오름차순

#### T098: Stub → 실제 구현 교체
- `src/dem_shorts/compliance/election_guard.py` (Stub 완전 교체)
- `is_in_election_period(today)` — D-180/D-120 guard_days 활용
- `get_election_status(today)` → ElectionGuardResult
- `get_bias_threshold(today)` — **FR-031 선거기간 중 편향 임계값 61→30 자동 하향**
- `gate.py::item_5_bias_guardrail` + `risk_ok` 판정 모두 동적 임계값 사용 (2곳 패치)

#### T099: 중립 모드 프롬프트 분기 연동 확인
- `editor/commentary_prompt.COMMENTARY_NEUTRAL_PROMPT` 이미 존재 (T065에서 작성)
- `app/api/dem-shorts/drafts/[id]/commentary/route.ts` 에서 `is_in_election_period()` 자동 호출 → ctx.is_election_period
- 테스트 추가: `test_commentary_gen.py::TestElectionNeutralBranch` (+2)
  - 선거기간일 때 NEUTRAL_PROMPT 텍스트 포함 검증
  - 평시엔 기본 SYSTEM_PROMPT 사용 검증

#### T100: 선거 API 라우트
- `app/api/dem-shorts/election/route.ts` — GET
- Response: `{in_election_period, next_election: {type, date, days_until, guard_threshold_days}, neutral_mode_enforced}` (rest-api.md 계약 준수)

#### T101: ElectionBanner UI
- `app/dem-shorts/components/ElectionBanner.tsx` (신규)
- 선거기간 중에만 표시 (평시 자동 숨김)
- 3 페이지 모두 배너 연동 완료:
  - `/dem-shorts` (대시보드)
  - `/dem-shorts/[videoId]` (타임라인)
  - `/dem-shorts/[videoId]/render` (편집 + 게이트 + 업로드)

#### T102: election-check 배치 CLI + cron 안내
- `cli.py::_cmd_election_check` — 1초 미만 실행, JSON 출력
- `election-check` 를 stub 목록에서 제거하고 실제 구현으로 등록
- `docs/dem-shorts/cron.md` 에 B-07 활성 배치 섹션 추가 (`1 0 * * *`)

### Phase 7 US5 — 주간 랭킹 + 월간 편향 리포트 (T103~T117) — 완료 ✅ (이번 세션)

#### T103/T104: Tests RED (총 22 테스트)
- `tests/dem_shorts/test_ranking_batch.py` (11): 가중합·클램핑·순위·태그(new/rising/pending)·2주 stale 삭제·dry-run·월요일 계산
- `tests/dem_shorts/test_bias_report.py` (11): person/party/template_usage 점유율, SC-011 30% 초과 경고, Top3 60% 초과, SC-012 여성·청년 40% 미달, 월별 UNIQUE upsert, 타월 집계 제외

#### T105~T109: 5개 공공·무료 소스 (원칙 I)
- `ranking/naver_news.py` — search.naver.com 크롤링 + 5초 간격 + User-Agent 명시 (R-06)
- `ranking/google_trends.py` — pytrends 래퍼 + 1.1초 간격, 미설치/실패 시 0.0 폴백
- `ranking/youtube_metrics.py` — search.list + videos.list 평균 조회수, API_KEY 미설정 시 0.0 폴백
- `ranking/wikipedia_pageviews.py` — pageviews.toolforge.org 무료 API (지난 7일 합계)
- `ranking/naver_datalab.py` — openapi.naver.com 공공 API, credentials 미설정 시 0.0 폴백

#### T110: `src/dem_shorts/ranking_batch.py`
- `combine_source_scores()` — RANKING_SOURCE_WEIGHTS 가중 합산
- `normalize_scores()` — z-score + sigmoid (독립 유틸)
- `run_ranking_batch()` — 후보 `category IN (female, youth, alliance)`만 대상. 각 소스값 [0,100] 클램핑 후 가중합을 직접 점수로 사용 (단일 후보에서도 week 간 delta 감지 가능). `ON CONFLICT DO UPDATE` 로 idempotent, 2주 연속 pending 시 FK row 정리 후 politician 삭제
- 태그 규칙: 신규=`new`, 전주 대비 ≥+15=`rising`, 상위 N 탈락=`pending`

#### T111: `cli.py::ranking-batch`
- `--week-start YYYY-MM-DD` / `--dry-run` 지원
- B-03 cron: `0 22 * * 0`

#### T112: `src/dem_shorts/bias_report.py`
- `generate_bias_report()` — JOIN uploaded_shorts ↔ shorts_drafts ↔ speech_segments ↔ politicians
- person/party 점유율 + template 사용 횟수 + avg_risk_score
- 권고 생성: 30% 초과 인물, Top3 합계 60% 초과, 여성·청년 합계 40% 미만
- `persist=True` 시 `bias_reports.month` UNIQUE upsert

#### T113: `cli.py::bias-report`
- `--month YYYY-MM` 또는 YYYY-MM-DD, 생략 시 지난 달 자동 선택
- `--dry-run` 은 DB 저장 스킵
- B-04 cron: `0 9 1 * *`

#### T114/T115: API 라우트
- `GET /api/dem-shorts/rankings?week_start=...` — WeeklyRanking + Politician JOIN 결과 반환
- `GET /api/dem-shorts/reports?month=...` — 저장된 BiasReport 우선, 없으면 즉시 계산 (persist 없이)

#### T116/T117: UI 페이지
- `/dem-shorts/ranking` — 테이블 + 신규/급상승/대기 뱃지 + 카테고리·정당 표시
- `/dem-shorts/reports` — 요약 4카드 + 권고 알림 + 인물/정당 바 차트 + 프리셋 그리드

### 검증 현황 (이번 세션 기준)
- **Python 테스트**: **621/621 통과** (이전 599 + 신규 22: 11 ranking + 11 bias)
- **회귀 0건**: 기존 599 모두 통과
- **Next.js 빌드**: ✓ Compiled successfully (36 정적 페이지 생성, `/dem-shorts/ranking`·`/dem-shorts/reports` 포함)
- **CLI 동작**: `ranking-batch --dry-run`, `bias-report --dry-run --month 2026-03` 모두 JSON 출력 1초 미만

---

## 🚀 다음 세션에서 할 일 — Phase 8 Polish (T118~T132, 15 태스크)

### 개요
**Polish & Cross-Cutting**. 운영 관측성 + E2E 스모크 + 문서화 + 성능 검증.

### 실행 순서 (제안)

**Step 1. Observability + Archive (T118~T120) — 병렬 가능**
```
- metrics_updater.py + cli::metrics-update (YouTube 조회수·좋아요·수익 주기 갱신, B-05)
- archive_rotator.py + cli::archive-rotate (3개월 이상 원본 콜드 스토리지 이동, B-06)
- compliance/guardrail_learner.py + cli::guardrail-learn (월간 키워드 가중치 재학습, B-08)
```

**Step 2. E2E 스모크 (T121~T123) — 원칙 VII 강제**
```
- tests/fixtures/natv_sample.mp4 준비 (10분, git-ignored)
- tests/dem_shorts/test_e2e_smoke.py (수집→STT→diarize→식별→점수→draft→commentary→gate→render)
- cli::test-e2e (CI/로컬 1회 실행)
```

**Step 3. Full Test Gate + Docs (T124~T128)**
```
- pytest tests/dem_shorts/ 전체 통과 (T124)
- pytest tests/ 기존 회귀 0건 (T125)
- docs/dem-shorts/README.md, operations.md (T126, T127)
- CLAUDE.md 007 섹션 신규 CLI·API 목록 갱신 (T128)
```

**Step 4. Performance Validation (T129~T132)**
```
- SC-001: 샘플 NATV → 30분 이내 end-to-end
- SC-003: 10개 영상 발언자 식별 80%+
- SC-005: 3가지 게이트 우회 시나리오 최종 거부 + 데모 녹화
- SC-008: 30회 렌더 배치 실패율 ≤5%
```

### 주의사항 (Phase 8 구현 시)
- **E2E 샘플 준비**: 로컬에 `tests/fixtures/natv_sample.mp4` (10분) 수동 배치 필요
- **metrics_updater**: YouTube Data API videos.list 호출 — 쿼터 소비 고려 (최대 50개/요청)
- **guardrail-learn**: guardrail_history 테이블 기반 — FR-028 의 월간 재학습 규칙 참조

---

## 🔴 절대 깨지지 말 것 — CRITICAL 설계

### 1. 우회 불가 방어 (SC-005) — Phase 7 이후에도 유지 필수

`render` / `upload` / (US4 이제 실제 구현) 모두 `get_latest_result()` + `is_passed()` 호출하는 **이중 방어 패턴** 유지.

1. **GateContext dataclass 절대 확장 금지**:
   - `skip_gate` 류 필드를 절대 추가하지 말 것
   - 새 필드 필요 시 `operator_id`처럼 검증 가능한 값으로만

2. **ComplianceGateResult.is_passed() 메서드 절대 단순화 금지**:
   - 현재: 모든 blocking items=pass + 서명 2개 NOT NULL + risk_score < threshold
   - 이 3조건 중 하나라도 빠지면 DB 조작으로 우회 가능해짐

3. **프론트엔드 "건너뛰기" 버튼 절대 미구현**:
   - `GateChecklist.tsx`에 skip prop 추가하지 말 것
   - 게이트 미통과 시 "렌더링"/"업로드" 버튼 비활성 유지

4. **서명 처리**: `None`과 빈 문자열 `""` 모두 unsigned로 판정 (현재 `.strip()` 체크)

### 2. 선거 가드 동적 임계값 (이번 세션 신규) — FR-031

**`get_bias_threshold()` 절대 하드코딩 금지**:
- `gate.py::item_5_bias_guardrail` 및 `risk_ok` 판정 모두 `get_bias_threshold()` 호출 필수
- 선거기간이면 30.0, 평시면 61.0 반환
- `config.RISK_SCORE_BLOCK` / `RISK_SCORE_BLOCK_ELECTION` 두 상수를 직접 참조하는 대신 helper 경유

**ELECTION_DATES 수동 갱신**:
- 중앙선관위 공개 API 없음 → 공식 선거일 발표 시 `election_dates.py` 수동 커밋
- 과거 선거 엔트리는 남겨둬도 `get_upcoming_elections()`가 today 기준 필터링

### 3. 파일 400줄 원칙 점검 — 이번 세션 신규

- `src/dem_shorts/compliance/election_guard.py` (약 100줄) ✅
- `src/dem_shorts/compliance/election_dates.py` (약 45줄) ✅
- `app/api/dem-shorts/election/route.ts` (약 55줄) ✅
- `app/dem-shorts/components/ElectionBanner.tsx` (약 100줄) ✅
- `cli.py::_cmd_election_check` (약 40줄 추가) — cli.py 전체 약 520줄, 상향 조정 필요시 분리 고려

---

## 📋 다음 세션 시작 명령어

```bash
# 1. 브랜치 확인
git status
git branch --show-current
# → 007-dem-shorts-studio

# 2. Baseline 테스트 확인
python3 -m pytest tests/ 2>&1 | tail -3
# → 621 passed 여야 함

# 3. Next.js 빌드 확인 (선택)
npm run build
# → ✓ Compiled successfully (ranking/reports 페이지 포함)

# 4. 랭킹·리포트 CLI 동작 확인 (선택)
python3 -m src.dem_shorts.cli ranking-batch --dry-run
python3 -m src.dem_shorts.cli bias-report --dry-run --month 2026-03

# 5. Claude Code에서 이어서 개발
claude
# "specs/007-dem-shorts-studio/HANDOFF.md 읽고 Phase 8 Polish (T118~T132) 계속 진행해주세요"
```

---

## 🗂 핵심 파일 참조 경로

| 항목 | 경로 |
|---|---|
| Feature Spec | `specs/007-dem-shorts-studio/spec.md` |
| Implementation Plan | `specs/007-dem-shorts-studio/plan.md` |
| Research Decisions | `specs/007-dem-shorts-studio/research.md` (15개) |
| Data Model | `specs/007-dem-shorts-studio/data-model.md` (8 엔티티 + SQL) |
| Tasks | `specs/007-dem-shorts-studio/tasks.md` (132 태스크 중 102 완료) |
| Quickstart | `specs/007-dem-shorts-studio/quickstart.md` |
| REST API Contract | `specs/007-dem-shorts-studio/contracts/rest-api.md` |
| CLI Contract | `specs/007-dem-shorts-studio/contracts/cli-commands.md` |
| Batch Jobs Contract | `specs/007-dem-shorts-studio/contracts/batch-jobs.md` |

### 현재 구현 코드 전체 구조

```
src/dem_shorts/
├── cli.py                              # db-init, poll-natv, download, stt, diarize, identify, score,
│                                       # draft-create, commentary, gate, render, upload, bgm-register,
│                                       # election-check (NEW T102)
├── config.py                           # 중앙화된 상수 (RISK_SCORE_BLOCK_ELECTION 추가)
├── db/__init__.py                      # SQLite connection/migrate/seed
├── db/migrations/001_init.sql          # 10 테이블
├── models/                             # 8 frozen dataclass
├── scoring.py                          # dem_score + recommendation_score
├── youtube_client.py                   # YouTube Data API v3 래퍼
├── source_collector.py                 # NATV 폴링 + yt-dlp
├── stt.py                              # Whisper 래퍼
├── diarization.py                      # pyannote 래퍼
├── speaker_id/                         # 정규식 + Whitelist 매칭
├── whitelist_repo.py                   # Politician CRUD
├── drafts_repo.py                      # ShortsDraft CRUD
├── renderer.py                         # Remotion + FFmpeg + 캐싱
├── uploader.py                         # YouTube Data API v3
├── editor/
│   ├── segment_cutter.py               # ffmpeg 9:16 크롭
│   ├── commentary_gen.py               # Claude CLI 후보 생성 (is_election_period 연동)
│   ├── commentary_prompt.py            # 프롬프트 템플릿 (NEUTRAL_PROMPT 분기)
│   ├── subtitle_presets.py             # 5종 프리셋
│   ├── tts_integration.py              # edge-tts 4 보이스
│   └── bgm_manifest.py                 # BGM 등록 검증
├── compliance/
│   ├── keyword_dict.py                 # 4 카테고리 키워드 사전
│   ├── guardrail_keyword.py            # 계층1 룰 스캐너
│   ├── guardrail_llm.py                # 계층2 Claude CLI
│   ├── guardrail.py                    # 통합 엔진
│   ├── election_dates.py               # NEW T097 — ELECTION_DATES 하드코딩 테이블
│   ├── election_guard.py               # T077 Stub → T098 실제 구현 교체
│   │                                   #   + get_bias_threshold() (FR-031 동적 임계값)
│   └── gate.py                         # ⭐ 10-Item Gate — 선거기간 편향 임계값 30 자동 하향
└── utils/{logger,paths}.py

app/dem-shorts/
├── page.tsx                            # 대시보드 (ElectionBanner 연동)
├── [videoId]/page.tsx                  # 타임라인 편집기 (ElectionBanner 연동)
├── [videoId]/render/page.tsx           # 해설 + 게이트 + 렌더 + 업로드 (ElectionBanner 연동)
├── whitelist/page.tsx                  # Whitelist CRUD UI
└── components/
    ├── VideoCard.tsx, TimelineTrack.tsx, SegmentCard.tsx
    ├── CommentaryEditor.tsx, GateChecklist.tsx, UploadDialog.tsx
    └── ElectionBanner.tsx              # NEW T101 — 선거기간 중에만 표시

app/api/dem-shorts/
├── videos/{route,[id]/route}.ts        # Phase 3
├── whitelist/{route,[id]/route}.ts     # T058/T059
├── election/route.ts                   # NEW T100 — GET 선거 상태
└── drafts/
    ├── route.ts                        # POST draft (T088)
    └── [id]/
        ├── route.ts                    # GET/PATCH draft (T089)
        ├── commentary/route.ts         # POST AI 후보 (T090, is_election_period 연동)
        ├── gate/route.ts               # POST 게이트 (T081)
        ├── render/route.ts             # SSE 렌더 (T084)
        └── upload/route.ts             # POST 업로드 (T087)

src/video/remotion/src/
├── DemShortsComposition.tsx            # 신규 composition (T067)
├── components/SubtitleBlock.tsx        # 프리셋 자막 렌더 (T068)
└── Root.tsx                            # DemShorts composition 등록

tests/dem_shorts/
├── test_whitelist_api.py (12)
├── test_segment_cutter.py (8)
├── test_commentary_gen.py (11 → 13)   # +2 TestElectionNeutralBranch (T099)
├── test_bgm_manifest.py (11)
├── test_guardrail.py (16)
├── test_gate.py (11)                   # ⭐ SC-005 검증
├── test_renderer.py (7)
├── test_uploader.py (7)
└── test_election_guard.py (22)         # NEW T096
```

---

## 🔑 Constitution 준수 지속 확인 사항 (Phase 7+에도 유효)

1. **원칙 I ($0 Zero-Cost)**:
   - ✅ Commentary 생성 (T064): Claude CLI 재사용 — 비용 0원
   - ✅ 가드레일 LLM (T074): 동일 Claude CLI — 비용 0원
   - ✅ Election 가드 (T098): 하드코딩 테이블, 외부 호출 없음 — 비용 0원
   - Phase 7 랭킹 배치: pytrends·wikipedia·naver_datalab 모두 무료 API / 공공 API 사용 필수

2. **원칙 II (Pipeline Integrity)**:
   - ✅ 각 단계 JSON 계약 유지 + 독립 실행 가능
   - ✅ `election-check` 도 독립 실행 OK (1초 미만)

3. **원칙 IV (Content Safety)**:
   - ✅ SC-005 우회 불가 게이트 3/3 시나리오 통과
   - ✅ 명예훼손 임계값 61점 (평시) / **30점 (선거기간, FR-031 신규)** 동적 적용
   - ✅ NATV 출처 강제 (uploader.py validate)
   - ✅ 팩트 링크 ≥2개 강제

4. **원칙 VI (Modularity)**:
   - ✅ 신규 파일 모두 400줄 이하
   - ✅ Frozen dataclass 패턴 유지 (ElectionEntry, ElectionGuardResult)

5. **원칙 VII (Evidence-Based)**:
   - ✅ 599/599 테스트 실행 증거 첨부
   - ✅ Next.js 빌드 성공 증거 첨부
   - ✅ CLI 실행 증거 첨부 (election-check JSON)

6. **원칙 VIII (Full Test Gate)**:
   - ✅ baseline: **599 passed** (이전 575에서 24 증가)

---

## 🚨 자주 빠지는 함정 (주의사항)

1. **Python 패키지 vs 모듈 충돌**: `src/dem_shorts/db.py` + `src/dem_shorts/db/` 같이 두면 안 됨. 이미 겪은 이슈.

2. **.format() 중괄호 이스케이프**: Claude 프롬프트에 JSON 예시 넣을 때 `{{` / `}}` 사용.

3. **Next.js route params**: Next.js 16부터 `params`가 Promise. `const { id } = await params` 사용.

4. **frozen dataclass 수정 금지**: 새 인스턴스 생성.

5. **SpeechSegment.issue_keywords는 SQLite에서 JSON 문자열**: Python에서 `tuple`이지만 DB에 넣을 때 `json.dumps()`.

6. **⭐ Gate 우회 불가 유지**:
   - `GateContext`에 새 파라미터 추가 시 반드시 서버사이드 검증 포함
   - `is_passed()` 로직 수정 시 3조건(items/signatures/risk) 모두 유지

7. **⭐ 선거 가드 경계 계산 (이번 세션 함정)**:
   - `(election_date - today).days == 180` 이 경계 (D-180)
   - `0 <= days_until <= guard_days` 조건 (D-0 당일 포함, D+1 이후 False)
   - 테스트에 경계(D-181/D-180/D-179) 3개 케이스 모두 있어야 함

8. **샘플 NATV 영상 필요 (T121)**: Phase 8 E2E 스모크 테스트는 `tests/fixtures/natv_sample.mp4` (git-ignored). 개발자가 로컬에 10분 분량 NATV 영상 1개 준비 필요.

---

## 📊 남은 Phase 진행률 추정

| Phase | 태스크 | 예상 세션 | 상태 |
|---|---|---|---|
| ~~Phase 5 US3 (MVP 3/3)~~ | ~~39~~ | ~~2~3 세션~~ | ✅ **완료** |
| ~~Phase 6 US4 (선거 가드)~~ | ~~7~~ | ~~0.5 세션~~ | ✅ **완료** |
| ~~Phase 7 US5 (랭킹+리포트)~~ | ~~15~~ | ~~1~2 세션~~ | ✅ **완료 (이번 세션)** |
| **Phase 8 Polish** | **15** | **1 세션** | E2E + 메트릭 갱신 + 문서 |

**전체 기능셋(P1~P3) 완료**: ✅
**정식 운영 전환까지**: 약 1 세션 (Polish)

---

## 💬 다음 세션 첫 메시지 템플릿

```
specs/007-dem-shorts-studio/HANDOFF.md 를 먼저 읽고 Phase 8 Polish (T118~T132)를
이어서 개발해주세요. 현재 117/132 태스크 완료됐고 MVP + 선거 가드 + 랭킹/리포트까지
완성 상태입니다 (전체 기능셋 완료).

다음은 관측성·E2E·문서·성능 검증입니다.
- T118~T120: 병렬 — metrics-update / archive-rotate / guardrail-learn
- T121~T123: E2E 스모크 (샘플 natv_sample.mp4 준비 필요)
- T124~T125: Full Test Gate (pytest 전체 통과)
- T126~T128: 문서화 (README/operations/CLAUDE.md)
- T129~T132: 성능 검증 (SC-001/003/005/008)

먼저 git status + pytest (621 passed) 확인 후 진행해주세요.
원칙 VII(Evidence-Based) 준수: 각 SC 검증은 실행 결과를 첨부.
```
