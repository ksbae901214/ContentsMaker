-- 010 PPP perspective axis — H2 방식
-- Spec: specs/007-dem-shorts-studio/spec.md (v2, 2026-04-20)
-- Charter: docs/politics-bias-charter.md

-- 1. perspectives 테이블 — 지원 관점 정의
CREATE TABLE IF NOT EXISTS perspectives (
  id          TEXT PRIMARY KEY,       -- 'dem' | 'ppp'
  label       TEXT NOT NULL,          -- '민주당 관점' | '국민의힘 관점'
  channel_id  TEXT UNIQUE,            -- YouTube 채널 ID (1:1, NULL 허용 = 업로드 비활성)
  is_active   INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL
);

-- 2. politicians — affiliation_perspective 추가
ALTER TABLE politicians
  ADD COLUMN affiliation_perspective TEXT NOT NULL DEFAULT 'dem';

CREATE INDEX IF NOT EXISTS idx_politicians_perspective
  ON politicians(affiliation_perspective, tier);

-- 3. source_videos — target_perspective + perspective_score
ALTER TABLE source_videos
  ADD COLUMN target_perspective TEXT NOT NULL DEFAULT 'dem';

ALTER TABLE source_videos
  ADD COLUMN perspective_score REAL NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_sv_perspective_score
  ON source_videos(target_perspective, perspective_score DESC);

-- 4. shorts_drafts — perspective
ALTER TABLE shorts_drafts
  ADD COLUMN perspective TEXT NOT NULL DEFAULT 'dem';

-- 5. uploaded_shorts — perspective
ALTER TABLE uploaded_shorts
  ADD COLUMN perspective TEXT NOT NULL DEFAULT 'dem';

-- 6. weekly_rankings — perspective
ALTER TABLE weekly_rankings
  ADD COLUMN perspective TEXT NOT NULL DEFAULT 'dem';

-- 7. bias_reports — perspective
ALTER TABLE bias_reports
  ADD COLUMN perspective TEXT NOT NULL DEFAULT 'dem';

-- 8. guardrail_history — perspective (FR-028 학습 분리)
ALTER TABLE guardrail_history
  ADD COLUMN perspective TEXT NOT NULL DEFAULT 'dem';
