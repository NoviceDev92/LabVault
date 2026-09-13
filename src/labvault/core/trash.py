"""Soft delete and trash management."""

import shutil
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from labvault.core.vault import Vault


@dataclass
class TrashedRun:
    id: int
    original_run_id: int
    experiment_id: int
    project_id: int
    version: int
    status: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]
    deleted_at: str
    original_path: str
    trash_path: str
    # Enrichment fields
    project_name: Optional[str] = None
    experiment_name: Optional[str] = None


def soft_delete_run(vault: Vault, run_id: int) -> TrashedRun:
    """Move a run to .trash/ and record it in deleted_runs."""
    with vault.get_connection() as conn:
        # Fetch run + context
        row = conn.execute(
            """
            SELECT r.id, r.experiment_id, r.version, r.status, r.notes, r.created_at,
                   e.project_id, p.slug, e.slug
            FROM runs r
            JOIN experiments e ON r.experiment_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE r.id = ?
            """,
            (run_id,),
        ).fetchone()

        if not row:
            raise ValueError(f"Run with id {run_id} not found.")

        rid, exp_id, version, status, notes, created_at, proj_id, proj_slug, exp_slug = row

        original_path = str(vault.path / "projects" / proj_slug / exp_slug / f"v{version}")

        # Generate a unique trash path using the run id
        trash_name = f"{proj_slug}_{exp_slug}_v{version}_run{rid}"
        trash_path_obj = vault.path / ".trash" / trash_name
        trash_path = str(trash_path_obj)

        # Move directory to trash
        original_path_obj = Path(original_path)
        if original_path_obj.exists():
            shutil.move(str(original_path_obj), trash_path)
        else:
            # Directory doesn't exist, just create the trash record anyway
            trash_path_obj.mkdir(parents=True, exist_ok=True)

        # Record in deleted_runs
        cursor = conn.execute(
            """
            INSERT INTO deleted_runs 
            (original_run_id, experiment_id, project_id, version, status, notes, created_at, original_path, trash_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rid, exp_id, proj_id, version, status, notes, created_at, original_path, trash_path),
        )
        trash_id = cursor.lastrowid

        # Delete from search index
        conn.execute("DELETE FROM search_index WHERE run_id = ?", (str(rid),))

        # Delete run (cascades to metrics, tags, artifacts)
        conn.execute("DELETE FROM runs WHERE id = ?", (rid,))

        deleted_at_row = conn.execute(
            "SELECT deleted_at FROM deleted_runs WHERE id = ?", (trash_id,)
        ).fetchone()

    return TrashedRun(
        id=trash_id,
        original_run_id=rid,
        experiment_id=exp_id,
        project_id=proj_id,
        version=version,
        status=status,
        notes=notes,
        created_at=created_at,
        deleted_at=deleted_at_row[0],
        original_path=original_path,
        trash_path=trash_path,
    )


def list_trash(vault: Vault) -> list[TrashedRun]:
    """List all trashed runs with project/experiment names."""
    with vault.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.original_run_id, d.experiment_id, d.project_id, d.version,
                   d.status, d.notes, d.created_at, d.deleted_at, d.original_path, d.trash_path,
                   p.name, e.name
            FROM deleted_runs d
            LEFT JOIN projects p ON d.project_id = p.id
            LEFT JOIN experiments e ON d.experiment_id = e.id
            ORDER BY d.deleted_at DESC
            """
        ).fetchall()

    return [
        TrashedRun(
            id=r[0], original_run_id=r[1], experiment_id=r[2], project_id=r[3],
            version=r[4], status=r[5], notes=r[6], created_at=r[7],
            deleted_at=r[8], original_path=r[9], trash_path=r[10],
            project_name=r[11], experiment_name=r[12],
        )
        for r in rows
    ]


def restore_from_trash(vault: Vault, trash_id: int) -> TrashedRun:
    """Restore a trashed run back to its original location and re-insert into DB."""
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM deleted_runs WHERE id = ?", (trash_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Trash item with id {trash_id} not found.")

        trashed = TrashedRun(
            id=row[0], original_run_id=row[1], experiment_id=row[2], project_id=row[3],
            version=row[4], status=row[5], notes=row[6], created_at=row[7],
            deleted_at=row[8], original_path=row[9], trash_path=row[10],
        )

        # Move directory back
        trash_path_obj = Path(trashed.trash_path)
        original_path_obj = Path(trashed.original_path)
        if trash_path_obj.exists():
            original_path_obj.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash_path_obj), str(original_path_obj))

        # Re-insert the run into runs table
        conn.execute(
            "INSERT INTO runs (experiment_id, version, status, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (trashed.experiment_id, trashed.version, trashed.status, trashed.notes, trashed.created_at),
        )

        # Remove from deleted_runs
        conn.execute("DELETE FROM deleted_runs WHERE id = ?", (trash_id,))

    return trashed
