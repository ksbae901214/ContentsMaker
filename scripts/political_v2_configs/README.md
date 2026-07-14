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
```
```
