# Dem-Shorts Studio — 운영 루틴 & 트러블슈팅

> 매일 / 매주 / 매월 운영자가 수행해야 할 점검 항목과 자주 마주치는 문제 해결법.

## 일상 루틴

### 매일

- **08:30 (수동)**: `npm run dev` → `/dem-shorts` 열기 → 신규 영상 점수 80+ 확인 → 1~3개 쇼츠 제작
- **자동 (cron)**: `poll-natv` 매 30분, `election-check` 매일 00:01, `metrics-update` 매시 00분

### 매주 일요일

- **자동 22:00**: `ranking-batch` 실행 → 여성·청년·연대 정치인 랭킹 갱신 (`/dem-shorts/ranking` 에서 신규 `rising` 태그 확인)
- **자동 03:00 토요일**: `archive-rotate` → 90일 이상 원본 파일 콜드 디렉토리로 이동

### 매월 1일

- **자동 03:00**: `guardrail-learn` → `data/dem_shorts/guardrail_weights.json` 생성. 운영자가 검토 후 `keyword_dict.py` 수동 반영
- **자동 09:00**: `bias-report` → `/dem-shorts/reports` 에서 전월 인물·정당 점유율 + SC-011/SC-012 권고 확인

### 선거 D-180 / D-120 진입 시

- 모든 페이지 상단에 빨간 `ElectionBanner` 자동 표시
- 게이트 편향 임계값이 61 → 30 으로 자동 하향 (FR-031)
- 해설 톤은 `commentary_prompt.COMMENTARY_NEUTRAL_PROMPT` 가 자동 적용 (정책 설명 중심)
- ⚠️ 운영자 절대 수칙: 특정 후보 우호 표현 금지, "이재명 대표" 등 호칭만 사용

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 게이트 통과 불가 — `해설 자막 N자` | 본인 해설 < 50자 | 해설 자막 더 작성 (FR-024) |
| 게이트 통과 불가 — `편향 리스크 N ≥ 30` | 선거기간 중 편향 키워드 사용 | 단정 표현(절대/확실히 등) 제거 후 재검수 |
| 게이트 통과 불가 — `팩트 URL 0개` | 팩트 출처 미첨부 | 출처 URL 2개 이상 입력 (FR-029) |
| `(미식별)` 발언자 표시 | 호명 패턴 < 신뢰도 0.7 | UI에서 수동으로 정치인 지정 |
| `quotaExceeded` (poll-natv) | YouTube API 일일 10,000 unit 초과 | 다음 날 자동 복구. cron 주기 60분으로 일시 완화 |
| YouTube 업로드 403 | OAuth 토큰 만료 | `python3 -m src.dem_shorts.cli youtube-auth` 재실행 |
| 디스크 100GB 미만 | 영상 누적 | `archive-rotate --days 60` 임시 단축 |
| 선거 배너 사라지지 않음 | 새 선거가 ELECTION_DATES 에 미등록 | `src/dem_shorts/compliance/election_dates.py` 수동 갱신 (PR) |
| `is_taken_down=1` 메트릭 알림 | YouTube 가 영상을 내림 | `uploaded_shorts.takedown_reason` 확인 → 정책 위반 사유 분석 |
| `metrics-update` 가 항상 `updated=0` | `YOUTUBE_API_KEY` 미설정 | `.env` 확인 |
| Remotion 렌더 hanging | npx 누락 / Node 미설치 | `node --version` >= 20, `npx -v` 확인 |

## 정기 점검

### 주간 (5분)
1. `data/dem_shorts/logs/batch/` 의 최신 로그 1~2개 grep `"failed"` → 0건 확인
2. `/dem-shorts/ranking` 에서 `pending` 태그 인물 수 추세 확인 (2주 연속 시 자동 삭제됨)

### 월간 (30분)
1. `/dem-shorts/reports` 에서 권고 메시지 확인:
   - 단일 인물 30% 초과 → 다음 달 인물 다양화 의식적으로
   - Top3(이재명·조국·정청래) 합계 60% 초과 → 여성·청년 카테고리 발언 비중 늘리기
   - 여성·청년 < 40% → 차별화 미달 (SC-012)
2. `data/dem_shorts/guardrail_weights.json` 확인 → multiplier 1.5+ 인 키워드는 `keyword_dict.py` 가중치 +10 / 0.7- 인 키워드는 -10 반영
3. `cli archive-rotate --dry-run` → 콜드 이동 후보 미리보기

## 수동 데이터 정정

```bash
# 잘못 식별된 발언자 수동 교정
sqlite3 data/dem_shorts/state.db
> UPDATE speech_segments SET politician_id=? WHERE id=?;

# whitelist 정치인 비활성화
sqlite3 data/dem_shorts/state.db
> UPDATE politicians SET is_active=0, tier='blocked' WHERE name='...';
```

또는 UI: `/dem-shorts/whitelist`.

## 안전 원칙 (절대)

`HANDOFF.md` 와 `quickstart.md` 안전 원칙을 반드시 숙지. 핵심 3가지:

1. **게이트 우회 금지**: `GateContext` 에 `skip_*` 필드 추가 금지, `is_passed()` 단순화 금지, UI "건너뛰기" 버튼 금지
2. **선거기간 동적 임계값 유지**: `gate.item_5_bias_guardrail` 와 risk_ok 판정 모두 `get_bias_threshold()` 경유
3. **NATV 출처 + 팩트 URL 2개 이상 강제**: `uploader.validate_upload_request` 수정 금지

## 비용 모니터링 (원칙 I — Zero Cost 유지)

| 항목 | 비용 | 한도 |
|---|---|---|
| YouTube Data API | $0 | 일일 10,000 unit (poll-natv 4,800 + metrics-update 720 = 약 5,520) |
| Whisper / pyannote | $0 | 로컬 실행 (HF 토큰 무료) |
| Claude CLI (해설·LLM 가드) | $0 | CLI 재사용 |
| 5개 랭킹 소스 | $0 | 모두 무료/공공 API |
| YouTube 업로드 | $0 | resumable upload |
| 외장 SSD (1회 비용) | ~$200 | 2TB 권장 |
| **월 변동비** | **$0** | (Premium+ 플랜 사용 안 함, 영상 부담만) |
