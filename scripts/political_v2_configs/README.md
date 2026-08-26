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
  TTS는 맨 끝에서 팩트 정리 + CTA로 마무리. CTA 문구는 035 규칙을 따른다 —
  선택지형(①/②) + `"댓글로 알려주세요"` 종결. "여러분 생각은?" 같은 열린
  질문은 실측 댓글율 0.24%라 쓰지 않는다.

## 편집 규칙 (권장)

- 4~6씬, 총 45초 캡: `클립(훅) → 클립 → [클립] → TTS(정리+CTA, 마지막)`
  — 표준 구성 (사용자 확정 2026-07-23). 인접 클립은 대립 배치.
- **`scenes[0]`(훅) = 확보한 클립 중 가장 센 컷** (사용자 지시 2026-08-13).
  사연이 있는 소재는 시간순으로 배열하기 쉬운데, 그러면 **상황 설명이 앞에 오고
  절정이 뒤로 간다.** 클립을 다 잘라 놓고 세기 순으로 다시 정렬한 뒤, 1등을
  scenes[0]에 놓고 나머지로 아크를 만든다. 순서를 바꿔 문맥이 깨지면 자막이
  메운다 — 훅이 약한 것보다 낫다.
  훅 부적격: 기자 나레이션, 상황·경위 설명, 배경 원경 화면, 서술형 어미로
  끝나는 자막. 훅 적격: 당사자 1인칭·반문형("제가 투기꾼입니까?"), 화면에
  숫자·문구가 박힌 컷, 감정이 실린 육성.
  → 실패 사례: 경제 1호 `bigeoju_1jutaek_v2_2.json` — 씬0을 기자 나레이션
  ("손주 돌보러 이사")으로 두고 진짜 훅("제가 투기꾼입니까?" + 입법의견 화면)을
  씬1에 뒀다. 둘을 바꿔야 했다.
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

---

# 035 — 조회수/댓글 개선 게이트 (2026-08-05)

채널 실측 88편 기준으로 추가된 **길이 캡 · 중반 CTA · 소재 프레임** 규칙.
V2.1 / V2.2 양쪽에 동일 적용된다.

## 왜 (실측 근거)

| 관측 | 수치 |
|---|---|
| 조회수 중앙값 | 1,169회 (88편) |
| 900~1,400 구간 집중도 | 41편 = **47%** |
| 제목 유형별 중앙값 | hook 1,151 / neutral 1,200 / report 1,121 — **차이 없음** |
| 제목 언어별 중앙값 | 한글 1,150 / 영어 1,151 — **차이 없음** |
| 좋아요율 / 댓글율 (최근 18편) | 2.56% / **0.24%** (건강 기준 4~5% / 0.5~1%) |
| 상위 2편 길이 | 38초(3,048회) · 40초(3,093회) — 최근 40편 평균은 **48초** |

조회수가 1,150 근처에 뭉쳐 있다 = 첫 노출 배치를 못 넘긴다는 뜻이고,
제목 실험이 지표를 못 움직였다 = 병목이 클릭이 아니라 **완주율**이라는 뜻이다.

## 1. 길이 38~42초 캡 (`scripts/political_length.py`)

- `validate` 단계: 글자 수 추정으로 **경고** (1.0배속 7.4자/초, 오차 ±15%)
- `render` 단계: 합성된 실제 타임라인 길이로 **하드 차단** — Remotion 렌더 전에 fail-fast
- 우회: config에 `"duration_gate": "off"`
- 초과 시 몇 자를 줄여야 하는지 메시지로 알려준다

> 기존 config 31개 중 23개가 이 캡에 걸린다. 과거 파일은 그대로 두고,
> **새로 만드는 config만** 캡 안에서 작성한다. 재렌더가 필요하면 나레이션을
> 줄이거나 씬 하나를 빼고, 그래도 안 되면 `duration_gate: "off"`.

## 2. CTA (`scripts/political_cta.py`)

top-level `cta` 블록을 쓰면 **마지막 씬 뒤에 tts 씬으로 자동 삽입**된다
(038, 2026-08-25 사용자 지시로 40% 지점 삽입에서 되돌림 — 아래 "038" 절 참고).

```json
"cta": {
  "text": "이거 누구 잘못?\n① 조국  ② 이준석",
  "voice": "1번 조국, 2번 이준석. 댓글로 알려주세요.",
  "hl": ["누구 잘못"]
}
```

- **편 가르는 선택지형 필수** — `①/②`·`1번/2번`·`누구 잘못`·`어느 쪽`·`찬성/반대`.
  "여러분 생각은 어떠신가요?" 같은 열린 질문은 경고 (실측 댓글율 0.24%)
- **나레이션은 "댓글로 알려주세요"로 닫는다** (사용자 지시 2026-08-18).
  CTA는 영상에서 유일하게 시청자에게 직접 말을 거는 문장이다. `"번호로 답글."`
  같은 명사형·반말 종결은 지시처럼 들리고 채널 톤(존댓말)과 어긋난다.
  → `lint_cta` 가 종결 문구를 검사해 경고한다.
- CTA 나레이션은 **4초(약 32자) 이내** — 본편 길이 캡을 잠식하지 않도록.
  종결 문구가 9자를 먹으므로 남는 건 **약 23자**다. 질문은 화면 자막이 이미
  보여주니 나레이션에서는 빼고 선택지만 읽는다
  (`"1번 조국, 2번 이준석. 댓글로 알려주세요."`)
- 일반 씬 나레이션에 "댓글" 문구가 남아 있으면 경고 (CTA는 1회만)
- 고정댓글은 `pinned_comment` > `cta.voice` > 기본값 순으로 자동 채워진다

> **CTA를 씬으로 직접 쓸 때도 같은 규칙이다.** 2026-08-14 지시 이후 CTA를
> 마지막 씬에 직접 쓰는 것도 표준으로 허용되는데(038 이후로는 top-level `cta`
> 블록도 결국 마지막 씬에 붙으므로 둘이 동일한 결과), `lint_cta` 는 top-level
> `cta` 블록만 본다. 그래서 `scene_cta_closing_warnings` 가 **자막에 `①`/`1번`
> 이 박힌 씬**을 CTA로 보고 종결을 따로 검사한다 (2026-08-18 장동혁 편에서
> `"번호로 답글."` 이 검사 없이 통과해 영상까지 나간 뒤 추가됨).

### 038 — CTA를 마지막 씬으로 되돌림 (2026-08-25)

035에서 CTA를 40% 지점으로 옮긴 이유는 "CTA가 마지막 씬에 있으면 도달 자체가
안 된다"(당시 댓글율 0.24%)는 실측 때문이었다. 사용자가 "CTA가 영상 중간에
나오는 게 싫다"고 명시적으로 지시해 **마지막 씬으로 되돌렸다** — `apply_cta()`가
이제 `at_frac` 없이 항상 `scenes` 끝에 CTA 씬을 붙인다. 이 결정으로 댓글율이
다시 떨어지는지는 렌더 몇 편 이후 재확인 권장(강제 아님).

## 3. 소재 프레임 — '결과가 난 사건'

터진 영상은 전부 결과가 있었다: 7,900회 '5선 오세훈의 13시간 대역전극',
5,600회 '박근혜 9년 침묵의 컴백', 3,048회 '토론장서 터짐'.
반면 'A가 B를 직격/저격' 공방형은 예외 없이 1,100대에 멈췄다.

- `yt_title`에 공방 단어(직격·저격·공방·정면충돌·발끈·일침…)만 있고
  결과 단어(결국·끝내·만에·철회·사퇴·무산·뒤집·역전·컴백·선고…)가 없으면
  `upload_package.md`에 경고
- 공방 장면을 써도 좋다 — 단 **그 공방이 무엇을 바꿨는지**를 제목에 담을 것
- Stage A 프롬프트(`src/analyzer/political_planner_stage_a_prompt.py`)에도
  동일 규칙 반영 — 폐기된 `[악역]-[응징동사]-[주인공]` 공식은 제거됨

## 편집 규칙 (035 반영 최종형)

```
클립(훅) → 클립 → 클립 → TTS(팩트 정리) → [CTA]     # V2.2
훅(육성) → TTS → TTS → TTS(팩트 정리) → [CTA]        # V2.1
```

- 총 **38~42초**. 팩트 정리로 마무리한 뒤 CTA가 맨 끝에 온다(038)
- V2.2는 CTA 삽입으로 클립 비중이 내려가므로 클립 길이를 함께 조정할 것

---

# 036 — 카테고리 확장 계측 (2026-08-13, Phase 0)

정치 외 **경제·사회·연예**를 같은 채널에 섞기로 확정(사용자 결정 2026-08-13).
카테고리별 성과를 못 쪼개면 확장이 도박이 되므로, **계측부터** 붙였다.

## config 키: `category`

```json
"category": "economic"
```

| 값 | 설명 |
|---|---|
| `political` | **기본값** — 미지정 시 이 값. 기존 config 31개는 무변경으로 동작 |
| `economic` | 금리·물가·부동산·세금·증시 |
| `society` | 판결·사건사고·교육·복지 |
| `entertainment` | 연예인·방송·열애/복귀 |

허용값 외 문자열은 **validate 단계에서 ValueError** — 렌더를 다 돌린 뒤가 아니라
시작 시점에 잡는다.

## 동작

1. 렌더가 끝나면 `upload_package.md` 머리에 카테고리가 표기되고,
2. `data/channel_analytics/category_ledger.json` 에 `{제목: category}` 가 자동 기록된다.
   업로드가 수동이라 유튜브 쪽엔 카테고리가 남지 않는다 — 이 원장이 유일한 정답 소스다.
3. 다음 `analyze_channel_performance.py` 실행부터 리포트에 **카테고리별 표**와
   희석/확대 경고가 붙는다.

```bash
PYTHONPATH=. .venv311/bin/python scripts/analyze_channel_performance.py
#   → 카테고리별 편수·중앙값·전체 대비 % + 희석(70% 미만)/확대(130% 이상) 경고
```

원장에 없는 과거 편은 **제목 키워드로 추론**한다(`scripts/shorts_category.py`).
best-effort라 틀릴 수 있고, 틀린 편은 `category_ledger.json` 의 `entries` 에
직접 써 넣으면 원장이 추론을 이긴다. 2026-08-05 스냅샷 88편 기준 미분류 2편(2%).

> **기준선 (2026-08-05 스냅샷, 추론 백필)**: political 73편 1,174회 /
> economic 11편 1,172회 / society 2편 948회 — 전체 중앙값 대비 전부 100% 언저리.
> 카테고리로는 아직 아무 차이가 없다는 뜻이고, 신규 카테고리는 이 선을 넘어야 한다.

## 도메인 규칙 팩 (Phase 1/2) — `scripts/shorts_domain.py`

파이프라인은 도메인과 무관하다. 렌더러·38~42초 캡·릴레이 구조·마지막 씬 CTA
삽입(038)은 경제든 연예든 그대로고, **검사 기준표만** 카테고리로 갈아끼운다.

| | 결과어(035 프레임) | CTA 축 | 제목 앵커 | 배경/emotion |
|---|---|---|---|---|
| political | 사퇴·부결·철회·경질 | ① 여당 ② 야당 | 실명 | 레드 / angry |
| economic | 동결·급락·파산·리콜·철수 | ① 이득 ② 손해 | **숫자·기업/기관명** | 청록 / relatable |
| society | 무죄·구속·선고·폐지·사과 | ① 약하다 ② 적당하다 | 사건명·실명 | 남색 / touching |
| entertainment | 인정·결별·하차·복귀·폭로 | ① 응원한다 ② 이르다 | 실명 | 보라 / funny |

`emotion_type`·`bg_colors`는 **config 명시값이 우선**, 미지정 시 위 기본값.

### 가드레일 2단

| 단계 | 대상 | 동작 |
|---|---|---|
| **차단** (`ValueError`) | 경제 투자 권유 — 매수·매도·추천주·급등각·존버·물타기·풀매수·몰빵·수익률 보장 | 렌더 전 fail-fast (유사투자자문 소지) |
| **경고** | 사회 피의사실 — 피의자·용의자·구속영장·범인 / 연예 미확인 사생활 — 불륜·임신설·이혼설·루머 / 경제 전망 표현 / 연예 `source_channel` 누락 | `upload_package.md` + 렌더 로그 |

둘 다 config `"domain_gate": "off"` 로 우회 — 단, 법적 리스크는 본인이 진다.

> 034 보도체 게이트(`~했다`류 과거형 어미 차단)는 **카테고리 공통**이다.
> 경제·연예 제목도 과거형으로 끝내면 렌더가 막히므로 명사로 닫을 것.

### 경제쇼츠의 훅 — 표정이 아니라 '내 돈이 걸린 한 문장'

034의 "클립 1순위 = 표정·리액션 절정"은 **정치 기준**이다. 경제 소재는 화자가
당국자·기자·전문가라 표정이 없는 경우가 대부분이라 그 기준을 그대로 적용하면
고를 컷이 없다. 경제의 절정은 표정이 아니라 **당사자가 자기 손해를 말하는 한 문장**이다.

훅 후보 우선순위:
1. 당사자 1인칭 항의·반문 — "제가 투기꾼입니까?", "이게 왜 제 잘못입니까"
2. 화면에 숫자·문구가 박힌 컷 (입법의견 게시판, 세금 시뮬레이션 표, 고지서)
3. 당국자의 말 바꾸기·후퇴 발언
4. (최후) 기자 나레이션 — **여기까지 내려오면 소재를 다시 볼 것**

소재 수집 단계에서 "이 소재에 1번짜리 육성이 있는가"를 먼저 확인한다. 없으면
클립 릴레이(V2.2)가 아니라 V2.1이 맞는 소재이거나, 소재 자체가 약한 것이다.

### ⚠️ `emotion_type` = 사실상 BGM 스위치 (필독)

**BGM은 `emotion_type` 하나로만 결정된다** (`select_bgm_for_script` →
`data/bgm/<emotion>_N.mp3`). 그런데 V2.1/V2.2에서는

- 배경 그라데이션 → `bg_colors` (또는 카테고리 기본값)
- 자막 색 → 씬별 `color`

로 **따로** 지정하므로, `emotion_type`을 바꿔도 화면은 그대로고 **BGM만 바뀐다**.
즉 `emotion_type`은 "이 영상에 어떤 음악을 깔 것인가"를 고르는 스위치로 쓰면 된다.

> **실패 사례 (2026-08-13)**: 하영 증조부 친일 논란 편이 카테고리 기본값
> `entertainment → funny` 를 그대로 물려받아 **`funny_2.mp3`(코믹 BGM)** 로 렌더됐다.
> 마지막 TTS 논평 구간에서 특히 뜬금없게 들린다. 카테고리 기본값은 소재의 톤을
> 모른다 — **소재마다 직접 지정할 것.**

| 소재 톤 | `emotion_type` | 쓰는 경우 |
|---|---|---|
| 사실 전달·중립 검증 | **`relatable`** | 논란이지만 단죄하지 않는 편, 정보·해설 |
| 대립·비판·긴장 | `angry` | 가해/피해 구도가 뚜렷한 공방·규탄 |
| 비극·회한·서사 | `touching` | 사망·은퇴·눈물·오랜 침묵 끝 복귀 |
| 축하·가벼움 | `funny` | 열애·수상·컴백 — **논란 소재엔 절대 금지** |

**카테고리 기본값**(미지정 시): political `angry` / economic `relatable` /
society `touching` / entertainment `funny`. 연예는 기본값이 `funny` 라
**논란·사건 소재라면 반드시 config에 `emotion_type` 을 명시**해야 한다.

렌더 로그의 `BGM 적용: <파일> (<emotion>)` 줄로 무엇이 깔렸는지 확인할 수 있고,
렌더 전에는 아래로 미리 확인한다.

```bash
PYTHONPATH=. .venv311/bin/python -c "
import json; from pathlib import Path
from scripts.political_cta import apply_cta
from scripts.shorts_domain import resolve_emotion_type
cfg = apply_cta(json.loads(Path('scripts/political_v2_configs/<name>.json').read_text()))
print('emotion:', resolve_emotion_type(cfg))"
```

### 연예쇼츠는 V2.2만 쓴다 (사용자 확정 2026-08-13)

연예 카테고리는 **V2.1을 만들지 않는다.** V2.1은 영상의 65%가 TTS 논평이라
연예 소재에서 논평이 곧 단죄로 읽히고, 명예훼손 노출이 V2.2보다 크다.
V2.2는 육성 릴레이 구조상 "사실을 보여주고 판단은 시청자에게" 가 편집에서 나온다.

→ 연예는 V2.2 한 편만 제작하고, 034의 플랫폼 분리(V2.2 유튜브 / V2.1 틱톡)에서
V2.1 자리를 비운다. 정치·경제·사회는 종전대로 병행 가능.

### 템플릿

| 파일 | 카테고리 |
|---|---|
| `_template_v2_2.json` | 정치 (기존) |
| `_template_economic_v2_2.json` | 경제 |
| `_template_society_v2_2.json` | 사회 |
| `_template_entertainment_v2_2.json` | 연예 — ⚠️ 방송 클립 저작권 최고 위험 · V2.2 전용 |

```bash
cp scripts/political_v2_configs/_template_economic_v2_2.json \
   scripts/political_v2_configs/<my_slug>_v2_2.json
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py \
   scripts/political_v2_configs/<my_slug>_v2_2.json download   # 클립 청음 확인
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py \
   scripts/political_v2_configs/<my_slug>_v2_2.json render
```

기존 정치 config 37개는 `category` 미지정 = `political` 이라 **무변경으로 통과**한다
(검증 완료: 차단 0 / 경고 0 / 렌더 기본값 변화 0).

---

# 037 — 제작 규격 고정 (2026-08-25, 사용자 지시)

## 1. 제목 폰트 크기 = 100px (고정)

`src/video/remotion/src/ShortsComposition.tsx` 의 `TitleBar` — `fontSize: 100`,
서체는 기본 `Noto Sans KR` 유지. **임의로 되돌리지 말 것.**

- 75px 기본값이 쇼츠 피드 썸네일에서 제목이 안 읽힌다는 판단으로 올렸다.
- 자막(`SceneText`)은 여기서 손대지 않는다 — 자막을 키우면 방송 번인 자막과
  겹치고, 한 줄에 들어가는 글자 수가 줄어 `WebkitLineClamp:3` 이 `…`로 자른다.
  (검은고딕 135px 을 자막에 시도했다가 전 씬이 3줄로 밀려 폐기, 2026-08-25)

## 2. 클립 컷은 **말 끝맺음까지** 넣는다

훅이든 본문이든 `mode: "clip"` 씬은 **문장 끝 단어가 다 발화된 뒤** 끊는다.
"…취소되며 후폭풍을 맞고 있" 처럼 어미가 잘리면 시청자가 다음 씬으로 넘어갈 때
말이 끊긴 것으로 인지해 이탈한다.

**눈대중·auto-caption 블록 타임스탬프로 잡지 말 것** — 롤링 자막은 문장 경계와
안 맞는다. 단어 단위 타임스탬프를 뽑아서 잡는다:

```bash
# 1) 자동자막 받기 (영상은 mweb, 자막은 기본 클라이언트 — 섞으면 자막이 빠진다)
.venv311/bin/yt-dlp "<url>" --skip-download --write-auto-subs \
  --sub-langs ko --convert-subs vtt -o "_sub/<key>"

# 2) 단어 단위 타임스탬프 추출 — <00:00:12.345><c>단어</c> 인라인 태그
python3 - <<'PY'
import re
from pathlib import Path
for m in re.finditer(r'<(\d\d):(\d\d):(\d\d)\.(\d+)><c>([^<]+)</c>',
                     Path('_sub/<key>.ko.vtt').read_text(encoding='utf-8')):
    t = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000
    print(f'{t:.1f}:{m.group(5).strip()}')
PY
```

`duration` 은 **마지막 단어 시작 + 그 단어 발화 길이**(= 다음 단어 시작 시각)로
잡는다. 다음 문장 첫 단어가 물려 들어가면 그 직전에서 끊는다 — 0.2~0.3초라도
엉뚱한 음절이 붙어 들리면 잘린 것만큼 어색하다.

**끝맺음을 살리면 컷이 길어져 42초 캡을 넘긴다.** 그때는 `duration_gate` 를 끄지
말고 **씬을 하나 뺀다** — 뺄 후보는 정보량이 가장 낮은 씬(속편이면 전편 복습 씬).

## 3. 원본에 박힌 자막 카드도 함께 확인한다

발화가 맞아도 화면 카드가 다른 문장이면 자막과 어긋나 보인다. 방송 클립은
카드와 나레이션이 최대 6초까지 어긋나므로 **컷 구간의 카드 문구를 눈으로 확인**할 것.

```bash
# 4초 간격으로 자막 띠만 잘라 한 장으로 — 카드 문구 훑기
ffmpeg -i src_<key>.mp4 -vf "fps=1/4,crop=iw:ih*0.30:0:ih*0.68,scale=440:-1,tile=1x13" \
  -frames:v 1 _chk/tile.png
```

카드가 소재와 무관하거나(뉴스 낭독 + 무관한 스트리밍 화면 등) 서술이 단정적인
채널은 **소스에서 뺀다** — 2026-08-25 박위 2탄에서 2개 소스를 이 사유로 교체했다.
