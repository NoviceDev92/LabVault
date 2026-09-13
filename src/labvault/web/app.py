"""FastAPI application factory."""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from labvault.core.vault import Vault
from labvault.web.routes import projects, experiments, runs, artifacts, search, compare, export, stats


def create_app(vault_path: str | Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LabVault",
        description="Local-first research & versioning platform API",
        version="0.1.0",
    )

    # CORS — localhost only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Vault instance — shared across requests
    vault = Vault.init(vault_path or os.environ.get("LABVAULT_PATH", "."))
    app.state.vault = vault

    # Include route modules
    app.include_router(projects.router, prefix="/api", tags=["projects"])
    app.include_router(experiments.router, prefix="/api", tags=["experiments"])
    app.include_router(runs.router, prefix="/api", tags=["runs"])
    app.include_router(artifacts.router, prefix="/api", tags=["artifacts"])
    app.include_router(search.router, prefix="/api", tags=["search"])
    app.include_router(compare.router, prefix="/api", tags=["compare"])
    app.include_router(export.router, prefix="/api", tags=["export"])
    app.include_router(stats.router, prefix="/api", tags=["stats"])

    @app.get("/api/health")
    def health():
        return {"status": "ok", "vault_path": str(vault.path)}

    # Mount static files for the frontend (Phase 5)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
