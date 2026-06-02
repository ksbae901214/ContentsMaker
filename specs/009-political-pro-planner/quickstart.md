# Quickstart: Political Shorts Planner

**Feature**: 009-political-pro-planner
**Audience**: 개발자 + 운영자 (기능 빠른 검증용)

---

## 사전 준비 (1회만)

```bash
# 1. 환경변수: Gemini TTS API 키 (https://aistudio.google.com/app/apikey)
export GEMINI_API_KEY='your-key-here'

# 2. Python/Node 의존성 (이미 설치돼 있으면 스킵)
pip install -r requirements.txt
npm install
cd src/video/remotion && npm install && cd ../../..

# 3. yt-dlp 최신 버전 (정치 영상 다운로드용)
pip install -U yt-dlp
```

---

## 5분 데모 — 웹 UI 경로

```bash
# 1. dev 서버 시작
npm run dev
# → http://localhost:3000 접속
```

브라우저 흐름:
1. 상단 탭 중 **"정치 기획"** 클릭
2. YouTube URL 입력란에 정치 영상 붙여넣기 (예: 김정치입니다 채널 영상)
3. **[3 기획안 생성]** 버튼 클릭 → 약 60~90초 대기
4. 3개 카드 비교 → 한 카드의 **[이 기획안으로 진행]** 클릭
5. 스크립트 검수 화면에서 씬별 텍스트 확인/수정
6. **[영상 생성]** 클릭 → 약 2분 대기
7. 결과 화면에서 9:16 MP4 다운로드 + "게시 전 검수 필수" 경고 확인

---

## 5분 데모 — CLI 경로

### A. 기획안만 미리 보기

```bash
python3 -m src.main political-pro "https://youtu.be/abc123" --plans-only
```

→ stdout에 3개 plan JSON 출력. 디버깅·반복 테스트에 유용.

### B. 인터랙티브 모드 (선택 입력)

```bash
python3 -m src.main political-pro "https://youtu.be/abc123" --interactive
```

→ 3개 plan 표시 후 `(1/2/3):` 프롬프트 → 선택 → 영상 생성.

### C. 비인터랙티브 자동 실행 (배치)

```bash
python3 -m src.main political-pro "https://youtu.be/abc123" --plan-idx 0
```

→ Plan 1로 자동 진행, exit 0 시 `data/outputs/...mp4` 출력.

---

## 결과 검증 체크리스트

생성된 영상 1편으로 다음을 확인하면 본 기능이 정상 작동:

- [ ] 파일 길이 30~60초 (`ffprobe -v error -show_entries format=duration ...mp4`)
- [ ] 해상도 1080x1920 (9:16) 또는 720x1280 (개발 단계)
- [ ] 첫 1~3초에 후킹 문구가 화면에 표시됨
- [ ] 마지막 씬에 CTA 문구가 표시됨
- [ ] 음성이 Charon(영국식 RP 아나운서 톤)으로 들림
- [ ] 화면에 원본 YouTube 영상의 발언 구간이 letterbox 9:16으로 렌더링됨
- [ ] 결과 화면에 "출력은 자동 생성 결과 — 게시 전 검수 필요" 경고 노출
- [ ] YouTube/TikTok 자동 업로드 토글이 **노출되지 않거나 비활성** (FR-020)

---

## 테스트 실행

```bash
# 1. 본 기능 관련 단위 테스트만
python3 -m pytest tests/test_political_plan_models.py tests/test_political_planner.py tests/test_gemini_tts_style_prompt.py -v

# 2. 전체 회귀 (Constitution 원칙 VIII Full Test Gate)
python3 -m pytest tests/ -v

# 3. Next.js 빌드
npm run build
```

---

## 운영자 중립성 검토 가이드 (SC-006)

본 기능 배포 전 또는 정기적으로(주 1회 권장) 다음을 수행:

1. 정치 영상 3개를 임의 선정 (서로 다른 정당·이슈)
2. 각 영상에 `--plans-only`로 3 기획안 생성 → 총 9개 plan 수집
3. 각 plan의 **hook / narrations / cta**를 직접 읽고 다음 기준으로 평가:
   - [ ] 특정 정당명이 비판적·찬양적 어조로 사용되지 않음
   - [ ] 특정 정치인을 "잘했다 / 못했다" 식으로 평가하지 않음
   - [ ] 영상에 없는 사실이 추가되지 않음(예: "이후 ○○가 사임했다" 등 외부 정보)
   - [ ] 추측·루머 표현 부재 ("…일지도 모른다", "…라는 소문")
4. **9개 plan 중 위반이 1건이라도 있으면**: `src/analyzer/political_planner_prompt.py`의 절대 준수 항목 강화 + 재테스트
5. 결과를 `data/political_pro/neutrality_audit_{YYYYMMDD}.md`에 기록 (선택)

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-------------|
| `transcript_unavailable` 오류 | 영상에 자막 없음 + STT 실패. 다른 영상 시도. `yt-dlp -U` 업데이트 권장. |
| `claude_plan_generation_failed` | Claude CLI 일시 오류. 1회 재시도 후 실패 시 잠시 후 재시도(`86476e5` 패턴). |
| `tts_failed` (key 없음) | `echo $GEMINI_API_KEY` 확인. 빈값이면 export 후 dev 서버 재시작. |
| Charon 한국어 발음 부자연스러움 | `style_prompt` 텍스트를 한글로 변경 시도 (research.md R2 참조). |
| 90초 초과 | 영상이 30분 초과인지 확인. transcript truncation 임계 조정 가능 (research.md R5). |

---

## 다음 단계

- 실제 영상 1편으로 위 검증 체크리스트 통과 → PR 생성
- 사용자 메모리(`feedback_test_video.md`)에 따라 작업 완료 시 **GPT 이미지 제외 테스트 영상** 자동 생성 필수
- `/speckit.tasks` 로 구현 태스크 분해 → `/speckit.implement` 로 진행
