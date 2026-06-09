# Quickstart — 정치쇼츠 V3 격리 모드 개발자 가이드

**Date**: 2026-06-05
**Branch**: `010-jpolitics-v3-isolated`

새 디렉토리 생성·테스트·E2E 검증·진입 버튼 추가까지의 개발자 경험 흐름.

## 사전 조건

| 항목 | 명령/값 |
|---|---|
| Python 버전 | `python3 --version` ≥ 3.11 |
| Node.js 버전 | `node --version` ≥ 20 |
| 환경 변수 | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` (이미 설정됨) |
| ffmpeg | `ffmpeg -version` (PATH에서 발견) |
| 브랜치 체크아웃 | `git checkout 010-jpolitics-v3-isolated` |

## 0단계: 샘플 자료 보관

```bash
mkdir -p data/jpolitics_reference
cp /tmp/jpolitics_analysis/sample*.mp4 data/jpolitics_reference/
cp /tmp/jpolitics_analysis/{frame,s2,s3}_*.png data/jpolitics_reference/
```

샘플 3편 키프레임을 lock-in 시각 자료로 보관.

## 1단계: 격리 디렉토리 트리 생성

```bash
mkdir -p src/jpolitics/{models,scraper,analyzer,tts,video}
mkdir -p src/video/remotion_v3/{src/components,public/clips,public/cards}
mkdir -p app/jpolitics/{components,api/plans,api/render,api/photo}
mkdir -p tests/jpolitics
mkdir -p data/jpolitics data/politician_cards/photos

# __init__.py 골격
touch src/jpolitics/__init__.py
touch src/jpolitics/models/__init__.py
touch src/jpolitics/scraper/__init__.py
touch src/jpolitics/analyzer/__init__.py
touch src/jpolitics/tts/__init__.py
touch src/jpolitics/video/__init__.py
touch tests/jpolitics/__init__.py
```

## 2단계: Remotion V3 패키지 부트스트랩

```bash
cd src/video/remotion_v3
npm init -y
npm install remotion@^4 @remotion/cli@^4 react@^19 react-dom@^19
npm install -D typescript@^5 @types/react@^19 @types/react-dom@^19
cat > tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
EOF
cd ../../..
```

## 3단계: TDD 사이클 — 모델 → 카드 → planner

```bash
# 모델 테스트 작성 (RED)
python3 -m pytest tests/jpolitics/test_models.py -v
# → 실패: 모듈 없음

# 모델 구현 (GREEN)
# src/jpolitics/models/script.py 작성
python3 -m pytest tests/jpolitics/test_models.py -v
# → 통과

# 인물 카드 페치 (RED → GREEN)
python3 -m pytest tests/jpolitics/test_politician_card.py -v

# Planner (RED → GREEN)
python3 -m pytest tests/jpolitics/test_planner.py -v

# TTS 락인 (RED → GREEN, 락인 가드 어설션 포함)
python3 -m pytest tests/jpolitics/test_tts_voice_lockin.py -v
```

## 4단계: Remotion 컴포넌트 개발

```bash
cd src/video/remotion_v3
npx remotion preview src/index.ts
# 브라우저에서 4종 레이아웃 미리보기
# - JpoliticsShorts (defaultProps로 talking_head 샘플)

# 컴포넌트별 props 변경하며 시각 검증
# - PinnedHeadline: 헤드라인 텍스트 길이 변경
# - VsCardScene: 정당 컬러 변경
# - ComparisonGridScene: 카드 1~4개 변동
# - DataCardScene: data_value 강조 색 변경

npx tsc --noEmit
# → 에러 0
cd ../../..
```

## 5단계: Python ↔ Remotion 통합

```bash
# Python renderer wrapper 테스트
python3 -m pytest tests/jpolitics/test_renderer.py -v

# E2E (fixture 사용)
python3 -m pytest tests/jpolitics/test_e2e.py -v
```

## 6단계: CLI 동작 검증

```bash
# YouTube URL 모드 (실제 호출, 무료 한도 내)
python3 -m src.jpolitics.main \
  https://www.youtube.com/watch?v=nPOJYSXdICI \
  --select-plan 1

# 주제 모드
python3 -m src.jpolitics.main \
  --source-type topic \
  --topic "양향자 추미애 경기도지사 대결" \
  --select-plan 2

# 결과
ls data/jpolitics/*/video.mp4
ls data/jpolitics/*/summary.txt
```

## 7단계: Next.js 페이지 동작 검증

```bash
npm run dev
# 별도 터미널
open http://localhost:3000/jpolitics

# 폼 입력 → /api/jpolitics/plans 호출 → 3 plans 노출
# 선택 → /api/jpolitics/render 호출 → 영상 생성
```

## 8단계: 진입 버튼 추가 (유일한 기존 파일 수정)

`app/page.tsx`의 헤더 영역(현재 NATV 클립 옆 또는 헤더 영역)에 다음 추가:

```tsx
import { useRouter } from "next/navigation";

// 컴포넌트 본문
const router = useRouter();

// 헤더 JSX에 추가
<button
  onClick={() => router.push("/jpolitics")}
  className="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold shadow"
>
  🟡 정치 V3
</button>
```

## 9단계: 회귀 가드 검증

```bash
# 기존 297+ 테스트 무회귀
python3 -m pytest tests/ -v --ignore=tests/jpolitics 2>&1 | tail -5
# → 297+ passed

# 신규 V3 테스트 50+ 통과
python3 -m pytest tests/jpolitics -v 2>&1 | tail -5
# → 50+ passed

# Next.js 빌드
npm run build
# → success

# Remotion V3 타입 체크
cd src/video/remotion_v3 && npx tsc --noEmit && cd ../../..
# → 에러 0

# Remotion V1/V2 타입 체크 (무회귀 확인)
cd src/video/remotion && npx tsc --noEmit && cd ../../..
# → 에러 0
```

## 10단계: 4종 레이아웃 샘플 영상 생성 + lock-in

```bash
# Talking Head 샘플
python3 -m src.jpolitics.main \
  https://www.youtube.com/watch?v=nPOJYSXdICI \
  --select-plan 1
# → data/jpolitics/*_조국_사퇴/video.mp4

# VS 카드 샘플
python3 -m src.jpolitics.main \
  --source-type topic --topic "양향자 vs 추미애 경기도지사 대결" \
  --select-plan 1

# 2x2 Grid 샘플
python3 -m src.jpolitics.main \
  --source-type topic --topic "평택을 후보 4명 비교" \
  --select-plan 1

# Data Card 샘플
python3 -m src.jpolitics.main \
  --source-type topic --topic "조국 재산 56억 5년간 0원 강조" \
  --select-plan 1
```

→ 사용자 시각 검수 후 lock-in 메모리 기록.

## 디버깅 팁

| 증상 | 진단/대응 |
|---|---|
| `npx remotion render` 실패 | `cd src/video/remotion_v3 && npm install` 재실행 |
| 인물 사진 못 가져옴 | `NAVER_CLIENT_ID` 환경변수 + `data/politician_cards/photos/` 권한 확인 |
| Stage A 분류가 항상 talking_head | Stage A 프롬프트의 4종 예시 강화 |
| 자막 글자 깨짐 | `Noto Sans KR Black` 폰트가 Remotion V3 `public/`에 복사됐는지 확인 |
| TTS 보이스 변경 시도 | 의도된 동작 — 테스트가 실패해야 정상 (SC-008 lock-in 가드) |
| V1 영상 바이트 변경 감지 | 즉시 PR 머지 차단 — V3 import가 V1 모듈을 mutating 호출하는지 검토 |

## 산출물 (Phase 10 완료 시)

```
data/jpolitics/
  ├── 20260605_104530_조국_사퇴/video.mp4 (talking_head, ~50s)
  ├── 20260605_111245_양향자_추미애/video.mp4 (vs_card, ~50s)
  ├── 20260605_113500_평택을_4명/video.mp4 (grid_2x2, ~55s)
  └── 20260605_114800_조국_재산/video.mp4 (data_card, ~45s)
```

## 다음 단계 → `/speckit.tasks`

`tasks.md` 생성 (Phase 2). Phase 0/1 산출물(plan.md / research.md / data-model.md / contracts/)을 기반으로 구현 태스크 분해.
