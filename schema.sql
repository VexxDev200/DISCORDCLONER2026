CREATE TABLE IF NOT EXISTS cloner_accounts (
  discord_user_id TEXT PRIMARY KEY,
  username TEXT,
  global_name TEXT,
  token TEXT NOT NULL,
  lang TEXT DEFAULT 'ru',
  last_used_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clone_sessions (
  id BIGSERIAL PRIMARY KEY,
  discord_user_id TEXT,
  source_guild_id TEXT NOT NULL,
  source_guild_name TEXT,
  target_guild_id TEXT NOT NULL,
  target_guild_name TEXT,
  status TEXT NOT NULL DEFAULT 'running',
  stats JSONB DEFAULT '{}'::jsonb,
  config JSONB DEFAULT '{}'::jsonb,
  error_message TEXT,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS id_mappings (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES clone_sessions(id) ON DELETE CASCADE,
  source_guild_id TEXT,
  target_guild_id TEXT,
  old_id TEXT NOT NULL,
  new_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (session_id, old_id, entity_type)
);

CREATE TABLE IF NOT EXISTS guild_snapshots (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES clone_sessions(id) ON DELETE CASCADE,
  guild_id TEXT NOT NULL,
  snapshot_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clone_logs (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES clone_sessions(id) ON DELETE CASCADE,
  level TEXT NOT NULL DEFAULT 'info',
  message TEXT NOT NULL,
  meta JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS global_id_mappings (
  old_id TEXT NOT NULL,
  new_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  source_guild_id TEXT,
  target_guild_id TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (old_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_clone_sessions_user ON clone_sessions(discord_user_id);
CREATE INDEX IF NOT EXISTS idx_id_mappings_session ON id_mappings(session_id);
CREATE INDEX IF NOT EXISTS idx_global_mappings_guilds ON global_id_mappings(source_guild_id, target_guild_id);

ALTER TABLE clone_sessions DROP CONSTRAINT IF EXISTS clone_sessions_discord_user_id_fkey;

CREATE TABLE IF NOT EXISTS pair_mappings (
  source_guild_id TEXT NOT NULL,
  target_guild_id TEXT NOT NULL,
  old_id TEXT NOT NULL,
  new_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (source_guild_id, target_guild_id, old_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_pair_mappings_target ON pair_mappings(target_guild_id);

ALTER TABLE cloner_accounts ADD COLUMN IF NOT EXISTS last_source_guild_id TEXT;
ALTER TABLE cloner_accounts ADD COLUMN IF NOT EXISTS last_target_guild_id TEXT;
ALTER TABLE cloner_accounts ADD COLUMN IF NOT EXISTS refresh_token TEXT;
ALTER TABLE cloner_accounts ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS oauth_flows (
  state TEXT PRIMARY KEY,
  discord_user_id TEXT NOT NULL,
  source_id TEXT,
  target_id TEXT,
  strategy TEXT DEFAULT '2',
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_flows_expires ON oauth_flows(expires_at);

CREATE TABLE IF NOT EXISTS bot_clone_queue (
  id BIGSERIAL PRIMARY KEY,
  discord_user_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  strategy TEXT DEFAULT '2',
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_bot_clone_queue_pending ON bot_clone_queue(status, created_at);

ALTER TABLE clone_sessions ADD COLUMN IF NOT EXISTS genome_hash TEXT;
ALTER TABLE clone_sessions ADD COLUMN IF NOT EXISTS entropy_seal TEXT;
ALTER TABLE clone_sessions ADD COLUMN IF NOT EXISTS mapping_profile TEXT DEFAULT 'default';

CREATE TABLE IF NOT EXISTS server_genomes (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES clone_sessions(id) ON DELETE CASCADE,
  guild_id TEXT NOT NULL,
  genome_hash TEXT NOT NULL,
  genome_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_server_genomes_guild ON server_genomes(guild_id, created_at DESC);

CREATE TABLE IF NOT EXISTS pair_mapping_profiles (
  source_guild_id TEXT NOT NULL,
  target_guild_id TEXT NOT NULL,
  profile_name TEXT NOT NULL DEFAULT 'default',
  old_id TEXT NOT NULL,
  new_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (source_guild_id, target_guild_id, profile_name, old_id, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_pair_profiles ON pair_mapping_profiles(source_guild_id, target_guild_id, profile_name);

CREATE TABLE IF NOT EXISTS clone_anomalies (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES clone_sessions(id) ON DELETE CASCADE,
  kind TEXT,
  name TEXT,
  endpoint TEXT,
  payload JSONB,
  error_text TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_clone_anomalies_session ON clone_anomalies(session_id);

CREATE TABLE IF NOT EXISTS shadow_sync_state (
  source_guild_id TEXT NOT NULL,
  target_guild_id TEXT NOT NULL,
  profile_name TEXT NOT NULL DEFAULT 'default',
  last_genome_hash TEXT,
  last_sync_at TIMESTAMPTZ,
  PRIMARY KEY (source_guild_id, target_guild_id, profile_name)
);
