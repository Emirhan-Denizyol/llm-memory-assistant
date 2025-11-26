-- app/db/schema.sql
PRAGMA foreign_keys = ON;
-- Basit şema sürüm işareti (isteğe bağlı)
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- LOCAL LTM: sohbet (session) bağlamlı kalıcı bilgi
CREATE TABLE IF NOT EXISTS local_memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  text TEXT NOT NULL,
  embedding BLOB NOT NULL,
  meta TEXT,
  emb_version TEXT DEFAULT 'ge-text-001',
  model TEXT DEFAULT 'google-text-embedding',
  dim INTEGER DEFAULT 768,
  created_at INTEGER NOT NULL,
  updated_at INTEGER,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- GLOBAL LTM: kullanıcı genel bilgileri
CREATE TABLE IF NOT EXISTS global_memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  text TEXT NOT NULL,
  embedding BLOB NOT NULL,
  meta TEXT,
  emb_version TEXT DEFAULT 'ge-text-001',
  model TEXT DEFAULT 'google-text-embedding',
  dim INTEGER DEFAULT 768,
  created_at INTEGER NOT NULL,
  updated_at INTEGER,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- (Opsiyonel) STM snapshot'larını diske almak istersen
CREATE TABLE IF NOT EXISTS stm_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,        -- user/assistant/system
  text TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_local_session ON local_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_local_user ON local_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_global_user ON global_memories(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_global_user_text ON global_memories(user_id, text);

-- Yardımcı seed (isteğe bağlı örnek kayıtlar)
-- INSERT OR IGNORE INTO users(user_id, created_at) VALUES ('demo', strftime('%s','now'));
-- INSERT OR IGNORE INTO sessions(session_id, user_id, title, created_at) VALUES ('demo-x', 'demo', 'X', strftime('%s','now'));
