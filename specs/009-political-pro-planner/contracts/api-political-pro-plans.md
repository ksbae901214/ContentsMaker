# Contract: POST /api/political-pro/plans

**Purpose**: YouTube 정치 영상 URL을 받아 3개의 ShortsPlan을 생성.

**Spec Mapping**: FR-001 ~ FR-008

---

## Request

```http
POST /api/political-pro/plans
Content-Type: application/json
```

```json
{
  "youtubeUrl": "https://www.youtube.com/watch?v=..."
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `youtubeUrl` | `string` | ✅ | YouTube 영상 URL (watch / youtu.be / shorts 모두 허용) |

---

## Response (Success — 200 OK)

```json
{
  "plans": [
    {
      "topic": "...",
      "hook": "...",
      "clipStartSec": 45.0,
      "clipEndSec": 75.0,
      "clipReason": "...",
      "flowIntro": "...",
      "flowMiddle": "...",
      "flowClimax": "...",
      "narrations": [
        {"startSec": 0, "endSec": 3, "text": "지금 이 장면..."},
        {"startSec": 3, "endSec": 7, "text": "..."}
      ],
      "cta": "...",
      "angle": "title_anchor"
    },
    { "...angle": "audience_resonance" },
    { "...angle": "comparison" }
  ],
  "videoPath": "/.../data/political_pro/20260513_184500_xyz/source.mp4",
  "videoDurationSec": 612.4,
  "transcriptPath": "/.../data/political_pro/20260513_184500_xyz/transcript.json",
  "videoTitle": "원본 영상 제목",
  "generatedAt": "2026-05-13T18:45:00+09:00"
}
```

### 보장
- `plans.length === 3`
- 각 plan의 `angle`은 서로 다름
- `clipStartSec < clipEndSec ≤ videoDurationSec`
- 각 plan은 RTF 6요소 모두 채워짐(빈 문자열 없음)

---

## Response (Error — 4xx / 5xx)

| Code | `error` | 발생 조건 | FR |
|------|---------|----------|-----|
| 400 | `invalid_url` | URL 형식 오류 또는 YouTube 도메인 아님 | FR-001 |
| 422 | `transcript_unavailable` | 자막 없음 + STT 실패 (둘 다) | FR-003 |
| 422 | `empty_transcript` | transcript는 있으나 의미 있는 발언 구간 없음 | spec Edge Case |
| 502 | `youtube_download_failed` | yt-dlp 다운로드 실패 (비공개·삭제·지역 제한) | spec Edge Case |
| 502 | `claude_plan_generation_failed` | Claude 호출 또는 JSON 파싱 1회 재시도 후에도 실패 | FR-008 |
| 504 | `timeout` | 전체 처리 90초 초과 | SC-001 |

### Error 본문 형식

```json
{
  "error": "transcript_unavailable",
  "detail": "사용자에게 표시할 1줄 메시지",
  "youtubeUrl": "...(원본 URL)"
}
```

---

## SSE 스트리밍 (옵션)

대안으로 `Accept: text/event-stream` 헤더 시 SSE로 진행 상황 전달:

```
event: progress
data: {"stage": "video_download", "message": "🎬 다운로드 중...", "expectedSeconds": 90}

event: progress
data: {"stage": "transcribe", "message": "🎙️ 음성 인식 중...", "expectedSeconds": 60}

event: progress
data: {"stage": "claude_plans", "message": "🤔 3 기획안 생성 중...", "expectedSeconds": 120}

event: done
data: {"plans": [...], "videoPath": "...", ...}
```

---

## Acceptance Tests

| 테스트 | 검증 항목 |
|--------|-----------|
| `T1: happy path` | 정상 정치 영상 URL → 200, plans.length=3, 모든 angle 다름 |
| `T2: invalid URL` | "not-a-url" → 400 invalid_url |
| `T3: no transcript` | 자막·STT 모두 실패 영상 → 422 transcript_unavailable |
| `T4: empty clip text` | 음악만 있는 영상 → 422 empty_transcript |
| `T5: claude retry success` | 첫 호출 JSON 파싱 실패 → 자동 재시도 성공 → 200 |
| `T6: claude retry fail` | 두 번 모두 실패 → 502 claude_plan_generation_failed |
| `T7: timeout` | 90초 초과 → 504 timeout |
