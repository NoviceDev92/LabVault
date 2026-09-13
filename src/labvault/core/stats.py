"""Vault-wide statistics."""

from dataclasses import dataclass

from labvault.core.vault import Vault


@dataclass
class VaultStats:
    total_projects: int
    total_experiments: int
    total_runs: int
    total_artifacts: int
    total_trashed: int
    disk_usage_bytes: int


def get_vault_stats(vault: Vault) -> VaultStats:
    """Gather vault-wide statistics."""
    with vault.get_connection() as conn:
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        total_experiments = conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
        total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        total_artifacts = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        total_trashed = conn.execute("SELECT COUNT(*) FROM deleted_runs").fetchone()[0]

    # Calculate disk usage
    disk_usage = 0
    projects_dir = vault.path / "projects"
    if projects_dir.exists():
        for f in projects_dir.rglob("*"):
            if f.is_file():
                disk_usage += f.stat().st_size

    trash_dir = vault.path / ".trash"
    if trash_dir.exists():
        for f in trash_dir.rglob("*"):
            if f.is_file():
                disk_usage += f.stat().st_size

    return VaultStats(
        total_projects=total_projects,
        total_experiments=total_experiments,
        total_runs=total_runs,
        total_artifacts=total_artifacts,
        total_trashed=total_trashed,
        disk_usage_bytes=disk_usage,
    )
