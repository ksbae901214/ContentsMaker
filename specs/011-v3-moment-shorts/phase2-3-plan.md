# 정치쇼츠 V3 "모먼트 직캠" — Phase 2·3 구현 계획

> Feature 027 (prompt_plan.md) / specs/011-v3-moment-shorts
> 작성: 2026-06-11 · 상태: Phase 0~1 완료, Phase 2~3 미착수
> 새 세션에서 이 문서만 보고 이어서 작업할 수 있도록 작성됨.

---

## 0. 배경 요약 (이미 완료된 것)

### 포맷 근거 — 벤치마크 실측 (2026-06-11)
조회수 상위 정치쇼츠 4편(겸손은힘들다 24만~280만뷰, YTN 26만뷰)을 다운로드해 키프레임·자막 분석한 결과:

| 공식 | 근거 |
|------|------|
| **풀블리드** — 검은 여백 0, 얼굴이 화면 60%+ | 4편 전부. 국회직캠(구독 207, 중앙값 1,200뷰)은 인셋 40%로 최대 격차 |
| **원본 육성** — TTS 내레이션 없음 | 웃음·언성·말투가 콘텐츠 그 자체 |
| **질문형 떡밥 훅** — 첫 1~2초 거대 타이포 카드, 답은 숨김 | "최강욱 의원은 **왜 또** 압수수색을 한 거예요?" (49.1만뷰), 키워드 파랑/빨강 강조 |
| **감정 모먼트 소재** — 정보 요약 ❌ | YTN: 같은 국회 클립 장르인데 "웃음 터진 순간"만으로 26만뷰 |
| **실시간 발언 자막** — 흰 글자+검은 테두리 1~2줄 | 겸손은힘들다 공통 |
| 길이 34~58초 | 짧을 필요 없음, 모먼트가 강하면 끝까지 봄 |

### Phase 0~1 완료 상태
- 구 V3(@김정치입니다 포맷) 6,834줄 삭제 완료 (git 히스토리 복구 가능)
- `app/page.tsx` 진입 버튼 주석 처리됨 (Phase 4에서 복원)
- 신규 `src/jpolitics/` 구축:
  - `constants.py` — `JPOLITICS_DATA_DIR`, `MOMENT_KINDS`, `MIN/MAX_MOMENT_SECONDS`(5~60s), `DEFAULT_TOP_N`
  - `models/moment.py` — `Moment`(frozen: start_sec/end_sec/kind/speaker/summary/hook_question/keywords/confidence), `MomentDetectionResult`(+`top(n)`, `save()`)
  - `analyzer/moment_detector.py` — `detect_moments_from_video()`(Gemini Files API 멀티모달, 2회 재시도), `detect_moments_from_transcript()`(폴백), `_parse_moments_json()`
  - `analyzer/prompts.py` — 검출 프롬프트 (질문형 훅 강제)
  - `main.py` — CLI `python3 -m src.jpolitics.main detect <URL> [--top N] [--no-multimodal]`
- E2E 검증: YTN 청문회 영상에서 멀티모달이 웃음 모먼트(22~32s, conf 1.0) 정확 검출
- 산출물: `data/jpolitics/{ts}_{slug}/` 에 원본 영상 + `moments.json`
- 테스트: `tests/jpolitics/` 17개 (전체 1300 passed)

### 격리 원칙 (절대 준수)
- **V1/V2 파일 0 수정** — 기존 코드는 read-only import만 (`# read-only import (격리 boundary)` 주석)
- 재사용 가능: `src.scraper.youtube_downloader`(download_video/extract_clip/parse_vtt_subtitles/transcribe_video_or_fallback), `src.analyzer.gemini_backend.call_gemini`, `src.analyzer.claude_analyzer._call_claude`
- 계승 lock-in: **효과음·BGM 0 / 씬 전환 효과 0 / 출처 라벨 하단 / 자동 업로드 차단(검수 필수)**
- 폐기된 구 lock-in: InJoonNeural TTS(신규는 원본 음성), 4종 레이아웃(신규는 풀블리드 단일), 3단계 영상추출 분업

---

## Phase 2: 클립 가공 (모먼트 → 9:16 풀블리드 클립)

### 목표
`moments.json`의 모먼트 1개를 선택하면, 원본 영상에서 해당 구간을 잘라 **9:16 풀블리드(1080×1920) + 원본 음성 그대로**인 클립 MP4를 만든다.

### 신규 모듈

#### `src/jpolitics/video/clip_maker.py`
```
make_moment_clip(
    source_video: Path,      # 다운로드된 원본 (16:9 가정, 9:16/기타도 처리)
    moment: Moment,
    output_path: Path,
    *,
    pad_before: float = 0.5,   # 모먼트 앞 여유 (말 잘림 방지)
    pad_after: float = 0.5,
    crop_x: float = 0.5,       # 가로 크롭 중심 0.0(왼쪽)~1.0(오른쪽), 기본 센터
) -> ClipResult
```

구현 규칙:
1. **컷**: `ffmpeg -ss {start-pad_before} -to {end+pad_after}` — 재인코딩 컷 (키프레임 정확도 우선, copy 모드 금지)
2. **크롭**: 16:9(1920×1080) → 9:16 풀블리드
   - `crop=ih*9/16:ih:(iw-ih*9/16)*{crop_x}:0` 후 `scale=1080:1920`
   - 입력이 이미 9:16이면 크롭 생략하고 scale만
   - 입력이 4:3 등 기타 비율이면 동일 공식으로 가로 크롭
3. **음성**: 원본 오디오 트랙 그대로 (`-c:a aac -b:a 192k`). TTS 없음. BGM·효과음 절대 추가 금지 (lock-in)
4. **출력**: H.264 yuv420p 1080×1920 30fps (`-r 30` — Remotion 합성 호환)
5. 클립 길이 검증: 5~61초 벗어나면 에러

#### `ClipResult` (frozen dataclass, `models/clip.py`)
```
source_video: str / clip_path: str / moment: Moment
width: int / height: int / fps: float / duration_sec: float
crop_x: float
to_dict / from_dict / save  — work_dir/clip_{n}.json 으로 저장
```

#### 자막 타이밍 추출 — `src/jpolitics/video/captions.py`
실시간 발언 자막용 cue 목록을 만든다 (Phase 3 Remotion 입력):
```
build_caption_cues(
    work_dir: Path,           # {ts}_{slug} — vtt가 이미 있으면 재사용
    source_url: str,
    video_path: Path,
    moment: Moment,
    pad_before: float,
) -> list[CaptionCue]         # 클립 기준 상대 시간으로 변환된 cue
```
1. 1순위: 기존 VTT (`youtube_downloader.download_subtitles` + `parse_vtt_subtitles` read-only 재사용)
2. 폴백: `transcribe_video_or_fallback` (Gemini→Whisper)
3. 모먼트 구간과 겹치는 cue만 골라 `start/end -= (moment.start_sec - pad_before)` 로 상대화
4. cue당 1~2줄(공백 포함 ~20자 단위 분할), 중복 텍스트 병합 (YouTube auto-vtt의 누적 중복 제거 — `/tmp/bench` 분석 시 확인된 패턴)

`CaptionCue` (frozen): `start_sec / end_sec / text`

### CLI 확장 (`src/jpolitics/main.py`)
```
python3 -m src.jpolitics.main cut <work_dir> --moment 1 [--crop-x 0.5] [--pad 0.5]
```
- `<work_dir>`: detect가 만든 `data/jpolitics/{ts}_{slug}/` 경로
- `moments.json` 로드 → `top()` 순서 기준 n번째 선택 → `clip_{n}.mp4` + `clip_{n}.json` + `captions_{n}.json` 생성
- 출력: 클립 경로 + 길이 + 다음 단계 안내

### 테스트 (TDD — 테스트 먼저)
`tests/jpolitics/test_clip_maker.py`:
- ffmpeg로 만든 5초 합성 테스트 영상(1920×1080 testsrc + sine 오디오) fixture
- 컷 결과: 길이 ±0.3s, 해상도 1080×1920, 오디오 트랙 존재(ffprobe 검증)
- crop_x=0.0 / 1.0 경계값에서 에러 없이 생성
- 모먼트가 영상 길이를 벗어나면 클램프
`tests/jpolitics/test_captions.py`:
- 가짜 VTT/세그먼트 → 모먼트 구간 필터 + 상대화 + 중복 병합 검증 (LLM·네트워크 mock)

### 완료 기준 (Phase 2)
- [ ] 단위 테스트 전부 통과 + 기존 전체 회귀 무손상
- [ ] 실측 E2E: Phase 1에서 검출한 YTN 모먼트(`data/jpolitics/20260611_140405_*`, 웃음 22~32s)로 `cut` 실행 → 1080×1920 클립 생성, 원본 음성 유지 확인 (ffprobe + 키프레임 육안)

---

## Phase 3: Remotion 컴포지션 (훅 타이포 카드 + 실시간 자막 + 출처)

### 목표
Phase 2 산출물(클립 + 캡션 cue)을 입력으로, 벤치마크 공식의 시각 요소를 얹은 최종 쇼츠 MP4를 렌더한다.

### 신규 Remotion 패키지 — `src/video/remotion_v3/` (구버전 삭제됨, 새로 생성)
독립 npm 패키지 (구 V3와 같은 위치, 내용은 전면 신규):
```
src/video/remotion_v3/
  package.json            # remotion 4.x (기존 src/video/remotion 버전과 맞춤)
  src/Root.tsx            # composition id: "MomentShorts"
  src/MomentComposition.tsx
  src/components/
    HookCard.tsx          # 질문형 타이포 훅 카드
    LiveCaption.tsx       # 실시간 발언 자막
    SourceLabel.tsx       # 출처 라벨 (lock-in 계승)
  src/types.ts            # props 타입 (camelCase)
  public/                 # 렌더 시 클립 복사
```

### 화면 설계 (벤치마크 실측 그대로)

```
┌─────────────────┐ 1080×1920
│  HookCard       │ ← 0~2.0초만 표시. 흰 배경 박스(상단 ~28% 영역),
│  (질문형 떡밥)    │    검정 고딕 볼드 72~84px 2~3줄, keywords는 파랑(#1d4ed8)/빨강(#dc2626)
├─────────────────┤
│                 │
│   클립 영상      │ ← 풀블리드 (OffthreadVideo, 1080×1920 꽉 채움)
│   (원본 음성)    │    HookCard 표시 중에도 영상은 뒤에서 재생 (검은 정지화면 금지)
│                 │
│  LiveCaption    │ ← 하단 ~22% 위치. 흰 글자+검은 테두리(텍스트 스트로크/섀도),
│                 │    1~2줄, cue 타이밍 따라 교체. 배경 박스 없음(겸손 스타일)
│  SourceLabel    │ ← 최하단. "출처: {channel} ({YYYY.MM.DD})" 작은 회색 (lock-in)
└─────────────────┘
```

규칙:
- **전환 효과 0, 효과음·BGM 0** (lock-in 계승) — 오디오는 클립 원본 트랙 1개만
- HookCard는 fade 없이 하드 컷으로 사라짐 (2.0초)
- LiveCaption cue가 없는 구간은 자막 비표시 (억지로 채우지 않음)
- 30fps, durationInFrames = ceil(clip_duration × 30)

### props (`types.ts`, camelCase)
```ts
{
  clipFileName: string,          // public/ 에 복사된 클립
  hookQuestion: string,
  hookKeywords: string[],        // 색 강조 대상
  captions: { startSec: number; endSec: number; text: string }[],
  sourceLabel: string,           // "출처: YTN (2016.12.15)"
  durationSec: number,
}
```

### 렌더러 — `src/jpolitics/video/renderer.py`
```
render_moment_short(
    clip_result: ClipResult,
    captions: list[CaptionCue],
    *,
    channel: str, source_date: str,
    output_path: Path,
) -> Path
```
- 클립을 `remotion_v3/public/`에 복사 → props JSON(snake→camel 변환) → `npx remotion render MomentShorts` subprocess → 출력 이동 → public/ 정리
- 기존 `src/video/renderer.py`(V1/V2)는 절대 수정하지 않고 패턴만 참고

### CLI 확장
```
python3 -m src.jpolitics.main render <work_dir> --moment 1
python3 -m src.jpolitics.main run <URL> --moment auto   # detect→cut→render 일괄 (auto=확신도 1위)
```

### 테스트
- `tests/jpolitics/test_renderer_props.py`: props 변환(snake→camel)·sourceLabel 포맷·durationInFrames 계산 단위 테스트 (subprocess mock)
- Remotion: `npx tsc --noEmit` 0 errors
- `npm run build` (Next.js) 회귀 무손상

### 완료 기준 (Phase 3)
- [ ] 단위 테스트 + tsc + 전체 회귀 통과
- [ ] 실측 E2E: YTN 웃음 모먼트로 최종 쇼츠 1편 렌더 → 키프레임 추출 육안 검수:
  - 0.5초 프레임: 훅 카드 표시 + 키워드 색 강조 + 뒤에 영상 재생 중
  - 5초/15초 프레임: 풀블리드(여백 0) + 자막 흰글자·검은테두리 + 하단 출처
  - ffprobe: 오디오 트랙 1개(원본), 1080×1920, 30fps
- [ ] 완료 시 3줄 요약 + 해시태그 제공 (고정 규칙)

---

## 다음 Phase 미리보기 (참고만)

- **Phase 4**: 질문형 제목 3안 + 해시태그 설명란 분리 + 고정댓글 질문 생성, `/jpolitics` 웹 UI (URL 입력 → 모먼트 카드 선택 → 렌더 → 미리보기), page.tsx 버튼 복원, 자동 업로드 차단 유지
- **Phase 5**: 실전 E2E (국회 원본 영상 1편 → 업로드 가능한 완성본) + 회귀 전체

## 리스크 메모

| 리스크 | 대응 |
|--------|------|
| 센터 크롭 시 화자 잘림 | `--crop-x` 수동 보정 (Phase 2). 얼굴 인식 자동 크롭은 후속 과제 |
| YouTube auto-VTT 중복 누적 텍스트 | captions.py에서 병합 처리 (벤치마크 vtt 분석에서 패턴 확인됨) |
| Gemini 무료 한도 (Files API 처리 flake) | detect에 2회 재시도 구현됨. 한도 소진 시 `--no-multimodal` |
| 모먼트 타임스탬프 부정확 (±수 초) | pad_before/after 기본 0.5s + Phase 4 UI에서 미세조정 슬라이더 검토 |
