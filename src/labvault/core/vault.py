import os
from pathlib import Path
from dataclasses import dataclass

from labvault.db.schema import initialize_db
from labvault.db.connection import get_connection

@dataclass
class Vault:
    path: Path

    @classmethod
    def init(cls, path: Path | str | None = None) -> "Vault":
        """Initialize a new vault or return an existing one."""
        if path is None:
            path = Path(os.environ.get("LABVAULT_PATH", Path.home() / "labvault"))
        else:
            path = Path(path)
            
        path.mkdir(parents=True, exist_ok=True)
        db_path = path / "labvault.db"
        
        # Initialize schema if db doesn't exist or is empty
        if not db_path.exists() or db_path.stat().st_size == 0:
            initialize_db(db_path)
            
        # Create default directories
        (path / "projects").mkdir(exist_ok=True)
        (path / ".trash").mkdir(exist_ok=True)
        
        return cls(path=path.resolve())
        
    @property
    def db_path(self) -> Path:
        return self.path / "labvault.db"
        
    def get_connection(self):
        """Get a database connection context manager."""
        return get_connection(self.db_path)
