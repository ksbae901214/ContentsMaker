-- 007-dem-shorts-studio initial schema
-- See specs/007-dem-shorts-studio/data-model.md for entity specifications.

-- politicians
CREATE TABLE IF NOT EXISTS politicians (
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
CREATE INDEX IF NOT EXISTS idx_politicians_tier_cat ON politicians(tier, category);

-- source_videos
CREATE TABLE IF NOT EXISTS source_videos (
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
CREATE INDEX IF NOT EXISTS idx_sv_published ON source_videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_sv_score ON source_videos(dem_score DESC);
CREATE INDEX IF NOT EXISTS idx_sv_status ON source_videos(status);

-- speech_segments
CREATE TABLE IF NOT EXISTS speech_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_video_id TEXT NOT NULL REFERENCES source_videos(video_id),
  start_sec REAL NOT NULL,
  end_sec REAL NOT NULL,
  politician_id INTEGER REFERENCES politicians(id),
  confidence REAL NOT NULL,
  stt_text TEXT,
  recommendation_score REAL NOT NULL DEFAULT 0,
  emotion_strength REAL DEFAULT 0,
  issue_keywords TEXT,
  is_solo INTEGER DEFAULT 0,
  has_profanity INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ss_video_start ON speech_segments(source_video_id, start_sec);
CREATE INDEX IF NOT EXISTS idx_ss_score ON speech_segments(recommendation_score DESC);

-- shorts_drafts
CREATE TABLE IF NOT EXISTS shorts_drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id INTEGER NOT NULL REFERENCES speech_segments(id),
  cut_start_sec REAL NOT NULL,
  cut_end_sec REAL NOT NULL,
  commentary_json TEXT,
  commentary_char_count INTEGER NOT NULL DEFAULT 0,
  tts_voice TEXT,
  tts_enabled INTEGER DEFAULT 0,
  subtitle_preset TEXT NOT NULL DEFAULT 'default',
  bgm_filename TEXT,
  fact_source_urls TEXT,
  risk_score REAL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft',
  rendered_path TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sd_status ON shorts_drafts(status);

-- gate_results
CREATE TABLE IF NOT EXISTS gate_results (
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
  failure_reasons TEXT,
  overall_status TEXT NOT NULL,
  risk_score REAL NOT NULL DEFAULT 0,
  validated_at TEXT NOT NULL
);

-- weekly_rankings
CREATE TABLE IF NOT EXISTS weekly_rankings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start TEXT NOT NULL,
  politician_id INTEGER NOT NULL REFERENCES politicians(id),
  rank INTEGER NOT NULL,
  score REAL NOT NULL,
  delta_vs_prev_week REAL DEFAULT 0,
  tag TEXT,
  data_sources TEXT,
  UNIQUE(week_start, politician_id)
);

-- uploaded_shorts
CREATE TABLE IF NOT EXISTS uploaded_shorts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER NOT NULL UNIQUE REFERENCES shorts_drafts(id),
  final_mp4_path TEXT NOT NULL,
  youtube_video_id TEXT UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  tags TEXT,
  scheduled_publish_at TEXT,
  published_at TEXT,
  fact_links TEXT,
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
CREATE TABLE IF NOT EXISTS bias_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  month TEXT NOT NULL UNIQUE,
  total_uploads INTEGER NOT NULL,
  person_shares TEXT,
  party_shares TEXT,
  template_usage TEXT,
  avg_risk_score REAL,
  top_n_person_warning TEXT,
  recommendations TEXT,
  generated_at TEXT NOT NULL
);

-- guardrail_history (FR-028)
CREATE TABLE IF NOT EXISTS guardrail_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id INTEGER REFERENCES shorts_drafts(id),
  keyword TEXT NOT NULL,
  category TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- migrations table (for future migrations)
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);
