# Contract: Remotion V3 — Composition Props

V3 격리 Remotion 패키지 (`src/video/remotion_v3/`)의 props 스키마.

## Composition 등록

```tsx
// src/video/remotion_v3/src/Root.tsx
<Composition
  id="JpoliticsShorts"
  component={JpoliticsComposition}
  durationInFrames={(durationSec * 30) | 0}  // 30fps
  fps={30}
  width={1080}
  height={1920}
  defaultProps={defaultProps}
/>
```

## Props 스키마 (JpoliticsComposition)

Python → TypeScript 경계에서 snake_case → camelCase 자동 변환 (`renderer.py`의 `_convert_to_camel_case()`).

```typescript
type JpoliticsCompositionProps = {
  metadata: {
    title: string;
    sourceType: "jpolitics_youtube" | "jpolitics_topic";
    sourceUrl?: string;
    sourceLabel?: string;       // 하단 출처 라벨 (FR-019)
    durationSec: number;
    createdAt: string;
    topic?: string;
  };
  scenes: JpoliticsSceneProps[];
  audio: {
    ttsVoice: "ko-KR-InJoonNeural";
    ttsRate: "+22%";
    ttsScript: string;
    audioPath: string;          // public/audio.mp3 상대경로
    sceneTimings: Array<{
      sceneId: number;
      startMs: number;
      endMs: number;
    }>;
  };
  background: {
    type: "gradient";
    colors: [string, string];
  };
  headlinePin: string;          // 영상 전체 고정 (FR-017)
};

type JpoliticsSceneProps = {
  id: number;
  timestamp: number;            // 초
  duration: number;             // 초
  type: "title" | "body" | "comment";
  text: string;
  voiceText: string;
  visualLayout: "normal" | "vs_card" | "grid_2x2" | "data_card";
  subtitleColor: "white" | "yellow" | "red" | "blue";
  subtitleEmphasis: boolean;
  comparisonCards?: PoliticianCardProps[];
  dataEmphasisColor: "red" | "yellow" | "blue";
  clipPath?: string;            // public/clip_{id}.mp4 상대경로
};

type PoliticianCardProps = {
  name: string;
  party: string;
  partyColor: string;           // 헥스 #RRGGBB
  photoPath?: string;           // public/cards/{name}.jpg 상대경로
  dataLabel?: string;
  dataValue?: string;
};
```

## 컴포넌트 라우팅 규칙

`JpoliticsComposition.tsx`는 씬별로 `visualLayout`을 보고 컴포넌트를 분기:

| `visualLayout` | 컴포넌트 | 필수 props | 설명 |
|---|---|---|---|
| `"normal"` | `<TalkingHeadScene />` | `text`, `clipPath?` | 원본 클립 풀스크린, 클립 없으면 그라데이션 |
| `"vs_card"` | `<VsCardScene />` | `comparisonCards` (2개) | 좌·우 분할, 정당 컬러 배경 |
| `"grid_2x2"` | `<ComparisonGridScene />` | `comparisonCards` (3~4개) | 2×2 그리드 + 데이터 빨강 강조 |
| `"data_card"` | `<DataCardScene />` | `comparisonCards` (1개, `dataValue` 필수) | 단일 인물 + 큰 데이터 |

## 공통 오버레이 (모든 씬)

1. `<PinnedHeadline />` — 영상 상단 노란 박스 (FR-017), `headlinePin` 사용
2. `<SubtitleBlock />` — 하단 자막 박스 (FR-018), 씬별 `text`/`subtitleColor`/`subtitleEmphasis`
3. `<LetterboxFrame />` — 하단 letterbox 영역, `sourceLabel` 표시 (FR-019)
4. `<Background />` — 그라데이션 배경

## 씬 전환 — 하드 컷 락인 (FR-035)

- `<Sequence>` 직접 연결, **fade/dissolve/slide 미사용**.
- 첫 씬: `from={0}` 위치 그대로, fade-in 없음.
- 마지막 씬 → Outro: 컷 전환.
- 어떤 씬도 `<Sequence>` 사이에 그라데이션 인터스티셜 컴포넌트 삽입 금지.
- `interpolate(frame, [0, 5], [0, 1])` 같은 entrance opacity 애니메이션 미사용.
- 컴포넌트 내부 마이크로 애니메이션은 허용 (예: VsCardScene 입장 slide, DataCardScene spring) — 단 씬 경계에서 다음 씬을 가리지 않을 것.

## 오디오 — 효과음 영구 0 락인 (FR-034)

- `<Audio src={staticFile(audio.audioPath)} />` 단일 트랙만 사용 (TTS 합성 결과 1개).
- BGM `<Audio>` 추가 금지.
- 효과음 `<Audio>` 추가 금지.
- 원본 클립의 native audio는 `<OffthreadVideo muted />` 로 음소거 강제 (TTS와 충돌 방지).

## PinnedHeadline 시각 사양

```css
position: absolute;
top: 80px;
left: 60px;
right: 60px;
height: 240px;
background: #FFD700;          /* 노랑 */
border: 4px solid #000;
border-radius: 12px;
font-family: "Noto Sans KR Black";
font-size: 72px;
font-weight: 900;
color: #000;
text-align: center;
padding: 30px 20px;
line-height: 1.2;
```

## SubtitleBlock 시각 사양 (V2 패턴 복제)

- 위치: 하단 320px 영역
- 배경: 흰 라이트박스 (#FFFFFF, opacity 0.95)
- 글자: 56px Noto Sans KR Bold, 검정 (#000), `subtitleColor`로 오버라이드
- `subtitleEmphasis = true` 시 폰트 1.4x, 빨강(#E61E2B) 강제
- V2의 `subtitle_split.py` 알고리즘으로 분할된 자막 사용

## VsCardScene 시각 사양

- 좌측 (0~540px) / 우측 (540~1080px) 분할
- 각 영역 배경: `partyColor` 그라데이션
- 인물 사진: 중앙, 600x600 둥근 모서리
- 정당명: 사진 하단, 흰색 36px
- 이름: 정당명 하단, 흰색 96px (대형)

## ComparisonGridScene 시각 사양

- 2×2 그리드, 각 셀 540×960px
- 인물 사진: 셀 중앙, 400×400 둥근 모서리
- 이름: 사진 하단, 검정 48px
- 데이터: 이름 하단, `dataEmphasisColor` (기본 빨강) 84px Bold
- 데이터 페이드 인: 씬 시작 후 0.5초 지연, 0.3초 fade

## DataCardScene 시각 사양

- 인물 사진: 화면 상단, 720×720 둥근 모서리
- 이름: 사진 하단, 검정 64px
- 데이터: 화면 중앙 하단, `dataEmphasisColor` 144px Black
- 데이터 레이블: 데이터 위, 검정 40px

## 자산 경로 규약

V3 렌더러는 모든 자산을 `src/video/remotion_v3/public/` 아래로 복사:

```
src/video/remotion_v3/public/
├── audio.mp3                  # TTS 합성 결과
├── clips/
│   └── clip_{sceneId}.mp4     # 씬별 원본 클립
└── cards/
    └── {name}.jpg             # 인물 카드 사진
```

Remotion props에는 `public/` 접두사 없이 상대 경로 전달 (예: `"audio.mp3"`).

## 렌더 명령 (Python 호출)

```bash
cd src/video/remotion_v3 && \
  npx remotion render src/index.ts JpoliticsShorts \
    /absolute/path/to/data/jpolitics/{ts}_{slug}/video.mp4 \
    --props='<JSON props string>' \
    --codec=h264 \
    --crf=22
```

## TypeScript 컴파일 검증

```bash
cd src/video/remotion_v3 && npx tsc --noEmit
```

→ 에러 0 통과 시 props 스키마 호환성 보장.

## 격리 보증

- `src/video/remotion/` (V1/V2)는 무관 — 별도 `node_modules`, 별도 Composition.
- 동시 렌더 시 자산 디렉토리 분리로 파일명 충돌 없음.
