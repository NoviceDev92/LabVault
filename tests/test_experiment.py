from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment, get_experiment, list_experiments

def test_create_and_get_experiment(tmp_path: Path):
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Test Project")
    experiment = create_experiment(vault, project, "LR Sweep")
    
    assert experiment.name == "LR Sweep"
    assert experiment.slug == "lr-sweep"
    assert experiment.project_id == project.id
    
    assert (vault.path / "projects" / "test-project" / "lr-sweep").is_dir()
    
    fetched = get_experiment(vault, project, "lr-sweep")
    assert fetched is not None
    assert fetched.id == experiment.id

def test_list_experiments(tmp_path: Path):
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Test Project")
    create_experiment(vault, project, "Exp A")
    create_experiment(vault, project, "Exp B")
    
    experiments = list_experiments(vault, project)
    assert len(experiments) == 2
    assert experiments[0].name == "Exp A"
    assert experiments[1].name == "Exp B"
