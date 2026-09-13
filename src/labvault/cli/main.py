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

@cli.command("ui")
@click.option("--port", default=5555, help="Port to serve the web UI on.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def ui(port: int, vault_path: str):
    """Launch the web dashboard."""
    import uvicorn
    import os
    os.environ["LABVAULT_PATH"] = str(vault_path)
    console.print(f"[bold green]Starting LabVault UI[/] at [cyan]http://localhost:{port}[/]")
    console.print(f"[dim]API docs at http://localhost:{port}/docs[/]")
    uvicorn.run("labvault.web.app:create_app", host="0.0.0.0", port=port, factory=True)

if __name__ == "__main__":
    cli()
