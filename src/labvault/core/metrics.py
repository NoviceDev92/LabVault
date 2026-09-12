from labvault.core.vault import Vault
from labvault.core.run import Run

def add_metrics(vault: Vault, run: Run, metrics: dict[str, float]) -> None:
    if not metrics:
        return
        
    with vault.get_connection() as conn:
        for key, value in metrics.items():
            conn.execute(
                "INSERT OR REPLACE INTO metrics (run_id, key, value) VALUES (?, ?, ?)",
                (run.id, key, value)
            )

def get_metrics(vault: Vault, run: Run) -> dict[str, float]:
    with vault.get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM metrics WHERE run_id = ?",
            (run.id,)
        ).fetchall()
        
    return {row[0]: row[1] for row in rows}
