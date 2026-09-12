import click
from rich.console import Console
from rich.table import Table

from labvault.core.vault import Vault
from labvault.core.project import get_project
from labvault.core.experiment import create_experiment, list_experiments

console = Console()

@click.group("experiment")
def experiment_group():
    """Manage experiments."""
    pass

@experiment_group.command("add")
@click.argument("project_slug")
@click.argument("name")
@click.option("--desc", default=None, help="Experiment description.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def experiment_add(project_slug: str, name: str, desc: str | None, vault_path: str):
    """Create a new experiment under a project."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    try:
        exp = create_experiment(vault, project, name, desc)
        console.print(
            f"[bold green]Created experiment:[/] {exp.name} [dim]({exp.slug})[/] "
            f"under [cyan]{project.name}[/]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)

@experiment_group.command("ls")
@click.argument("project_slug")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def experiment_ls(project_slug: str, vault_path: str):
    """List all experiments in a project."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiments = list_experiments(vault, project)

    if not experiments:
        console.print(f"[dim]No experiments in '{project.name}'. Create one with:[/] labvault experiment add {project_slug} <name>")
        return

    table = Table(title=f"Experiments in '{project.name}'", show_lines=True)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Name", style="bold cyan")
    table.add_column("Slug", style="green")
    table.add_column("Description")

    for e in experiments:
        table.add_row(str(e.id), e.name, e.slug, e.description or "-")

    console.print(table)
