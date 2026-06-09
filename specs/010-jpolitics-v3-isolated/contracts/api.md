# Contract: HTTP API — `/api/jpolitics/*`

V3 격리 모드 Next.js API 라우트. 기존 `/api/*`와 분리.

## Endpoint 1: `POST /api/jpolitics/plans`

3개 기획안 생성 요청.

### Request Body (YouTube 모드)

```json
{
  "sourceType": "youtube",
  "youtubeUrl": "https://www.youtube.com/watch?v=...",
  "videoTitle": "(선택) 사용자가 명시한 영상 제목"
}
```

### Request Body (Topic 모드)

```json
{
  "sourceType": "topic",
  "topic": "양향자 vs 추미애 경기도지사 대결",
  "tone": "분노·격앙",
  "details": ""
}
```

### Response (200 OK)

```json
{
  "ok": true,
  "outputDir": "data/jpolitics/20260605_104530_경기지사_대결",
  "videoTitle": "양향자 추미애 첫 공방",
  "videoDurationSec": 167.3,
  "plans": [
    {
      "rank": 1,
      "angle": "title_anchor",
      "formatType": "A",
      "layoutClassification": "vs_2way",
      "topic": "...",
      "hook": "...",
      "clipSection": "01:23~01:45",
      "reason": "...",
      "flowIntro": "...",
      "flowMiddle": "...",
      "flowClimax": "...",
      "narrations": [
        {
          "sceneId": 0,
          "text": "양향자, 추미애에 첫 공격",
          "voiceText": "양향자 후보가 추미애 후보에게 먼저 공격에 나섰습니다.",
          "visualLayout": "vs_card",
          "subtitleColor": "yellow",
          "subtitleEmphasis": true,
          "cardsMetadata": [
            {"name": "양향자", "party": "국민의힘"},
            {"name": "추미애", "party": "더불어민주당"}
          ]
        }
      ],
      "cta": "여러분의 생각은 어떠신가요?",
      "headlinePin": "양향자 추미애 첫 공방",
      "youtubeSearchKeywords": null
    }
  ]
}
```

### Response (4xx/5xx)

```json
{
  "ok": false,
  "error": "transcript_extraction_failed",
  "message": "자막을 추출할 수 없습니다. 주제 입력 모드로 다시 시도하세요."
}
```

| HTTP | error 코드 | 의미 |
|---|---|---|
| 400 | `invalid_input` | URL 형식 오류, 필수 필드 누락 |
| 422 | `transcript_extraction_failed` | YouTube 비공개/삭제/지역제한 |
| 500 | `planner_failure` | Gemini/Claude API 오류 |
| 429 | `rate_limit_exceeded` | 외부 API 무료 한도 초과 |

## Endpoint 2: `POST /api/jpolitics/render`

선택한 기획안 + 검수 결과로 영상 생성.

### Request Body

```json
{
  "outputDir": "data/jpolitics/20260605_104530_경기지사_대결",
  "selectedPlanRank": 2,
  "scriptOverrides": {
    "scenes": [
      {
        "id": 0,
        "text": "양향자의 첫 공격, 추미애 맞대응",
        "visualLayout": "vs_card",
        "subtitleColor": "yellow",
        "subtitleEmphasis": true,
        "headlinePin": "양향자 추미애 첫 공방"
      }
    ]
  }
}
```

`scriptOverrides`는 사용자가 검수 화면(FR-013~015)에서 수정한 필드만 포함. 미수정 필드는 기획안 원본 사용.

### Response (200 OK)

```json
{
  "ok": true,
  "videoPath": "data/jpolitics/20260605_104530_경기지사_대결/video.mp4",
  "videoDurationSec": 52.3,
  "scriptPath": "data/jpolitics/20260605_104530_경기지사_대결/script.json",
  "summaryPath": "data/jpolitics/20260605_104530_경기지사_대결/summary.txt",
  "summary": {
    "lines": [
      "양향자 후보의 첫 공격에 추미애 후보가 즉답으로 맞섰다.",
      "경기도지사 자리를 둘러싼 양 후보의 대결 구도가 본격화됐다.",
      "민주당과 국민의힘의 정치 색깔이 영상 한 장면에 응축됐다."
    ],
    "hashtags": ["#양향자", "#추미애", "#경기도지사", "#지방선거", "#민주당", "#국민의힘", "#정치", "#2026선거"]
  }
}
```

### Streaming (SSE 옵션)

`Accept: text/event-stream` 헤더 시 진행 상황 스트리밍:

```
event: progress
data: {"step": "tts", "percent": 30}

event: progress
data: {"step": "render", "percent": 60}

event: complete
data: {"videoPath": "...", "summary": {...}}
```

### Response (4xx/5xx)

| HTTP | error 코드 | 의미 |
|---|---|---|
| 400 | `invalid_input` | outputDir 미존재, selectedPlanRank 범위 초과 |
| 404 | `plans_not_found` | plans.json 없음 (재실행 시 plans 먼저 호출 필요) |
| 500 | `tts_failure` / `render_failure` | TTS 또는 Remotion 렌더 오류 |

## Endpoint 3: `GET /api/jpolitics/politician-card/:name`

인물 카드 페치 (캐시 우선).

### Response (200 OK)

```json
{
  "ok": true,
  "card": {
    "name": "양향자",
    "party": "국민의힘",
    "partyColor": "#E61E2B",
    "photoPath": "data/politician_cards/photos/양향자.jpg",
    "photoUrl": "/api/jpolitics/photo/양향자.jpg",
    "cached": true,
    "fetchedAt": "2026-06-04T18:23:10"
  }
}
```

### Response (Photo 없음)

```json
{
  "ok": true,
  "card": {
    "name": "신생당후보",
    "party": "기타",
    "partyColor": "#888888",
    "photoPath": null,
    "photoUrl": null,
    "cached": false,
    "fetchedAt": "2026-06-05T10:45:30"
  }
}
```

## 공통 헤더

- `Content-Type: application/json` (요청·응답)
- `X-V3-Mode: jpolitics` (디버깅용 식별자)

## 격리 보증

- `/api/jpolitics/*` 라우트는 `/api/*` 기존 핸들러와 독립 (`app/api/*` vs `app/jpolitics/api/*`).
- 동시 호출 시 디렉토리 충돌 없음 (`data/jpolitics/{ts}_{slug}/` 격리).
- V1/V2 API의 어떤 응답도 영향받지 않음 (SC-010).
