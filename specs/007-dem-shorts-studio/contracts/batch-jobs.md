# Batch Jobs Contract — Dem-Shorts Studio

**Scheduler**: cron (macOS/Linux) 또는 개발 단계에서 수동 실행
**Log**: `data/dem_shorts/logs/batch/{date}_{job}.log`

---

## B-01. NATV 폴링 배치 (FR-001)

| 항목 | 값 |
|---|---|
| 실행 주기 | 30분 (설정 가능) |
| cron | `*/30 * * * *` |
| 명령 | `python3 -m src.dem_shorts.cli poll-natv --since-hours 1` |
| 평균 소요 | ~30초 (API 호출) |
| 리소스 | API 쿼터 ~100 unit/회 |
| 실패 처리 | 3회 재시도 (5/15/60분 지수 백오프) |
| 알림 | 쿼터 90% 도달 시 이메일/로그 |

**선결 조건**: YouTube Data API 키 `.env` 또는 OS 키체인에 저장.

---

## B-02. 다운로드·STT·Diarization 워커 (FR-002, FR-012, FR-013)

| 항목 | 값 |
|---|---|
| 실행 방식 | 큐 워커 (상시 실행) |
| 명령 | `python3 -m src.dem_shorts.cli pipeline --all-pending` |
| 동시 실행 | 최대 2건 (다운로드) / 1건 (STT) / 1건 (diarize) |
| 평균 소요 | 다운로드 5분 · STT 30분(CPU) / 5분(GPU) · diarize 5분 |
| 리소스 | 디스크 I/O, GPU 1개(선택), CPU 4코어 권장 |
| 실패 처리 | 개별 영상 실패 시 플래그만 세우고 다음 영상 진행 (원칙 II) |

---

## B-03. 주간 랭킹 배치 (FR-008, FR-009)

| 항목 | 값 |
|---|---|
| 실행 주기 | 매주 일요일 22:00 KST |
| cron | `0 22 * * 0` |
| 명령 | `python3 -m src.dem_shorts.cli ranking-batch` |
| 평균 소요 | 10~20분 (5개 데이터 소스 순회) |
| 리소스 | 네이버 뉴스 크롤링(5초 간격), API 호출 |
| 실패 처리 | 다음날 09:00 자동 재시도 (1회) |
| 출력 | WeeklyRanking 테이블 업데이트 + Politician.tier 재배치 |

**데이터 소스 호출**:
1. 네이버 뉴스 검색 크롤링 (robots.txt 준수)
2. Google Trends (pytrends)
3. YouTube Data API search.list
4. Wikipedia pageviews API
5. 네이버 데이터랩 공공 API

---

## B-04. 월간 편향 리포트 배치 (FR-038)

| 항목 | 값 |
|---|---|
| 실행 주기 | 매월 1일 09:00 KST |
| cron | `0 9 1 * *` |
| 명령 | `python3 -m src.dem_shorts.cli bias-report --month <prev-month>` |
| 평균 소요 | 1분 미만 (DB 집계만) |
| 출력 | BiasReport 테이블 + 대시보드 알림 |

---

## B-05. YouTube 메트릭 갱신 배치

| 항목 | 값 |
|---|---|
| 실행 주기 | 1시간 (업로드 후 24시간은 15분 주기) |
| cron | `0 * * * *` |
| 명령 | `python3 -m src.dem_shorts.cli metrics-update` |
| 리소스 | API ~50 unit/영상 × 최근 30개 = 1,500 unit/회 |

업로드된 쇼츠의 view_count·like_count 갱신 (FR-038 리포트 입력).

---

## B-06. 아카이브 순환 배치 (edge case)

| 항목 | 값 |
|---|---|
| 실행 주기 | 주 1회 (매주 토 03:00) |
| cron | `0 3 * * 6` |
| 명령 | `python3 -m src.dem_shorts.cli archive-rotate --days 90` |
| 조건 | 디스크 여유 100GB 미만 시 자동 트리거 |
| 출력 | 3개월 이상된 원본 영상을 콜드 스토리지(외장 SSD)로 이동 |

---

## B-07. 선거기간 감지 배치 (FR-030)

| 항목 | 값 |
|---|---|
| 실행 주기 | 매일 00:01 |
| cron | `1 0 * * *` |
| 명령 | `python3 -m src.dem_shorts.cli election-check` |
| 평균 소요 | 1초 미만 (하드코딩 테이블 조회) |
| 출력 | D-180/D-120 경계 진입 시 운영자 알림 + 중립 모드 플래그 |

SC-007: 경계 진입 후 24시간 이내 대시보드 배너 표시.

---

## B-08. 가드레일 학습 배치 (FR-028)

| 항목 | 값 |
|---|---|
| 실행 주기 | 매월 1일 03:00 |
| cron | `0 3 1 * *` |
| 명령 | `python3 -m src.dem_shorts.cli guardrail-learn` |
| 출력 | `guardrail_history` 기반 키워드 가중치 재조정 |

---

## 배치 실행 모니터링

**로그 형식** (JSON Lines, `data/dem_shorts/logs/batch/`):
```json
{"ts": "2026-04-16T22:00:00+09:00", "job": "ranking-batch", "status": "started"}
{"ts": "2026-04-16T22:12:30+09:00", "job": "ranking-batch", "status": "done", "duration_sec": 750, "updated": 20}
```

**실패 알림 채널**:
- 로그 파일 (항상)
- 이메일 (설정 가능, 선택)
- 운영자 대시보드 상단 빨간 배너 (마지막 실패 시각 표시)

**리셋 방법**: 실패한 배치는 다음 주기 자동 재시도. 수동 재실행은 CLI로.
