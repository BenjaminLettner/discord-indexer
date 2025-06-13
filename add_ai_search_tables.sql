-- Migration script to add AI search embedding tables

-- Table to store file embeddings for AI search
CREATE TABLE IF NOT EXISTS file_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    content_text TEXT NOT NULL,
    embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES indexed_files(id) ON DELETE CASCADE,
    UNIQUE(file_id)
);

-- Table to store link embeddings for AI search
CREATE TABLE IF NOT EXISTS link_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    content_text TEXT NOT NULL,
    embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (link_id) REFERENCES indexed_links(id) ON DELETE CASCADE,
    UNIQUE(link_id)
);

-- Index for faster embedding lookups
CREATE INDEX IF NOT EXISTS idx_file_embeddings_file_id ON file_embeddings(file_id);
CREATE INDEX IF NOT EXISTS idx_link_embeddings_link_id ON link_embeddings(link_id);

-- Table to store AI search queries for analytics and caching
CREATE TABLE IF NOT EXISTS ai_search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    query_text TEXT NOT NULL,
    query_embedding BLOB,
    results_count INTEGER DEFAULT 0,
    search_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_ai_search_queries_user_id ON ai_search_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_search_queries_created_at ON ai_search_queries(created_at);