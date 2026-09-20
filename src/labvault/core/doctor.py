"""Vault integrity checker — verifies DB ↔ filesystem consistency."""

from dataclasses import dataclass, field
from pathlib import Path

from labvault.core.vault import Vault
from labvault.core.artifact import list_artifacts
from labvault.core.run import Run, get_run_directory
from labvault.core.experiment import Experiment
from labvault.utils.hashing import compute_sha256


@dataclass
class IntegrityReport:
    """Results of a vault integrity check."""
    orphaned_db_records: list[str] = field(default_factory=list)  # DB artifacts missing on disk
    orphaned_files: list[str] = field(default_factory=list)       # Disk files missing from DB
    hash_mismatches: list[str] = field(default_factory=list)      # Hash doesn't match content
    missing_meta: list[str] = field(default_factory=list)         # Runs without _meta.json
    total_artifacts_checked: int = 0
    is_healthy: bool = True


def check_integrity(vault: Vault) -> IntegrityReport:
    """Run a full integrity scan of the vault.

    Checks:
    1. Every artifact in the DB has a corresponding file on disk.
    2. Every artifact file on disk has a corresponding DB record (within known run dirs).
    3. Content hashes match (optional, can be slow for large files).
    4. Every run directory contains a _meta.json.
    """
    report = IntegrityReport()

    with vault.get_connection() as conn:
        # Fetch all runs with their experiment and project info
        runs_info = conn.execute("""
            SELECT r.id, r.experiment_id, r.version,
                   e.slug AS exp_slug, e.project_id,
                   p.slug AS proj_slug
            FROM runs r
            JOIN experiments e ON r.experiment_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE r.status != 'trashed'
        """).fetchall()

        # Fetch all artifacts
        all_artifacts = conn.execute("""
            SELECT a.id, a.run_id, a.filename, a.content_hash, a.size_bytes
            FROM artifacts a
        """).fetchall()

    # Build run_id → directory mapping
    run_dirs: dict[int, Path] = {}
    for row in runs_info:
        rid, _, version, exp_slug, _, proj_slug = row
        run_dir = vault.path / "projects" / proj_slug / exp_slug / f"v{version}"
        run_dirs[rid] = run_dir

    # Check 1: DB artifacts → disk
    db_files_by_run: dict[int, set] = {}
    for art_id, run_id, filename, content_hash, size_bytes in all_artifacts:
        report.total_artifacts_checked += 1
        db_files_by_run.setdefault(run_id, set()).add(filename)

        run_dir = run_dirs.get(run_id)
        if not run_dir:
            report.orphaned_db_records.append(f"Artifact #{art_id} ({filename}): run {run_id} has no directory")
            report.is_healthy = False
            continue

        file_path = run_dir / filename
        if not file_path.exists():
            report.orphaned_db_records.append(f"{filename} in run {run_id}: file missing from disk at {file_path}")
            report.is_healthy = False
            continue

        # Check hash (skip large files > 50MB for speed)
        if size_bytes and size_bytes < 50 * 1024 * 1024:
            actual_hash = compute_sha256(file_path)
            if actual_hash != content_hash:
                report.hash_mismatches.append(
                    f"{filename} in run {run_id}: expected {content_hash[:12]}…, got {actual_hash[:12]}…"
                )
                report.is_healthy = False

    # Check 2: Disk files → DB (only in known run dirs)
    for rid, run_dir in run_dirs.items():
        if not run_dir.exists():
            continue
        db_filenames = db_files_by_run.get(rid, set())
        for file_path in run_dir.iterdir():
            if file_path.is_file() and file_path.name != "_meta.json":
                if file_path.name not in db_filenames:
                    report.orphaned_files.append(f"{file_path.name} in {run_dir}: exists on disk but not in DB")
                    report.is_healthy = False

    # Check 3: _meta.json presence
    for rid, run_dir in run_dirs.items():
        if run_dir.exists() and not (run_dir / "_meta.json").exists():
            report.missing_meta.append(f"Run {rid} at {run_dir}: missing _meta.json")
            report.is_healthy = False

    return report
