from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.artifact import add_artifact, list_artifacts, detect_artifact_type

def test_detect_artifact_type():
    assert detect_artifact_type("model.pt") == "model"
    assert detect_artifact_type("train.py") == "code"
    assert detect_artifact_type("config.yaml") == "config"
    assert detect_artifact_type("metrics.csv") == "data"
    assert detect_artifact_type("chart.png") == "figure"
    assert detect_artifact_type("unknown.bin") == "other"

def test_add_and_list_artifacts(tmp_path: Path):
    vault = Vault.init(tmp_path / "vault")
    project = create_project(vault, "Test Project")
    experiment = create_experiment(vault, project, "Exp A")
    run = create_run(vault, experiment)
    
    # Create a dummy file to add
    dummy_file = tmp_path / "model.pt"
    dummy_file.write_text("dummy model weights")
    
    artifact = add_artifact(vault, run, dummy_file)
    assert artifact.filename == "model.pt"
    assert artifact.artifact_type == "model"
    
    run_dir = vault.path / "projects" / project.slug / experiment.slug / "v1"
    assert (run_dir / "model.pt").exists()
    
    artifacts = list_artifacts(vault, run)
    assert len(artifacts) == 1
    assert artifacts[0].filename == "model.pt"

    # Add same file again (dedup)
    artifact2 = add_artifact(vault, run, dummy_file)
    assert artifact2.id == artifact.id
