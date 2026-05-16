# Implementation Plan: Dem-Shorts Studio (민주당 친화형 정치 쇼츠 반자동 제작 시스템)

**Branch**: `007-dem-shorts-studio` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-dem-shorts-studio/spec.md`

**Note**: This plan is authored retrospectively after implementation shipped through Phase 8 Polish (T001~T128 complete). All design details below reflect code already merged on this branch.

## Summary

NATV(국회방송) 공개 영상을 소스로 민주당·조국혁신당 정치인 중심의 친화형 쇼츠를 반자동 제작하는 독립 워크플로우(`mode=dem_shorts`). 기존 006 정치해설 모드를 건드리지 않고, 5단계 파이프라인(수집 → STT/화자분리 → 발언구간 하이라이트 → 해설·TTS → 컴플라이언스 게이트 → 렌더 → 업로드)을 신규 구축한다. 1인 운영자가 30분 이내 영상 1편을 업로드하고, 6개월 내 YouTube 파트너 프로그램 수익화 승인을 목표로 한다.

**기술 전략**: Python 백엔드 배치(수집·STT·diarization·랭킹·리포트) + Next.js 16 UI(드래프트 편집·게이트 검수·업로드) + Remotion 렌더(9:16, 1080×1920, 30fps). 변동 비용 $0 (원칙 I) — Whisper/pyannote 로컬, edge-tts 무료, Remotion 로컬 렌더, 무료 스톡 BGM.

## Technical Context

**Language/Version**:
- 백엔드 배치·파이프라인: Python 3.11+
- Next.js UI: TypeScript 5+ / React 19 / Next.js 16 (App Router)
- Remotion 렌더: TypeScript / React

**Primary Dependencies**:
- STT: `openai-whisper` (`large-v3` 모델, 로컬)
- 화자 분리: `pyannote.audio>=3.1` (HuggingFace 토큰, 무료)
- YouTube: `google-api-python-client` (Data API v3, 업로드 `youtube.upload` scope)
- 랭킹 집계: `pytrends` (Google Trends) + Naver 뉴스 HTML 크롤링 (`playwright`, 5초 간격·robots.txt 준수)
- OCR: `opencv-python` + `pytesseract` (이름자막 후처리, Sprint 2+)
- TTS: 기존 `edge-tts` 재활용
- 렌더: 기존 Remotion 파이프라인 재활용 (`src/video/remotion`)
- UI: shadcn/ui + Tailwind (기존 스택), SSE 스트리밍 (기존 `/api/generate` 패턴)

**Storage**:
- SQLite (`data/dem_shorts/state.db`) — 엔티티 8종 (SourceVideo/Politician/SpeechSegment/ShortsDraft/ComplianceGateResult/WeeklyRanking/UploadedShorts/BiasReport)
- JSON 파이프라인 파일 — 단계 간 교환 (원칙 II)
- 파일 시스템 — 원본 영상(`data/dem_shorts/archive/`), 전사본, 드래프트 MP4, 로그

**Testing**: `pytest` (백엔드), `vitest + @testing-library/react` (Next.js UI, T118 기준 기존 선행 feature에서 세팅됨)

**Target Platform**: macOS/Linux 로컬 1인 운영 (GPU 가용 시 렌더 가속; CPU fallback 8분 이내)

**Project Type**: Web application (Next.js UI + Python 배치 + Remotion 렌더) — 단일 리포 내 3개 런타임 혼재

**Performance Goals**:
- SC-001: 신규 영상 감지 → 업로드 완료 **30분 이내**
- SC-002: 신규 NATV 영상 자동 감지 **30분 이내**
- SC-003: Whitelist 발언 구간 식별 정확도 **80%+** (신뢰도 0.7 기준, Sprint 2 목표)
- SC-008: 월 30편 기준 렌더링 실패율 **5% 이하**
- NATV 6시간 본회의 STT: GPU 0.1x realtime, CPU 2x realtime 허용

**Constraints**:
- 변동 비용 **$0** (원칙 I) — 유료 API(Clova 등) 금지
- 컴플라이언스 게이트 **100% 우회 불가** (SC-005)
- 원본 비율 ≤50%, 해설 자막 ≥50자 (FR-025, SC-006)
- 영상 길이 60초 이내 (FR-018)
- 완전 자동 업로드 금지 — 운영자 최종 클릭 필수 (FR-037)
- 기존 006 정치해설 모드 코드 경로 **변경 금지** (FR-041)

**Scale/Scope**:
- 월 30편 쇼츠 업로드, 일 1편 + 3일치 예약 발행 버퍼
- Whitelist 고정 3명 + 여성·청년 Top20 자동 등록 + 대기/제외 관리
- NATV 원본 월 약 300GB 수집 → 3개월 주기 콜드 스토리지 이동 (T120 `archive-rotate` CLI)
- SQLite 단일 파일 — 단일 운영자 사용 가정

## Constitution Check

*GATE: Verified post-implementation. All principles pass.*

| 원칙 | 준수 방식 | 증거 |
|------|----------|------|
| I. Zero-Cost Pipeline | Whisper/pyannote 로컬, edge-tts, 무료 스톡 BGM, Naver/Trends 무료 크롤링. 유료 API 0건. | `requirements-dem-shorts.txt`에 유료 SDK 없음 |
| II. Pipeline Integrity | 5단계 독립 JSON 계약: `data/dem_shorts/{raw,transcripts,segments,drafts,outputs}/*.json` | `src/dem_shorts/models/*.to_dict()/from_dict()` |
| III. Text-First Video | Remotion 기존 9:16 + 해설 자막 타임라인 편집기. 원본 오디오 -12dB + TTS 0dB. | `src/dem_shorts/editor/` + `renderer.py` |
| IV. Content Safety & Legal | 10개 게이트 우회 불가 구현 + 선거법 D-180/D-120 자동 가드 + 명예훼손/혐오 리스크 스코어. | `src/dem_shorts/compliance/` (T048~T057) + `FR-025`~`FR-032` |
| V. Emotion-Driven | 자막 스타일 프리셋 5종(이재명/정청래/청년/핫이슈/일반) + TTS 보이스 프리셋 4종. | `editor/presets.py` |
| VI. Modularity & Immutability | 모든 모델 `@dataclass(frozen=True)` + 400줄 이하 파일 유지 + 모듈 독립 실행. | `src/dem_shorts/models/*.py` |
| VII. Evidence-Based Completion | 각 Phase별 pytest 실행 증거 첨부. 최종 **648 passed** 확인. | Phase 8 T128 기록 |
| VIII. Full Test Gate | +27 테스트 추가(9 metrics + 7 archive + 9 guardrail-learn + 2 e2e stub), 전체 pytest 통과. | 621 → 648 passed |

**위반**: 없음. Complexity Tracking 섹션 불필요.

## Project Structure

### Documentation (this feature)

```text
specs/007-dem-shorts-studio/
├── plan.md                  # 이 파일 (retrospective)
├── research.md              # Phase 0 — R-01~R-17 기술 결정
├── data-model.md            # Phase 1 — 엔티티 8종 + SQLite 스키마
├── quickstart.md            # Phase 1 — 로컬 부트스트랩 + 운영 시나리오
├── contracts/
│   ├── cli-commands.md      # Phase 1 — CLI (source-collect, stt-run, ranking-refresh, metrics-update, archive-rotate, guardrail-learn, test-e2e)
│   ├── batch-jobs.md        # Phase 1 — cron 배치 (B-01~B-08)
│   └── rest-api.md          # Phase 1 — Next.js API (/api/dem-shorts/*)
├── checklists/
│   └── requirements.md      # FR/SC 체크리스트
├── HANDOFF.md               # Phase 종료 핸드오프 노트
└── tasks.md                 # Phase 2 — T001~T128 (전체 완료)
```

### Source Code (repository root)

```text
src/dem_shorts/                      # Python 백엔드 (신규 모듈, 006과 독립)
├── models/                          # frozen dataclass 8종
│   ├── source_video.py
│   ├── politician.py
│   ├── speech_segment.py
│   ├── shorts_draft.py
│   ├── gate_result.py
│   ├── weekly_ranking.py
│   ├── uploaded_shorts.py
│   └── bias_report.py
├── db/                              # SQLite 스키마·마이그레이션
├── source_collector.py              # NATV 폴링 + 다운로드 (FR-001~FR-005)
├── stt.py                           # Whisper 로컬 STT (FR-012)
├── diarization.py                   # pyannote 화자 분리 (FR-013)
├── speaker_id/                      # 3단서 식별 (자막 호명/OCR/출석자)
├── scoring.py                       # 민주당 점유도 + 쇼츠 추천 점수 (FR-004, FR-016)
├── whitelist_repo.py                # Politician CRUD (FR-006~FR-011)
├── ranking/                         # 여성/청년 주간 랭킹 집계 (FR-008)
├── ranking_batch.py                 # 주간 배치 (B-02)
├── editor/                          # 자막·TTS·BGM 편집 + 프리셋 (FR-017~FR-024)
├── compliance/                      # 10개 게이트 + 리스크 스코어 + 선거법 (FR-025~FR-032)
│   └── guardrail_learner.py         # T122 패턴 재학습 (FR-028)
├── renderer.py                      # Remotion 렌더 래퍼 (FR-033~FR-035)
├── uploader.py                      # YouTube Data API v3 (FR-036~FR-037)
├── drafts_repo.py                   # ShortsDraft CRUD
├── bias_report.py                   # 월간 리포트 집계 (FR-038, SC-011)
├── metrics_updater.py               # T118 B-05 YouTube 조회수 갱신
├── archive_rotator.py               # T120 B-06 90일+ 콜드 이동
├── sc003_comparator.py              # SC-003 정확도 회귀 측정
├── e2e_smoke.py                     # T126 스모크 테스트 하네스
├── cli.py                           # source-collect/stt-run/upload-shorts/...
├── cli_polish.py                    # metrics-update/archive-rotate/guardrail-learn/test-e2e
├── config.py                        # 설정 중앙화 (원칙 VI)
├── youtube_client.py                # YouTube API 래퍼 (Data v3 + Upload)
└── utils/

app/dem-shorts/                      # Next.js 16 UI (App Router)
├── page.tsx                         # 대시보드 (우선순위 영상 목록)
├── [videoId]/                       # 편집기 + 컴플라이언스 검수
├── whitelist/                       # Whitelist CRUD UI
├── ranking/                         # 주간 랭킹 조회
├── reports/                         # 월간 편향 리포트
└── components/

app/api/dem-shorts/                  # REST 엔드포인트 (contracts/rest-api.md)
├── videos/
├── drafts/
├── whitelist/
├── rankings/
├── reports/
└── election/

src/video/remotion/                  # 기존 Remotion 패키지 재사용 (FR-042)

tests/dem_shorts/                    # pytest 테스트 (전체 +248)
docs/dem-shorts/                     # README / operations / cron 문서 (T127, T128)
data/dem_shorts/                     # 런타임 데이터
├── state.db
├── archive/                         # 원본 NATV MP4
├── transcripts/
├── segments/
├── drafts/
├── outputs/
├── bgm/
└── logs/batch/
```

**Structure Decision**: 기존 ContentsMaker의 Web application 구조를 유지하되, dem-shorts 기능은 `src/dem_shorts/`, `app/dem-shorts/`, `app/api/dem-shorts/` 세 네임스페이스에 격리하여 006 경로와 **완전히 분리** (FR-041). TTS·Remotion은 기존 구현을 import-only로 재사용하고 원본 호출부에 수정을 가하지 않는다 (FR-042).

## Complexity Tracking

> Constitution Check 전 항목 통과 — 예외·위반 없음.

해당 없음.
