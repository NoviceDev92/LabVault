"""Export runs and experiment tables in various formats."""

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Optional

from labvault.core.vault import Vault
from labvault.core.experiment import Experiment
from labvault.core.run import Run, list_runs, get_run_directory
from labvault.core.metrics import get_metrics
from labvault.core.tags import get_tags
from labvault.core.artifact import list_artifacts


def _build_table_data(vault: Vault, experiment: Experiment) -> tuple[list[str], list[dict]]:
    """Build tabular data for an experiment's runs. Returns (headers, rows)."""
    runs = list_runs(vault, experiment)

    all_metric_keys: set[str] = set()
    all_tag_keys: set[str] = set()
    rows_raw = []

    for run in runs:
        metrics = get_metrics(vault, run)
        tags = get_tags(vault, run)
        all_metric_keys.update(metrics.keys())
        all_tag_keys.update(tags.keys())
        rows_raw.append((run, metrics, tags))

    sorted_metric_keys = sorted(all_metric_keys)
    sorted_tag_keys = sorted(all_tag_keys)

    headers = ["version", "status"] + sorted_metric_keys + [f"tag:{k}" for k in sorted_tag_keys]

    rows = []
    for run, metrics, tags in rows_raw:
        row = {
            "version": f"v{run.version}",
            "status": run.status,
        }
        for mk in sorted_metric_keys:
            row[mk] = str(metrics.get(mk, ""))
        for tk in sorted_tag_keys:
            row[f"tag:{tk}"] = tags.get(tk, "")
        rows.append(row)

    return headers, rows


def export_table_csv(vault: Vault, experiment: Experiment) -> str:
    """Export experiment runs as CSV string."""
    headers, rows = _build_table_data(vault, experiment)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_table_json(vault: Vault, experiment: Experiment) -> str:
    """Export experiment runs as JSON string."""
    headers, rows = _build_table_data(vault, experiment)
    return json.dumps({"headers": headers, "rows": rows}, indent=2)


def export_table_markdown(vault: Vault, experiment: Experiment) -> str:
    """Export experiment runs as Markdown table."""
    headers, rows = _build_table_data(vault, experiment)

    # Header row
    lines = ["| " + " | ".join(headers) + " |"]
    # Separator
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    # Data rows
    for row in rows:
        cells = [row.get(h, "") for h in headers]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def export_table_latex(vault: Vault, experiment: Experiment) -> str:
    """Export experiment runs as LaTeX table."""
    headers, rows = _build_table_data(vault, experiment)

    def escape_latex(s: str) -> str:
        return s.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")

    col_spec = "l" * len(headers)
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\toprule",
        " & ".join(escape_latex(h) for h in headers) + r" \\",
        r"\midrule",
    ]

    for row in rows:
        cells = [escape_latex(row.get(h, "")) for h in headers]
        lines.append(" & ".join(cells) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        f"\\caption{{{escape_latex(experiment.name)}}}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def export_table(vault: Vault, experiment: Experiment, fmt: str = "csv") -> str:
    """Export experiment table in the specified format."""
    exporters = {
        "csv": export_table_csv,
        "json": export_table_json,
        "markdown": export_table_markdown,
        "latex": export_table_latex,
    }
    exporter = exporters.get(fmt)
    if not exporter:
        raise ValueError(f"Unknown format: '{fmt}'. Use one of: {list(exporters.keys())}")
    return exporter(vault, experiment)


def pack_run_zip(vault: Vault, experiment: Experiment, run: Run) -> bytes:
    """Pack a run directory into a ZIP file and return the bytes."""
    run_dir = get_run_directory(vault, experiment, run)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if run_dir.exists():
            for file_path in run_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(run_dir)
                    zf.write(file_path, arcname)

    return buffer.getvalue()
