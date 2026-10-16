# 정치쇼츠 제작 파이프라인 — Gemini 이식용 상세 매뉴얼

이 문서 하나로 ContentsMaker의 정치쇼츠 워크플로를 **다른 AI(Gemini 등)에서 재현**할 수 있다.
두 가지 용도를 모두 지원한다.

- **A. 지침으로 쓰기** — 이 문서를 Gemini Gem/프로젝트 지식에 넣고, AI에게 기획·대본·제목·CTA를 시킨다.
  영상 처리(다운로드/컷/렌더)는 로컬 ffmpeg 명령으로 사람이 실행한다.
- **B. 프로젝트를 새로 짓기** — 5~9장의 규칙·상수·알고리즘을 그대로 구현하면 이 저장소 없이도 같은 결과가 나온다.

> 원본 구현: `scripts/render_political_v2_1.py`, `scripts/render_political_v2_2.py`,
> `scripts/political_cta.py`, `scripts/political_length.py`, `scripts/political_upload_package.py`,
> `scripts/naver_top_political.py`, `src/dem_shorts/editor/segment_cutter.py`,
> `src/tts/gemini_tts_generator.py`

---

## 0. 전체 그림

```
① 네이버 인기 뉴스 수집 → 소재 1건 선정 ('결과가 난 사건'만)
      ↓
② 그 사건의 유튜브 원본 영상 탐색 (yt-dlp ytsearch) + 자막(srt) 확보
      ↓
③ 발언 구간 실측 → 9:16 클립 컷 (ffmpeg, 문장 완결 단위)
      ↓
④ 자막 설계 (색·위치·강조·화자 라벨)
      ↓
⑤ AI 논평(나레이션) + 제목 + 중반 CTA 작성  ← Gemini가 가장 잘하는 부분
      ↓
⑥ TTS 합성 (Gemini Charon, 뉴스캐스터 톤, 1.1배속)
      ↓
⑦ 타임라인 조립 → 렌더 → upload_package.md → 사람이 검수 후 수동 업로드
```

### AI 단독으로 가능한 것 / 로컬 도구가 필요한 것

| 단계 | Gemini 단독 | 로컬 도구 필요 |
|---|---|---|
| ① 뉴스 수집 | 검색 그라운딩으로 이슈 후보 나열 | 정확한 랭킹·댓글 수는 네이버 API/curl |
| ② 영상 탐색 | 유튜브 URL을 붙여 넣으면 내용 요약·발언 위치 후보 제시 | 다운로드는 `yt-dlp` |
| ③ 컷 편집 | 컷 계획(초 단위 목록)까지 | 실제 컷은 `ffmpeg` |
| ④ 자막 | 자막 문안·색·강조어 전부 | 번인은 Remotion 또는 ffmpeg |
| ⑤ 논평·제목·CTA | **전부 가능** | 없음 |
| ⑥ TTS | Gemini TTS API 호출 코드 작성 | API 키 + 실행 환경 |
| ⑦ 검수·업로드 | 체크리스트 판정 | 업로드는 사람이 수동 (자동 업로드 금지) |

### 실행 환경 (이 저장소를 쓸 때)

```bash
# Python 3.11 가상환경 + ffmpeg + node 20 필요
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py <config.json> download
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py <config.json> render
```

| 환경변수 | 용도 |
|---|---|
| `GEMINI_API_KEY` | Charon TTS (무료 티어 5 RPM / 10 req·일) |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 검색 API (25,000 req/일 무료) |

---

## 1. 네이버에서 인기 뉴스 가져오기

목표는 "많이 보도된 이슈"가 아니라 **"결과가 난 사건 중 논쟁이 붙은 것"** 한 건을 고르는 것이다.

### 1-A. 검색 API로 보도량 랭킹 (권장, 안정적)

`scripts/naver_top_political.py` — 어제(KST) 정치 기사를 모아 **제목에 등장한 정치 엔티티 빈도**로 랭킹한다.
(수천 건을 LLM에 한 번에 넣어 클러스터링하면 응답이 잘려 실패하므로, 문자열 매칭으로 집계한다.)

```bash
PYTHONPATH=. .venv311/bin/python scripts/naver_top_political.py \
    2026-08-12T00:00:00 2026-08-13T00:00:00 5
```

동작:
1. 네이버 검색 API에 `정치·국회·대통령·여당·야당·국민의힘·민주당` 7개 쿼리, `sort=date`, 페이지네이션(`start=1,101,…,1001`)으로 수집
2. 제목 중복 제거(같은 제목 = 재배포)
3. 인물·정당·기관·이슈 키워드(`ENTITIES` 약 60개)를 제목에 부분 매칭 → 등장 기사 수로 정렬
4. `국회/선거/재판/정치/대통령`처럼 너무 흔한 말(`GENERIC`)은 순위에서 제외
5. 출력: `[{rank, entity, article_count, headlines[6], sample_link}]`

> 캐시가 `/tmp/naver_political_news.json`에 남는다. 새로 받으려면 지울 것.

### 1-B. 랭킹 페이지 + 실제 댓글 수 (논쟁도 지표)

**브라우저 자동화(Claude in Chrome)로는 네이버에 접근할 수 없다** — 서버측 URL 분류로 하드 차단이라 우회 경로가 없다. `curl`로 간다.

```bash
# 1) 인기 기사 랭킹 HTML — 응답이 cp949 이므로 디코딩 필수
curl -s -A "Mozilla/5.0 ... Chrome/126.0 Safari/537.36" \
  "https://news.naver.com/main/ranking/popularMemo.naver?date=20260812" > /tmp/rank.html
python3 -c "print(open('/tmp/rank.html','rb').read().decode('cp949'))" | head -50
```

- 기사 링크 패턴: `href="https://n.news.naver.com/article/{oid}/{aid}?ntype=RANKING" class="list_title..."`
- **댓글 수는 HTML에 없다.** cbox API로 따로 조회한다(Referer에 기사 URL 필요, 동시 6스레드까지 무난):

```
https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json
  ?ticket=news&templateId=default_politics&pool=cbox5&lang=ko&country=KR
  &objectId=news{oid},{aid}&pageSize=1&indexSize=1&page=1&sort=NEW
```
JSONP 응답의 `result.count.total`이 총 댓글 수 = **논쟁 강도 지표**. 이 값이 높은 기사가 쇼츠 소재로 좋다.

### 1-C. Gemini 단독으로 할 때

검색 그라운딩으로 "어제 한국 정치 뉴스 중 가장 많이 보도된 이슈 5개"를 뽑되, **반드시 2개 이상의 언론사 기사로 교차검증**하고 각 사실에 출처 URL을 붙인다. 그라운딩 결과의 날짜·수치는 자주 틀리므로, 숫자(시간·표결수·금액)는 원문에서 재확인한다.

### 1-D. 소재 게이트 — 이걸 통과 못 하면 만들지 않는다

채널 실측 88편 분석 결과:

| 관측 | 수치 |
|---|---|
| 조회수 중앙값 | 1,169회 |
| 900~1,400 구간 집중 | 41편 = **47%** |
| 제목 유형별 중앙값 | hook 1,151 / neutral 1,200 / report 1,121 → **차이 없음** |
| 좋아요율 / 댓글율(최근 18편) | 2.56% / **0.24%** (건강 기준 4~5% / 0.5~1%) |
| 상위 2편 길이 | 38초(3,048회) · 40초(3,093회) |

→ 병목은 클릭이 아니라 **완주율**이고, 터진 영상은 전부 **결과가 난 사건**이었다
(‘13시간 대역전극’, ‘9년 침묵의 컴백’, ‘토론장서 터짐’).
반대로 ‘A가 B를 직격/저격’ 공방형은 예외 없이 1,100대에서 멈췄다.

**소재 선정 규칙**
1. 사건에 **결말**이 있어야 한다 — 철회·사퇴·번복·역전·통과·부결·구속·선고·컴백…
2. 공방 장면을 써도 좋지만, **그 공방이 무엇을 바꿨는지**가 제목에 들어가야 한다
3. 당사자 **육성 영상이 존재**해야 한다 (없으면 기사 화면 캡처로 대체 — 8장 참조)
4. 댓글이 갈리는 사안일 것 (중반 CTA에서 ①/② 선택지를 만들 수 있어야 함)

**산출물 — 이슈 카드 (다음 단계 입력)**
```
사건명:
결과 한 문장:      (…끝에 …가 철회됐다)
확정 사실 3~5개:   각각 출처 URL
등장인물 2~4명:    실명
대립 축:           A 주장 ↔ B 반박
CTA 선택지:        ① ___  ② ___
```

---

## 2. 그 뉴스에 맞는 유튜브 영상 찾기

### 2-A. 검색어 작법

`yt-dlp`의 `ytsearch`를 쓴다. 검색어는 **인물 + 발언 키워드 + 장면 종류**로 짠다.

| 상황 | 검색어 예 |
|---|---|
| 특정 발언 | `조국 일베 감별법 무섭노 발언 논란` |
| 반박 측 | `이준석 조국 사상검증 무섭노` |
| 여야 반응 한 번에 | `YTN 여야 반응 <사건명>` ← **뉴스 리포트 1편이면 양쪽 육성이 다 들어있다** (V2.2에 최적) |
| 회의·표결 현장 | `<사건명> 본회의 표결 현장` |

### 2-B. 다운로드

config의 `sources` 스펙(스크립트가 그대로 yt-dlp에 넘긴다):

```json
"sources": {
  "joguk": { "query": "조국 일베 감별법 무섭노 발언 논란", "dur_max": 900, "dur_min": 20,
             "search_n": 6, "verify_frac": 0.25 },
  "chA":   { "url": "https://www.youtube.com/watch?v=VSAn-JTZsFA", "dur_max": 900 }
}
```

수동 실행 시:

```bash
yt-dlp "ytsearch6:조국 일베 감별법 무섭노 발언 논란" \
  --match-filter "duration<900 & duration>20" --max-downloads 1 \
  -f "bv*[height<=720]+ba/b[height<=720]" --merge-output-format mp4 \
  -o "src_joguk.%(ext)s"

# 자막(발언 위치 검색용) — 다운로드 없이 자막만
yt-dlp --write-auto-sub --sub-lang ko --skip-download --convert-subs srt <URL>
```

720p로 제한하는 이유: 쇼츠는 1080×1920으로 다시 굽기 때문에 원본 화질이 그 이상일 필요가 없고, 다운로드가 훨씬 빠르다.

### 2-C. 인물 확인 (반드시)

검색 결과가 엉뚱한 인물일 수 있다. 다운로드 직후 **검증 프레임**을 뽑아 눈으로 확인한다.

```bash
ffmpeg -ss $(python3 -c "print(<총길이>*0.25)") -i src_joguk.mp4 -frames:v 1 _verify/joguk.png
```

- `download` 명령이 `data/political_pro/<slug>/_verify/<key>.png`에 자동 생성한다
- 틀리면 `query`를 고쳐 `download --force`

### 2-D. Gemini를 쓸 때

Gemini는 유튜브 URL을 직접 읽을 수 있으므로 "이 영상에서 X가 Y라고 말하는 대목이 몇 분쯤인지" 후보를 뽑는 데 쓴다. 단 **타임스탬프는 신뢰하지 말 것** — 실측상 드리프트가 크다. AI가 준 시각은 ±10초 탐색 힌트로만 쓰고, 경계는 3장의 방법으로 확정한다.

---

## 3. 필요한 부분만 잘라서 편집

### 3-A. 클립 경계 실측 (핵심 노하우)

1. **텍스트로 위치 찾기**: srt 자막에서 발언 문장을 검색해 대략의 초를 얻는다
2. **무음으로 문장 끝 확정**:

```bash
ffmpeg -ss 120 -t 20 -i src_joguk.mp4 -vn \
  -af "highpass=f=150,silencedetect=n=-25dB:d=0.15" -f null /dev/null
```
   출력의 `silence_start` 가 문장이 끝난 지점이다.
3. **문장 끝 + 0.5~0.8초 휴지까지 포함**해서 컷한다. 말이 잘린 채 씬이 바뀌면 시청자가 즉시 이탈한다.
4. **청음 확인 필수**: 잘린 클립을 실제로 들어본다. (`download` 명령이 `_verify/clip_NN.mp4` 프리뷰를 만들어 준다)

> 뉴스 리포트는 BGM이 계속 깔려 있어 `silencedetect` 결과가 0개일 수 있다.
> 이때는 1초 간격 콘택트시트(프레임) + 방송 번인 자막으로 경계를 잡는다.

### 3-B. 9:16 변환 + 컷 (`src/dem_shorts/editor/segment_cutter.py`와 동일)

```bash
ffmpeg -y -i src_joguk.mp4 -ss 42.0 -t 3.5 \
  -vf "scale='if(gt(a,1080/1920),1080,-2)':'if(gt(a,1080/1920),-2,1920)',pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" \
  -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k -movflags +faststart \
  scene_00.mp4
```

- **크롭이 아니라 레터박스 패딩**을 쓴다. 얼굴이 잘리는 것보다 위아래 검은 띠가 낫고, 이 띠가 자막 자리가 된다
- 원본 음성을 쓰는 클립은 위처럼 오디오를 유지, **TTS 나레이션 씬은 `-an`으로 음소거**한다 (더블 트랙 에코 방지)
- 컷 길이 상한 60초 (스크립트는 여유 있게 55초로 제한)
- 시작점이 원본 길이를 넘으면 ffmpeg가 262바이트짜리 빈 파일을 조용히 만든다 → 길이를 먼저 `ffprobe`로 확인할 것

### 3-C. 원본 음성 정규화 + 립싱크 보정

```bash
# 육성 클립 오디오 정규화 (영상은 재인코딩 없이 copy)
ffmpeg -y -i scene_00.mp4 -c:v copy \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,atrim=start=0.044,asetpts=PTS-STARTPTS" \
  -ar 48000 -c:a aac -b:a 128k scene_00_norm.mp4
```

- `loudnorm=I=-16:TP=-1.5:LRA=11` — 방송 클립마다 다른 음량을 쇼츠 표준으로 맞춘다
- `atrim=start=0.044` — **AAC priming(2112샘플) 때문에 클립 음성이 영상보다 44ms 늦는 현상**을 상쇄한다.
  (Remotion의 OffthreadVideo가 priming을 스킵하지 않아 생기는 문제. 다른 렌더러를 쓰면 실측 후 조정)
- 클립 길이는 **30fps 격자에 반올림**(`round(dur*30)/30`)한다. 반프레임(±17ms)이 밀리면 입모양이 어긋난다

### 3-D. 두 가지 편집 포맷 (둘 다 표준)

**V2.1 — TTS 브리핑형** (`render_political_v2_1.py`)
```
S0 훅: 원본 육성 1~10초 (노란 자막, 하단)
S1~  : TTS 나레이션 씬 (영상은 인물 클립, 음소거)
```
- TTS mp3 **앞에 훅 길이만큼 무음을 넣고**(`adelay`) 모든 씬 타이밍을 그만큼 뒤로 민다 → 훅 구간엔 TTS가 침묵

**V2.2 — 원본 육성 릴레이형** (`render_political_v2_2.py`, 유튜브 기본)
```
S0 클립(훅) → S1 클립(반박) → [CTA] → S2 클립(재반박) → S3 TTS(팩트 정리, 마지막 1개)
```
- 육성 클립 2~3개가 뼈대, TTS 논평은 **기본 1개(최대 2개)**
- 인접 클립은 **대립 배치**: A 주장 → B 반박 → A 재반박 (갈등 아크를 육성만으로 만든다)
- 클립 선정 1순위는 발언 내용이 아니라 **표정·리액션 절정** (웃음·한숨·야유·침묵·눈물)
- 클립 오디오 비중 **≥65%** 권장 (미달 시 경고)
- TTS는 tts 씬만 합성한 뒤 씬별로 잘라, 클립 길이만큼 무음을 사이에 끼워 배치한다:

```
[0:a]atrim=start=S:end=E,asetpts=PTS-STARTPTS,adelay=D:all=1[s0]; ... [s0][s1]amix=inputs=N:normalize=0,apad=whole_dur=T[aout]
```

### 3-E. 길이 캡 — 38~42초 (하드 게이트)

| 상수 | 값 |
|---|---|
| 권장 하한 | 38초 |
| **하드 캡** | **42초** (최종 mp4 기준) |
| 아웃트로 | 항상 +4초 자동 부착 |
| 낭독 속도 | 1.0배속 7.4자/초 → 1.1배속 **8.14자/초** |

- 씬 타임라인이 38초여도 최종 파일은 42초다(아웃트로 포함) — 이 함정 때문에 실측 기준으로 판정한다
- **검증 단계**: 글자 수 추정으로 경고(오차 ±15%) / **렌더 단계**: 합성된 실제 길이로 **차단**
- 초과 시 몇 글자를 줄여야 하는지 계산: `잘라낼 글자 = 초과초 × 7.4 × 배속`
- 우회는 config `"duration_gate": "off"` (권장하지 않음)

**역산 예시**: 클립 3개 합계 14초 + 아웃트로 4초 → TTS에 쓸 수 있는 시간 24초 → 1.1배속 기준 **약 195자**. 여기에 CTA 32자가 포함된다.

---

## 4. 자막 넣기

### 4-A. 색·크기·위치 규칙

| 항목 | 값 |
|---|---|
| 폰트 | Noto Sans KR, weight 700 (강조·훅 900) |
| 색 | white `#FFFFFF` / red `#FF4444`(충돌·비판) / yellow `#FFD93D`(훅·육성·CTA) / blue `#5DADE2`(인용) |
| 강조 | `emph: true` → 폰트 **1.25배** + 900 |
| 세로 위치 | 기본 0.652 / 훅 0.5(중앙) / `subtitle_position:"bottom"` → **0.78** |
| 외곽선 | 검정 스트로크 + 드롭섀도우 (배경 어디서든 읽히게) |
| 줄 수 | 2줄, 줄당 약 21자 이내 (`\n`으로 직접 분리) |

**위치 규칙(락인)**: 원본 육성 씬 자막은 **반드시 하단(0.78)**. 16:9 영상이 레터박스로 화면 중앙(0.34~0.66)에 놓이므로, 0.78이면 인물 얼굴을 가리지 않고 검은 띠 위에 얹힌다. 방송 번인 자막(로어서드)과 겹치면 그때만 중앙으로 되돌린다.

### 4-B. 자막 문안 규칙

1. **화자 라벨** — 클립이 릴레이로 이어질 때 누가 말하는지 잃지 않도록 첫 줄에 `[이준석]` 같은 라벨을 붙인다
2. **발언 전체를 보여준다** — 추출 구간 안에서 화자가 말한 내용이 자막에 다 나와야 한다. 도입부 한 줄만 띄우고 멈추면 클라이맥스가 묻힌다. 길면 3~4초짜리 카드 2~3장으로 나눠 교체한다
3. **강조 단어(`hl`)** — 씬마다 2개 이내. 색이 바뀌어 시선을 끈다
4. 육성 씬 자막은 **발언 요지**(따옴표 인용), TTS 씬 자막은 **나레이션의 요약**이지 전문 받아쓰기가 아니다

### 4-C. Remotion 없이 자막을 넣으려면

이 저장소는 Remotion(React)으로 자막을 얹지만, ffmpeg만으로도 같은 규칙을 구현할 수 있다.

```bash
# 시간대별 자막 교체 (카드 2장)
ffmpeg -i scene_00.mp4 \
 -vf "drawtext=fontfile=/System/Library/Fonts/AppleSDGothicNeo.ttc:\
text='일베는 기계적으로 노':fontsize=64:fontcolor=#FFD93D:borderw=6:bordercolor=black:\
x=(w-text_w)/2:y=h*0.78:enable='between(t,0,3.5)'" -c:a copy out.mp4
```
또는 자막 카드를 투명 PNG로 렌더해 `overlay=...:enable='between(t,a,b)'`로 얹는 방식(원본 `scripts/extract_clip.py`가 쓰는 방법)이 한글 줄바꿈·강조색 처리에 더 편하다.

---

## 5. 기사에 대한 AI 의견(논평) 작성

### 5-A. 문체 규칙

- **보도체 금지**: "~했습니다" 고정형은 쓰지 않는다. **대립 서사체** — 주장 → 반박 → 역공의 아크를 만들고 문말을 다양하게 쓴다
- 한 씬 = 한 호흡. TTS가 읽었을 때 3~7초
- **사실과 의견을 섞지 않는다**: 확정 사실(출처 있는 것)만 단정하고, 해석은 "~로 보인다/~라는 뜻이다"로 분리
- 마지막 씬은 **팩트 정리로 닫는다**. 댓글 유도는 마지막이 아니라 CTA 씬이 담당한다

### 5-B. 제목 (`yt_title`) — 렌더 전에 차단되는 항목

**하드 차단 (게이트)**
- 제목 안 **해시태그 금지** → 해시태그는 설명란에 3~4개만
- **보도체 금지** — 어미 `한다/합니다/습니다/입니다/이다/된다/됐다`, 과거형 `~았/었/였/졌/쳤/렸/꼈/혔/웠/했다`, 단어 `논란/현황/총정리/공방/설명/촉구/발표`가 있으면 차단
- 우회: `"yt_title_lint": "off"` (권장하지 않음)

**경고 (권장)**
- 길이: 코드 lint는 15~30자에 경고, 034 벤치마크 권장은 **12~20자**
- 실명 1~2개 포함
- `속보/충격!`형 금지 — 실측상 천장이 낮다
- **결과 없는 공방형 경고**: `직격·저격·공방·정면충돌·맞불·발끈·일침·돌직구·질타·반박·역공·설전`만 있고
  `결국·끝내·만에·끝에·무산·철회·사퇴·번복·뒤집·역전·확정·통과·부결·컴백·복귀·실형·선고·기각·구속·해임·경질` 같은 결과어가 없으면 경고

좋은 예: `'무섭노' 한마디에 사상검증, 결국 사과한 조국` / `죽창 들자던 사람이, 9시간 만에 물러섰다`
나쁜 예: `이준석, 조국 사상검증 논란 직격` (보도체 + 공방형 + 결과 없음)

### 5-C. 중반 CTA — 댓글율 개선 장치

| 규칙 | 값 |
|---|---|
| 위치 | 전체 길이의 **40% 지점**에 가장 가까운 씬 경계 (`at_frac`으로 조정) |
| 금지 위치 | 훅(scene 0) 앞, 마지막 씬 뒤 |
| 형식 | **편 가르는 선택지형 필수** — `①/②`, `1번/2번`, `누구 잘못`, `어느 쪽`, `찬성/반대`, `vs` |
| 길이 | 나레이션 **4초(약 32자) 이내** |
| 중복 | 다른 씬 나레이션에 "댓글/덧글"이 남아 있으면 경고 (CTA는 1회만) |

```json
"cta": {
  "text": "이거 누구 잘못?\n① 조국  ② 이준석",
  "voice": "누구 잘못일까요? 1번 조국, 2번 이준석. 번호로 답글.",
  "hl": ["누구 잘못"],
  "at_frac": 0.4
}
```

"여러분 생각은 어떠신가요?" 같은 열린 질문은 실측 댓글율 0.24%. **편이 갈려야 답글이 붙는다.**

삽입 알고리즘: 씬별 예상 길이를 누적하며 `0.4 × 전체` 에 가장 가까운 경계 인덱스를 고르고, 그 자리에 tts 씬을 끼워 넣는다(인덱스는 1 이상, 마지막 이하로 클램프).

### 5-D. 사실 검증·법적 선

- 발언 인용은 **원본 영상에서 직접 확인**한 문장만 (기사 재인용으로 자막을 쓰지 않는다)
- 확정되지 않은 혐의는 "혐의", "주장"으로 표기
- 출처(채널명·영상 제목·URL)를 설명란에 반드시 명시
- **자동 업로드 금지** — 정치 콘텐츠는 사람이 검수한 뒤 수동 업로드한다 (코드에도 가드가 걸려 있다)

---

## 6. 의견에 맞는 TTS 생성

### 6-A. 락인된 설정 (바꾸지 말 것)

| 항목 | 값 |
|---|---|
| 모델 | `gemini-2.5-flash-preview-tts` |
| 목소리 | **Charon** (앵커 톤) |
| 스타일 프롬프트 | `Read in a fast, clear newscaster tone with neutral political delivery:` |
| temperature | **0.5** (낮을수록 일정한 낭독) |
| 출력 | raw PCM **24kHz / 16-bit / mono** (WAV 헤더 없음) |
| 배속 | `atempo=1.1` (육성 클립에는 적용하지 않는다) |

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
style = "Read in a fast, clear newscaster tone with neutral political delivery:"
resp = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=f"{style} {narration_text}",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        temperature=0.5,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon"))),
    ),
)
pcm = resp.candidates[0].content.parts[0].inline_data.data  # 헤더 없는 PCM
```

PCM → mp3:
```bash
ffmpeg -f s16le -ar 24000 -ac 1 -i voice.pcm -codec:a libmp3lame -q:a 2 voice.mp3
```

### 6-B. 씬 타이밍 계산

무료 티어가 5 RPM이라 **모든 나레이션을 한 번에 합성**한 뒤, 씬별 **글자 수 비율**로 구간을 나눈다.
그다음 실제 무음 지점으로 경계를 보정한다(`src/tts/silence_align.py`). 배속을 걸면 타이밍도 `1/speed`로 스케일한다.

### 6-C. 알려진 함정

- **런어웨이 캐시**: TTS가 수백 초짜리 무음을 붙여 렌더가 실패하는 경우 → `data/tts_cache/<key>` 삭제 후 재합성
- **429 RESOURCE_EXHAUSTED**: 콘텐츠 해시 캐시(`data/tts_cache/{hash}.mp3`)나 제목 매칭 폴백으로 재사용
- Gemini TTS는 **비결정적** — 같은 텍스트도 합성마다 길이가 달라진다. 그래서 길이 판정은 항상 합성 후 실측으로 한다
- 긴 한국어 정치 텍스트 + style_prompt 조합에서 간헐적으로 빈 응답이 온다 → 지수 백오프로 재시도(1·2·4·8초)
- **대안**: `edge-tts` 무료, `ko-KR-SunHiNeural` (품질은 Charon보다 낮지만 한도가 없다)

---

## 7. 조립 · 검수 · 업로드

### 7-A. 최종 타임라인 조립

```
전체 오디오 = [클립0 원본음성][TTS 세그먼트][클립1 원본음성][CTA TTS]…
전체 영상   = 씬별 9:16 mp4를 타이밍 순서대로 이어붙임 + 배경 그라데이션 + 아웃트로 4초
```
- BGM은 사용, **인트로 BGM은 끔** (0초의 육성을 덮지 않도록)
- 전환 효과·효과음은 끔 (SFX는 프로젝트 전역 비활성)

### 7-B. 업로드 패키지 (`upload_package.md` 자동 생성)

- 제목 A/B안 (+ lint 경고)
- 설명: 요약 / `출처: 채널명 — 영상 제목` / 원본 URL / 해시태그
- 해시태그: `persons` 기반 `#인물명` 최대 4개
- 고정댓글: `pinned_comment` > `cta.voice` > 기본 선택지형 문구
- 권장 업로드 시각: **가장 가까운 평일 20:00**
- 썸네일 후보 3장 (영상의 2% / 25% / 55% 지점 프레임)

### 7-C. 업로드 전 체크리스트

- [ ] 썸네일이 인물 표정 절정 컷인가 (웃음/한숨/야유/침묵)
- [ ] 같은 주제 V2.1/V2.2 중복 업로드 금지 — **플랫폼 분리 (V2.2→유튜브, V2.1→틱톡)**
- [ ] 제목에 해시태그 없음 · 해시태그는 설명란 3~4개만
- [ ] 길이 38~42초인가
- [ ] CTA가 40% 지점에 있고 편 가르는 선택지형인가
- [ ] 소재가 '누가 누구를 저격'이 아니라 '결과가 난 사건'인가
- [ ] 정치 콘텐츠 — **검수 후 수동 업로드**

### 7-D. 운영 리듬

일 1~3편, 평일 20~21시, 2~3주 무공백. 이 리듬 없이는 어떤 개선도 측정되지 않는다.

---

## 8. 예외 상황 대응

| 상황 | 대응 |
|---|---|
| 당사자 육성 영상이 없다 (전언 보도·보도자료) | 기사 화면을 캡처해 **세로 팬을 건 mp4**로 만들고 TTS가 원문을 읽는다. 출력은 **16:9(1080×608)** 로 만들어야 다른 소스와 비율이 같아 하단 자막이 본문을 덮지 않는다 (`scripts/capture_article.py`) |
| 같은 소스를 여러 씬에 쓴다 | 씬마다 `frac`(시작 위치 비율)을 다르게 → 같은 프레임 반복 방지 |
| 클립 뒤쪽이 모자라 화면이 얼어붙는다 | 남은 소스 길이 < 씬 길이 → 시작점을 앞당기거나 다른 소스로 교체 |
| 길이 캡에 걸린다 | ① 나레이션 글자 수 줄이기 ② 씬 1개 빼기 ③ 최후에 `duration_gate: "off"` |
| 유튜브 검색이 엉뚱한 인물을 가져온다 | `query`에 소속·직함을 추가하고 `download --force` |

---

## 9. 다른 도구로 옮길 때 필요한 상수 요약

```python
# 길이
CHARS_PER_SEC_1X = 7.4      # 한국어 Charon 낭독 (1.0배속 실측 중앙값)
DEFAULT_TTS_SPEED = 1.1     # 표준 배속 → 실효 8.14자/초
TARGET_MIN_SEC, TARGET_MAX_SEC = 38.0, 42.0
OUTRO_SEC = 4.0             # 렌더 시 항상 덧붙음

# 클립
HOOK_MIN_SEC, HOOK_MAX_SEC = 1.0, 10.0    # 훅(scene 0)
CLIP_BODY_MAX_SEC = 12.0                  # 본문 육성 클립
CUT_MAX_SEC = 60.0                        # ffmpeg 컷 상한
FPS = 30                                  # 클립 길이는 이 격자에 반올림
AAC_PRIMING_COMP_MS = 44                  # 립싱크 보정
CLIP_RATIO_MIN = 0.65                     # V2.2 육성 오디오 비중 하한

# CTA / 패키징
CTA_AT_FRAC = 0.4
CTA_MAX_SEC = 4.0
MAX_HASHTAGS = 4
UPLOAD_HOUR = 20

# 영상
SHORTS_WIDTH, SHORTS_HEIGHT = 1080, 1920
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
SUBTITLE_COLORS = {"white": "#FFFFFF", "red": "#FF4444",
                   "yellow": "#FFD93D", "blue": "#5DADE2"}
SUBTITLE_POS_Y = {"default": 0.652, "hook": 0.5, "bottom": 0.78}
```

---

## 10. 함께 보는 문서

- `docs/gemini/02-gem-instructions.md` — Gemini Gem에 그대로 붙여 넣는 지침(압축본)
- `docs/gemini/03-prompt-templates.md` — 단계별 복붙 프롬프트
- `scripts/political_v2_configs/README.md` — config 전체 스키마
- `scripts/political_v2_configs/_template_v2_1.json` / `_template_v2_2.json` — 실제 예시
