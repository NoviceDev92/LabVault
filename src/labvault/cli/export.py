"""CLI commands for exporting experiment tables and packing runs."""

import click
from pathlib import Path
from rich.console import Console

from labvault.core.vault import Vault
from labvault.core.project import get_project
from labvault.core.experiment import get_experiment
from labvault.core.run import get_run, list_runs
from labvault.core.export import export_table, pack_run_zip

console = Console()


@click.command("export-table")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.option("--format", "fmt", default="csv",
              type=click.Choice(["csv", "latex", "markdown", "json"]),
              help="Output format.")
@click.option("--output", "-o", default=None, help="Output file path. Defaults to stdout.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def export_table_cmd(project_slug: str, exp_slug: str, fmt: str,
                     output: str | None, vault_path: str):
    """Export an experiment's results table to CSV, LaTeX, Markdown, or JSON."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found.")
        raise SystemExit(1)

    result = export_table(vault, experiment, fmt)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        console.print(f"[bold green]✓[/] Exported {fmt.upper()} table to [cyan]{output}[/]")
    else:
        console.print(result)


@click.command("pack")
@click.argument("project_slug")
@click.argument("exp_slug")
@click.argument("version", type=int)
@click.option("--output", "-o", default=None, help="Output ZIP path.")
@click.option("--vault", "vault_path", default=".", help="Path to vault root.")
def pack_cmd(project_slug: str, exp_slug: str, version: int,
             output: str | None, vault_path: str):
    """Pack a run as a portable ZIP archive."""
    vault = Vault.init(vault_path)
    project = get_project(vault, project_slug)
    if not project:
        console.print(f"[bold red]Error:[/] Project '{project_slug}' not found.")
        raise SystemExit(1)

    experiment = get_experiment(vault, project, exp_slug)
    if not experiment:
        console.print(f"[bold red]Error:[/] Experiment '{exp_slug}' not found.")
        raise SystemExit(1)

    run = get_run(vault, experiment, version)
    if not run:
        console.print(f"[bold red]Error:[/] Run v{version} not found.")
        raise SystemExit(1)

    zip_bytes = pack_run_zip(vault, experiment, run)

    if not output:
        output = f"{exp_slug}_v{version}.zip"

    Path(output).write_bytes(zip_bytes)
    size_kb = len(zip_bytes) / 1024
    console.print(f"[bold green]✓[/] Packed run v{version} → [cyan]{output}[/] ({size_kb:.1f} KB)")
