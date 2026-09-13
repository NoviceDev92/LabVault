import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from labvault.core.vault import Vault
from labvault.core.experiment import Experiment

@dataclass
class Run:
    id: int
    experiment_id: int
    version: int
    status: str
    notes: Optional[str]
    created_at: str
    sealed_at: Optional[str]

def create_run(
    vault: Vault, 
    experiment: Experiment, 
    tags: Optional[dict[str, str]] = None,
    metrics: Optional[dict[str, float]] = None,
    notes: Optional[str] = None
) -> Run:
    with vault.get_connection() as conn:
        # Get next version
        row = conn.execute(
            "SELECT MAX(version) FROM runs WHERE experiment_id = ?",
            (experiment.id,)
        ).fetchone()
        version = (row[0] or 0) + 1
        
        # Insert run
        cursor = conn.execute(
            "INSERT INTO runs (experiment_id, version, notes) VALUES (?, ?, ?)",
            (experiment.id, version, notes)
        )
        run_id = cursor.lastrowid
        
        # Get created_at
        run_row = conn.execute(
            "SELECT created_at FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        created_at = run_row[0]
        
    run = Run(
        id=run_id, 
        experiment_id=experiment.id, 
        version=version, 
        status="draft", 
        notes=notes, 
        created_at=created_at, 
        sealed_at=None
    )
    
    # Add tags and metrics if provided
    if tags:
        from labvault.core.tags import add_tags
        add_tags(vault, run, tags)
        
    if metrics:
        from labvault.core.metrics import add_metrics
        add_metrics(vault, run, metrics)
        
    # Create the run directory
    run_dir = get_run_directory(vault, experiment, run)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate _meta.json
    generate_meta_json(vault, experiment, run)
    
    # Update search index
    from labvault.core.search import update_search_index
    update_search_index(vault, run.id)
    
    return run

def get_run(vault: Vault, experiment: Experiment, version: int) -> Optional[Run]:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, experiment_id, version, status, notes, created_at, sealed_at "
            "FROM runs WHERE experiment_id = ? AND version = ?",
            (experiment.id, version)
        ).fetchone()
        
    if row:
        return Run(
            id=row[0], experiment_id=row[1], version=row[2], 
            status=row[3], notes=row[4], created_at=row[5], sealed_at=row[6]
        )
    return None

def list_runs(vault: Vault, experiment: Experiment) -> list[Run]:
    with vault.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, experiment_id, version, status, notes, created_at, sealed_at "
            "FROM runs WHERE experiment_id = ? ORDER BY version DESC",
            (experiment.id,)
        ).fetchall()
        
    return [Run(
        id=row[0], experiment_id=row[1], version=row[2], 
        status=row[3], notes=row[4], created_at=row[5], sealed_at=row[6]
    ) for row in rows]

def get_run_directory(vault: Vault, experiment: Experiment, run: Run) -> Path:
    # Need to fetch project slug
    with vault.get_connection() as conn:
        project_slug = conn.execute(
            "SELECT slug FROM projects WHERE id = ?",
            (experiment.project_id,)
        ).fetchone()[0]
        
    return vault.path / "projects" / project_slug / experiment.slug / f"v{run.version}"

def generate_meta_json(vault: Vault, experiment: Experiment, run: Run) -> None:
    from labvault.core.tags import get_tags
    from labvault.core.metrics import get_metrics
    from labvault.core.artifact import list_artifacts
    
    tags = get_tags(vault, run)
    metrics = get_metrics(vault, run)
    artifacts = list_artifacts(vault, run)
    
    with vault.get_connection() as conn:
        project_slug = conn.execute(
            "SELECT slug FROM projects WHERE id = ?",
            (experiment.project_id,)
        ).fetchone()[0]
    
    meta = {
        "project": project_slug,
        "experiment": experiment.slug,
        "version": run.version,
        "status": run.status,
        "created_at": run.created_at,
        "sealed_at": run.sealed_at,
        "tags": tags,
        "metrics": metrics,
        "artifacts": [
            {
                "filename": a.filename,
                "type": a.artifact_type,
                "size_bytes": a.size_bytes
            } for a in artifacts
        ],
        "notes": run.notes
    }
    
    run_dir = get_run_directory(vault, experiment, run)
    meta_path = run_dir / "_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def seal_run(vault: Vault, experiment: Experiment, run: Run) -> Run:
    """Mark a run as sealed (immutable). No further modifications allowed."""
    if run.status == "sealed":
        raise ValueError(f"Run v{run.version} is already sealed.")

    from labvault.utils.timestamps import get_current_timestamp
    sealed_at = get_current_timestamp()

    with vault.get_connection() as conn:
        conn.execute(
            "UPDATE runs SET status = 'sealed', sealed_at = ? WHERE id = ?",
            (sealed_at, run.id),
        )

    run.status = "sealed"
    run.sealed_at = sealed_at

    # Regenerate _meta.json with updated status
    generate_meta_json(vault, experiment, run)

    return run
