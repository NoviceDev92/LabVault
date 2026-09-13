import sqlite3
from pathlib import Path

from labvault.db.connection import get_connection

SCHEMA_SQL = """
-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Experiments
CREATE TABLE IF NOT EXISTS experiments (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, slug)
);

-- Runs (each run = one version of an experiment)
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,          -- v1, v2, v3...
    status        TEXT DEFAULT 'draft',      -- draft | sealed
    notes         TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    sealed_at     DATETIME,
    UNIQUE(experiment_id, version)
);

-- Metrics (numeric key-value pairs per run)
CREATE TABLE IF NOT EXISTS metrics (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER REFERENCES runs(id) ON DELETE CASCADE,
    key     TEXT NOT NULL,
    value   REAL NOT NULL,
    UNIQUE(run_id, key)
);

-- Tags (free-form key-value pairs per run)
CREATE TABLE IF NOT EXISTS tags (
    id      INTEGER PRIMARY KEY,
    run_id  INTEGER REFERENCES runs(id) ON DELETE CASCADE,
    key     TEXT NOT NULL,
    value   TEXT NOT NULL,
    UNIQUE(run_id, key)
);

-- Artifacts (files within a run)
CREATE TABLE IF NOT EXISTS artifacts (
    id           INTEGER PRIMARY KEY,
    run_id       INTEGER REFERENCES runs(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    artifact_type TEXT NOT NULL,             -- code, config, model, result, figure, data, document, other
    size_bytes   INTEGER,
    content_hash TEXT,                       -- SHA-256 for dedup detection
    rel_path     TEXT NOT NULL,              -- relative path within the run folder
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index (run_id stored as text for FTS5 compatibility)
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    run_id, project_name, experiment_name, run_notes, tag_values, metric_keys
);

-- Deleted runs (soft delete / trash)
CREATE TABLE IF NOT EXISTS deleted_runs (
    id              INTEGER PRIMARY KEY,
    original_run_id INTEGER NOT NULL,
    experiment_id   INTEGER NOT NULL,
    project_id      INTEGER NOT NULL,
    version         INTEGER NOT NULL,
    status          TEXT,
    notes           TEXT,
    created_at      DATETIME,
    deleted_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    original_path   TEXT NOT NULL,          -- filesystem path before deletion
    trash_path      TEXT NOT NULL           -- filesystem path in .trash/
);
"""

def initialize_db(db_path: Path | str) -> None:
    """Initialize the SQLite database with the required schema."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
