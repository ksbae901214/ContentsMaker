# 039 — 하루 3편 자동 제작·업로드

하루 3슬롯을 무인으로 돌린다. **기존 렌더러(`render_political_v2_2.py`)는 한 줄도
수정하지 않는다** — 이 패키지는 그 앞단에서 config 를 만들어 주는 생산자다.

| 슬롯 | 시각(KST) | 카테고리 | 소재 범위 | 포맷 |
|---|---|---|---|---|
| `morning` | 07:00 | political | 전날 00:00~24:00 | V2.2 (+V2.1) |
| `noon` | 12:00 | economic | 전날 00:00~24:00 | V2.2 (+V2.1) |
| `evening` | 18:00 | entertainment | **당일** 00:00~현재 | V2.2만 (036) |

```
topic_ranker    소재 후보 (댓글수/조회수 순)
  → source_finder   yt-dlp 검색 → 채널 정책 필터
  → cut_planner     자동자막 → 단어 타임스탬프 → 문장 경계 컷 (037-2)
  → config_drafter  Claude 초안 → 게이트 통과까지 최대 3회 재작성
  → render_political_v2_2.py download → render   (기존, 무수정)
  → review_gate     게시 / 보류
  → upload_shorts   YouTube 공개 + TikTok 초안 + 고정댓글
  → notify          결과 요약
```

## 실행

```bash
PYTHONPATH=. .venv311/bin/python -m scripts.auto_daily.runner --slot morning
PYTHONPATH=. .venv311/bin/python -m scripts.auto_daily.launchd --install
launchctl load ~/Library/LaunchAgents/com.contentsmaker.auto-daily-morning.plist
```

산출물: `data/auto_daily/{YYYYMMDD}_{slot}/` — `topics.json`, `config.json`, `_sub/`.
영상과 `upload_package.md` 는 렌더러 규칙대로 `data/political_pro/{slug}/` 에 생긴다.

## 시작 전 반드시 해야 하는 3가지

이걸 안 하면 **모든 슬롯이 보류로 끝난다** (그게 의도된 기본값이다).

1. **채널 화이트리스트 등록** — `data/auto_daily/channel_policy.json` 의 `allow` 가
   비어 있으면 후보가 0이다. 등록 기준은 그 파일의 `_comment` 참고 (037-3).
2. **YouTube OAuth** — `python3 -m src.main youtube-auth` (토큰이 없으면 업로드 불가)
3. **TikTok 인증** — 앱 등록 후 `python3 -m src.main tiktok-auth`

## 자동화되지 않는 것 — 숨기지 말 것

| | 왜 | 사람이 할 일 |
|---|---|---|
| **게시 승인** | 초기 2주 전면 보류가 확정 정책. 저작권 스트라이크는 되돌릴 수 없다 | 알림 확인 → 승인 |
| **TikTok 게시** | API 가 `SELF_ONLY` 고정. 공개 게시는 심사 통과 앱만 | 앱에서 1탭 게시 |
| **댓글 고정** | YouTube Data API v3 에 고정 엔드포인트가 **없다** | 스튜디오에서 고정 |
| **훅 품질** | 게이트는 형식만 본다. 밋밋한 훅은 안 걸린다 | 보류분 채택률 측정 |

`always_hold` 를 끄는 조건은 `data/auto_daily/review_policy.json` 의 `_comment` 에 있다.

## 설계 메모

- **실패 격리** — 소재 하나가 실패하면 다음 소재로, 컷을 못 뽑으면 다음 후보로
  넘어간다. 어느 단계도 예외를 위로 던지지 않는다. 아침이 죽었다고 점심·저녁까지
  날아가면 안 된다.
- **원본은 URL 로 고정** — `config_drafter` 가 `sources.main.url` 에 정확한 영상
  URL 을 박는다. 검색어를 남기면 렌더러가 같은 검색으로 **다른 영상**을 받아
  모든 컷이 엉뚱한 구간을 가리킨다. 렌더는 성공하고 내용만 틀리는 최악의 실패다.
- **게이트는 새로 만들지 않는다** — `validate_config` / `config_warnings` 를 그대로
  부른다. 두 벌이 되면 034/035/036 게이트가 조용히 갈라진다.
- **컷은 말 끝맺음까지** — 눈대중·블록 타임스탬프 금지. 단어 단위 타임스탬프에서
  종결어미 + 휴지로 문장 경계를 잡는다. 상한을 넘는 문장은 자르지 않고 **버린다**.
