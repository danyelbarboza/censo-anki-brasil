CREATE TABLE IF NOT EXISTS census_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  survey_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  addon_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, survey_id)
);
CREATE TABLE IF NOT EXISTS debug_submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  schema_version TEXT NOT NULL,
  addon_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS server_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_census_responses_survey ON census_responses(survey_id);
CREATE INDEX IF NOT EXISTS idx_debug_created ON debug_submissions(created_at);
