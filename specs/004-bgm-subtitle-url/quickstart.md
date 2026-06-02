# Quickstart: BGM + 자막 줄바꿈 + URL 소스 확장

## 사전 준비

### 1. Playwright 설치 (URL 파싱용)

```bash
pip install playwright
playwright install chromium
```

### 2. BGM 파일 배치

`data/bgm/` 폴더에 4개 MP3 파일을 다운로드:

1. Pixabay Music (https://pixabay.com/music/) 접속
2. 감정별 키워드로 검색하여 30초 이상 트랙 다운로드:
   - "happy upbeat" → `data/bgm/funny.mp3`
   - "emotional piano" → `data/bgm/touching.mp3`
   - "tense dramatic" → `data/bgm/angry.mp3`
   - "chill lo-fi" → `data/bgm/relatable.mp3`

### 3. 개발 서버 재시작

```bash
npm run dev
```

## 기능 테스트

### BGM 테스트

```bash
# CLI — BGM ON (기본)
python3 -m src.main image screenshot.png

# CLI — BGM OFF
python3 -m src.main image screenshot.png --no-bgm

# 웹 UI
# 1. localhost:3000 접속
# 2. "배경음악 넣기" 체크박스 확인
# 3. 영상 생성 → MP4에서 BGM 재생 확인
```

### 자막 줄바꿈 테스트

```bash
# 영상 생성 후 script.json 확인
cat data/scripts/*.json | python3 -m json.tool | grep text
# text 필드에 \n이 포함되어 있는지 확인
# highlight_words 필드가 존재하는지 확인
```

### URL 파싱 테스트

```bash
# 디시인사이드
python3 -m src.main url "https://gall.dcinside.com/board/view/?id=..."

# 네이트판
python3 -m src.main url "https://pann.nate.com/talk/..."

# 네이버 카페
python3 -m src.main url "https://cafe.naver.com/..."

# 웹 UI
# 1. localhost:3000 접속
# 2. "URL 입력" 탭 클릭
# 3. URL 붙여넣기 → "영상 생성" 클릭
```

## 검증 체크리스트

- [ ] BGM ON 영상: TTS + BGM 동시 재생됨
- [ ] BGM OFF 영상: TTS만 재생됨
- [ ] 씬 텍스트에 `\n` 줄바꿈 삽입됨
- [ ] 감정별 키워드 하이라이트 색상 적용됨
- [ ] 디시인사이드 URL → 영상 생성 성공
- [ ] 네이트판 URL → 영상 생성 성공
- [ ] 네이버 카페 URL → 영상 생성 성공
- [ ] 지원 안 하는 URL → 에러 메시지 표시
