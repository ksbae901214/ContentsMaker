# ContentsMaker

블라인드 인기글을 만화 스타일 YouTube Shorts 영상으로 자동 변환하는 파이프라인.

## 파이프라인 흐름

```
스크린샷/텍스트 입력
       ↓
  [1] 텍스트 추출 (Claude Code OCR)
       ↓
  [2] AI 분석 → ShortsScript JSON (감정 감지, 씬 분할, TTS 대본)
       ↓
  [3] 만화 이미지 생성 (GPT Image, 웹툰 스타일)
       ↓
  [4] 음성 생성 (edge-tts, 젊은 여성 목소리, 1.2배속)
       ↓
  [5] 영상 렌더링 (Remotion, 1080x1920, 1.2배속)
       ↓
  최종 MP4 (9:16 세로, 30-50초)
```

## 기술 스택

| 모듈 | 기술 | 비용 |
|------|------|------|
| OCR/분석 | Claude Code (Sonnet 4.6) | $0 (CLI 포함) |
| 이미지 | GPT Image (`gpt-image-1`, low quality) | ~$0.005/장 |
| TTS | edge-tts (Microsoft Edge) | $0 |
| 영상 | Remotion (React, 로컬 렌더링) | $0 |
| 웹 UI | Next.js 16 | $0 |

**영상 1개당 비용**: ~$0.03 (이미지 6장 기준)

## 설치

```bash
# Python 의존성
pip install -r requirements.txt

# Node.js 의존성 (루트 + Remotion)
npm install
cd src/video/remotion && npm install && cd ../../..

# 환경변수
cp .env.example .env.local
# .env.local에 OPENAI_API_KEY 설정
```

## 사용법

### 웹 UI (권장)

```bash
npm run dev
# http://localhost:3000 접속
```

스크린샷 드래그 앤 드롭 또는 직접 텍스트 입력으로 영상 생성.

### CLI

```bash
# 스크린샷 → 영상 (풀 파이프라인)
python3 -m src.main image screenshot1.png screenshot2.png

# 수동 입력 → 영상
python3 -m src.main manual --file data/raw/sample.json

# 개별 단계 실행
python3 -m src.main analyze --file data/raw/sample.json
python3 -m src.main tts --file data/scripts/script.json
python3 -m src.main render --script data/scripts/script.json --audio data/audio/voice.mp3

# 전체 파이프라인 (raw JSON → 영상)
python3 -m src.main pipeline --file data/raw/sample.json

# 유명인 소개 쇼츠 (Phase 9, 학습 목적 전용)
python3 -m src.main celebrity "손흥민"                # 전체 파이프라인
python3 -m src.main celebrity "세종대왕" --no-video   # 정지 이미지만
python3 -m src.main celebrity "유재석" --no-images    # 그라데이션만
```

## 유명인 소개 쇼츠 (Phase 9)

인물 이름 1개 → 나무위키 정보 수집 → Claude 대본 생성 → 네이버 이미지 검색 → Freepik image-to-video → MP4.

**⚠️ 학습 목적 전용**: 나무위키 CC BY-NC-SA 3.0(비상업) + 네이버 이미지(타 사이트 저작권)로 구성되므로 **공개 업로드 금지**. YouTube/TikTok 업로드 UI는 이 탭에서 비활성화됩니다.

### 사전 설정

```bash
# 1. 네이버 검색 API 키 발급 (무료, 일 25,000 쿼리)
#    https://developers.naver.com/apps/ → 애플리케이션 등록 → 검색
echo 'NAVER_CLIENT_ID=xxx' >> .env.local
echo 'NAVER_CLIENT_SECRET=yyy' >> .env.local

# 2. Freepik 로그인 (영상 모드 사용 시)
python3 -m src.main freepik_login
```

### 실행

- **CLI**: `python3 -m src.main celebrity "이름"`
- **웹 UI**: http://localhost:3000 → "👤 유명인" 탭

### 파일 배치

- 스크립트: `data/scripts/{YYYYMMDD_HHMMSS}_celebrity_{name}.json`
- 이미지: `data/images/celebrity/{YYYYMMDD_HHMMSS}_{name}/*.jpg` + `metadata.json`
- 영상 클립: `data/videos/celebrity/{YYYYMMDD_HHMMSS}_{name}/scene_*.mp4`
- 최종 MP4: `data/outputs/{YYYYMMDD_HHMMSS}_{name}.mp4`

영상 마지막 씬에는 자동으로 "출처: 나무위키" 문구가 포함됩니다.

## 프로젝트 구조

```
ContentsMaker/
├── app/                          # Next.js 웹 UI
│   ├── page.tsx                  #   메인 페이지 (업로드 + 입력)
│   └── api/
│       ├── generate/route.ts     #   영상 생성 API (SSE 스트리밍)
│       ├── download/route.ts     #   영상 다운로드
│       └── stats/route.ts        #   사용 통계
│
├── src/                          # Python 백엔드
│   ├── main.py                   #   CLI 진입점
│   ├── config/
│   │   └── settings.py           #   전역 설정
│   ├── scraper/
│   │   ├── image_extractor.py    #   스크린샷 OCR (Claude Code)
│   │   ├── manual_input.py       #   수동 텍스트 입력
│   │   ├── models.py             #   BlindPost 데이터 모델
│   │   └── validator.py          #   입력 검증
│   ├── analyzer/
│   │   ├── claude_analyzer.py    #   AI 분석 (Claude Code)
│   │   ├── script_models.py      #   ShortsScript 데이터 모델
│   │   └── prompt_template.py    #   분석 프롬프트
│   ├── illustrator/
│   │   ├── image_generator.py    #   GPT Image API 호출
│   │   ├── prompt_builder.py     #   이미지 프롬프트 생성
│   │   └── reference_manager.py  #   스타일 레퍼런스 관리
│   ├── tts/
│   │   ├── edge_tts_generator.py #   음성 생성 (edge-tts)
│   │   └── voice_config.py       #   감정별 음성 설정
│   └── video/
│       ├── renderer.py           #   Remotion CLI 래퍼
│       └── remotion/             #   Remotion React 프로젝트
│           └── src/
│               ├── Root.tsx
│               ├── ShortsComposition.tsx
│               ├── types.ts
│               └── components/
│                   ├── SceneText.tsx
│                   └── Background.tsx
│
├── data/                         # 데이터 디렉토리
│   ├── raw/                      #   추출된 원본 JSON
│   ├── scripts/                  #   분석 결과 스크립트 JSON
│   ├── audio/                    #   생성된 음성 MP3
│   ├── images/                   #   생성된 만화 이미지
│   ├── references/               #   스타일 레퍼런스 이미지
│   │   ├── characters/           #     캐릭터 시트
│   │   └── backgrounds/          #     배경 이미지
│   └── outputs/                  #   최종 영상 MP4
│
└── tests/                        # 테스트
```

## 핵심 데이터 모델

### ShortsScript (script.json)

```json
{
  "metadata": {
    "title": "영상 제목",
    "emotion_type": "funny|touching|angry|relatable",
    "duration": 45
  },
  "scenes": [
    {
      "id": 1,
      "timestamp": 0,
      "duration": 5,
      "type": "title|body|comment",
      "text": "화면 표시 텍스트",
      "voice_text": "TTS 읽을 텍스트",
      "emphasis": "high|medium|low"
    }
  ],
  "audio": {
    "tts_script": "전체 TTS 대본",
    "voice": "ko-KR-SunHiNeural",
    "rate": "+20%",
    "pitch": "+0Hz"
  },
  "background": {
    "type": "gradient",
    "colors": ["#4169E1", "#1E90FF", "#87CEEB"]
  }
}
```

## 감정별 설정

| 감정 | 그라데이션 | 설명 |
|------|-----------|------|
| funny | 빨강→주황→노랑 | 밝고 유쾌한 |
| touching | 보라→라벤더→자주 | 따뜻하고 감성적 |
| angry | 크림슨→다크레드 | 강렬하고 드라마틱 |
| relatable | 로열블루→스카이블루 | 편안하고 공감되는 |

모든 감정에서 동일한 TTS 설정: `ko-KR-SunHiNeural` (젊은 여성), `+20%` 속도 (1.2배속).

## 영상 설정

- **해상도**: 1080x1920 (9:16 세로)
- **FPS**: 30
- **속도**: 1.2배속 (TTS + 영상 동기화)
- **텍스트**: 55px 균일 크기, 화면 중앙에서 10% 아래
- **이미지**: 한국 웹툰/소셜툰 스타일, 1024x1536 (2:3)

## 레퍼런스 이미지 (선택)

`data/references/`에 이미지를 넣으면 캐릭터/배경 스타일 일관성이 향상됩니다:

| 경로 | 용도 |
|------|------|
| `characters/fullbody.png` | 남녀 전신 비율/스타일 |
| `characters/female_expressions.png` | 여성 캐릭터 표정 |
| `characters/male_expressions.png` | 남성 캐릭터 표정 |
| `backgrounds/apartment.jpeg` | 한국 아파트 거실 |
| `backgrounds/office.jpeg` | 한국 회사 사무실 |
| `backgrounds/bar.jpeg` | 카페/바 |

## 배포

Cloudflare Tunnel로 로컬 서버를 도메인에 연결:

```bash
# 터널 실행
cloudflared tunnel --config ~/.cloudflared/config-contentsmaker.yml run contentsmaker
```

## 개발 이력

| Phase | 브랜치 | 내용 |
|-------|--------|------|
| 1 | `001-foundation-scraper` | 프로젝트 초기화, 수동 입력 스크래퍼, 데이터 모델 |
| 2 | `002-analyzer-tts` | Claude Code AI 분석, edge-tts 음성 생성 |
| 3 | `003-video-remotion` | Remotion 영상 렌더링, GPT Image 만화, Next.js 웹 UI |
