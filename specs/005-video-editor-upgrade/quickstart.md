# Quickstart: 영상 제작/편집 기능 고도화

## 개발 환경 요구사항

- Python 3.11+
- Node.js 20+
- npm 10+
- Seedance 2.0 API 키 (Phase 2부터 필요)

## 설치

```bash
# 1. 브랜치 전환
git checkout 005-video-editor-upgrade

# 2. Python 의존성
pip install -r requirements.txt

# 3. Node.js 의존성 (루트)
npm install

# 4. Remotion 의존성
cd src/video/remotion && npm install && cd ../../..

# 5. 환경 변수
cp .env.example .env.local
# .env.local에 추가:
# OPENAI_API_KEY=sk-...
# SEEDANCE_API_KEY=... (Phase 2부터)
```

## Phase별 개발 순서

### Phase 1: 편집 고도화
```bash
# 새 패키지 설치 (드래그앤드롭)
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities

# 개발 서버
npm run dev
```

### Phase 2: AI 영상 클립
```bash
# Seedance SDK 설치
pip install seedance-sdk  # 또는 API 직접 호출

# Remotion Player 설치
npm install @remotion/player
```

### Phase 3: 고급 편집
```bash
# 효과음 다운로드 → data/sfx/에 배치
# 프로젝트 디렉토리 생성
mkdir -p data/projects data/sfx
```

### Phase 4: 확장
```bash
# 템플릿 디렉토리
mkdir -p data/templates
```

## 테스트 실행

```bash
# Python 테스트
python3 -m pytest tests/ -v

# TypeScript 타입 체크
cd src/video/remotion && npx tsc --noEmit
```

## 테스트 영상 생성 (이미지 비용 없이)

```bash
# OPENAI_API_KEY를 비우면 이미지 생성 스킵
OPENAI_API_KEY="" python3 -m src.main pipeline --file data/raw/sample.json
```
