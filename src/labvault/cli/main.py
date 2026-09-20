import click
from rich.console import Console

from labvault.core.vault import Vault
from labvault.cli.project import project_group
from labvault.cli.experiment import experiment_group
from labvault.cli.run import run_group
from labvault.cli.artifact import artifact_group
from labvault.cli.show import show
from labvault.cli.search import search_cmd
from labvault.cli.trash import trash_group
from labvault.cli.stats import stats_cmd
from labvault.cli.export import export_table_cmd, pack_cmd
from labvault.cli.diff import diff_cmd
from labvault.cli.config import config_cmd
from labvault.cli.doctor import doctor_cmd
from labvault.cli.watch import watch_cmd

console = Console()

@click.group()
@click.version_option()
def cli():
    """LabVault - Local-first research & versioning platform."""
    pass

@cli.command("init")
@click.argument("path", default=".")
def init(path: str):
    """Initialize a new vault in the given directory."""
    vault = Vault.init(path)
    console.print(f"[bold green]Vault initialized at:[/] {vault.path}")

# Register command groups
cli.add_command(project_group)
cli.add_command(experiment_group)
cli.add_command(run_group)
cli.add_command(artifact_group)
cli.add_command(show)
cli.add_command(search_cmd)
cli.add_command(trash_group)
cli.add_command(stats_cmd)
cli.add_command(export_table_cmd)
cli.add_command(pack_cmd)
cli.add_command(diff_cmd)
cli.add_command(config_cmd)
cli.add_command(doctor_cmd)
cli.add_command(watch_cmd)

@cli.command("ui")
@click.option("--port", default=None, type=int, help="Port to serve the web UI on.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def ui(port: int | None, vault_path: str):
    """Launch the web dashboard."""
    import uvicorn
    import os

    # Read port from config if not provided
    if port is None:
        from labvault.core.config import get_config_value
        port = get_config_value("ui.port") or 5555

    os.environ["LABVAULT_PATH"] = str(vault_path)
    console.print(f"[bold green]Starting LabVault UI[/] at [cyan]http://localhost:{port}[/]")
    console.print(f"[dim]API docs at http://localhost:{port}/docs[/]")
    uvicorn.run("labvault.web.app:create_app", host="0.0.0.0", port=port, factory=True)

if __name__ == "__main__":
    cli()

