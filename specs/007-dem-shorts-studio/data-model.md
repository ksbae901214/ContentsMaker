# Phase 1 Data Model: Dem-Shorts Studio

**Feature**: 007-dem-shorts-studio
**Storage**: SQLite (`data/dem_shorts/state.db`) + JSON pipeline files + 파일 시스템(미디어)
**Persistence**: Frozen dataclass (원칙 VI) with `to_dict()` / `from_dict()` serialization

---

## Entity Relationship Overview

```
Politician 1 ──── N SpeechSegment ──── N ShortsDraft 1 ──── 1 ComplianceGateResult
  │                       │                    │
  │                       │                    └─── 1 UploadedShorts
  │                       │
WeeklyRanking N ─── 1 Politician       SourceVideo 1 ── N SpeechSegment
                                                │
                                           BiasReport (월별 집계)
```

---

## 1. SourceVideo — NATV에서 수집된 원본 영상

**저장소**: SQLite `source_videos` 테이블
**수명주기**: `new` → `downloading` → `stt_running` → `ready` → `archived` | `excluded`

```python
@dataclass(frozen=True)
class SourceVideo:
    video_id: str                    # YouTube video ID (PK)
    title: str
    description: str
    published_at: datetime           # 게시일 (KST)
    duration_sec: int
    thumbnail_url: str
    session_type: str                # "plenary"/"committee"/"audit"/"hearing"/"press"/"other" (FR-003)
    download_path: str | None        # archive/{video_id}.mp4
    stt_status: str                  # "pending"/"running"/"done"/"failed"
    diarization_status: str          # "pending"/"running"/"done"/"failed"
    dem_score: float                 # 민주당 점유도 0~100 (FR-004)
    excluded_reason: str | None      # None / "length_over_6h" / "no_dem_politician" / "dem_score_zero"
    status: str                      # "new"/"downloading"/"stt_running"/"ready"/"archived"/"excluded"
    created_at: datetime
    updated_at: datetime
```

**검증 룰**:
- `duration_sec > 21600` (6시간) → `status='excluded'`, `excluded_reason='length_over_6h'` (FR-002)
- `dem_score == 0` → `excluded_reason='no_dem_politician'` (FR-005)
- `session_type` 값은 enum 6개 중 하나 필수

**인덱스**: `video_id`(PK), `published_at DESC`, `dem_score DESC`, `status`

---

## 2. Politician — Whitelist 관리 대상

**저장소**: SQLite `politicians` 테이블

```python
@dataclass(frozen=True)
class Politician:
    id: int                          # PK, auto-increment
    name: str                        # "이재명"
    party: str                       # "더불어민주당"/"조국혁신당"/"국민의힘"/...
    role: str                        # "국회의원"/"당대표"/"위원장"/...
    photo_url: str | None
    bio: str                         # 대표 이력
    tone_guide: str                  # "민생·개혁 리더 톤. 직설적이되 공격성 자제"
    tier: str                        # "pinned"/"auto"/"pending"/"blocked" (FR-007, FR-009)
    category: str                    # "fixed"/"female"/"youth"/"alliance" (FR-008, FR-011)
    is_active: bool                  # False → 식별은 하지만 하이라이트 제외 (edge case)
    ranking_score: float | None      # 주간 랭킹 점수 (auto 등급에만)
    added_at: datetime
    updated_at: datetime
```

**초기 데이터** (FR-006):
```python
SEED_POLITICIANS = [
    {"name": "이재명", "party": "더불어민주당", "role": "당대표", "tier": "pinned", "category": "fixed"},
    {"name": "조국", "party": "조국혁신당", "role": "당대표", "tier": "pinned", "category": "fixed"},
    {"name": "정청래", "party": "더불어민주당", "role": "법제사법위원장", "tier": "pinned", "category": "fixed"},
]
```

**검증 룰**:
- `tier` ∈ {pinned, auto, pending, blocked}
- `category` ∈ {fixed, female, youth, alliance}
- `tier='auto'` 인물은 최대 20명 (FR-009)
- `tier='pending'` 2주 연속 유지 시 DELETE

**인덱스**: `id`(PK), `(tier, category)`, `name` UNIQUE

---

## 3. SpeechSegment — 영상 내 발언 구간

**저장소**: 원시 데이터는 JSON (`segments/{video_id}.json`, 단계 독립 실행용), 메타 요약은 SQLite `speech_segments`

```python
@dataclass(frozen=True)
class SpeechSegment:
    id: int                          # PK (SQLite)
    source_video_id: str             # FK → SourceVideo.video_id
    start_sec: float
    end_sec: float
    politician_id: int | None        # FK → Politician.id (None = 미식별)
    confidence: float                # 0~1 (FR-014)
    stt_text: str                    # 해당 구간 전사
    recommendation_score: float      # 쇼츠 추천 점수 (FR-016)
    emotion_strength: float          # 0~1 (!·? 빈도 + 볼륨 변화)
    issue_keywords: list[str]        # ["연금개혁", "대정부질문"]
    is_solo: bool                    # 단독 발언 구간 여부
    has_profanity: bool              # 욕설 감지 (추천 점수 -50점)
```

**검증 룰**:
- `end_sec > start_sec`
- `confidence < 0.7` → `politician_id = None`, UI에서 "(미식별)" 표시 (FR-014)
- `recommendation_score` 공식 (FR-016):
  ```
  score = (Whitelist 상위 인물 × 20) + (발언 길이 30~90초 = 40, else 감점)
        + (emotion_strength × 30) + (issue_keywords 수 × 5)
        + (is_solo × 10) - (has_profanity × 50)
  ```

**인덱스**: `(source_video_id, start_sec)`, `politician_id`, `recommendation_score DESC`

---

## 4. ShortsDraft — 제작 중인 쇼츠 초안

**저장소**: SQLite `shorts_drafts` + 편집 상세는 JSON (`drafts/{draft_id}.json`)
**수명주기**: `draft` → `gate_pending` → `gate_passed` → `rendering` → `rendered` → `uploaded` | `failed`

```python
@dataclass(frozen=True)
class ShortsDraft:
    id: int                          # PK
    segment_id: int                  # FK → SpeechSegment.id
    cut_start_sec: float             # 운영자가 자른 구간 시작
    cut_end_sec: float               # 끝 (cut_end - cut_start ≤ 60 per FR-018)
    commentary_blocks: list[dict]    # [{"start": 0, "end": 3, "text": "...", "style": "..."}]
    commentary_char_count: int       # 누적 글자 수 (FR-024 실시간 검증용)
    tts_voice: str | None            # "male_strong"/"male_stable"/"female_calm"/"female_young"
    tts_enabled: bool
    subtitle_preset: str             # FR-021: "leejaemyung"/"jungcheongrae"/"youth"/"hotissue"/"default"
    bgm_filename: str | None         # FR-035: bgm_manifest 등록된 파일만
    fact_source_urls: list[str]      # FR-029: 최소 2개 필수
    risk_score: float                # 0~100 (FR-026)
    status: str                      # "draft"/"gate_pending"/"gate_passed"/"rendering"/...
    rendered_path: str | None        # outputs/{draft_id}.mp4
    created_at: datetime
    updated_at: datetime
```

**검증 룰**:
- `cut_end_sec - cut_start_sec <= 60` (FR-018)
- `commentary_char_count >= 50` 아니면 gate 통과 불가 (FR-024, FR-025 게이트1)
- 원본 비율 ≤ 50% (FR-025 게이트2): 원본 구간 길이 / 전체 길이 ≤ 0.5
- `len(fact_source_urls) >= 2` (FR-029)
- `subtitle_preset` ∈ 5개 enum
- `bgm_filename` is None OR `bgm_manifest.json`에 등록된 파일

**인덱스**: `segment_id`, `status`, `updated_at DESC`

---

## 5. ComplianceGateResult — 10개 항목 검증 이력

**저장소**: SQLite `gate_results`
**Key**: FR-025의 10개 항목. **우회 불가 원칙 (SC-005)**.

```python
@dataclass(frozen=True)
class ComplianceGateResult:
    id: int
    draft_id: int                    # FK → ShortsDraft.id (1:1)

    # 10개 항목 (pass/fail/warn)
    item_1_commentary_length: str    # 해설 50자 이상 — 자동, 차단
    item_2_ratio: str                # 원본≤50%, 해설≥30% — 자동, 차단
    item_3_duration: str             # ≤60초 — 자동, 차단
    item_4_source_label: str         # NATV 출처 표시 — 자동, 차단
    item_5_bias_guardrail: str       # 편향 게이트 통과 — 자동, 경고
    item_6_template_repeat: str      # 최근 3회 연속 아님 — 자동, 경고
    item_7_whitelist_person: str     # Whitelist 인물 1명↑ — 자동, 차단
    item_8_election_guard: str       # 선거법 가드 — 자동, 차단
    item_9_fact_checked: str         # 팩트 검증 — 수동, 차단
    item_10_no_defamation: str       # 명예훼손 없음 — 수동, 차단

    # 수동 체크 서명 (운영자 확인)
    manual_fact_check_signed_by: str | None    # 운영자 ID, None이면 게이트 미통과
    manual_defamation_check_signed_by: str | None

    # 실패 사유 상세
    failure_reasons: list[dict]      # [{"item": 1, "reason": "해설 자막 38자"}]

    # 종합
    overall_status: str              # "pass"/"fail"/"warn_only"
    risk_score: float                # 0~100, 종합 리스크 (FR-026)

    validated_at: datetime
```

**검증 룰 (서버사이드 강제)**:
- `overall_status='pass'` iff 10개 아이템 모두 `pass` **AND** 수동 서명 2개 모두 NOT NULL (FR-025, SC-005)
- `risk_score >= 61` → 강제 차단 (FR-026, 게이트 통과 불가능)
- **프론트엔드 어떤 조작으로도 이 로직 우회 불가** — `drafts/[id]/render` 와 `drafts/[id]/upload` API 모두 이 테이블 조회 후 차단

**인덱스**: `draft_id` UNIQUE, `overall_status`

---

## 6. WeeklyRanking — 여성·청년 정치인 주간 랭킹

**저장소**: SQLite `weekly_rankings`

```python
@dataclass(frozen=True)
class WeeklyRanking:
    id: int
    week_start: date                 # 해당 주 월요일 00:00 KST
    politician_id: int               # FK → Politician.id
    rank: int                        # 1~20 (auto), 21+ (pending)
    score: float                     # 0~100
    delta_vs_prev_week: float        # 전주 대비 증감
    tag: str                         # "new"/"rising"/"pending"
    data_sources: dict               # {"naver_news": 35, "trends": 48, ...}
```

**검증 룰**:
- `(week_start, politician_id)` UNIQUE
- `rank ≤ 20` → Politician.tier=`auto` 자동 업데이트 (FR-009)
- 2주 연속 `rank > 20` → Politician.tier=`pending` 후 삭제
- 전주 대비 +15 이상 → 운영자 알림 (FR-008)

**인덱스**: `(week_start, rank)`, `politician_id`

---

## 7. UploadedShorts — YouTube 발행된 최종 쇼츠

**저장소**: SQLite `uploaded_shorts`

```python
@dataclass(frozen=True)
class UploadedShorts:
    id: int
    draft_id: int                    # FK → ShortsDraft.id
    final_mp4_path: str
    youtube_video_id: str            # YouTube ID
    title: str
    description: str                 # "... NATV 국회방송 ..." 포함 필수
    tags: list[str]
    scheduled_publish_at: datetime | None
    published_at: datetime | None    # 실제 공개 시각
    fact_links: list[str]            # 설명란에 포함된 팩트 출처
    view_count: int                  # YouTube API로 주기적 갱신
    like_count: int
    comment_count: int
    est_revenue: float | None        # YPP 승인 후
    is_taken_down: bool              # YouTube가 내림 여부
    takedown_reason: str | None
    uploaded_at: datetime
    metrics_updated_at: datetime
```

**검증 룰**:
- `description` 에 "NATV 국회방송" 문자열 반드시 포함 (FR-029)
- `len(fact_links) >= 2` (FR-029)
- `draft_id` UNIQUE (1 draft = 1 upload)
- `scheduled_publish_at` is None 또는 미래 시각

**인덱스**: `draft_id` UNIQUE, `published_at DESC`, `is_taken_down`

---

## 8. BiasReport — 월간 편향 밸런스 리포트

**저장소**: SQLite `bias_reports` (materialized view)

```python
@dataclass(frozen=True)
class BiasReport:
    id: int
    month: date                      # 해당 월 1일
    total_uploads: int
    person_shares: dict              # {"이재명": 0.20, "조국": 0.15, ...}
    party_shares: dict               # {"더불어민주당": 0.80, "조국혁신당": 0.20}
    template_usage: dict             # {"default": 12, "leejaemyung": 8, ...}
    avg_risk_score: float
    top_n_person_warning: list[str]  # 30% 초과한 인물들 (SC-011)
    recommendations: list[str]       # ["이재명 50% — 권장 30% 초과"]
    generated_at: datetime
```

**생성 규칙**:
- 매월 1일 자동 배치 생성 (FR-038)
- `person_shares[name] > 0.30` → 권고 메시지 추가 (SC-011)
- 이재명·조국·정청래 3인 합계 > 0.60 → 권고 (SC-011)
- `female/youth` 카테고리 합계 < 0.40 → 차별화 미달 권고 (SC-012)

**인덱스**: `month` UNIQUE

---

## SQLite 마이그레이션 스키마

**파일**: `src/dem_shorts/db/migrations/001_init.sql`

```sql
-- politicians
CREATE TABLE politicians (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  party TEXT NOT NULL,
  role TEXT,
  photo_url TEXT,
  bio TEXT,
  tone_guide TEXT,
  tier TEXT NOT NULL CHECK(tier IN ('pinned','auto','pending','blocked')),
  category TEXT NOT NULL CHECK(category IN ('fixed','female','youth','alliance')),
  is_active INTEGER NOT NULL DEFAULT 1,
  ranking_score REAL,
  added_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_politicians_tier_cat ON politicians(tier, category);

-- source_videos
CREATE TABLE source_videos (
  video_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  published_at TEXT NOT NULL,
  duration_sec INTEGER NOT NULL,
  thumbnail_url TEXT,
  session_type TEXT NOT NULL,
  download_path TEXT,
  stt_status TEXT NOT NULL DEFAULT 'pending',
  diarization_status TEXT NOT NULL DEFAULT 'pending',
  dem_score REAL NOT NULL DEFAULT 0,
  excluded_reason TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_sv_published ON source_videos(published_at DESC);
CREATE INDEX idx_sv_score ON source_videos(dem_score DESC);
CREATE INDEX idx_sv_status ON source_videos(status);

-- speech_segments
CREATE TABLE speech_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_video_id TEXT NOT NULL REFERENCES source_videos(video_id),
  start_sec REAL NOT NULL,
  end_sec REAL NOT NULL,
  politician_id INTEGER REFERENCES politicians(id),
  confidence REAL NOT NULL,
  stt_text TEXT,
  recommendation_score REAL NOT NULL DEFAULT 0,
  emotion_strength REAL DEFAULT 0,
  issue_keywords TEXT,              -- JSON array
  is_solo INTEGER DEFAULT 0,
  has_profanity INTEGER DEFAULT 0
);
CREATE INDEX idx_ss_video_start ON speech_segments(source_video_id, start_sec);
CREATE INDEX idx_ss_score ON speech_segments(recommendation_score DESC);

-- shorts_drafts
CREATE TABLE shorts_drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id INTEGER NOT NULL REFERENCES speech_segments(id),
  cut_start_sec REAL NOT NULL,
  cut_end_sec REAL NOT NULL,
  commentary_json TEXT,             -- JSON (commentary_blocks)
  commentary_char_count INTEGER NOT NULL DEFAULT 0,
  tts_voice TEXT,
  tts_enabled INTEGER DEFAULT 0,
  subtitle_preset TEXT NOT NULL DEFAULT 'default',
  bgm_filename TEXT,
  fact_source_urls TEXT,            -- JSON array
  risk_score REAL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft',
  rendered_path TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_sd_status ON shorts_drafts(status);

-- gate_results
CREATE TABLE gate_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER NOT NULL UNIQUE REFERENCES shorts_drafts(id),
  item_1_commentary_length TEXT NOT NULL,
  item_2_ratio TEXT NOT NULL,
  item_3_duration TEXT NOT NULL,
  item_4_source_label TEXT NOT NULL,
  item_5_bias_guardrail TEXT NOT NULL,
  item_6_template_repeat TEXT NOT NULL,
  item_7_whitelist_person TEXT NOT NULL,
  item_8_election_guard TEXT NOT NULL,
  item_9_fact_checked TEXT NOT NULL,
  item_10_no_defamation TEXT NOT NULL,
  manual_fact_check_signed_by TEXT,
  manual_defamation_check_signed_by TEXT,
  failure_reasons TEXT,             -- JSON array
  overall_status TEXT NOT NULL,
  risk_score REAL NOT NULL DEFAULT 0,
  validated_at TEXT NOT NULL
);

-- weekly_rankings
CREATE TABLE weekly_rankings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start TEXT NOT NULL,
  politician_id INTEGER NOT NULL REFERENCES politicians(id),
  rank INTEGER NOT NULL,
  score REAL NOT NULL,
  delta_vs_prev_week REAL DEFAULT 0,
  tag TEXT,
  data_sources TEXT,                -- JSON
  UNIQUE(week_start, politician_id)
);

-- uploaded_shorts
CREATE TABLE uploaded_shorts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER NOT NULL UNIQUE REFERENCES shorts_drafts(id),
  final_mp4_path TEXT NOT NULL,
  youtube_video_id TEXT UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  tags TEXT,                        -- JSON
  scheduled_publish_at TEXT,
  published_at TEXT,
  fact_links TEXT,                  -- JSON
  view_count INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  comment_count INTEGER DEFAULT 0,
  est_revenue REAL,
  is_taken_down INTEGER DEFAULT 0,
  takedown_reason TEXT,
  uploaded_at TEXT NOT NULL,
  metrics_updated_at TEXT NOT NULL
);

-- bias_reports
CREATE TABLE bias_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  month TEXT NOT NULL UNIQUE,
  total_uploads INTEGER NOT NULL,
  person_shares TEXT,               -- JSON
  party_shares TEXT,
  template_usage TEXT,
  avg_risk_score REAL,
  top_n_person_warning TEXT,        -- JSON array
  recommendations TEXT,              -- JSON array
  generated_at TEXT NOT NULL
);

-- guardrail_history (FR-028)
CREATE TABLE guardrail_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER REFERENCES shorts_drafts(id),
  keyword TEXT NOT NULL,
  category TEXT NOT NULL,           -- hate/defamation/bias/false
  action TEXT NOT NULL,             -- "warned"/"operator_ignored"/"operator_fixed"
  created_at TEXT NOT NULL
);
```
