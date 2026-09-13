"""Export API routes — table export and run ZIP download."""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response

from labvault.core.experiment import Experiment
from labvault.core.run import Run
from labvault.core.export import export_table, pack_run_zip

router = APIRouter()


def _get_vault(request: Request):
    return request.app.state.vault


def _get_experiment_by_id(vault, exp_id: int) -> Experiment:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, project_id, name, slug, description FROM experiments WHERE id = ?",
            (exp_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Experiment with id {exp_id} not found.")
    return Experiment(id=row[0], project_id=row[1], name=row[2], slug=row[3], description=row[4])


def _get_run_by_id(vault, run_id: int) -> Run:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, experiment_id, version, status, notes, created_at, sealed_at FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Run with id {run_id} not found.")
    return Run(id=row[0], experiment_id=row[1], version=row[2], status=row[3],
               notes=row[4], created_at=row[5], sealed_at=row[6])


@router.get("/export/table")
def api_export_table(
    request: Request,
    experiment_id: int = Query(..., description="Experiment ID"),
    format: str = Query("csv", description="Export format: csv, json, markdown, latex"),
):
    vault = _get_vault(request)
    experiment = _get_experiment_by_id(vault, experiment_id)

    try:
        content = export_table(vault, experiment, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    content_types = {
        "csv": "text/csv",
        "json": "application/json",
        "markdown": "text/markdown",
        "latex": "text/plain",
    }
    media_type = content_types.get(format, "text/plain")
    filename = f"{experiment.slug}_results.{format}"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/run/{run_id}")
def api_export_run_zip(run_id: int, request: Request):
    vault = _get_vault(request)
    run = _get_run_by_id(vault, run_id)
    experiment = _get_experiment_by_id(vault, run.experiment_id)

    try:
        zip_bytes = pack_run_zip(vault, experiment, run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"{experiment.slug}_v{run.version}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
