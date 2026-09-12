import json
from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run, get_run, list_runs

def test_create_and_get_run(tmp_path: Path):
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Test Project")
    experiment = create_experiment(vault, project, "Exp A")
    
    run1 = create_run(vault, experiment, tags={"env": "local"}, metrics={"f1": 0.9})
    run2 = create_run(vault, experiment)
    
    assert run1.version == 1
    assert run2.version == 2
    
    run_dir = vault.path / "projects" / project.slug / experiment.slug / "v1"
    assert run_dir.is_dir()
    
    meta_path = run_dir / "_meta.json"
    assert meta_path.exists()
    
    with open(meta_path) as f:
        meta = json.load(f)
        assert meta["version"] == 1
        assert meta["tags"]["env"] == "local"
        assert meta["metrics"]["f1"] == 0.9

    fetched = get_run(vault, experiment, 1)
    assert fetched is not None
    assert fetched.id == run1.id
    
def test_list_runs(tmp_path: Path):
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Test Project")
    experiment = create_experiment(vault, project, "Exp A")
    
    create_run(vault, experiment)
    create_run(vault, experiment)
    
    runs = list_runs(vault, experiment)
    assert len(runs) == 2
    # list_runs orders by version DESC
    assert runs[0].version == 2
    assert runs[1].version == 1
