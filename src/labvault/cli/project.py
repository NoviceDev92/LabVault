import click
from rich.console import Console
from rich.table import Table
from pathlib import Path

from labvault.core.vault import Vault
from labvault.core.project import create_project, get_project, list_projects
from labvault.utils.slugify import slugify

console = Console()

@click.group("project")
def project_group():
    """Manage projects."""
    pass

@project_group.command("add")
@click.argument("name")
@click.option("--desc", default=None, help="Project description.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def project_add(name: str, desc: str | None, vault_path: str):
    """Create a new project."""
    vault = Vault.init(vault_path)
    try:
        project = create_project(vault, name, desc)
        console.print(f"[bold green]Created project:[/] {project.name} [dim]({project.slug})[/]")
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise SystemExit(1)

@project_group.command("ls")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def project_ls(vault_path: str):
    """List all projects."""
    vault = Vault.init(vault_path)
    projects = list_projects(vault)

    if not projects:
        console.print("[dim]No projects found. Create one with:[/] labvault project add <name>")
        return

    table = Table(title="Projects", show_lines=True)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Name", style="bold cyan")
    table.add_column("Slug", style="green")
    table.add_column("Description")

    for p in projects:
        table.add_row(str(p.id), p.name, p.slug, p.description or "-")

    console.print(table)
