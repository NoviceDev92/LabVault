from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.metrics import add_metrics, get_metrics
from labvault.core.tags import add_tags, get_tags, remove_tag

def test_add_and_get_metrics(tmp_path: Path):
    vault = Vault.init(tmp_path / "vault")
    project = create_project(vault, "Project")
    experiment = create_experiment(vault, project, "Exp")
    run = create_run(vault, experiment)
    
    add_metrics(vault, run, {"f1": 0.95, "loss": 0.1})
    metrics = get_metrics(vault, run)
    
    assert metrics["f1"] == 0.95
    assert metrics["loss"] == 0.1

def test_add_and_get_tags(tmp_path: Path):
    vault = Vault.init(tmp_path / "vault")
    project = create_project(vault, "Project")
    experiment = create_experiment(vault, project, "Exp")
    run = create_run(vault, experiment)
    
    add_tags(vault, run, {"env": "local", "gpu": "T4"})
    tags = get_tags(vault, run)
    
    assert tags["env"] == "local"
    assert tags["gpu"] == "T4"
    
    remove_tag(vault, run, "gpu")
    tags = get_tags(vault, run)
    
    assert "gpu" not in tags
    assert tags["env"] == "local"
