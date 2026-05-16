# Dem-Shorts Studio (007)

> 민주당 친화형 정치 쇼츠 반자동 제작 시스템. NATV 국회방송을 입력으로 발언자 식별 → 컴플라이언스 게이트 → YouTube Shorts 발행.

전체 사양은 [specs/007-dem-shorts-studio/spec.md](../../specs/007-dem-shorts-studio/spec.md), 운영자 1일차 가이드는 [quickstart.md](../../specs/007-dem-shorts-studio/quickstart.md) 를 참조하세요. 본 문서는 **설치·필수 명령 요약**입니다.

## 1. 설치

```bash
# Python · Node 의존성
pip install -r requirements.txt
pip install -r requirements-dem-shorts.txt
npm install
cd src/video/remotion && npm install && cd ../../..

# DB 초기화 (이재명·조국·정청래 시드)
python3 -m src.dem_shorts.cli db-init
```

## 2. 필수 환경 변수 (`.env`)

| 키 | 용도 | 비고 |
|---|---|---|
| `YOUTUBE_API_KEY` | NATV 폴링 + 메트릭 갱신 | Google Cloud Console |
| `HUGGINGFACE_TOKEN` | pyannote 화자 분리 모델 다운로드 | https://huggingface.co/settings/tokens |
| `NATV_CHANNEL_HANDLE` | 기본 `@NATV_korea` | |
| `DEM_SHORTS_COLD_DIR` | 아카이브 콜드 스토리지 (선택) | 기본 `data/dem_shorts/cold/` |

## 3. CLI 명령 한 눈에 보기

| 단계 | 명령 |
|---|---|
| 폴링 | `python3 -m src.dem_shorts.cli poll-natv [--since-hours N] [--dry-run]` |
| 다운로드 | `python3 -m src.dem_shorts.cli download --video-id <ID>` |
| STT | `python3 -m src.dem_shorts.cli stt --video-id <ID>` |
| 화자 분리 | `python3 -m src.dem_shorts.cli diarize --video-id <ID>` |
| 발언자 식별 | `python3 -m src.dem_shorts.cli identify --video-id <ID>` |
| 점수 갱신 | `python3 -m src.dem_shorts.cli score --video-id <ID>` |
| 초안 생성 | `python3 -m src.dem_shorts.cli draft-create --segment-id <SID> --cut-start <S> --cut-end <E>` |
| 해설 후보 | `python3 -m src.dem_shorts.cli commentary --draft-id <ID>` |
| 게이트 | `python3 -m src.dem_shorts.cli gate --draft-id <ID> --manual-fact-check --manual-defamation-check` |
| 렌더 | `python3 -m src.dem_shorts.cli render --draft-id <ID>` |
| 업로드 | `python3 -m src.dem_shorts.cli upload --draft-id <ID> --title "..." --description-file desc.txt` |
| BGM 등록 | `python3 -m src.dem_shorts.cli bgm-register --filename a.mp3 --mood calm --license CC0 --path /...` |
| 선거 점검 | `python3 -m src.dem_shorts.cli election-check` |
| 주간 랭킹 | `python3 -m src.dem_shorts.cli ranking-batch [--week-start YYYY-MM-DD]` |
| 월간 리포트 | `python3 -m src.dem_shorts.cli bias-report [--month YYYY-MM]` |
| 메트릭 갱신 | `python3 -m src.dem_shorts.cli metrics-update [--limit N]` |
| 아카이브 순환 | `python3 -m src.dem_shorts.cli archive-rotate [--days 90] [--cold-dir PATH]` |
| 가드레일 학습 | `python3 -m src.dem_shorts.cli guardrail-learn [--days 30]` |
| E2E 스모크 | `python3 -m src.dem_shorts.cli test-e2e [--real-models]` |

모든 명령은 `--dry-run` 또는 `--help` 지원. 출력 JSON 포맷.

## 4. REST API (Next.js)

`npm run dev` 후 `http://localhost:3000`:

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/api/dem-shorts/videos` | 수집된 영상 목록 (점수 내림차순) |
| GET | `/api/dem-shorts/videos/[id]` | 영상 상세 + speech_segments |
| GET | `/api/dem-shorts/whitelist` | 정치인 whitelist |
| POST | `/api/dem-shorts/whitelist` | whitelist 추가 |
| GET | `/api/dem-shorts/election` | 선거기간 상태 + 다음 선거 정보 |
| GET | `/api/dem-shorts/rankings?week_start=...` | 주간 랭킹 |
| GET | `/api/dem-shorts/reports?month=...` | 월간 편향 리포트 |
| POST | `/api/dem-shorts/drafts` | draft 생성 |
| GET/PATCH | `/api/dem-shorts/drafts/[id]` | draft 조회·수정 |
| POST | `/api/dem-shorts/drafts/[id]/commentary` | AI 해설 후보 |
| POST | `/api/dem-shorts/drafts/[id]/gate` | 컴플라이언스 게이트 |
| POST (SSE) | `/api/dem-shorts/drafts/[id]/render` | 렌더 (스트리밍) |
| POST | `/api/dem-shorts/drafts/[id]/upload` | YouTube 업로드 |

UI 페이지: `/dem-shorts` (대시보드), `/dem-shorts/[videoId]` (타임라인), `/dem-shorts/[videoId]/render` (편집·게이트·업로드), `/dem-shorts/whitelist`, `/dem-shorts/ranking`, `/dem-shorts/reports`.

## 5. 스모크 테스트

```bash
# CI 가드 (stub 모드, ~1초)
python3 -m src.dem_shorts.cli test-e2e

# 실제 Whisper/pyannote/Remotion 검증 (5~10분, 샘플 mp4 필요)
# tests/fixtures/README.md 참고하여 natv_sample.mp4 준비 후:
python3 -m src.dem_shorts.cli test-e2e --real-models
```

## 6. 추가 문서

| 항목 | 경로 |
|---|---|
| 운영 루틴·트러블슈팅 | [operations.md](operations.md) |
| Cron 등록 안내 | [cron.md](cron.md) |
| 사양 / 설계 / 결정 사항 | `specs/007-dem-shorts-studio/` |
| Constitution (절대 원칙) | `.specify/memory/constitution.md` |
