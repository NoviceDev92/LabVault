"""Experiment API routes."""

from fastapi import APIRouter, Request, HTTPException

from labvault.core.project import get_project
from labvault.core.experiment import create_experiment, get_experiment, list_experiments
from labvault.web.schemas import ExperimentCreate, ExperimentResponse

router = APIRouter()


def _get_vault(request: Request):
    return request.app.state.vault


@router.get("/projects/{project_slug}/experiments", response_model=list[ExperimentResponse])
def api_list_experiments(project_slug: str, request: Request):
    vault = _get_vault(request)
    project = get_project(vault, project_slug)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found.")
    exps = list_experiments(vault, project)
    return [
        ExperimentResponse(id=e.id, project_id=e.project_id, name=e.name, slug=e.slug, description=e.description)
        for e in exps
    ]


@router.post("/projects/{project_slug}/experiments", response_model=ExperimentResponse, status_code=201)
def api_create_experiment(project_slug: str, body: ExperimentCreate, request: Request):
    vault = _get_vault(request)
    project = get_project(vault, project_slug)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found.")
    try:
        e = create_experiment(vault, project, body.name, body.description)
        return ExperimentResponse(id=e.id, project_id=e.project_id, name=e.name, slug=e.slug, description=e.description)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/projects/{project_slug}/experiments/{exp_slug}", response_model=ExperimentResponse)
def api_get_experiment(project_slug: str, exp_slug: str, request: Request):
    vault = _get_vault(request)
    project = get_project(vault, project_slug)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found.")
    e = get_experiment(vault, project, exp_slug)
    if not e:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_slug}' not found.")
    return ExperimentResponse(id=e.id, project_id=e.project_id, name=e.name, slug=e.slug, description=e.description)
