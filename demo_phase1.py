import sys
from pathlib import Path

# Add the src directory to Python path if running directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

from labvault.core.vault import Vault
from labvault.core.project import create_project, list_projects
from labvault.core.experiment import create_experiment
from labvault.core.run import create_run
from labvault.core.artifact import add_artifact

def main():
    print("Initializing LabVault at ./my_local_vault...")
    vault = Vault.init("./my_local_vault")
    
    print("Creating project 'Computer Vision'...")
    project = create_project(vault, "Computer Vision", "My CV experiments")
    
    print("Creating experiment 'ResNet Ablation'...")
    exp = create_experiment(vault, project, "ResNet Ablation")
    
    print("Creating a Run with metrics and tags...")
    run = create_run(
        vault, 
        exp, 
        tags={"env": "local", "gpu": "RTX3090"}, 
        metrics={"accuracy": 0.95, "loss": 0.12},
        notes="First test run"
    )
    
    print(f"Created Run version: v{run.version}")
    
    # Let's create a dummy file to add as an artifact
    dummy_file = Path("dummy_model.pt")
    dummy_file.write_text("fake weights data")
    
    print(f"Adding artifact: {dummy_file}...")
    add_artifact(vault, run, dummy_file)
    
    print(f"\nDone! Check out the folder structure at: {vault.path.absolute()}")
    print("Look inside for the SQLite DB and the nested project folders with your _meta.json file!")

if __name__ == "__main__":
    main()
