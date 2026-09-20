"""Compare multiple runs side-by-side with structured diffs."""

from dataclasses import dataclass, field
from typing import Optional

from labvault.core.vault import Vault
from labvault.core.run import Run
from labvault.core.metrics import get_metrics
from labvault.core.tags import get_tags
from labvault.core.artifact import list_artifacts, Artifact


@dataclass
class MetricDelta:
    key: str
    values: dict[int, float]  # run_id -> value
    min_val: float
    max_val: float
    spread: float  # max - min


@dataclass
class TagDiff:
    key: str
    values: dict[int, str]  # run_id -> value
    is_uniform: bool  # True if all runs have the same value


@dataclass
class ArtifactDiff:
    filename: str
    present_in: list[int]  # run_ids that have this file
    sizes: dict[int, int]  # run_id -> size_bytes


@dataclass
class ComparisonResult:
    run_ids: list[int]
    run_versions: dict[int, int]  # run_id -> version
    metric_deltas: list[MetricDelta]
    tag_diffs: list[TagDiff]
    artifact_diffs: list[ArtifactDiff]


def compare_runs(vault: Vault, run_ids: list[int]) -> ComparisonResult:
    """Compare multiple runs and return structured diffs."""
    if len(run_ids) < 2:
        raise ValueError("Need at least 2 runs to compare.")

    # Fetch all run data
    runs_data: dict[int, dict] = {}
    run_versions: dict[int, int] = {}

    for rid in run_ids:
        with vault.get_connection() as conn:
            row = conn.execute(
                "SELECT id, experiment_id, version, status, notes, created_at, sealed_at "
                "FROM runs WHERE id = ?",
                (rid,),
            ).fetchone()
            if not row:
                raise ValueError(f"Run with id {rid} not found.")

            run = Run(
                id=row[0], experiment_id=row[1], version=row[2],
                status=row[3], notes=row[4], created_at=row[5], sealed_at=row[6],
            )
            run_versions[rid] = run.version

            metrics = get_metrics(vault, run)
            tags = get_tags(vault, run)
            artifacts = list_artifacts(vault, run)

            runs_data[rid] = {
                "metrics": metrics,
                "tags": tags,
                "artifacts": artifacts,
            }

    # Build metric deltas
    all_metric_keys: set[str] = set()
    for data in runs_data.values():
        all_metric_keys.update(data["metrics"].keys())

    metric_deltas = []
    for key in sorted(all_metric_keys):
        values = {}
        for rid in run_ids:
            val = runs_data[rid]["metrics"].get(key)
            if val is not None:
                values[rid] = val
        if values:
            vals = list(values.values())
            metric_deltas.append(MetricDelta(
                key=key,
                values=values,
                min_val=min(vals),
                max_val=max(vals),
                spread=max(vals) - min(vals),
            ))

    # Build tag diffs
    all_tag_keys: set[str] = set()
    for data in runs_data.values():
        all_tag_keys.update(data["tags"].keys())

    tag_diffs = []
    for key in sorted(all_tag_keys):
        values = {}
        for rid in run_ids:
            val = runs_data[rid]["tags"].get(key)
            if val is not None:
                values[rid] = val
        unique_vals = set(values.values())
        tag_diffs.append(TagDiff(
            key=key,
            values=values,
            is_uniform=len(unique_vals) <= 1,
        ))

    # Build artifact diffs
    all_filenames: set[str] = set()
    for data in runs_data.values():
        for a in data["artifacts"]:
            all_filenames.add(a.filename)

    artifact_diffs = []
    for filename in sorted(all_filenames):
        present_in = []
        sizes = {}
        for rid in run_ids:
            for a in runs_data[rid]["artifacts"]:
                if a.filename == filename:
                    present_in.append(rid)
                    sizes[rid] = a.size_bytes
                    break
        artifact_diffs.append(ArtifactDiff(
            filename=filename,
            present_in=present_in,
            sizes=sizes,
        ))

    return ComparisonResult(
        run_ids=run_ids,
        run_versions=run_versions,
        metric_deltas=metric_deltas,
        tag_diffs=tag_diffs,
        artifact_diffs=artifact_diffs,
    )


# ---------------------------------------------------------------------------
# File-level content comparison
# ---------------------------------------------------------------------------

@dataclass
class FileDiff:
    filename: str
    diff_type: str  # "text", "image", "binary"
    diff_lines: list[str] = field(default_factory=list)  # unified diff lines (text only)
    images: dict[int, str] = field(default_factory=dict)  # run_id -> base64 data URI (image only)
    sizes: dict[int, int] = field(default_factory=dict)   # run_id -> size_bytes
    hashes: dict[int, str] = field(default_factory=dict)  # run_id -> content_hash


_TEXT_EXTENSIONS = {
    ".py", ".ipynb", ".sh", ".yaml", ".yml", ".json", ".toml", ".cfg",
    ".ini", ".txt", ".md", ".tex", ".log", ".csv", ".tsv",
}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".bmp", ".webp"}


def compare_file_contents(
    vault: Vault,
    run_ids: list[int],
    filename: str,
) -> FileDiff:
    """Compare a single file across multiple runs by content."""
    import base64
    import difflib
    from pathlib import Path as _Path

    if len(run_ids) < 2:
        raise ValueError("Need at least 2 runs to compare.")

    ext = _Path(filename).suffix.lower()

    # Resolve each run's file path
    run_paths: dict[int, _Path] = {}
    sizes: dict[int, int] = {}
    hashes: dict[int, str] = {}

    for rid in run_ids:
        with vault.get_connection() as conn:
            run_row = conn.execute(
                "SELECT id, experiment_id, version, status, notes, created_at, sealed_at "
                "FROM runs WHERE id = ?", (rid,),
            ).fetchone()
            if not run_row:
                raise ValueError(f"Run {rid} not found.")

            exp_row = conn.execute(
                "SELECT id, project_id, name, slug, description "
                "FROM experiments WHERE id = ?", (run_row[1],),
            ).fetchone()

            proj_slug = conn.execute(
                "SELECT slug FROM projects WHERE id = ?", (exp_row[1],),
            ).fetchone()[0]

        run_dir = vault.path / "projects" / proj_slug / exp_row[3] / f"v{run_row[2]}"
        fpath = run_dir / filename

        if fpath.exists() and fpath.is_file():
            run_paths[rid] = fpath
            sizes[rid] = fpath.stat().st_size
            # Fetch hash from DB if available
            with vault.get_connection() as conn:
                art_row = conn.execute(
                    "SELECT content_hash FROM artifacts WHERE run_id = ? AND filename = ?",
                    (rid, filename),
                ).fetchone()
            hashes[rid] = art_row[0] if art_row else ""

    if len(run_paths) < 2:
        return FileDiff(
            filename=filename,
            diff_type="binary",
            sizes=sizes,
            hashes=hashes,
        )

    # Determine diff type by extension
    if ext in _TEXT_EXTENSIONS:
        # Read text from first two available runs and produce unified diff
        ordered_ids = [rid for rid in run_ids if rid in run_paths]
        a_id, b_id = ordered_ids[0], ordered_ids[1]
        try:
            a_lines = run_paths[a_id].read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            b_lines = run_paths[b_id].read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        except Exception:
            return FileDiff(filename=filename, diff_type="binary", sizes=sizes, hashes=hashes)

        diff_lines = list(difflib.unified_diff(
            a_lines, b_lines,
            fromfile=f"v{_get_version(vault, a_id)}:{filename}",
            tofile=f"v{_get_version(vault, b_id)}:{filename}",
            lineterm="",
        ))
        return FileDiff(
            filename=filename,
            diff_type="text",
            diff_lines=diff_lines,
            sizes=sizes,
            hashes=hashes,
        )

    elif ext in _IMAGE_EXTENSIONS:
        images: dict[int, str] = {}
        mime_map = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp",
        }
        mime = mime_map.get(ext, "application/octet-stream")
        for rid, fpath in run_paths.items():
            raw = fpath.read_bytes()
            b64 = base64.b64encode(raw).decode("utf-8")
            images[rid] = f"data:{mime};base64,{b64}"
        return FileDiff(
            filename=filename,
            diff_type="image",
            images=images,
            sizes=sizes,
            hashes=hashes,
        )

    else:
        return FileDiff(
            filename=filename,
            diff_type="binary",
            sizes=sizes,
            hashes=hashes,
        )


def _get_version(vault: Vault, run_id: int) -> int:
    with vault.get_connection() as conn:
        row = conn.execute("SELECT version FROM runs WHERE id = ?", (run_id,)).fetchone()
    return row[0] if row else 0

