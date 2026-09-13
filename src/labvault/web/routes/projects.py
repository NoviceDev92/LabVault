"""Project API routes."""

from fastapi import APIRouter, Request, HTTPException

from labvault.core.project import create_project, get_project, list_projects
from labvault.web.schemas import ProjectCreate, ProjectResponse

router = APIRouter()


def _get_vault(request: Request):
    return request.app.state.vault


@router.get("/projects", response_model=list[ProjectResponse])
def api_list_projects(request: Request):
    vault = _get_vault(request)
    projects = list_projects(vault)
    return [ProjectResponse(id=p.id, name=p.name, slug=p.slug, description=p.description) for p in projects]


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def api_create_project(body: ProjectCreate, request: Request):
    vault = _get_vault(request)
    try:
        p = create_project(vault, body.name, body.description)
        return ProjectResponse(id=p.id, name=p.name, slug=p.slug, description=p.description)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{slug}", response_model=ProjectResponse)
def api_get_project(slug: str, request: Request):
    vault = _get_vault(request)
    p = get_project(vault, slug)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found.")
    return ProjectResponse(id=p.id, name=p.name, slug=p.slug, description=p.description)


@router.delete("/projects/{slug}", status_code=204)
def api_delete_project(slug: str, request: Request):
    vault = _get_vault(request)
    p = get_project(vault, slug)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found.")
    with vault.get_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (p.id,))
    return None
