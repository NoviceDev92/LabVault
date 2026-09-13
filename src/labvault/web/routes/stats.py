"""Vault stats API route."""

from fastapi import APIRouter, Request
from labvault.core.stats import get_vault_stats
from labvault.utils.filesize import format_bytes

router = APIRouter()


@router.get("/stats")
def api_get_stats(request: Request):
    vault = request.app.state.vault
    stats = get_vault_stats(vault)
    return {
        "total_projects": stats.total_projects,
        "total_experiments": stats.total_experiments,
        "total_runs": stats.total_runs,
        "total_artifacts": stats.total_artifacts,
        "total_trashed": stats.total_trashed,
        "disk_usage_bytes": stats.disk_usage_bytes,
        "disk_usage_formatted": format_bytes(stats.disk_usage_bytes),
        "vault_path": str(vault.path),
    }
