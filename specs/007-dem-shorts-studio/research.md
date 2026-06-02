# Phase 0 Research: Dem-Shorts Studio

**Date**: 2026-04-16
**Feature**: 007-dem-shorts-studio
**Purpose**: Resolve all technical unknowns before Phase 1 design.

---

## R-01. NATV YouTube 채널 폴링 방식

**Decision**: YouTube Data API v3 `channels.list` + `search.list` (channelId filter, order=date, publishedAfter=last_poll). 폴링 주기 30분, 일일 쿼터 10,000 unit 내 충분 (1회 폴링 ~100 unit × 48회 = 4,800 unit).

**Rationale**:
- NATV 채널 ID는 공개 (`@NATV_korea` 또는 `@natvkorea`) — `channels.list?forHandle=NATV_korea`로 확인
- 공식 API는 안정성 + 메타데이터 완결성(title·description·duration·thumbnail) 보장
- RSS(`/feeds/videos.xml?channel_id=XXX`)는 최근 15개만 반환 + description 단축 → 부적합

**Alternatives considered**:
- RSS 피드 + yt-dlp 메타데이터 조회: API 키 불필요하지만 최근 15개 제한 + 일부 메타데이터 누락
- Invidious 미러 API: 비공식, 안정성 부족

---

## R-02. 한국어 STT 엔진

**Decision**: **openai-whisper** (로컬, `large-v3` 모델). GPU 가용 시 ~0.1x realtime, CPU만 시 ~2x realtime. 변동 비용 $0 (원칙 I).

**Rationale**:
- NATV 영상은 대부분 1~6시간 본회의/상임위 → 로컬 처리 가능한 시간
- `large-v3`는 한국어 WER 5~7% 수준 (국회 발언의 표준 발음·전문용어에 강건)
- 기존 ContentsMaker에 이미 Whisper 통합 전례 가능 (requirements.txt 확장만 필요)

**Alternatives considered**:
- Clova Speech API: 유료 ($0.004/분) — 원칙 I 위반
- faster-whisper: `large-v3` 동일 품질 + 2~4배 빠름 → **Phase 2 전환 고려**. Phase 1은 안정성 우선하여 openai-whisper

---

## R-03. 화자 분리 (Diarization)

**Decision**: **pyannote.audio 3.1** (`pyannote/speaker-diarization-3.1` 모델, HuggingFace 토큰 필요 무료). 영상당 평균 5분 (CPU).

**Rationale**:
- 국회 영상은 의장·의원 다수 교대 발언 구조 → diarization 필수
- pyannote 3.1은 한국어 음성에도 검증됨 (다국어 훈련), DER 15% 수준
- MIT 라이선스, API 비용 없음 (HuggingFace 계정만 필요)

**Alternatives considered**:
- NeMo: 복잡한 설치, CUDA 의존성 강함
- WhisperX: Whisper + pyannote 통합 → 추후 Phase 2 최적화 시 전환 옵션

---

## R-04. 발언자 식별 (Speaker Identification) — 3단서 결합 전략

**Decision**: 하이브리드 룰 + LLM 검증. MVP는 자막 호명 패턴만 (정확도 60~70% 목표).

**Rationale**:
1. **자막 호명 패턴** (MVP): STT 텍스트에서 `(?:[가-힣]{2,4})\s*(?:의원|대표|장관|위원장)` 정규식 매칭 → 가장 높은 정밀도
2. **영상 OCR** (Sprint 2+): Tesseract로 화면 하단 이름자막 추출 (약 30fps × 6시간 → 5분 샘플링), OpenCV로 ROI 고정 크롭
3. **출석자 명단 대조** (Sprint 2+): 국회 홈페이지 위원회 명단 크롤링 (주 1회 갱신), diarization 클러스터별 호명 빈도 매칭

MVP 60~70% → Sprint 2 종료 시 80% 목표 (SC-003). Confidence 0.7 미만은 "(미식별)" 처리 (FR-014).

**Alternatives considered**:
- 얼굴 인식 (face-recognition 라이브러리): 프라이버시 이슈 + 정치인 기본 사진 DB 수집·관리 부담 → Phase 3 이후 고도화

---

## R-05. 민주당 점유도 점수 계산 (FR-004)

**Decision**: SpeechSegment 단위로 정치인 매칭 후 Politician 테이블의 `party` 필드 집계.

**점수 공식** (기획서 반영, 0~100 clamp):
```
score =
  min(민주당 인물 감지 수 × 10, 40)
+ (Whitelist 상위 인물 포함 시 20, else 0)
+ min(이재명·조국·정청래 등장 시 각 15, 총 30)
+ (여성·청년 Top20 포함 시 10)
+ min(이슈 키워드 매칭 수 × 5, 20)
- (영상 길이 6시간 초과 시 10)
- 동일 인물 최근 3회 반복 감점 (직전 업로드 history 확인, 최대 30)
```

**Rationale**: 각 항목 가중치는 기획서 4.2 FD-SRC-02 공식 그대로. 6시간 초과는 애초에 FR-002에서 제외되지만 보조 감점으로 유지.

**Alternatives considered**:
- LLM 기반 스코어링: 비용 발생 + 해석 불가능. 룰 기반이 디버깅 쉬움.

---

## R-06. 여성·청년 정치인 주간 랭킹 데이터 소스 (FR-008)

**Decision**: **공공 무료 소스만 사용 (원칙 I)**.

| 소스 | 획득 방법 | 가중치 |
|---|---|---|
| 네이버 뉴스 검색 | 공개 웹 `search.naver.com/news.naver` 크롤링 (robots.txt 준수, 5초 간격) | 30% |
| Google Trends | `pytrends` 라이브러리 (비공식, 무료) | 25% |
| YouTube Data API | search.list?q={이름} 조회수·업로드 집계 | 25% |
| 위키백과 페이지뷰 | `pageviews.toolforge.org` 무료 API | 10% |
| 공공 트렌드 보강 | 네이버 데이터랩 공공 API | 10% |

X/Twitter 언급은 API 유료화(2024~) → 제외 (기획서 10% 가중치를 Wikipedia+데이터랩으로 재분배).

**Rationale**: 기획서의 "트위터 10%"는 API 비용 발생 → 원칙 I 위반. 대체로 위키백과·데이터랩 사용. 주 1회 일요일 22:00 배치(cron).

**Alternatives considered**:
- 네이버 검색 공식 API: 일 2,500건 제한, 뉴스 본문 제외 → 크롤링 보조 필요

---

## R-07. 자막 스타일 프리셋 5종 (FR-021)

**Decision**: Remotion 컴포넌트 레벨 프리셋. `SubtitlePreset` 타입으로 정의, 기존 `SceneText.tsx` 재사용 + `preset` prop 추가.

**5종 정의**:
| 프리셋 키 | 색상·스타일 | 기본 사용처 |
|---|---|---|
| `leejaemyung` | 파란 테두리 / 굵은 흰색 | 이재명 영상 |
| `jungcheongrae` | 빨간 악센트 / 검정 박스 | 정청래 영상 |
| `youth` | 노란 팝 / 캐주얼 | 청년 정치인 시리즈 |
| `hotissue` | 빨간 배경 / 흰 글씨 | 속보·논란 |
| `default` | 검정 반투명 박스 / 흰 글씨 | 기본 해설 |

**Rationale**: 기존 Remotion `SceneText.tsx`의 스타일 옵션 확장으로 구현 가능 → 별도 컴포넌트 불필요 (원칙 VI 모듈성).

---

## R-08. 10개 컴플라이언스 게이트 구현 방식 (FR-025)

**Decision**: **서버사이드 강제** + **DB 플래그**. 프론트엔드 버튼 비활성화는 UX일 뿐, 진짜 차단은 서버에서.

**구현 핵심**:
1. `ComplianceGateResult` SQLite 레코드 10개 항목 모두 `status='pass'` 확인 **AND** `manual_fact_check_signed_by`, `manual_defamation_check_signed_by` 컬럼 NOT NULL
2. 렌더링 API (`POST /api/dem-shorts/drafts/[id]/render`)는 게이트 통과 안된 draft의 렌더링 요청 거부 (403)
3. 업로드 API (`POST /api/dem-shorts/drafts/[id]/upload`)도 동일 확인
4. 프론트엔드 "건너뛰기" 옵션 **절대 미구현** (기획서 6.1-2 권고)

**Rationale**: 기획서 6.1-2 "개발자 본능상 스킵 옵션을 만들고 싶겠지만 절대 만들지 마세요". 모든 게이트 로직은 서버 측 함수 `gate.validate(draft_id) -> GateResult` 내 집중.

**테스트 (SC-005)**: `test_gate.py`에 "프론트엔드 우회/API 직접 호출/DB 조작" 3가지 시나리오 각각 거부 확인.

---

## R-09. 편향·혐오 가드레일 엔진 (FR-027)

**Decision**: **2계층 하이브리드** (Claude CLI로 $0 유지).

**계층 1 — 키워드 룰 (빠름, ms 단위)**:
- 혐오 키워드 사전 (1,000건) — `compliance/keyword_dict.py` 정적 파일
- 명예훼손 위험어 — 단정적 비난 ("사기", "범죄자", "속이는")
- 편향 단정어 — ("절대", "무조건", "항상")
- 한 키워드 당 카테고리별 가중치

**계층 2 — LLM 분류 (느림, Claude CLI)**:
- 해설 자막 + 메타데이터를 Claude CLI에 넘기고 4카테고리(혐오/허위/편향/명예훼손) 0~100 점수 JSON 응답
- 시스템 프롬프트: `compliance/llm_prompt.py` 템플릿
- 비용: $0 (Claude CLI, 원칙 I 유지)

**계층 3 — 이력 학습 (FR-028)**:
- 운영자 수정·무시 이력을 `guardrail_history` 테이블에 누적
- 월 1회 자동으로 키워드 가중치 재조정 (덜 경고할 키워드 -10%, 더 경고할 키워드 +10%)

**Rationale**: 기획서는 "쇼츠당 100원" 유료 LLM 전제였으나 Claude CLI로 대체 → $0 달성하면서 Recall 높은 LLM 분류 확보.

---

## R-10. 선거기간 자동 감지 (FR-030)

**Decision**: **하드코딩된 선거 일정 테이블 + 동적 계산**.

**테이블** (`compliance/election_dates.py`):
```python
ELECTION_DATES = [
    {"type": "general_election", "date": "2028-04-12", "guard_days": 120},
    {"type": "presidential_election", "date": "2027-05-03", "guard_days": 180},
    # 보궐·지방선거 갱신
]
```

**동적 계산**: 매 API 요청마다 현재 날짜와 비교하여 선거기간 플래그 반환. `GET /api/dem-shorts/election` 엔드포인트.

**Rationale**: 중앙선관위 공개 API는 없음 → 공식 선거일 발표 시 수동 갱신(`git commit`). 연 1~2회 수동 업데이트로 충분.

**Alternatives considered**:
- RSS/뉴스 자동 감지: 오탐 위험 + 법적 책임 리스크 → 수동 갱신이 안전

---

## R-11. BGM 라이선스 관리 (FR-035)

**Decision**: **저작권 프리 BGM만 로컬 라이브러리 관리**. `data/dem_shorts/bgm/` 디렉토리 + `bgm_manifest.json` 메타데이터.

**manifest 스키마**:
```json
{
  "filename": "calm_01.mp3",
  "source": "YouTube Audio Library",
  "license": "YT-CC0",
  "license_url": "https://...",
  "mood": ["calm", "serious"],
  "duration_sec": 120,
  "added_at": "2026-04-01"
}
```

**업로드 게이트 검증**: FR-035에서 `bgm_manifest.json`에 등록된 파일만 렌더링에 사용 허용. 외부 파일 드래그 드롭 시 거부.

**Rationale**: YouTube Audio Library·Pixabay·FMA의 CC0/CC-BY 음원만 사전 검증·등록 → 법적 리스크 제거.

---

## R-12. SQLite vs JSON 파일 저장 경계

**Decision**: **혼합**. 파이프라인 단계 데이터는 JSON, 영구 상태는 SQLite.

| 데이터 | 저장소 | 이유 |
|---|---|---|
| SourceVideo 메타 | SQLite | 관계형 쿼리 (정당별·세션타입별 집계) |
| 다운로드된 원본 영상 | 파일 시스템 (`archive/`) | 바이너리 대용량 |
| STT 전사 결과 | JSON 파일 (`transcripts/{video_id}.json`) | 단계 독립 실행 보장 (원칙 II) |
| Diarization 결과 | JSON 파일 (`segments/{video_id}.json`) | 동일 |
| Politician Whitelist | SQLite | CRUD + 등급 필터 |
| WeeklyRanking | SQLite | 주차별 집계·변화량 추적 |
| ShortsDraft 상태 | SQLite | 진행 상태 추적 + 게이트 결과 관계 |
| ComplianceGateResult | SQLite | draft FK 필수 |
| UploadedShorts 이력 | SQLite | YouTube video_id·조회수 지속 업데이트 |
| BiasReport 집계 | SQLite (materialized) | 월별 조회 빠르게 |
| 최종 MP4 산출물 | 파일 시스템 (`outputs/`) | 바이너리 |

**Rationale**: 원칙 II(파이프라인 단계 간 JSON)와 원칙 VI(모듈성) 조화. 관계형 상태는 SQLite(`sqlite3` 표준 라이브러리, 의존성 추가 없음, $0).

---

## R-13. YouTube 업로드 방식 (FR-036, FR-037)

**Decision**: YouTube Data API v3 `videos.insert` (resumable upload) + **운영자 최종 확인 버튼 필수**.

**플로우**:
1. 게이트 통과 + 렌더링 완료 후 `UploadedShorts` status=`ready_to_upload`
2. 운영자가 UI에서 "YouTube 업로드" 클릭 → 제목·설명·태그·예약 시간 최종 확인 다이얼로그
3. 확인 → `POST /api/dem-shorts/drafts/[id]/upload` → Python uploader → YouTube
4. 성공 시 `youtube_video_id` 저장, 실패 시 에러 로그 + 재시도 안내

**Rationale**: FR-037 "완전 자동 업로드 금지" 강제. 운영자 실수 방지용 최종 확인 다이얼로그는 UX 요건.

**Alternatives considered**:
- 예약 발행만 자동: YouTube Studio 수동 예약과 동일 수준 편의성 → 미채택 (파이프라인 통합성 우선)

---

## R-14. Remotion 렌더링 확장 (FR-033, FR-034)

**Decision**: **기존 Remotion 컴포지션 재사용** + **dem-shorts 전용 composition 추가**. 기존 `BlindShorts` composition은 불변 (FR-041 격리).

**신규 composition**: `DemShorts` — 소스 영상 백그라운드 + 해설 자막 오버레이 + TTS 오디오 + BGM. 프리셋 5종을 prop으로 받음.

**스마트 캐싱 (FR-034)**: 자막만 변경된 경우 Remotion `--cache` 활용 + 원본 영상·TTS·BGM 단계 스킵. FFmpeg subtitle 오버레이만 재실행 → 3분 → ~1분.

**Rationale**: 원본 `src/video/renderer.py`는 수정하지 않고 `src/dem_shorts/renderer.py`에서 Remotion CLI를 별도 호출.

---

## R-15. 테스트 영상 자동 생성 전략 (원칙 VII)

**Decision**: **샘플 NATV 영상 1개 고정** (`tests/fixtures/natv_sample.mp4`, ~10분 분량) + **E2E 스모크 테스트** 1건.

**E2E 시나리오**:
1. 샘플 영상 파일 투입 → 수집 파이프라인 시뮬레이션
2. STT → diarization → 발언자 식별 → 점수화
3. 30초 구간 자동 선택 → AI 해설 3개 생성 → 그중 1개 선택
4. 10개 게이트 검증 (모두 통과하도록 해설 50자 이상 자동 주입)
5. 렌더링 → MP4 출력 (업로드 스텝은 skip)
6. 출력 MP4 재생 시간·해상도 확인

**Rationale**: 원칙 VII "테스트 영상 자동 생성" 강제 — 샘플 NATV 영상을 git-ignored `tests/fixtures/`에 보관하고 CI에서는 mock 동작. 개발자 로컬에서는 실제 파이프라인 1회 통과 증거 필수.

---

## 종합 결정 요약

| 영역 | 선택 |
|---|---|
| NATV 폴링 | YouTube Data API v3 (30분 주기) |
| STT | openai-whisper `large-v3` (로컬) |
| Diarization | pyannote.audio 3.1 |
| 발언자 식별 | 호명 패턴 MVP → OCR/명단 Sprint 2 |
| 점유도 점수 | 룰 기반 (기획서 FD-SRC-02) |
| 여성·청년 랭킹 | 네이버 뉴스·Google Trends·YouTube·Wikipedia·데이터랩 |
| 자막 프리셋 | Remotion 확장 (5종) |
| 컴플라이언스 게이트 | 서버사이드 강제, 우회 불가 |
| 편향 가드레일 | 키워드(즉각) + Claude CLI(정확) 2계층 |
| 선거 감지 | 하드코딩 테이블 + 동적 D-day |
| BGM | 로컬 라이선스 manifest |
| 저장소 | SQLite(상태) + JSON(파이프라인) + 파일(바이너리) |
| 업로드 | YouTube Data API + 최종 확인 버튼 |
| 렌더러 | Remotion `DemShorts` 신규 composition |
| 테스트 | 샘플 NATV 영상 + E2E 스모크 |

**NEEDS CLARIFICATION 잔여**: 없음.
