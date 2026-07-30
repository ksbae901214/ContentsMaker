# 정치쇼츠 V2 설정 (render_political_v2.py)

주제만 바꿔 재사용하는 정치쇼츠 V2 제작 설정. 표준 구조는
memory `political-shorts-v2-production-structure` 참조.

## 사용법

```bash
# 1) 인물 클립 다운로드 + 검증 프레임 추출
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2.py \
    scripts/political_v2_configs/<name>.json download

#    → data/political_pro/<slug>/_verify/*.png 프레임으로 인물이 맞는지 육안 확인.
#      틀리면 config의 query를 바꿔 download --force 재실행.

# 2) Gemini Charon TTS → 인물별 씬 컷 → Remotion 렌더
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2.py \
    scripts/political_v2_configs/<name>.json render
```

## config.json 스키마

| 키 | 필수 | 설명 |
|----|------|------|
| `slug` | ✅ | 작업 폴더명 → `data/political_pro/<slug>/` |
| `title` | ✅ | 유튜브 훅 제목(상단 배너) |
| `source_channel` / `source_title` / `youtube_url` | | 출처 라벨용 |
| `emotion_type` | | 기본 `angry` (배경 그라데이션) |
| `rate` | | edge-tts 폴백용 낭독 속도(기본 `+0%`) |
| `bg_colors` | | 배경 그라데이션 hex 배열 |
| `fallback_source` | | 인물 클립 없을 때 폴백 소스 키(보통 종합클립) |
| `sources` | ✅ | 인물키 → 소스 스펙 (아래) |
| `scenes` | ✅ | 씬 배열 (아래) |

### sources[key]
- `query`: yt-dlp `ytsearch` 검색어 (인물 무대/기자회견/현장영상 키워드 권장)
- `url`: 특정 영상 지정 시 (query 대신)
- `dur_max` / `dur_min`: 검색 결과 길이 필터(초)
- `search_n`: ytsearch 후보 수(기본 6)
- `verify_frac`: 검증 프레임 추출 위치 비율(0~1)

### scenes[i]
- `type`: `title`(훅) / `body` / `comment`
- `color`: `white`(기본) / `blue`(인용) / `red`(충돌·비판) / `yellow`(훅·강조)
- `emph`: true → 1.4x 볼드 (훅·CTA 권장)
- `source`: sources의 인물키 (이 씬에 나올 인물)
- `frac`: 그 소스 영상에서 클립 시작 위치 비율(같은 소스 여러 씬은 값 다르게 → 프레임 반복 방지)
- `text`: 자막(\n 2줄) / `voice`: 나레이션(TTS) / `hl`: 강조 단어 배열

예시: `josguk_ilbe.json` (조국 '일베 감별법' 편, 검증 완료).

---

# 정치쇼츠 V2.1 확장 (render_political_v2_1.py)

V2 config 와 호환 + 아래 키 추가 (prompt_plan 031). V2 스크립트/설정은 무변경.

```bash
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_1.py \
    scripts/political_v2_configs/<name>.json download   # + 훅 육성 구간 소리 확인
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_1.py \
    scripts/political_v2_configs/<name>.json render     # 렌더 + upload_package.md
```

## V2.1 추가 키

| 키 | 필수 | 설명 |
|----|------|------|
| `yt_title` | 권장 | 유튜브 업로드 제목. "[악역]-[응징]-[주인공]" 15~30자, 실명 1~2개 (lint 경고 제공) |
| `yt_title_alt` | | A/B 테스트용 대안 제목 |
| `persons` | 권장 | 등장 실명 배열 → #해시태그 자동 생성 (2~4개) |
| `hashtags` | | 해시태그 직접 지정 시 persons보다 우선 |
| `description` / `pinned_comment` | | 업로드 설명·고정댓글 (미지정 시 자동 구성) |
| `hook` | | **훅 씬 원본 육성** (아래). 미지정 시 V2와 동일하게 TTS 훅 |

### hook (scene 0 = 원본 발언 육성)

- `source`: sources의 인물키 — **가장 대립·충격적인 원본 발언 구간**
- `start_sec`: 발언 시작 초 (또는 `frac`: 비율) — download 후 소리로 확인해 지정
- `duration`: 1.0~10.0초 (기본 3.0). **발언 문장이 끝맺음될 때까지 포함할 것**
  (silencedetect로 문장 끝 휴지 확인: `ffmpeg -ss <근처> -t 15 -i src.mp4 -vn
  -af "highpass=f=150,silencedetect=n=-25dB:d=0.15" -f null /dev/null`)
- `text`: 노란 자막 (기본 yt_title) / `hl`: 강조 단어
- `subtitle_position`: 기본 `"bottom"` — 자막을 영상 아래 레터박스에 배치
  (인물 가림 방지). 중앙 배치를 원하면 `""`

동작: scene 0 = 원본 오디오(mute=False + loudnorm), TTS는 scene 1부터
(TTS mp3 앞 무음 패딩 + 타이밍 시프트). 씬 `type`의 `comment`는 `body`로 강제.

렌더 완료 시 `data/political_pro/<slug>/upload_package.md` 자동 생성
(제목 A/B·설명·해시태그·고정댓글·권장 업로드 시각·썸네일 후보 3장).

예시: `_template_v2_1.json`

---

# 정치쇼츠 V2.2 확장 (render_political_v2_2.py) — 원본 육성 릴레이

포맷 반전 (prompt_plan 033): **육성 클립 3~5개가 영상의 뼈대**, TTS 논평은
기본 1개(최대 2개, 3개부터 경고). V2.1 스크립트/설정은 무변경.

```bash
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py \
    scripts/political_v2_configs/<name>.json download   # + clip 프리뷰 청음 확인
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py \
    scripts/political_v2_configs/<name>.json render     # 렌더 + upload_package.md
```

## V2.1과 다른 점

- top-level `hook` 섹션 **없음** — 훅도 `scenes[0]`의 clip 씬으로 통일 (scene 0은 clip 강제).
- scene에 `mode: "clip" | "tts"` (기본 tts) 추가.
- TTS는 tts 씬만 합성 후 씬별 세그먼트로 잘라 클립 길이만큼 무음을 사이사이
  배치(타임라인 조립) — 육성↔TTS가 몇 번이든 교차 가능.
- 렌더 시 클립 오디오 비중 출력 (권장 ≥ 65%, 미달 경고).

## scenes[i] (mode별)

### mode: "clip" (원본 육성 — 뼈대)
- `source`: sources 키. `start_sec`(권장, 실측) 또는 `frac` + `duration`(1~10s).
  **발언 문장이 끝맺음될 때까지 포함** (silencedetect로 문장 끝 휴지 확인).
- `text`: 발언 요지 자막 (scene 0만 생략 시 yt_title 폴백). `hl`: 강조 단어.
- `speaker`: 화자명 — 자막 첫 줄에 `[화자]` 라벨 (클립 릴레이 문맥 단절 방지).
- `color`: 기본 `yellow`. `subtitle_position`: 기본 `"bottom"`(인물 가림 방지),
  방송 번인 자막과 겹치면 `""`(중앙).
- 동작: 원본 오디오(mute=False + loudnorm), TTS 없음.

### mode: "tts" (논평 — 기본 1개)
- V2.1 씬과 동일: `voice`(필수)/`frac` 또는 `start_sec`/`color`/`emph`/`text`/`hl`.
- **마지막 씬 1개 권장 (사용자 확정 2026-07-23)**: 클립 릴레이가 앞을 채우고,
  TTS는 맨 끝에서 팩트 정리 + CTA("여러분 생각은? 댓글로")로 마무리.

## 편집 규칙 (권장)

- 4~6씬, 총 45초 캡: `클립(훅) → 클립 → [클립] → TTS(정리+CTA, 마지막)`
  — 표준 구성 (사용자 확정 2026-07-23). 인접 클립은 대립 배치.
- **클립 선정 1순위 = 표정·리액션 절정** (웃음/한숨/야유/침묵/눈물, 034 벤치마크):
  경쟁 채널 최상위 영상(93만~148만회)의 공통점은 '발언 내용'이 아니라
  '반응 장면'. 발언이 완결되는 컷 중에서도 화자 또는 상대의 감정이
  드러나는 구간을 고른다. TTS 팩트 정리(마지막 1씬)는 차별점으로 유지.
- **제목(yt_title)은 보도체·해시태그 금지** — validate 단계에서 차단(034).
  감정훅형('눈물까지 고인 장동혁') 또는 호기심형('아니 아직도 발급을 안 했어?')
  12~20자. 해시태그는 설명란 3~4개만 (upload_package.md가 자동 이동).
  실전 예시: `leejm_pyeonbeop_v2_2.json` (3클립 여야 릴레이 + TTS 정리),
  `ohsh_yeoron_v2_2.json` (여야 대변인 맞대결 + TTS 정리).
- 인접 클립은 대립 배치: A 주장 → B 반박 → A 재반박 (갈등 아크를 육성만으로).
- download 후 `_verify/clip_NN.mp4` **청음 확인 필수** (문장 완결 여부).

예시: `_template_v2_2.json`
```
```
