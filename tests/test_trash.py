from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run, get_run, seal_run
from labvault.core.trash import soft_delete_run, list_trash, restore_from_trash


def test_soft_delete_and_list(tmp_path: Path):
    vault = Vault.init(tmp_path / "vault")
    proj = create_project(vault, "Proj")
    exp = create_experiment(vault, proj, "Exp")
    run = create_run(vault, exp, notes="to be deleted")

    run_dir = vault.path / "projects" / proj.slug / exp.slug / f"v{run.version}"
    assert run_dir.exists()

    trashed = soft_delete_run(vault, run.id)
    assert trashed.version == 1
    assert not run_dir.exists()

    trash_items = list_trash(vault)
    assert len(trash_items) == 1
    assert trash_items[0].version == 1

    # Run should no longer be fetchable
    fetched = get_run(vault, exp, 1)
    assert fetched is None


def test_restore_from_trash(tmp_path: Path):
    vault = Vault.init(tmp_path / "vault")
    proj = create_project(vault, "Proj")
    exp = create_experiment(vault, proj, "Exp")
    run = create_run(vault, exp, notes="restore me")

    run_dir = vault.path / "projects" / proj.slug / exp.slug / f"v{run.version}"

    soft_delete_run(vault, run.id)
    assert not run_dir.exists()

    trash_items = list_trash(vault)
    restore_from_trash(vault, trash_items[0].id)

    assert run_dir.exists()
    assert len(list_trash(vault)) == 0


def test_seal_run(tmp_path: Path):
    vault = Vault.init(tmp_path / "vault")
    proj = create_project(vault, "Proj")
    exp = create_experiment(vault, proj, "Exp")
    run = create_run(vault, exp)

    assert run.status == "draft"
    sealed = seal_run(vault, exp, run)
    assert sealed.status == "sealed"
    assert sealed.sealed_at is not None

    # Sealing again should raise
    import pytest
    with pytest.raises(ValueError, match="already sealed"):
        seal_run(vault, exp, sealed)
