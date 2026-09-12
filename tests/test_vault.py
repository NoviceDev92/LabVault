from pathlib import Path
from labvault.core.vault import Vault

def test_vault_init(tmp_path: Path):
    vault_path = tmp_path / "myvault"
    vault = Vault.init(vault_path)
    
    assert vault.path == vault_path
    assert (vault_path / "labvault.db").exists()
    assert (vault_path / "projects").is_dir()
    assert (vault_path / ".trash").is_dir()
    
def test_vault_open_existing(tmp_path: Path):
    vault_path = tmp_path / "myvault"
    vault1 = Vault.init(vault_path)
    vault2 = Vault.init(vault_path)
    
    assert vault1.path == vault2.path
    assert vault1.db_path == vault2.db_path
