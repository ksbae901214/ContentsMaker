# CLI Contract — Dem-Shorts Studio

**Entry point**: `python3 -m src.dem_shorts.cli <subcommand> [flags]`
**목적**: 배치 작업·개발자 디버깅·파이프라인 단계별 독립 실행 (원칙 II)

---

## 수집 파이프라인

### `poll-natv`
NATV 채널 신규 영상 감지 + 다운로드 큐 추가 (FR-001, FR-002).

```bash
python3 -m src.dem_shorts.cli poll-natv [--since-hours N] [--dry-run]
```

**플래그**:
- `--since-hours`: 최근 N시간 내 영상 (기본 24)
- `--dry-run`: DB 저장 없이 감지된 영상만 출력

**출력** (JSON Lines):
```json
{"event": "new", "video_id": "abc", "title": "...", "dem_score": 0}
{"event": "queued", "video_id": "abc", "download_path": "archive/abc.mp4"}
```

**Exit code**: 0=성공, 1=API 오류, 2=쿼터 초과

---

### `download`
단일 영상 다운로드 (FR-002).

```bash
python3 -m src.dem_shorts.cli download --video-id abc123 [--force]
```

---

### `stt`
STT 실행 (FR-012). 결과는 `data/dem_shorts/transcripts/{video_id}.json`.

```bash
python3 -m src.dem_shorts.cli stt --video-id abc123 [--model large-v3] [--device cpu|cuda]
```

**출력 JSON**:
```json
{
  "video_id": "abc123",
  "segments": [
    {"start": 0.0, "end": 3.2, "text": "안녕하십니까..."}
  ],
  "language": "ko"
}
```

---

### `diarize`
화자 분리 (FR-013). 결과는 `data/dem_shorts/segments/{video_id}.json`.

```bash
python3 -m src.dem_shorts.cli diarize --video-id abc123
```

---

### `identify`
발언자 식별 (FR-013~016). 결과를 `speech_segments` 테이블에 upsert.

```bash
python3 -m src.dem_shorts.cli identify --video-id abc123 [--confidence-threshold 0.7]
```

---

### `score`
민주당 점유도 + 추천 점수 계산 (FR-004, FR-016). SourceVideo·SpeechSegment 업데이트.

```bash
python3 -m src.dem_shorts.cli score --video-id abc123
```

---

### `pipeline`
수집→STT→diarize→identify→score 일괄 실행.

```bash
python3 -m src.dem_shorts.cli pipeline --video-id abc123
python3 -m src.dem_shorts.cli pipeline --all-pending
```

**독립 실행 원칙 (원칙 II)**: 각 단계는 이전 단계 JSON 산출물만 있으면 독립 실행 가능. 실패 시 해당 단계부터 재개.

---

## 편집·렌더·업로드

### `draft-create`
발언 구간에서 쇼츠 초안 생성 (UI 없이 CLI 테스트용).

```bash
python3 -m src.dem_shorts.cli draft-create --segment-id 42 \
  --cut-start 125 --cut-end 175 --preset leejaemyung
```

### `commentary`
AI 해설 후보 생성 (FR-020, Claude CLI 호출).

```bash
python3 -m src.dem_shorts.cli commentary --draft-id 5 [--tone "객관적"]
```

### `gate`
컴플라이언스 게이트 실행 (FR-025).

```bash
python3 -m src.dem_shorts.cli gate --draft-id 5 \
  --manual-fact-check --manual-defamation-check \
  --operator-id owner
```

**Exit code**: 0=pass, 1=fail (risk_score ≥61), 2=warn_only

### `render`
렌더링 (FR-033). 게이트 통과한 draft만.

```bash
python3 -m src.dem_shorts.cli render --draft-id 5 [--smart-cache]
```

### `upload`
YouTube 업로드 (FR-036, FR-037).

```bash
python3 -m src.dem_shorts.cli upload --draft-id 5 \
  --title "제목" --description-file desc.txt --schedule "2026-04-17T18:00:00+09:00"
```

---

## 배치 작업

### `ranking-batch`
주간 여성·청년 랭킹 집계 (FR-008, FR-009).

```bash
python3 -m src.dem_shorts.cli ranking-batch [--week-start 2026-04-13] [--dry-run]
```

**cron 등록 예**:
```
0 22 * * 0 cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli ranking-batch
```

### `bias-report`
월간 편향 리포트 생성 (FR-038).

```bash
python3 -m src.dem_shorts.cli bias-report [--month 2026-04]
```

### `archive-rotate`
3개월 경과 원본 영상을 콜드 스토리지로 이동 (edge case: 디스크 여유).

```bash
python3 -m src.dem_shorts.cli archive-rotate --days 90 [--target /path/to/cold]
```

---

## 개발·디버깅

### `db-init`
SQLite 마이그레이션 실행 (초기 설치).

```bash
python3 -m src.dem_shorts.cli db-init
```

Seed 데이터 (이재명·조국·정청래) 자동 삽입.

### `db-migrate`
추가 마이그레이션 적용.

### `whitelist-seed`
Whitelist 추가 시드 (여성·청년 정치인 수동 초기 데이터).

```bash
python3 -m src.dem_shorts.cli whitelist-seed --file politicians_seed.json
```

### `test-e2e`
E2E 스모크 테스트 (원칙 VII).

```bash
python3 -m src.dem_shorts.cli test-e2e [--fixture tests/fixtures/natv_sample.mp4]
```

샘플 영상 1개로 수집→렌더까지 전체 파이프라인 1회 실행, 최종 MP4 출력 시 종료.
