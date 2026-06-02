# Dem-Shorts Studio — Cron 배치 등록 안내

T040: B-01 NATV 폴링 배치 crontab 샘플.

## 현재 활성 배치 (MVP + Phase 6 시점)

### B-01: NATV 폴링 (30분 주기)

```cron
*/30 * * * * cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli poll-natv --since-hours 1 >> data/dem_shorts/logs/batch/cron.log 2>&1
```

**사전 조건**:
- `.env`의 `YOUTUBE_API_KEY` 설정
- `python3 -m src.dem_shorts.cli db-init` 1회 실행

**예상 소요**: 30초 이내 (API 1회)
**쿼터 소모**: 약 100 unit/회 × 48회/일 = 4,800 unit (일일 상한 10,000 unit 내)

### B-03: 주간 랭킹 (일요일 22:00) — Phase 7 (T111)

```cron
0 22 * * 0 cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli ranking-batch >> data/dem_shorts/logs/batch/cron.log 2>&1
```

여성·청년·연대 카테고리 정치인 랭킹 갱신 (FR-008/009). 5개 무료/공공 소스 가중합.

### B-04: 월간 편향 리포트 (매월 1일 09:00) — Phase 7 (T113)

```cron
0 9 1 * * cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli bias-report >> data/dem_shorts/logs/batch/cron.log 2>&1
```

전월 업로드 인물·정당·프리셋 점유율 + SC-011/SC-012 권고 메시지 생성.

### B-05: YouTube 메트릭 갱신 (매시 00분) — Phase 8 (T118)

```cron
0 * * * * cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli metrics-update --limit 30 >> data/dem_shorts/logs/batch/cron.log 2>&1
```

업로드된 쇼츠의 view/like/comment 갱신 (FR-038 입력). 응답에서 사라진 video_id
는 `is_taken_down=1` 마킹 후 운영자 알림.

**쿼터**: videos.list 1회 ≈ 3 unit × 50 id 일괄 = 24시간 약 720 unit (여유 충분).
업로드 후 24시간(fresh) 구간은 운영에서 별도 cron 으로 15분 주기 호출 권장.

### B-06: 아카이브 순환 (매주 토 03:00) — Phase 8 (T119)

```cron
0 3 * * 6 cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli archive-rotate --days 90 >> data/dem_shorts/logs/batch/cron.log 2>&1
```

90일 이상된 source_videos 의 download_path 파일을 콜드 스토리지(외장 SSD)로 이동.
`DEM_SHORTS_COLD_DIR` 환경변수로 위치 지정 (기본 `data/dem_shorts/cold/`).

**디스크 여유 100GB 미만 시 자동 트리거**는 운영 측 외부 스크립트로 별도 구성.

### B-08: 가드레일 학습 (매월 1일 03:00) — Phase 8 (T120)

```cron
0 3 1 * * cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli guardrail-learn --days 30 >> data/dem_shorts/logs/batch/cron.log 2>&1
```

`guardrail_history` 의 운영자 fixed/ignored 액션을 분석해 키워드 multiplier
산출 (FR-028). 출력: `data/dem_shorts/guardrail_weights.json` — 운영자가 매월
검토 후 `keyword_dict.py` 에 수동 반영.

### B-07: 선거기간 감지 (매일 00:01) — Phase 6 (T102)

```cron
1 0 * * * cd /Users/kyusik/ContentsMaker && python3 -m src.dem_shorts.cli election-check >> data/dem_shorts/logs/batch/cron.log 2>&1
```

**역할**: 대선 D-180 / 총선 D-120 경계 진입을 매일 점검 (FR-030). 경계 진입 시
`data/dem_shorts/logs/batch/{date}_election-check.log` 에 JSON Lines 기록.
대시보드 배너는 `GET /api/dem-shorts/election` 을 실시간 조회하므로 본 배치는
"운영자 알림용 로그·메트릭" 목적.

**예상 소요**: 1초 미만 (하드코딩 테이블 조회)
**외부 의존**: 없음 (네트워크 호출 없음)

**출력 예시**:
```json
{"in_election_period": false, "next_election_type": "presidential_election", "next_election_date": "2027-05-03", "days_until": 382, "bias_threshold": 61.0, "neutral_mode_enforced": false}
```

### 등록 방법 (macOS)

```bash
# 현재 crontab 편집
crontab -e

# 위 라인 추가 후 저장
# 확인:
crontab -l
```

### 실행 확인

```bash
tail -f data/dem_shorts/logs/batch/cron.log
# 또는 구조화된 이벤트 로그:
cat data/dem_shorts/logs/batch/$(date +%Y%m%d)_poll-natv.log | jq .
```

---

## 후속 Phase 배치 (구현 예정)

| Batch ID | cron | 설명 | Phase |
|---|---|---|---|
| B-02 다운로드·STT·Diarize 워커 | 상시 실행 (별도 daemon) | `pipeline --all-pending` | Phase 4 (미구현) |

전체 상세는 `contracts/batch-jobs.md` 참조.
