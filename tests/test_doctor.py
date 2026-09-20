"""Tests for core/doctor.py — vault integrity checker."""

from pathlib import Path

from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.artifact import add_artifact
from labvault.core.doctor import check_integrity


def _setup_vault(tmp_path: Path):
    """Create a vault with a project, experiment, run, and artifact."""
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Doctor Project")
    experiment = create_experiment(vault, project, "Check Exp")
    run = create_run(vault, experiment, metrics={"f1": 0.9})

    # Add an artifact
    f = tmp_path / "train.py"
    f.write_text("print('hello')\n", encoding="utf-8")
    add_artifact(vault, run, f)

    return vault, project, experiment, run


def test_healthy_vault(tmp_path: Path):
    """A clean vault should report no issues."""
    vault, _, _, _ = _setup_vault(tmp_path)
    report = check_integrity(vault)

    assert report.is_healthy is True
    assert len(report.orphaned_db_records) == 0
    assert len(report.orphaned_files) == 0
    assert len(report.hash_mismatches) == 0
    assert len(report.missing_meta) == 0
    assert report.total_artifacts_checked == 1


def test_missing_file_on_disk(tmp_path: Path):
    """Deleting a file from disk should be caught as an orphaned DB record."""
    vault, project, experiment, run = _setup_vault(tmp_path)

    # Manually delete the artifact file
    run_dir = vault.path / "projects" / project.slug / experiment.slug / f"v{run.version}"
    artifact_path = run_dir / "train.py"
    artifact_path.unlink()

    report = check_integrity(vault)

    assert report.is_healthy is False
    assert len(report.orphaned_db_records) == 1
    assert "train.py" in report.orphaned_db_records[0]


def test_orphaned_file_on_disk(tmp_path: Path):
    """A file on disk with no DB record should be flagged."""
    vault, project, experiment, run = _setup_vault(tmp_path)

    # Manually add a file to the run directory without registering in DB
    run_dir = vault.path / "projects" / project.slug / experiment.slug / f"v{run.version}"
    orphan = run_dir / "rogue_file.txt"
    orphan.write_text("I shouldn't be here", encoding="utf-8")

    report = check_integrity(vault)

    assert report.is_healthy is False
    assert len(report.orphaned_files) == 1
    assert "rogue_file.txt" in report.orphaned_files[0]


def test_missing_meta_json(tmp_path: Path):
    """Deleting _meta.json should be caught."""
    vault, project, experiment, run = _setup_vault(tmp_path)

    # Delete _meta.json
    run_dir = vault.path / "projects" / project.slug / experiment.slug / f"v{run.version}"
    meta_path = run_dir / "_meta.json"
    meta_path.unlink()

    report = check_integrity(vault)

    assert report.is_healthy is False
    assert len(report.missing_meta) == 1


def test_hash_mismatch(tmp_path: Path):
    """Corrupting a file's content should trigger a hash mismatch."""
    vault, project, experiment, run = _setup_vault(tmp_path)

    # Modify the file after it was registered
    run_dir = vault.path / "projects" / project.slug / experiment.slug / f"v{run.version}"
    artifact_path = run_dir / "train.py"
    artifact_path.write_text("CORRUPTED CONTENT\n", encoding="utf-8")

    report = check_integrity(vault)

    assert report.is_healthy is False
    assert len(report.hash_mismatches) == 1
    assert "train.py" in report.hash_mismatches[0]
