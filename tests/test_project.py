from pathlib import Path
from labvault.core.vault import Vault
from labvault.core.project import create_project, get_project, list_projects

def test_create_and_get_project(tmp_path: Path):
    vault = Vault.init(tmp_path)
    project = create_project(vault, "Test Project", "A test description")
    
    assert project.name == "Test Project"
    assert project.slug == "test-project"
    assert project.description == "A test description"
    
    assert (vault.path / "projects" / "test-project").is_dir()
    
    fetched = get_project(vault, "test-project")
    assert fetched is not None
    assert fetched.id == project.id
    assert fetched.name == project.name

def test_list_projects(tmp_path: Path):
    vault = Vault.init(tmp_path)
    create_project(vault, "Project A")
    create_project(vault, "Project B")
    
    projects = list_projects(vault)
    assert len(projects) == 2
    assert projects[0].name == "Project A"
    assert projects[1].name == "Project B"
