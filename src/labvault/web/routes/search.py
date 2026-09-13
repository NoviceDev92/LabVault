"""Search API route."""

from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query

from labvault.core.search import search
from labvault.web.schemas import SearchResultResponse

router = APIRouter()


def _get_vault(request: Request):
    return request.app.state.vault


@router.get("/search", response_model=list[SearchResultResponse])
def api_search(
    request: Request,
    q: Optional[str] = Query(None, description="Full-text search query"),
    tag: Optional[list[str]] = Query(None, description="Tag filters (KEY=VALUE)"),
    metric: Optional[list[str]] = Query(None, description='Metric filters (e.g., "f1 > 0.9")'),
    after: Optional[str] = Query(None, description="Only runs after this date (YYYY-MM-DD)"),
    before: Optional[str] = Query(None, description="Only runs before this date (YYYY-MM-DD)"),
):
    vault = _get_vault(request)
    try:
        results = search(
            vault,
            query=q,
            tag_filters=tag,
            metric_filters=metric,
            after=after,
            before=before,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [
        SearchResultResponse(
            run_id=r.run_id,
            project_name=r.project_name,
            project_slug=r.project_slug,
            experiment_name=r.experiment_name,
            experiment_slug=r.experiment_slug,
            version=r.version,
            notes=r.notes,
            metrics=r.metrics,
            tags=r.tags,
        )
        for r in results
    ]
