"""Compare API route."""

from fastapi import APIRouter, Request, HTTPException

from labvault.core.comparison import compare_runs
from labvault.web.schemas import CompareRequest, CompareResponse, MetricDeltaResponse, TagDiffResponse, ArtifactDiffResponse

router = APIRouter()


def _get_vault(request: Request):
    return request.app.state.vault


@router.post("/compare", response_model=CompareResponse)
def api_compare(body: CompareRequest, request: Request):
    vault = _get_vault(request)
    try:
        result = compare_runs(vault, body.run_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CompareResponse(
        run_ids=result.run_ids,
        run_versions={str(k): v for k, v in result.run_versions.items()},
        metric_deltas=[
            MetricDeltaResponse(
                key=md.key,
                values={str(k): v for k, v in md.values.items()},
                min_val=md.min_val,
                max_val=md.max_val,
                spread=md.spread,
            )
            for md in result.metric_deltas
        ],
        tag_diffs=[
            TagDiffResponse(
                key=td.key,
                values={str(k): v for k, v in td.values.items()},
                is_uniform=td.is_uniform,
            )
            for td in result.tag_diffs
        ],
        artifact_diffs=[
            ArtifactDiffResponse(
                filename=ad.filename,
                present_in=ad.present_in,
                sizes={str(k): v for k, v in ad.sizes.items()},
            )
            for ad in result.artifact_diffs
        ],
    )
