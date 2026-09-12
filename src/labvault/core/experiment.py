from dataclasses import dataclass
from typing import Optional

from labvault.core.vault import Vault
from labvault.core.project import Project
from labvault.utils.slugify import slugify

@dataclass
class Experiment:
    id: int
    project_id: int
    name: str
    slug: str
    description: Optional[str]

def create_experiment(vault: Vault, project: Project, name: str, description: Optional[str] = None) -> Experiment:
    slug = slugify(name)
    with vault.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO experiments (project_id, name, slug, description) VALUES (?, ?, ?, ?)",
            (project.id, name, slug, description)
        )
        experiment_id = cursor.lastrowid
        
    # Create the experiment directory
    (vault.path / "projects" / project.slug / slug).mkdir(parents=True, exist_ok=True)
    
    return Experiment(
        id=experiment_id, 
        project_id=project.id, 
        name=name, 
        slug=slug, 
        description=description
    )

def get_experiment(vault: Vault, project: Project, slug: str) -> Optional[Experiment]:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, project_id, name, slug, description FROM experiments WHERE project_id = ? AND slug = ?",
            (project.id, slug)
        ).fetchone()
        
    if row:
        return Experiment(id=row[0], project_id=row[1], name=row[2], slug=row[3], description=row[4])
    return None

def list_experiments(vault: Vault, project: Project) -> list[Experiment]:
    with vault.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, project_id, name, slug, description FROM experiments WHERE project_id = ? ORDER BY name",
            (project.id,)
        ).fetchall()
        
    return [Experiment(id=row[0], project_id=row[1], name=row[2], slug=row[3], description=row[4]) for row in rows]
