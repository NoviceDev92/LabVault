import click
from rich.console import Console

from labvault.core.vault import Vault
from labvault.cli.project import project_group
from labvault.cli.experiment import experiment_group
from labvault.cli.run import run_group
from labvault.cli.artifact import artifact_group
from labvault.cli.show import show

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

if __name__ == "__main__":
    cli()
