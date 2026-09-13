"""Pydantic request/response models for the web API."""

from pydantic import BaseModel
from typing import Optional


# --- Projects ---

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None


# --- Experiments ---

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: int
    project_id: int
    name: str
    slug: str
    description: Optional[str] = None


# --- Runs ---

class RunCreate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[dict[str, str]] = None
    metrics: Optional[dict[str, float]] = None


class RunUpdate(BaseModel):
    notes: Optional[str] = None
    tags: Optional[dict[str, str]] = None
    metrics: Optional[dict[str, float]] = None


class ArtifactResponse(BaseModel):
    id: int
    run_id: int
    filename: str
    artifact_type: str
    size_bytes: int
    content_hash: str
    rel_path: str
    created_at: str


class RunResponse(BaseModel):
    id: int
    experiment_id: int
    version: int
    status: str
    notes: Optional[str] = None
    created_at: str
    sealed_at: Optional[str] = None
    metrics: Optional[dict[str, float]] = None
    tags: Optional[dict[str, str]] = None
    artifacts: Optional[list[ArtifactResponse]] = None


# --- Search ---

class SearchResultResponse(BaseModel):
    run_id: int
    project_name: str
    project_slug: str
    experiment_name: str
    experiment_slug: str
    version: int
    notes: Optional[str] = None
    metrics: dict[str, float]
    tags: dict[str, str]


# --- Compare ---

class CompareRequest(BaseModel):
    run_ids: list[int]


class MetricDeltaResponse(BaseModel):
    key: str
    values: dict[int, float]
    min_val: float
    max_val: float
    spread: float


class TagDiffResponse(BaseModel):
    key: str
    values: dict[int, str]
    is_uniform: bool


class ArtifactDiffResponse(BaseModel):
    filename: str
    present_in: list[int]
    sizes: dict[int, int]


class CompareResponse(BaseModel):
    run_ids: list[int]
    run_versions: dict[int, int]
    metric_deltas: list[MetricDeltaResponse]
    tag_diffs: list[TagDiffResponse]
    artifact_diffs: list[ArtifactDiffResponse]
