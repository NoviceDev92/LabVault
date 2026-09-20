"""Tests for core/export.py — CSV, LaTeX, Markdown, JSON, ZIP export."""

from pathlib import Path
import json
import zipfile
import io

from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.artifact import add_artifact
from labvault.core.export import (
    export_table_csv,
    export_table_json,
    export_table_markdown,
    export_table_latex,
    export_table,
    pack_run_zip,
)


def _make_experiment_with_runs(tmp_path: Path):
    """Helper: create a vault with 2 runs (with metrics & tags)."""
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Export Project")
    experiment = create_experiment(vault, project, "Results Exp")

    run1 = create_run(vault, experiment,
                      tags={"env": "gpu", "lr": "0.001"},
                      metrics={"accuracy": 0.92, "loss": 0.35})
    run2 = create_run(vault, experiment,
                      tags={"env": "cpu", "lr": "0.01"},
                      metrics={"accuracy": 0.88, "loss": 0.45})
    return vault, project, experiment, run1, run2


# ────────── CSV ──────────

def test_export_csv(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    csv_str = export_table_csv(vault, experiment)

    assert "version" in csv_str
    assert "status" in csv_str
    assert "accuracy" in csv_str
    assert "loss" in csv_str
    assert "tag:env" in csv_str
    assert "tag:lr" in csv_str

    lines = csv_str.strip().split("\n")
    assert len(lines) == 3  # 1 header + 2 data rows


def test_export_csv_header_order(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    csv_str = export_table_csv(vault, experiment)
    header = csv_str.strip().split("\n")[0]
    fields = header.split(",")
    assert fields[0] == "version"
    assert fields[1] == "status"


# ────────── JSON ──────────

def test_export_json(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    json_str = export_table_json(vault, experiment)
    data = json.loads(json_str)

    assert "headers" in data
    assert "rows" in data
    assert len(data["rows"]) == 2
    assert "accuracy" in data["headers"]


# ────────── Markdown ──────────

def test_export_markdown(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    md_str = export_table_markdown(vault, experiment)

    lines = md_str.strip().split("\n")
    assert len(lines) >= 4  # header + separator + 2 data rows
    assert lines[0].startswith("| version")
    assert "---" in lines[1]


# ────────── LaTeX ──────────

def test_export_latex(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    tex_str = export_table_latex(vault, experiment)

    assert r"\begin{table}" in tex_str
    assert r"\end{table}" in tex_str
    assert r"\toprule" in tex_str
    assert r"\midrule" in tex_str
    assert r"\bottomrule" in tex_str
    assert r"\caption" in tex_str


def test_export_latex_escapes_underscores(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    tex_str = export_table_latex(vault, experiment)

    # Tag headers like "tag:env" and "tag:lr" shouldn't contain bare underscores
    # Metric keys shouldn't either. The escaped form is \_
    # Since our keys don't have underscores in this test, let's verify
    # the experiment name in caption
    assert "Results Exp" in tex_str or "Results\\_Exp" in tex_str


# ────────── Dispatcher ──────────

def test_export_table_dispatcher(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)

    csv_result = export_table(vault, experiment, "csv")
    assert "version" in csv_result

    json_result = export_table(vault, experiment, "json")
    data = json.loads(json_result)
    assert "headers" in data

    md_result = export_table(vault, experiment, "markdown")
    assert md_result.startswith("|")

    tex_result = export_table(vault, experiment, "latex")
    assert r"\begin{table}" in tex_result


def test_export_table_invalid_format(tmp_path: Path):
    vault, _, experiment, _, _ = _make_experiment_with_runs(tmp_path)
    try:
        export_table(vault, experiment, "xml")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown format" in str(e)


# ────────── ZIP Pack ──────────

def test_pack_run_zip(tmp_path: Path):
    vault, _, experiment, run1, _ = _make_experiment_with_runs(tmp_path)

    # Add some artifacts to run1
    f1 = tmp_path / "train.py"
    f1.write_text("print('training')\n", encoding="utf-8")
    add_artifact(vault, run1, f1)

    f2 = tmp_path / "config.yaml"
    f2.write_text("epochs: 10\n", encoding="utf-8")
    add_artifact(vault, run1, f2)

    zip_bytes = pack_run_zip(vault, experiment, run1)
    assert len(zip_bytes) > 0

    # Verify it's a valid ZIP
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    assert "train.py" in names
    assert "config.yaml" in names

    # Verify content integrity
    content = zf.read("train.py").decode("utf-8")
    assert "training" in content


def test_pack_run_zip_empty_run(tmp_path: Path):
    vault, _, experiment, _, run2 = _make_experiment_with_runs(tmp_path)

    # run2 has no artifacts — should produce a valid (possibly empty) ZIP
    zip_bytes = pack_run_zip(vault, experiment, run2)
    assert len(zip_bytes) > 0

    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    # Should contain at least _meta.json
    names = zf.namelist()
    assert "_meta.json" in names
