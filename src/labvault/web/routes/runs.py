"""Run API routes."""

from fastapi import APIRouter, Request, HTTPException

from labvault.core.run import Run, create_run, get_run, list_runs, seal_run
from labvault.core.metrics import get_metrics, add_metrics
from labvault.core.tags import get_tags, add_tags
from labvault.core.artifact import list_artifacts
from labvault.core.experiment import Experiment
from labvault.web.schemas import RunCreate, RunUpdate, RunResponse, ArtifactResponse

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


def _enrich_run(vault, run: Run) -> RunResponse:
    metrics = get_metrics(vault, run)
    tags = get_tags(vault, run)
    arts = list_artifacts(vault, run)
    return RunResponse(
        id=run.id, experiment_id=run.experiment_id, version=run.version,
        status=run.status, notes=run.notes, created_at=run.created_at,
        sealed_at=run.sealed_at, metrics=metrics, tags=tags,
        artifacts=[
            ArtifactResponse(
                id=a.id, run_id=a.run_id, filename=a.filename,
                artifact_type=a.artifact_type, size_bytes=a.size_bytes,
                content_hash=a.content_hash, rel_path=a.rel_path, created_at=a.created_at,
            )
            for a in arts
        ],
    )


@router.get("/experiments/{exp_id}/runs", response_model=list[RunResponse])
def api_list_runs(exp_id: int, request: Request):
    vault = _get_vault(request)
    experiment = _get_experiment_by_id(vault, exp_id)
    runs = list_runs(vault, experiment)
    return [_enrich_run(vault, r) for r in runs]


@router.post("/experiments/{exp_id}/runs", response_model=RunResponse, status_code=201)
def api_create_run(exp_id: int, body: RunCreate, request: Request):
    vault = _get_vault(request)
    experiment = _get_experiment_by_id(vault, exp_id)
    try:
        run = create_run(vault, experiment, tags=body.tags, metrics=body.metrics, notes=body.notes)
        return _enrich_run(vault, run)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}", response_model=RunResponse)
def api_get_run(run_id: int, request: Request):
    vault = _get_vault(request)
    run = _get_run_by_id(vault, run_id)
    return _enrich_run(vault, run)


@router.patch("/runs/{run_id}", response_model=RunResponse)
def api_update_run(run_id: int, body: RunUpdate, request: Request):
    vault = _get_vault(request)
    run = _get_run_by_id(vault, run_id)

    if run.status == "sealed":
        raise HTTPException(status_code=400, detail="Cannot modify a sealed run.")

    if body.metrics:
        add_metrics(vault, run, body.metrics)
    if body.tags:
        add_tags(vault, run, body.tags)
    if body.notes is not None:
        with vault.get_connection() as conn:
            conn.execute("UPDATE runs SET notes = ? WHERE id = ?", (body.notes, run.id))
        run.notes = body.notes

    # Regenerate meta
    experiment = _get_experiment_by_id(vault, run.experiment_id)
    from labvault.core.run import generate_meta_json
    generate_meta_json(vault, experiment, run)

    return _enrich_run(vault, run)


@router.post("/runs/{run_id}/seal", response_model=RunResponse)
def api_seal_run(run_id: int, request: Request):
    vault = _get_vault(request)
    run = _get_run_by_id(vault, run_id)
    experiment = _get_experiment_by_id(vault, run.experiment_id)
    try:
        sealed = seal_run(vault, experiment, run)
        return _enrich_run(vault, sealed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
