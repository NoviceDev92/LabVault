from labvault.core.vault import Vault
from labvault.core.run import Run

def add_tags(vault: Vault, run: Run, tags: dict[str, str]) -> None:
    if not tags:
        return
        
    with vault.get_connection() as conn:
        for key, value in tags.items():
            conn.execute(
                "INSERT OR REPLACE INTO tags (run_id, key, value) VALUES (?, ?, ?)",
                (run.id, key, value)
            )

def get_tags(vault: Vault, run: Run) -> dict[str, str]:
    with vault.get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM tags WHERE run_id = ?",
            (run.id,)
        ).fetchall()
        
    return {row[0]: row[1] for row in rows}

def remove_tag(vault: Vault, run: Run, key: str) -> None:
    with vault.get_connection() as conn:
        conn.execute(
            "DELETE FROM tags WHERE run_id = ? AND key = ?",
            (run.id, key)
        )
