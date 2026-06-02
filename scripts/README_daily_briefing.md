# 매일 정치 브리핑 자동 실행 (Feature 020)

매일 아침 07:00 KST에 자동으로 어제 정치 YouTube + 네이버 뉴스를 수집해 핫한 이슈 순으로 기획안을 생성합니다.

## 1. 사전 준비

### YouTube 모니터링 채널 등록

`data/briefing_channels.json` 파일 생성:

```json
{
  "version": 1,
  "channels": [
    {"channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx", "name": "MBC 라디오 시사", "category": "neutral"},
    {"channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx", "name": "뉴스핌TV", "category": "neutral"}
  ]
}
```

**채널 ID 추출 방법:**
1. 채널 페이지 열기 (예: `https://youtube.com/@MBCRadio`)
2. 페이지 소스 보기 → `og:url` 또는 `channelId` 검색
3. `UC`로 시작하는 24자 문자열이 channel_id

**균형 권장**: 보수/진보/중립 채널을 함께 등록해 한쪽 편향 방지.

### 환경변수

다음 키들을 발급 후 plist에 입력:

| 키 | 발급처 |
|---|---|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | https://developers.naver.com/apps/ → 검색 API |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `YOUTUBE_API_KEY` (선택) | Google Cloud Console → APIs → YouTube Data API v3 → API Key |

`YOUTUBE_API_KEY` 미설정 시 `data/.youtube_token.json` OAuth 토큰으로 자동 폴백.

## 2. 수동 트리거

CLI:
```bash
python3 -m src.main daily-briefing --top 5
```

웹 UI:
- 메인 페이지 우상단 "🗞️ 오늘의 브리핑" 버튼 클릭
- 또는 직접 접근: `http://localhost:3000/daily-briefing`
- "새 브리핑 실행" 버튼 클릭 (최대 10분 소요)

## 3. 자동 실행 (macOS launchd)

### 설치

```bash
# 1) plist 편집 — EnvironmentVariables 영역에 실제 API 키 입력
nano scripts/com.contentsmaker.daily-briefing.plist

# 2) WorkingDirectory가 본인 경로와 다르면 수정 (기본: /Users/kyusik/ContentsMaker)

# 3) LaunchAgents 디렉토리로 복사
cp scripts/com.contentsmaker.daily-briefing.plist ~/Library/LaunchAgents/

# 4) 활성화
launchctl load ~/Library/LaunchAgents/com.contentsmaker.daily-briefing.plist

# 5) 즉시 1회 실행 (테스트)
launchctl start com.contentsmaker.daily-briefing

# 6) 로그 확인
tail -f data/daily_briefing/.cron.log
tail -f data/daily_briefing/.cron.err.log
```

### 비활성화

```bash
launchctl unload ~/Library/LaunchAgents/com.contentsmaker.daily-briefing.plist
```

### 상태 확인

```bash
launchctl list | grep contentsmaker
```

## 4. 결과 확인

```
data/daily_briefing/YYYY-MM-DD/
├── issues.json              # 모든 이슈 + 점수 + 메타
├── plans/
│   ├── 01/                  # rank 1 이슈
│   │   └── plans.json       # generate_three_plans 결과 (3 plans)
│   ├── 02/
│   ├── 03_manual_required.json   # 자막 없는 이슈 (수동 처리 필요)
│   ...
```

## 5. 비용

| 항목 | 일별 사용량 | 한도 | 비용 |
|---|---|---|---|
| YouTube Data API | ~60 units (채널 20개 기준) | 10,000 units/day | $0 |
| 네이버 검색 API | ~4 req (정치/국회/대통령/선거) | 25,000 req/day | $0 |
| Gemini 2.5 Flash (클러스터링) | 1 호출 | 250 req/day (무료) | $0 |
| Claude (generate_three_plans × 5) | 15 호출 (Stage A + Stage B×3 × 5) | 무제한 (CLI) | $0 |
| **총** | | | **$0** |

## 6. 트러블슈팅

**`data/briefing_channels.json` 가 비어 있음**
→ 채널을 추가하세요 (위 1단계 참조). 빈 상태에서는 영상 수집 0건 → 이슈 0개.

**`NAVER_CLIENT_ID` 환경변수 없음**
→ plist의 `EnvironmentVariables`에 추가하거나, 수동 실행이라면 `~/.zshrc`에 `export` 추가.

**모든 이슈가 `manual_required` 상태**
→ 영상에 한국어 자막이 없음. 영상 다운로드 + Whisper STT를 사용하려면 별도 처리 필요.

**launchd 실행이 안 됨**
→ `launchctl list | grep contentsmaker` 으로 등록 여부 확인.
→ `data/daily_briefing/.cron.err.log` 확인.
→ macOS Privacy 설정에서 launchd가 디스크 접근 권한이 있는지 확인.
