import sqlite3
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """Provide a transactional scope around a series of operations."""
    conn = sqlite3.connect(str(db_path))
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    # Use Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA journal_mode = WAL;")
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
