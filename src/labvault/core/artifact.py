import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from labvault.core.vault import Vault
from labvault.core.run import Run, get_run_directory, generate_meta_json
from labvault.utils.hashing import compute_sha256

@dataclass
class Artifact:
    id: int
    run_id: int
    filename: str
    artifact_type: str
    size_bytes: int
    content_hash: str
    rel_path: str
    created_at: str

def detect_artifact_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mapping = {
        ".py": "code", ".ipynb": "code", ".sh": "code",
        ".yaml": "config", ".yml": "config", ".json": "config", ".toml": "config",
        ".pt": "model", ".pth": "model", ".onnx": "model", ".h5": "model", ".pkl": "model",
        ".csv": "result", ".txt": "result", ".log": "result",
        ".png": "figure", ".jpg": "figure", ".jpeg": "figure", ".svg": "figure", ".pdf": "document",
        ".parquet": "data", ".npy": "data", ".tsv": "data",
        ".md": "document", ".tex": "document", ".docx": "document"
    }
    # pdf could be figure or document, defaulting to document
    if ext == ".csv":
        return "data" # Or result. Let's return data as a default, users can override if we add it
    return mapping.get(ext, "other")

def add_artifact(vault: Vault, run: Run, filepath: Path | str, artifact_type: Optional[str] = None) -> Artifact:
    filepath = Path(filepath)
    if not filepath.exists() or not filepath.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")
        
    filename = filepath.name
    size_bytes = filepath.stat().st_size
    content_hash = compute_sha256(filepath)
    
    if artifact_type is None:
        artifact_type = detect_artifact_type(filename)
        
    # Check if duplicate in this run
    with vault.get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM artifacts WHERE run_id = ? AND content_hash = ? AND filename = ?",
            (run.id, content_hash, filename)
        ).fetchone()
        
        if existing:
            # File already exists identically, return it
            return get_artifact(vault, existing[0])
            
        # Insert artifact
        cursor = conn.execute(
            "INSERT INTO artifacts (run_id, filename, artifact_type, size_bytes, content_hash, rel_path) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run.id, filename, artifact_type, size_bytes, content_hash, filename)
        )
        artifact_id = cursor.lastrowid
        
    # Copy file to vault
    from labvault.core.experiment import get_experiment # Need to fetch experiment
    
    # We need experiment to get run dir. This is a bit inefficient, let's just fetch experiment_id and then experiment
    with vault.get_connection() as conn:
        experiment_id = run.experiment_id
        row = conn.execute("SELECT project_id, name, slug, description FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
        from labvault.core.experiment import Experiment
        experiment = Experiment(id=experiment_id, project_id=row[0], name=row[1], slug=row[2], description=row[3])
    
    run_dir = get_run_directory(vault, experiment, run)
    dest_path = run_dir / filename
    
    shutil.copy2(filepath, dest_path)
    
    # Regenerate meta.json
    generate_meta_json(vault, experiment, run)
    
    return get_artifact(vault, artifact_id)

def get_artifact(vault: Vault, artifact_id: int) -> Artifact:
    with vault.get_connection() as conn:
        row = conn.execute(
            "SELECT id, run_id, filename, artifact_type, size_bytes, content_hash, rel_path, created_at "
            "FROM artifacts WHERE id = ?",
            (artifact_id,)
        ).fetchone()
        
    return Artifact(
        id=row[0], run_id=row[1], filename=row[2], artifact_type=row[3], 
        size_bytes=row[4], content_hash=row[5], rel_path=row[6], created_at=row[7]
    )

def list_artifacts(vault: Vault, run: Run) -> list[Artifact]:
    with vault.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, run_id, filename, artifact_type, size_bytes, content_hash, rel_path, created_at "
            "FROM artifacts WHERE run_id = ? ORDER BY filename",
            (run.id,)
        ).fetchall()
        
    return [Artifact(
        id=row[0], run_id=row[1], filename=row[2], artifact_type=row[3], 
        size_bytes=row[4], content_hash=row[5], rel_path=row[6], created_at=row[7]
    ) for row in rows]


def extract_metrics_from_file(filepath: Path | str) -> dict[str, float]:
    """Auto-extract numeric key-value pairs from .json or .csv files.

    For JSON: scans top-level keys for numeric values.
    For CSV: reads the first data row and extracts numeric columns.
    Returns a dict of metric_key -> float_value.
    """
    import csv as csv_mod
    import json as json_mod

    filepath = Path(filepath)
    ext = filepath.suffix.lower()
    metrics: dict[str, float] = {}

    try:
        if ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json_mod.load(f)
            if isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        metrics[key] = float(val)

        elif ext == ".csv":
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv_mod.DictReader(f)
                for row in reader:
                    for key, val in row.items():
                        if key and val:
                            try:
                                metrics[key] = float(val)
                            except (ValueError, TypeError):
                                pass
                    break  # Only first row
    except Exception:
        pass  # Silently return empty if file can't be parsed

    return metrics

