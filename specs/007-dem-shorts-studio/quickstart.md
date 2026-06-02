# Quickstart — Dem-Shorts Studio

**목적**: 운영자(프로젝트 오너 1인)가 0일차부터 첫 쇼츠 업로드까지 30분 이내 완료하도록 하는 실전 가이드.

---

## 사전 준비 (1회만)

### 1. 시스템 요구사항
- macOS (Darwin 24+) 또는 Linux
- Python 3.11+, Node.js 20+
- FFmpeg 설치 (`brew install ffmpeg` / `apt install ffmpeg`)
- 외장 SSD 2TB 마운트 (영상 아카이브용)
- GPU 권장 (NVIDIA) — 없어도 동작, 다만 STT/렌더링 느림

### 2. 계정·키 발급
- **YouTube Data API v3 키**: Google Cloud Console → 프로젝트 생성 → API 활성화 → OAuth 2.0 클라이언트 ID 발급
- **YouTube OAuth 토큰**: 업로드용, 최초 1회 브라우저 인증
- **HuggingFace 토큰** (무료): pyannote.audio 모델 다운로드용 — https://huggingface.co/settings/tokens
- **변호사 자문**: 프로젝트 시작 전 필수 (기획서 6.1-1, 20~30만원) — 인증·토큰 아님, 법적 안전 장치

### 3. 환경 변수 (`.env`)
```bash
YOUTUBE_API_KEY=...
YOUTUBE_OAUTH_CLIENT=...
HUGGINGFACE_TOKEN=...
NATV_CHANNEL_HANDLE=@NATV_korea
DEM_SHORTS_ARCHIVE_DIR=/Volumes/SSD2TB/natv_archive
```

---

## 1일차 — 설치

```bash
# 1. 의존성 설치
pip install -r requirements.txt    # 기존
pip install -r requirements-dem-shorts.txt    # 신규: whisper, pyannote.audio, google-api-python-client, pytrends

npm install                         # Next.js UI
cd src/video/remotion && npm install   # Remotion 재사용

# 2. DB 초기화 (시드: 이재명·조국·정청래)
python3 -m src.dem_shorts.cli db-init

# 3. YouTube OAuth 인증 (1회)
python3 -m src.dem_shorts.cli youtube-auth

# 4. BGM 라이브러리 초기화 (저작권 프리만)
mkdir -p data/dem_shorts/bgm
# YouTube Audio Library / Pixabay 음원을 data/dem_shorts/bgm/ 에 복사 후:
python3 -m src.dem_shorts.cli bgm-register --auto-detect

# 5. 샘플 테스트 영상으로 E2E 검증 (원칙 VII)
python3 -m src.dem_shorts.cli test-e2e
```

**검증**: `test-e2e` 완료 시 `data/dem_shorts/outputs/e2e_sample.mp4` 생성됨 + 재생 확인.

---

## 2일차 — 첫 쇼츠 제작 (30분 이내)

### Step 1 — 대시보드 열기 (30초)
```bash
npm run dev        # localhost:3000/dem-shorts
```

신규 NATV 영상이 민주당 점유도 점수 내림차순으로 표시됨 (US1, FR-004).

### Step 2 — 영상 선택 (1분)
점수 80+ 영상을 클릭 → 타임라인 편집기 진입 (US2).

- 이재명·조국·정청래 발언 구간이 색상별로 하이라이트
- 각 구간 옆에 추천 점수 표시

### Step 3 — 구간 자르기 (3분)
추천 점수 높은 구간 선택 → 시작~종료 조정 (≤60초) → "쇼츠 만들기" 클릭.

### Step 4 — 해설 자막 작성 (10~15분, 핵심)
- "AI 추천 해설" 버튼 → 후보 3개 중 하나 선택 or 직접 편집
- **최소 50자 이상 확보** (FR-024, 빨간색 경고 사라질 때까지)
- 자막 스타일 프리셋 선택 (이재명 영상이면 `leejaemyung`)
- TTS 추가 (선택): 보이스 프리셋 4종 중 선택
- BGM 선택 (저작권 프리 라이브러리에서)
- **팩트 출처 URL 2개 이상 첨부** (FR-029)

### Step 5 — 컴플라이언스 게이트 (2분)
"업로드 검수" 버튼 클릭 → 10개 항목 자동/수동 체크.

- 자동 8개 → 즉시 결과 (통과/경고/차단)
- 수동 2개 → 운영자가 직접 체크박스 클릭
  - ☐ 팩트 검증 완료 (출처 URL 2개 직접 확인)
  - ☐ 명예훼손 요소 없음 (문제 표현 재확인)

**핵심**: 어떤 항목이라도 "차단"이면 렌더링/업로드 버튼 **완전 비활성화** (SC-005). 해결 후 재검수.

### Step 6 — 렌더링 (2~5분)
"렌더링 시작" → SSE 진행 표시.

### Step 7 — YouTube 업로드 (1분)
"YouTube 업로드" → 제목·설명·태그 최종 확인 다이얼로그 → "확정" 클릭.

- 설명란에 "NATV 국회방송" 자동 포함 (FR-029 강제)
- 팩트 링크 자동 포함
- 예약 발행 시각 설정 가능

완료 → 쇼츠가 YouTube Shorts로 발행됨.

---

## 주간·월간 루틴

### 매주 일요일 22:00
자동: 여성·청년 정치인 랭킹 배치 실행 (B-03).
수동: 대시보드 → "주간 랭킹" 탭에서 신규 진입자 확인 (`rising` 태그).

### 매월 1일
자동: 편향 밸런스 리포트 생성 (B-04).
수동: 리포트 확인 → 특정 인물 30% 초과 경고 있으면 다음 달 다양성 조정.

### 선거 D-180/D-120 진입 시
자동: 배너 표시 + 중립 모드 강제.
수동: "해설 자막 톤을 정책 설명 중심으로 전환" 룰 준수.

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| "게이트 통과 불가, 해설 자막 미달" | 본인 해설 < 50자 | 해설 자막 추가 입력 |
| "NATV 영상 감지 안됨" | API 쿼터 초과 or 휴회 기간 | `cli poll-natv --dry-run` 로 수동 확인 |
| "STT 결과 품질 낮음" | 음질 불량 영상 | 수동 자막 편집 모드 전환 |
| "발언자 (미식별)" | 신뢰도 <0.7 | UI에서 수동으로 정치인 지정 |
| "디스크 공간 부족" | 영상 누적 300GB+ | `cli archive-rotate --days 90` |
| "YouTube 업로드 403" | OAuth 토큰 만료 | `cli youtube-auth` 재실행 |
| "선거기간 배너 지속 표시" | 하드코딩 테이블 수동 갱신 필요 | `compliance/election_dates.py` 편집 |

---

## 안전 원칙 체크리스트 (기획서 6.1)

**절대 하지 말 것**:
- 컴플라이언스 게이트 "건너뛰기" 옵션 추가 금지 (R-01 Critical)
- 본인 해설 50자 미만으로 업로드 금지
- 단정적 비난 표현 ("사기", "범죄자", "속이는") 사용 금지
- 선거기간 중 특정 후보 우호 표현 금지 (R-03 Critical)
- 출처 미표시 업로드 금지

**반드시 할 것**:
- 업로드 전 팩트 URL 2개 이상 확인 (R-02 Critical)
- 월 1회 편향 리포트 확인
- 선거 D-180/D-120 앞서 룰 재확인
- 문제 영상 접수 시 즉시 비공개 (삭제 금지, 증거 보존)

---

## 성공 검증

운영 12개월 후 다음 체크리스트 확인:

- [ ] 법적 이슈 0건 (SC-010)
- [ ] YPP 승인 완료 (SC-009)
- [ ] 월 30개 업로드 지속
- [ ] 여성·청년 카테고리 40%↑ (SC-012)
- [ ] 특정 인물 쇼츠 비중 30% 이하 (SC-011)

5개 중 3개 이상 달성 시 프로젝트 성공.
