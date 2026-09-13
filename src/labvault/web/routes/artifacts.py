"""Artifact API routes — upload, download, preview."""

import base64
import csv
import io
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from labvault.core.run import Run, get_run_directory
from labvault.core.artifact import add_artifact, get_artifact, list_artifacts, Artifact
from labvault.core.experiment import Experiment
from labvault.web.schemas import ArtifactResponse

router = APIRouter()


def _get_vault(request: Request):
    return request.app.state.vault


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


def _get_experiment_by_id(vault, exp_id: int) -> Experiment:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, project_id, name, slug, description FROM experiments WHERE id = ?",
            (exp_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Experiment with id {exp_id} not found.")
    return Experiment(id=row[0], project_id=row[1], name=row[2], slug=row[3], description=row[4])


@router.post("/runs/{run_id}/artifacts", response_model=ArtifactResponse, status_code=201)
async def api_upload_artifact(run_id: int, request: Request, file: UploadFile = File(...)):
    vault = _get_vault(request)
    run = _get_run_by_id(vault, run_id)
    experiment = _get_experiment_by_id(vault, run.experiment_id)

    # Save uploaded file to a temp location, then use add_artifact
    run_dir = get_run_directory(vault, experiment, run)
    run_dir.mkdir(parents=True, exist_ok=True)
    temp_path = run_dir / file.filename

    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        art = add_artifact(vault, run, temp_path)
        return ArtifactResponse(
            id=art.id, run_id=art.run_id, filename=art.filename,
            artifact_type=art.artifact_type, size_bytes=art.size_bytes,
            content_hash=art.content_hash, rel_path=art.rel_path, created_at=art.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/artifacts/{artifact_id}/download")
def api_download_artifact(artifact_id: int, request: Request):
    vault = _get_vault(request)
    try:
        art = get_artifact(vault, artifact_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    run = _get_run_by_id(vault, art.run_id)
    experiment = _get_experiment_by_id(vault, run.experiment_id)
    run_dir = get_run_directory(vault, experiment, run)
    file_path = run_dir / art.rel_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk.")

    return FileResponse(str(file_path), filename=art.filename)


@router.get("/artifacts/{artifact_id}/preview")
def api_preview_artifact(artifact_id: int, request: Request):
    vault = _get_vault(request)
    try:
        art = get_artifact(vault, artifact_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    run = _get_run_by_id(vault, art.run_id)
    experiment = _get_experiment_by_id(vault, run.experiment_id)
    run_dir = get_run_directory(vault, experiment, run)
    file_path = run_dir / art.rel_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk.")

    # Images: return base64
    if art.artifact_type == "figure":
        content = file_path.read_bytes()
        ext = file_path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        b64 = base64.b64encode(content).decode("utf-8")
        return {"type": "image", "mime": mime, "data": f"data:{mime};base64,{b64}"}

    # CSV: return as JSON table
    if file_path.suffix.lower() == ".csv":
        text = file_path.read_text(encoding="utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        headers = reader.fieldnames or []
        return {"type": "table", "headers": headers, "rows": rows}

    # Text files: return content
    text_extensions = {".py", ".txt", ".log", ".md", ".yaml", ".yml", ".json", ".toml", ".sh", ".cfg", ".ini", ".tex", ".csv", ".tsv"}
    if file_path.suffix.lower() in text_extensions:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return {"type": "text", "content": text, "language": file_path.suffix.lstrip(".")}

    # Binary: just return metadata
    return {"type": "binary", "filename": art.filename, "size_bytes": art.size_bytes}
