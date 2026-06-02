# REST API Contract — Dem-Shorts Studio

**Base path**: `/api/dem-shorts`
**Auth**: 동일 머신 단일 사용자, 세션 인증 불필요 (MVP)
**Format**: JSON request/response, SSE 진행 스트림

---

## SourceVideo 대시보드

### GET `/api/dem-shorts/videos`
신규 NATV 영상 우선순위 목록 조회 (FR-004, US1).

**Query params**:
| 이름 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `since_hours` | int | 24 | 최근 N시간 |
| `min_score` | float | 0 | 최소 민주당 점유도 |
| `session_type` | str | (all) | 필터 |
| `include_excluded` | bool | false | 자동 제외 포함 여부 (FR-005) |
| `limit` | int | 50 | 최대 |

**Response 200**:
```json
{
  "videos": [
    {
      "video_id": "abc123",
      "title": "제422회 국회 본회의",
      "published_at": "2026-04-15T14:00:00+09:00",
      "duration_sec": 7200,
      "thumbnail_url": "https://...",
      "session_type": "plenary",
      "dem_score": 82.5,
      "stt_status": "done",
      "status": "ready",
      "excluded_reason": null
    }
  ],
  "total": 12
}
```

---

### GET `/api/dem-shorts/videos/:videoId`
단일 영상 + 발언 구간 타임라인 (US2).

**Response 200**:
```json
{
  "video": { /* SourceVideo 전체 필드 */ },
  "segments": [
    {
      "id": 42,
      "start_sec": 120.5,
      "end_sec": 178.0,
      "politician": {"id": 1, "name": "이재명", "photo_url": "..."},
      "confidence": 0.92,
      "stt_text": "민생 경제를 위해...",
      "recommendation_score": 78.0,
      "issue_keywords": ["민생", "경제"],
      "is_solo": true
    }
  ]
}
```

**Error 404**: 영상 없음 or `status='excluded'`.

---

## Whitelist 관리

### GET `/api/dem-shorts/whitelist`
정치인 목록 조회.

**Query**: `tier`, `category`, `active`

**Response 200**:
```json
{"politicians": [/* Politician[] */]}
```

### POST `/api/dem-shorts/whitelist`
정치인 추가 (FR-007).

**Body**:
```json
{
  "name": "전용기",
  "party": "더불어민주당",
  "role": "국회의원",
  "tier": "pinned",
  "category": "youth",
  "bio": "...",
  "tone_guide": "..."
}
```

**Response 201**: 생성된 Politician.
**Error 409**: 이미 존재하는 이름.
**Error 400**: `tier='auto'`로 직접 등록 불가 (FR-009, 랭킹 배치만 가능).

### PATCH `/api/dem-shorts/whitelist/:id`
등급·카테고리·활성 변경.

### DELETE `/api/dem-shorts/whitelist/:id`
제거 (`tier='pinned'`은 경고 후 허용).

---

## ShortsDraft 편집 플로우

### POST `/api/dem-shorts/drafts`
발언 구간에서 쇼츠 초안 생성 (US3 시작).

**Body**:
```json
{
  "segment_id": 42,
  "cut_start_sec": 125.0,
  "cut_end_sec": 175.0,
  "subtitle_preset": "leejaemyung"
}
```

**Validation**:
- `cut_end - cut_start <= 60` (FR-018) — 위반 시 400
- `subtitle_preset` ∈ 5 enum
- `segment_id` 존재

**Response 201**: 생성된 ShortsDraft (status=`draft`).

---

### POST `/api/dem-shorts/drafts/:id/commentary`
AI 해설 자막 후보 3개 생성 (FR-020).

**Body**:
```json
{
  "tone_hint": "팩트 기반 객관적",
  "max_chars_per_candidate": 15
}
```

**Response 200**:
```json
{
  "candidates": [
    {"text": "민생경제 3% 성장 강조", "confidence": 0.85},
    {"text": "이재명, 국회서 정면돌파", "confidence": 0.78},
    {"text": "야당과 공방, 결국 합의", "confidence": 0.72}
  ]
}
```

**내부**: Claude CLI 호출 → 비용 $0 (원칙 I).

---

### PATCH `/api/dem-shorts/drafts/:id`
해설 자막 블록·TTS·BGM 업데이트.

**Body**:
```json
{
  "commentary_blocks": [
    {"start": 0, "end": 3, "text": "민생경제\n3% 성장 강조", "style": "high"}
  ],
  "tts_voice": "male_stable",
  "tts_enabled": true,
  "bgm_filename": "calm_01.mp3",
  "fact_source_urls": ["https://news.example.com/1", "https://news.example.com/2"]
}
```

**검증**:
- `bgm_filename`이 `bgm_manifest.json` 등록된 파일인지 확인 (FR-035)
- `commentary_char_count` 자동 재계산

---

### POST `/api/dem-shorts/drafts/:id/gate`
**컴플라이언스 게이트 실행** (FR-025, SC-005 **핵심**).

**Body**:
```json
{
  "manual_fact_check": true,
  "manual_defamation_check": true,
  "operator_id": "owner"
}
```

**Response 200**:
```json
{
  "overall_status": "pass",
  "risk_score": 24.5,
  "items": {
    "1_commentary_length": "pass",
    "2_ratio": "pass",
    "3_duration": "pass",
    "4_source_label": "pass",
    "5_bias_guardrail": "warn",
    "6_template_repeat": "pass",
    "7_whitelist_person": "pass",
    "8_election_guard": "pass",
    "9_fact_checked": "pass",
    "10_no_defamation": "pass"
  },
  "failure_reasons": [],
  "warnings": [{"item": 5, "reason": "단정 표현 1회 감지: '절대'"}]
}
```

**Response 400** (게이트 실패 예시):
```json
{
  "overall_status": "fail",
  "risk_score": 68.0,
  "items": { "1_commentary_length": "fail", ... },
  "failure_reasons": [
    {"item": 1, "reason": "해설 자막 38자 (50자 이상 필요)"},
    {"item": 10, "reason": "수동 명예훼손 체크 미확인"}
  ]
}
```

**핵심 보안 (SC-005)**:
- 어떤 파라미터로도 게이트 우회 불가
- `manual_*_check`이 false면 `item_9/10='fail'`
- `risk_score >= 61` → 강제 `overall_status='fail'` (FR-026)

---

### POST `/api/dem-shorts/drafts/:id/render`
렌더링 트리거. **게이트 통과한 draft만 허용**.

**Response 200**: SSE 진행 스트림
```
data: {"type": "progress", "stage": "subtitle_rendering", "pct": 20}
data: {"type": "progress", "stage": "audio_mixing", "pct": 50}
data: {"type": "progress", "stage": "encoding", "pct": 90}
data: {"type": "done", "rendered_path": "outputs/drafts/42.mp4", "duration_sec": 58}
```

**Response 403**: 게이트 미통과
```json
{"error": "gate_not_passed", "detail": "먼저 /gate 엔드포인트를 통과해야 합니다"}
```

---

### POST `/api/dem-shorts/drafts/:id/upload`
YouTube 업로드 (FR-036, FR-037).

**Body**:
```json
{
  "title": "이재명 '민생경제 3% 성장' 정면돌파",
  "description": "...\n\n📺 출처: NATV 국회방송\n📰 팩트 링크: ...",
  "tags": ["이재명", "민생", "국회", "NATV"],
  "scheduled_publish_at": "2026-04-17T18:00:00+09:00",
  "operator_confirmed": true
}
```

**Validation**:
- `operator_confirmed=true` 필수 (FR-037)
- `description`에 "NATV 국회방송" 포함 검증 (FR-029)
- `len(fact_links) >= 2` 검증
- 게이트 통과 재확인 (이중 방어)

**Response 200**:
```json
{
  "youtube_video_id": "xyz789",
  "youtube_url": "https://youtube.com/shorts/xyz789",
  "published_at": "2026-04-17T18:00:00+09:00"
}
```

**Response 403**: 게이트/팩트/출처 검증 실패.

---

## 랭킹·리포트·선거

### GET `/api/dem-shorts/rankings`
주간 랭킹 조회 (FR-008).

**Query**: `week_start` (기본=이번주)

**Response 200**:
```json
{
  "week_start": "2026-04-13",
  "rankings": [
    {"rank": 1, "politician": {...}, "score": 87.3, "delta": +5.2, "tag": "rising"},
    ...
  ]
}
```

### POST `/api/dem-shorts/rankings/run`
주간 랭킹 배치 수동 실행 (정기 실행은 매주 일 22:00 cron).

---

### GET `/api/dem-shorts/reports`
월간 편향 리포트 (FR-038).

**Query**: `month` (기본=지난달)

**Response 200**: BiasReport 객체.

---

### GET `/api/dem-shorts/election`
현재 선거기간 상태 (FR-030).

**Response 200**:
```json
{
  "in_election_period": false,
  "next_election": {
    "type": "presidential_election",
    "date": "2027-05-03",
    "days_until": 382,
    "guard_threshold_days": 180
  },
  "neutral_mode_enforced": false
}
```

선거기간 진입 시 `in_election_period=true`, 모든 게이트에서 편향 임계값 30점 적용 (FR-031).
