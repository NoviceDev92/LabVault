from dataclasses import dataclass
from typing import Optional

from labvault.core.vault import Vault
from labvault.utils.slugify import slugify

@dataclass
class Project:
    id: int
    name: str
    slug: str
    description: Optional[str]

def create_project(vault: Vault, name: str, description: Optional[str] = None) -> Project:
    slug = slugify(name)
    with vault.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO projects (name, slug, description) VALUES (?, ?, ?)",
            (name, slug, description)
        )
        project_id = cursor.lastrowid
        
    # Create the project directory
    (vault.path / "projects" / slug).mkdir(parents=True, exist_ok=True)
    
    return Project(id=project_id, name=name, slug=slug, description=description)

def get_project(vault: Vault, slug: str) -> Optional[Project]:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, slug, description FROM projects WHERE slug = ?",
            (slug,)
        ).fetchone()
        
    if row:
        return Project(id=row[0], name=row[1], slug=row[2], description=row[3])
    return None

def list_projects(vault: Vault) -> list[Project]:
    with vault.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, slug, description FROM projects ORDER BY name"
        ).fetchall()
        
    return [Project(id=row[0], name=row[1], slug=row[2], description=row[3]) for row in rows]
