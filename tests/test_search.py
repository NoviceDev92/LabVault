from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.search import search, update_search_index


def _setup_vault_with_runs(tmp_path: Path):
    """Helper: create a vault with multiple runs for search testing."""
    vault = Vault.init(tmp_path / "vault")
    proj = create_project(vault, "CV Project")
    exp = create_experiment(vault, proj, "ResNet Sweep")

    r1 = create_run(vault, exp,
                    tags={"env": "local", "gpu": "T4"},
                    metrics={"accuracy": 0.92, "loss": 0.15},
                    notes="baseline run")
    r2 = create_run(vault, exp,
                    tags={"env": "cloud", "gpu": "A100"},
                    metrics={"accuracy": 0.97, "loss": 0.05},
                    notes="improved learning rate")
    r3 = create_run(vault, exp,
                    tags={"env": "local", "gpu": "T4"},
                    metrics={"accuracy": 0.88, "loss": 0.22},
                    notes="ablation study")
    return vault, proj, exp, [r1, r2, r3]


def test_fts_text_search(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault, query="baseline")
    assert len(results) == 1
    assert results[0].version == 1


def test_fts_text_search_no_results(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault, query="nonexistent_term_xyz")
    assert len(results) == 0


def test_tag_filter(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault, tag_filters=["env=local"])
    assert len(results) == 2
    versions = {r.version for r in results}
    assert versions == {1, 3}


def test_metric_filter_gt(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault, metric_filters=["accuracy > 0.9"])
    assert len(results) == 2
    versions = {r.version for r in results}
    assert versions == {1, 2}


def test_metric_filter_lt(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault, metric_filters=["loss < 0.1"])
    assert len(results) == 1
    assert results[0].version == 2


def test_combined_tag_and_metric_filter(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault, tag_filters=["env=local"], metric_filters=["accuracy > 0.9"])
    assert len(results) == 1
    assert results[0].version == 1


def test_search_all_no_filters(tmp_path: Path):
    vault, proj, exp, runs = _setup_vault_with_runs(tmp_path)
    results = search(vault)
    assert len(results) == 3
