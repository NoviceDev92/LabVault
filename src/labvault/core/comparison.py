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
