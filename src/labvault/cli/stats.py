import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from labvault.core.vault import Vault
from labvault.core.stats import get_vault_stats
from labvault.utils.filesize import format_bytes

console = Console()


@click.command("stats")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def stats_cmd(vault_path: str):
    """Show vault-wide statistics."""
    vault = Vault.init(vault_path)
    s = get_vault_stats(vault)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Projects", str(s.total_projects))
    table.add_row("Experiments", str(s.total_experiments))
    table.add_row("Runs", str(s.total_runs))
    table.add_row("Artifacts", str(s.total_artifacts))
    table.add_row("Trashed", str(s.total_trashed))
    table.add_row("Disk Usage", format_bytes(s.disk_usage_bytes))

    console.print(Panel(table, title="[bold]Vault Statistics[/]", border_style="cyan"))
